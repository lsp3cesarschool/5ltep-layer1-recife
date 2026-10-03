"""What to validate, in batches that fit the runner's time limit, and validating it.

The work queue is built once per weekly chain (after the census) and consumed by as many
batches as needed: each batch validates resources until its time budget runs out, and the
next batch continues. A resource enters the queue when:

  new       it was never validated;
  schema    the schema it is validated against changed (or appeared);
  changed   the portal says it changed: URL, CKAN last_modified/size, or the server's ETag,
            Last-Modified or Content-Length (HEAD request, no download);
  error     the last attempt failed;
  reader    the last result came from a reader that has since learned more: "not tabular" before
            the kind was recorded (a zip of spreadsheets was "without CSV members" then), or a table
            whose other formats were never compared with it;
  rotation  it was last validated more than ROTATION_DAYS ago (a full re-check, since some
            servers give no change signal at all).
"""

import logging
import multiprocessing
import shutil
import tempfile
import time
from concurrent.futures import FIRST_COMPLETED, Future, ProcessPoolExecutor, ThreadPoolExecutor, wait
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

from src import ckan, config, drift, safety, schemas, tabular, validate

logger = logging.getLogger(__name__)
ORDER = {"new": 0, "schema": 1, "changed": 2, "error": 3, "reader": 4, "rotation": 5}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def tables_of(census: dict):
    for ds in census["datasets"]:
        for t in ds["tables"]:
            yield ds["name"], t


def reason_for(dataset: str, t: dict, prev: dict | None, now: datetime, head=ckan.head) -> str | None:
    if not prev:
        return "new"
    _, schema = schemas.select(dataset, t["id"])
    if schemas.fingerprint(schema) != prev.get("schema_fingerprint"):
        return "schema"
    ck = prev.get("ckan") or {}
    if t["url"] != ck.get("url") or t.get("last_modified") != ck.get("last_modified") or t.get("size") != ck.get("size"):
        return "changed"
    if prev.get("status") == "error":
        return "error"
    if (prev.get("status") == "not-tabular" and not prev.get("not_tabular_kind")) \
            or (t.get("distributions") and prev.get("status") == "ok" and "distributions" not in prev):
        return "reader"
    validated = prev.get("validated_at") or prev.get("checked_at")
    if not validated or datetime.fromisoformat(validated) < now - timedelta(days=config.ROTATION_DAYS):
        return "rotation"
    before = prev.get("http") or {}
    if any(before.get(k) for k in ("etag", "last_modified", "content_length")):
        h = head(t["url"])
        if any(h.get(k) and before.get(k) and h.get(k) != before.get(k) for k in ("etag", "last_modified", "content_length")):
            return "changed"
    return None


def plan(census: dict, validation: dict, now: datetime | None = None, head=ckan.head) -> list[dict]:
    now = now or datetime.now(timezone.utc)
    queue = []
    for ds in census["datasets"]:
        if ds.get("hold"):
            # Its dictionary (or a header) did not answer and there is no earlier reading: which schema
            # its files follow is unknown. They wait (pending) for the next run, instead of being
            # checked against a weaker schema and counted as if that were the portal's documentation.
            continue
        for t in ds["tables"]:
            prev = validation.get(t["id"])
            reason = reason_for(ds["name"], t, prev, now, head)
            if reason:
                queue.append({"id": t["id"], "dataset": ds["name"], "reason": reason,
                              "since": (prev or {}).get("validated_at") or ""})
    return sorted(queue, key=lambda q: (ORDER[q["reason"]], q["since"]))


def validate_one(dataset: str, t: dict, prev: dict | None, local: dict | None = None) -> tuple[dict, dict | None, list[dict]]:
    """(validation entry, observed schema, drift events) for one resource. `local`: the file already
    downloaded (`_fetch`: its folder and digest, or the error of the download); without it the file
    is read over the network."""
    kind, schema = schemas.select(dataset, t["id"])
    fp = schemas.fingerprint(schema)
    entry = {"dataset": dataset, "checked_at": now_iso(), "schema_kind": kind, "schema_fingerprint": fp,
             "ckan": {"url": t["url"], "last_modified": t.get("last_modified"), "size": t.get("size")}}
    started = time.monotonic()
    failures_before = ckan.failures_snapshot()
    entry["host"] = urlparse(t.get("url") or "").hostname
    try:
        tables, digest = _read(t["url"], schema, local)
    except tabular.NotTabular as exc:
        # "no-tables": a container of documents or maps, not tabular data (left out of the universe);
        # "html"/"pdf": the link returns a page or a document instead of the table (a failure).
        return {**entry, "status": "not-tabular", "not_tabular_kind": exc.kind, "error": str(exc)[:300],
                "validated_at": entry["checked_at"]}, None, []
    except Exception as exc:
        logger.warning("%s: %s", t["id"], safety.error_text(exc, 300))
        return {**entry, "status": "error", "error": safety.error_text(exc, 300),
                **({k: prev[k] for k in ("header", "summary", "validated_at", "sha256", "pass_history", "first_seen")
                    if k in prev} if prev else {})}, None, []
    tables_ok = [x for x in tables if not x.get("empty")]
    summary = validate.summarise(tables, schema)
    entry["timing"] = digest.get("timing")
    if t.get("distributions") and tables_ok:
        entry["distributions"] = check_distributions(t["distributions"], tables_ok[0]["header"])
    failed = (local or {}).get("failures") or _delta(failures_before)
    if failed:
        entry["network_failures"] = failed
    # Memory of the file: when it was first seen, and whether it conformed in its last validations.
    # (records written before first_seen existed date from their first check, not from today)
    entry["first_seen"] = next((prev[k] for k in ("first_seen", "validated_at", "checked_at") if prev and prev.get(k)),
                               entry["checked_at"])
    history = list((prev or {}).get("pass_history") or [])
    if summary.get("conformance"):
        history = (history + [[entry["checked_at"][:10], summary["conformance"]["pass"]]])[-12:]
    entry["pass_history"] = history
    entry.update(status="ok" if tables_ok else "empty", validated_at=entry["checked_at"],
                 # download and validation (a file downloaded beforehand: its download time added)
                 seconds=round(time.monotonic() - started
                               + ((digest.get("timing") or {}).get("download_s", 0) if local else 0), 1),
                 sha256=digest.get("sha256"),
                 bytes=digest.get("bytes"), kind=digest.get("kind"), http=digest.get("http"),
                 summary=summary)
    if not tables_ok:
        return entry, None, []
    first = tables_ok[0]
    entry["header"] = first["header"]
    observed = {
        **first["observed"],
        "x5ltep": {"status": "observed", "observed_at": entry["checked_at"], "sha256": entry["sha256"],
                   "encoding": first["encoding"], "delimiter": first["delimiter"],
                   "sample_rows": min(first["rows"], config.SAMPLE_ROWS), "tables": len(tables_ok),
                   "distinct_headers": summary["distinct_headers"],
                   **({"members_with_other_headers": sorted(x["member"] for x in tables_ok
                                                            if x["header"] != first["header"])[:50]}
                      if summary["distinct_headers"] > 1 else {})},
    }
    previous = schemas.load(schemas.path(dataset, t["id"], "observed"))
    events = drift.compare(dataset, t, previous, observed)
    return entry, observed, events


def _delta(before: dict) -> dict:
    return {k: n - before.get(k, 0) for k, n in ckan.failures_snapshot().items() if n > before.get(k, 0)}


def _read(url: str, schema: dict | None, local: dict | None = None) -> tuple[list[dict], dict]:
    """(results per table, digest). A file downloaded beforehand is read from disk. Otherwise (too
    large for its share of the disk) a zip is validated while it downloads; its tables are then put in
    the order a zip read from disk gives, so that the first header, the one compared for drift, does
    not depend on how the file was read. A zip that cannot be read as a stream (an unusual layout) is
    downloaded whole and read from disk."""
    from stream_unzip import TruncatedDataError, UnzipError

    if local and "error" in local:
        raise local["error"]
    if local:
        with tabular.open_local(Path(local["dir"]) / "resource", local["digest"]) as src:
            tables = [validate.check_table(tb, schema) for tb in src.tables]
        return sorted(tables, key=lambda x: tabular.member_order(x.get("member"))), src.digest

    def read(stream_zip: bool):
        with tabular.open_resource(url, stream_zip=stream_zip) as src:
            tables = [validate.check_table(tb, schema) for tb in src.tables]
        return sorted(tables, key=lambda x: tabular.member_order(x.get("member"))), src.digest

    try:
        return read(True)
    except UnzipError as exc:
        if isinstance(exc, TruncatedDataError):
            raise                   # the download was cut short: a network failure, asked again later
        logger.info("%s could not be read as a stream (%s); downloading it whole", url, exc)
        return read(False)


def check_distributions(distributions: list[dict], header: list[str]) -> list[dict]:
    """The same table in other formats: are its columns the same as in the one validated in full?"""
    from src import dictionaries

    norm = lambda names: {dictionaries.norm(n) for n in names if n}
    out = []
    for d in distributions:
        rec = {"id": d["id"], "format": d.get("format"), "name": d.get("name")}
        try:
            fmt, cols = tabular.peek_header(d["url"])
            missing = sorted(norm(header) - norm(cols))
            extra = sorted(norm(cols) - norm(header))
            rec.update(status="ok", read_as=fmt, same_columns=not missing and not extra,
                       missing=missing[:30], extra=extra[:30])
        except tabular.NotTabular as exc:
            rec.update(status="not-tabular", reason=str(exc)[:200])
        except Exception as exc:
            rec.update(status="error", reason=safety.error_text(exc, 160))
        out.append(rec)
    return out


class _Inline:
    """An executor that runs each task at once, in this process (one worker: no process to start)."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def submit(self, fn, *args) -> Future:
        fut: Future = Future()
        try:
            fut.set_result(fn(*args))
        except Exception as exc:
            fut.set_exception(exc)
        return fut


def _worker_init() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def _fetch(url: str, limit: float) -> dict:
    """Download one file to a folder of its own (in a thread of the main process). Returns the folder
    and the digest, or the error, which validate_one turns into the entry."""
    folder = tempfile.mkdtemp(prefix="l1-")
    before = ckan.failures_snapshot()
    try:
        return {"dir": folder, "digest": tabular.fetch(url, Path(folder), limit), "failures": _delta(before)}
    except Exception as exc:
        shutil.rmtree(folder, ignore_errors=True)
        return {"error": exc, "failures": _delta(before)}


def _size(t: dict) -> int:
    try:
        return int(t.get("size") or 0)
    except (TypeError, ValueError):
        return 0


def on_disk(t: dict, workers: int) -> bool:
    """A spreadsheet or Parquet file read over the network goes to the runner's disk whole: one that
    may not fit beside others (unknown size, or more than its share of the disk) is validated alone."""
    if t.get("candidate") not in ("parquet", "xlsx", "xls", "ods"):
        return False
    size = _size(t)
    return not size or size > config.MAX_ZIP_BYTES / workers


def run_batch(census: dict, queue: list[dict], validation: dict, minutes: float, on_progress=None,
              workers: int | None = None, executor=None) -> dict:
    """Validate queued resources until the budget ends. Returns ids done, observed schemas, drift.

    Each file is downloaded whole to the disk, at most one at a time from each server (03/10/2026:
    three connections at once to ANEEL's server made each of them 5 to 10 times slower, and the three
    together slower than one), and validated from there by one of VALIDATE_WORKERS processes (the
    validation is CPU-bound) while the next file downloads. A file larger than its share of the disk
    is read over the network by its process, which holds its server's connection meanwhile.

    `on_progress(out)` is called when a resource starts and when it ends, so that what was done
    survives a job killed in the middle of a very large file.
    """
    workers = max(1, workers or config.VALIDATE_WORKERS)
    share = config.MAX_ZIP_BYTES / (workers + 1)      # files on disk: at most workers + 1 of them
    tables = {t["id"]: (ds, t) for ds, t in tables_of(census)}
    deadline = time.monotonic() + minutes * 60
    done, observed, events = [], {}, []
    pending = list(queue)
    fetching, ready, running = {}, [], {}           # downloading / on disk, waiting / validating
    busy = set()                                    # servers with a connection open

    def progress() -> None:
        if on_progress:
            started = [r[0]["id"] for r in fetching.values()] + [r[0]["id"] for r in ready] \
                + [r[0]["id"] for r in running.values()]
            on_progress({"done": done + started, "observed": observed, "drift": events})

    def mark(item: dict, dataset: str, t: dict) -> dict | None:
        prev = validation.get(t["id"])
        # Marked before it starts: if the job is killed in the middle of a very large file, the
        # next batch moves on instead of starting the same file again, and the file comes back
        # next week (reason "error").
        validation[t["id"]] = {**(prev or {"dataset": dataset}), "status": "error", "checked_at": now_iso(),
                               "error": "did not finish within the batch time limit", "reason": item["reason"]}
        return prev

    def finish(item: dict, dataset: str, t: dict, prev: dict | None, result) -> None:
        try:
            entry, obs, ev = result()
        except Exception as exc:          # the worker itself failed (e.g. out of memory)
            logger.warning("%s: %s", t["id"], safety.error_text(exc, 300))
            entry, obs, ev = ({"dataset": dataset, "checked_at": now_iso(), "status": "error",
                               "error": safety.error_text(exc, 300),
                               **({k: prev[k] for k in ("header", "summary", "validated_at", "sha256",
                                                        "pass_history", "first_seen") if k in prev}
                                  if prev else {})}, None, [])
        validation[t["id"]] = {**entry, "reason": item["reason"]}
        if obs:
            observed[(dataset, t["id"])] = obs
        events.extend(ev)
        done.append(item["id"])

    if executor is None:
        executor = _Inline() if workers == 1 else ProcessPoolExecutor(
            workers, mp_context=multiprocessing.get_context("spawn"), initializer=_worker_init)
    try:
        with executor as pool, ThreadPoolExecutor(workers) as downloads:
            while True:
                alone_running = any(r[5] for r in running.values())
                # files on disk go to a free process
                while ready and len(running) < workers and not alone_running:
                    item, dataset, t, prev, local = ready.pop(0)
                    logger.info("validating %s/%s (%s)", dataset, t["name"], item["reason"])
                    running[pool.submit(validate_one, dataset, t, prev, local)] = \
                        (item, dataset, t, prev, None, False, local["dir"])
                # new files, one connection per server
                i = 0
                while i < len(pending) and time.monotonic() <= deadline and not alone_running:
                    item = pending[i]
                    if item["id"] not in tables:
                        done.append(pending.pop(i)["id"])     # gone from the portal since the census
                        continue
                    dataset, t = tables[item["id"]]
                    host = urlparse(t.get("url") or "").hostname
                    if host in busy:
                        i += 1
                        continue
                    if item.get("direct") or _size(t) > share:
                        alone = on_disk(t, workers)
                        if alone and (running or ready or fetching):
                            break                             # waits for the disk to be free
                        if len(running) >= workers:
                            i += 1
                            continue
                        pending.pop(i)
                        prev = mark(item, dataset, t)
                        logger.info("validating %s/%s over the network (%s)", dataset, t["name"], item["reason"])
                        running[pool.submit(validate_one, dataset, t, prev)] = (item, dataset, t, prev, host, alone, None)
                        busy.add(host)
                        progress()
                        if alone:
                            break
                        continue
                    on_disk_files = len(fetching) + len(ready) + sum(1 for r in running.values() if r[6])
                    if on_disk_files > workers or len(fetching) >= workers:
                        break
                    pending.pop(i)
                    prev = mark(item, dataset, t)
                    logger.info("downloading %s/%s (%s)", dataset, t["name"], item["reason"])
                    fetching[downloads.submit(_fetch, t["url"], share)] = (item, dataset, t, prev, host)
                    busy.add(host)
                    progress()
                if not (fetching or ready or running):
                    break
                finished, _ = wait(list(fetching) + list(running), return_when=FIRST_COMPLETED)
                for fut in finished:
                    if fut in fetching:
                        item, dataset, t, prev, host = fetching.pop(fut)
                        busy.discard(host)
                        local = fut.result()
                        if isinstance(local.get("error"), tabular.TooLarge):
                            # larger than the server said, or it said nothing: read over the network
                            pending.insert(0, {**item, "direct": True})
                            if prev:
                                validation[t["id"]] = prev
                            else:
                                validation.pop(t["id"], None)
                        elif "error" in local:
                            finish(item, dataset, t, prev, lambda: validate_one(dataset, t, prev, local))
                        else:
                            ready.append((item, dataset, t, prev, local))
                        continue
                    item, dataset, t, prev, host, _, folder = running.pop(fut)
                    busy.discard(host)
                    if folder:
                        shutil.rmtree(folder, ignore_errors=True)
                    finish(item, dataset, t, prev, fut.result)
                progress()
    finally:
        for r in ready:                             # left on disk only when interrupted
            shutil.rmtree(r[4]["dir"], ignore_errors=True)
    return {"done": done, "observed": observed, "drift": events}

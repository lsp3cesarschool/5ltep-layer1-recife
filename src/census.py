"""Census: every dataset of the portal on the schema maturity scale.

Only the CKAN API and the dictionary files are read here (no data file). For each tabular
resource (a CSV, or a zip that may hold CSVs) the census records what the portal declares
about its structure, and its level:

  0  no dictionary or schema is associated with the resource
  1  a dictionary readable only by people (PDF, HTML, or a field list written in the resource's
     description), or a machine-readable one that cannot be processed (an HTML page behind
     the link, malformed JSON...)
  2  a machine-readable dictionary (CSV, JSON, XML, XLSX) that the toolkit reads
  3  types exposed through the API in a standard form: a Table Schema attached to the resource,
     or DataStore fields with real types (a DataStore whose fields are all "text" declares nothing)
  4  level 3 and the file conforms to the declared schema (set by the report, after validation)

The maturity level describes the portal; it does not change when the toolkit extracts a
schema from a PDF (that makes conformance checkable, which is reported separately).
"""

import logging
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import requests
import urllib3

from src import ckan, config, dictionaries, drift, linker, safety, schemas, tabular, types_map

logger = logging.getLogger(__name__)
MANAGED_KINDS = ("attached", "declared", "described", "datastore")   # written by the census; others are not touched


def _type_findings(fields: list[dict]) -> dict:
    spellings = Counter((f.get("type") or "").strip() for f in fields)
    unmapped, dates, dates_with_format = [], 0, 0
    for f in fields:
        ts_type, extra, note = types_map.map_type(f.get("type") or "")
        if note and note.startswith(("declared type not recognised", "type not declared")):
            unmapped.append((f.get("type") or "").strip())
        if ts_type in ("date", "datetime"):
            dates += 1
            dates_with_format += "format" in extra
    return {"type_spellings": dict(spellings), "unmapped_types": sorted(set(unmapped)),
            "fields_untyped": sum(1 for f in fields if not (f.get("type") or "").strip()),
            "date_fields": dates, "date_fields_with_format": dates_with_format}


def _download_error_kind(exc: Exception) -> str:
    """'unreachable' when the server did not answer (no connection, a timeout, a download cut short,
    a 5xx): a fact about that moment, asked again later, never a finding about the dictionary.
    'download-failed' for every answer that is the portal's (404, a redirect loop, a bad
    certificate, an invalid address): a broken link."""
    status = getattr(getattr(exc, "response", None), "status_code", None)
    if status is not None:
        return "unreachable" if status >= 500 else "download-failed"
    if isinstance(exc, requests.exceptions.SSLError):
        return "download-failed"
    if isinstance(exc, (requests.ConnectionError, requests.Timeout, requests.exceptions.ChunkedEncodingError,
                        urllib3.exceptions.ProtocolError)):
        return "unreachable"
    return "download-failed"


class _Breaker:
    """Stops asking the file server once it stopped answering (UNREACHABLE_STREAK failures in a row):
    each request that times out costs minutes of retries, and a whole survey (Recife, 03/10/2026)
    spent almost five hours waiting for a server that was down. What was not asked is asked again in
    the retry rounds, each of which starts by probing the server again."""

    def __init__(self):
        self.misses, self.lock = 0, threading.Lock()

    def is_open(self) -> bool:
        return self.misses >= config.UNREACHABLE_STREAK

    def record(self, answered: bool) -> None:
        with self.lock:
            self.misses = 0 if answered else self.misses + 1

    def reset(self) -> None:
        with self.lock:
            self.misses = 0


BREAKER = _Breaker()
NOT_ASKED = "not asked: the file server stopped answering in this survey"
HEADER_DEADLINE = [float("inf")]   # monotonic time after which no header is read (set by `run`)


def unreachable(ds: dict) -> list[str]:
    """Ids of the dataset's dictionaries, and of its files whose header was needed for the link, whose
    server did not answer in this survey: the link to a dictionary is not known without them."""
    return ([d["id"] for d in ds.get("dictionaries") or [] if d.get("error_kind") == "unreachable"]
            + [t["id"] for t in ds.get("tables") or [] if t.get("header_unreachable")])


def read_dictionary(res: dict) -> tuple[dict, dictionaries.Dictionary | None]:
    fmt = (res.get("format") or "").upper().strip(". ")
    entry = {"id": res["id"], "name": res.get("name") or "", "format": fmt, "url": res.get("url"),
             "kind": dictionaries.kind(fmt)}
    if entry["kind"] == "other" and (res.get("url") or "").lower().split("?")[0].endswith(".pdf"):
        entry["format"], entry["kind"] = "PDF", "human"
    if entry["kind"] == "machine" or entry["format"] == "PDF":
        if BREAKER.is_open():
            entry.update(readable=False, error=NOT_ASKED, error_kind="unreachable")
            return entry, None
        try:
            data, sha = ckan.fetch_bytes(res["url"], config.MAX_DICTIONARY_BYTES)
        except ValueError as exc:
            BREAKER.record(True)
            entry.update(readable=False, error=str(exc), error_kind="too-large")
            return entry, None
        except Exception as exc:
            kind = _download_error_kind(exc)
            BREAKER.record(kind != "unreachable")
            entry.update(readable=False, error=safety.error_text(exc, 160), error_kind=kind)
            return entry, None
        BREAKER.record(True)
        entry.update(sha256=sha, bytes=len(data))
        if entry["format"] == "PDF":
            if data[:5] != b"%PDF-":
                entry.update(readable=False, error="the link does not return a PDF", error_kind="html-page"
                             if data.lstrip()[:15].lower().startswith((b"<!doctype", b"<html")) else "malformed")
            return entry, None
        d = dictionaries.read(data, fmt)
        entry.update(readable=d.readable, reader=d.reader, error=d.error, error_kind=d.error_kind,
                     parts=[{"label": p.label, "fields": len(p.fields)} for p in d.parts],
                     declared_resource_ids=d.declared_resource_ids, declared_datasets=d.declared_datasets)
        if d.readable:
            entry.update(_type_findings([f for p in d.parts for f in p.fields]))
        return entry, d
    entry["readable"] = False
    return entry, None


def _write(dataset: str, t: dict, kind: str, schema: dict, written: set, events: list) -> None:
    """Write a schema the portal declares; a change from the committed one is a declared drift."""
    p = schemas.path(dataset, t["id"], kind)
    events += drift.compare_declared(dataset, t, kind, schemas.load(p), schema)
    schemas.write(p, schema)
    written.add(p)


FORMAT_WORDS = {"csv", "tsv", "txt", "json", "xml", "xlsx", "xls", "ods", "parquet", "zip", "formato", "format",
                "arquivo", "file", "dados", "data"}


def _table_key(name: str) -> tuple:
    return tuple(sorted(w for w in dictionaries.norm(name).split() if w not in FORMAT_WORDS))


def group_distributions(tables: list[dict]) -> list[dict]:
    """The same table published in several formats ("Autos de infração" as CSV, JSON and XML;
    "auto-infracao.csv" and "auto-infracao.parquet") becomes one table: the preferred format is
    validated in full and the others are listed as its distributions (only their columns are
    checked). A group needs one resource per format; otherwise the resources stay separate tables
    (several CSVs with the same name are different files)."""
    buckets: dict[tuple, list[dict]] = {}
    order: list[tuple] = []
    for t in tables:
        key = _table_key(t["name"]) or ("__id__", t["id"])
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append(t)
    out = []
    for key in order:
        items = buckets[key]
        formats = [i["candidate"] for i in items]
        if len(items) > 1 and len(set(formats)) == len(formats):
            items = sorted(items, key=lambda i: tabular.PRIORITY.get(i["candidate"], 99))
            primary = dict(items[0])
            primary["distributions"] = [{"id": i["id"], "name": i["name"], "format": i["candidate"], "url": i["url"]}
                                        for i in items[1:]]
            out.append(primary)
        else:
            out.extend(items)
    return out


def level_of(resource: dict, dict_entry: dict | None) -> int:
    if resource.get("attached") or (resource.get("datastore") or {}).get("typed"):
        return 3
    if dict_entry is None:
        return 1 if resource.get("described") else 0
    if dict_entry["kind"] == "machine" and dict_entry.get("readable"):
        return 2
    return 1


def peek_header(t: dict) -> tuple[list[str] | None, str | None]:
    """(the column names of a table, or None; why not: "unreachable" when the server did not answer,
    "time" past SURVEY_HEADER_MAX_MINUTES). No row is kept. A file that cannot be read as a table is
    linked by its header from its first validation on; one whose server did not answer is asked again
    (see `run`). A text file is read only to its first line; a zip, a spreadsheet or a Parquet is
    downloaded whole (its columns are only known that way; Recife's file server ignores byte ranges)."""
    if time.monotonic() > HEADER_DEADLINE[0]:
        return None, "time"
    if BREAKER.is_open():
        return None, "unreachable"
    try:
        h = tabular.peek_header(t["url"], rows=0)[1] or None
    except Exception as exc:
        answered = _download_error_kind(exc) != "unreachable"
        BREAKER.record(answered)
        logger.info("header of %s not read in the survey: %s", t["id"], safety.error_text(exc, 160))
        return None, None if answered else "unreachable"
    BREAKER.record(True)
    return h, None


def _cost(t: dict) -> tuple[int, int]:
    """Cheapest header first: a text file is read to its first line, anything else whole."""
    try:
        size = int(t.get("size") or 0)
    except (TypeError, ValueError):
        size = 0
    return (0 if t["candidate"] == "csv" else 1, size)


def census_dataset(pkg: dict, portal_url: str, headers: dict[str, list[str]], written: set, events: list) -> dict:
    res_all = pkg.get("resources") or []
    dict_res = [r for r in res_all if dictionaries.is_dictionary(r)]
    data_res = [r for r in res_all if r not in dict_res]
    dicts, parsed = [], {}
    for r in dict_res:
        entry, d = read_dictionary(r)
        dicts.append(entry)
        if d is not None:
            parsed[r["id"]] = d
    tables = []
    for r in data_res:
        cand = tabular.is_candidate(r)
        if not cand:
            continue
        t = {"id": r["id"], "name": r.get("name") or "", "format": (r.get("format") or "").upper(),
             "url": r.get("url"), "candidate": cand, "last_modified": r.get("last_modified") or r.get("metadata_modified"),
             "size": r.get("size"), "attached": False, "datastore": None, "described": 0}
        described = dictionaries.from_description(r.get("description") or "")
        described_from = r["id"]
        if not described:
            # The same data in another format (XML, JSON, HTML) may carry the field list the CSV lacks.
            sibling = next((x for x in data_res if x is not r and linker.jaccard(x.get("name") or "", r.get("name") or "") >= 0.99
                            and dictionaries.from_description(x.get("description") or "")), None)
            if sibling:
                described = dictionaries.from_description(sibling.get("description") or "")
                described_from = sibling["id"]
        if r.get("schema"):
            attached = schemas.from_attached(r["schema"])
            t["attached"] = attached is not None
            if attached:
                _write(pkg["name"], t, "attached", attached, written, events)
        if r.get("datastore_active") and config.CHECK_DATASTORE:
            ds_fields = ckan.datastore_fields(portal_url, r["id"])
            if ds_fields is not None:
                ds_schema = schemas.from_datastore(ds_fields)
                t["datastore"] = {"fields": len(ds_fields), "typed": ds_schema is not None}
                if ds_schema:
                    _write(pkg["name"], t, "datastore", ds_schema, written, events)
        tables.append(t)
        if described:
            t["described"] = len(described)
            t["described_from"] = described_from
            t["_described"] = described

    tables = group_distributions(tables)
    link_input = [{"id": d["id"], "name": d["name"], "declared_resource_ids": d.get("declared_resource_ids"),
                   "parts": [{"label": p.label, "names": [f["name"] for f in p.fields]} for p in parsed[d["id"]].parts]
                   if d["id"] in parsed and parsed[d["id"]].parts else None}
                  for d in dicts]
    # A file never validated has no known header. It is read now (only the columns) where the header
    # decides something in this run, so that the file is checked against the right schema at once:
    # its link to a dictionary, or the oracle of a PDF dictionary (one header is enough). Nothing else
    # is read: a zip is downloaded whole for its columns (Recife: 73 zips, 21 GB, most of them named
    # by their dictionary's own list of resource ids, where the header changes nothing).
    headers = dict(headers)

    def peek(t: dict) -> str | None:
        h, why = peek_header(t)
        if h:
            t["header_peeked"] = headers[t["id"]] = h
        elif why == "time":
            t["header_deferred"] = True   # linked without it; its validation gives it to the next survey
        return why

    links = linker.link(link_input, tables, headers)
    for t in tables:
        if t["id"] not in headers and linker.header_decides(link_input, links.get(t["id"])):
            if peek(t) == "unreachable":
                t["header_unreachable"] = True
    links = linker.link(link_input, tables, headers)
    for d in dicts:
        linked = [t for t in tables if (links.get(t["id"]) or {}).get("dictionary") == d["id"]]
        if d.get("format") == "PDF" and d.get("sha256") and linked and not any(t["id"] in headers for t in linked):
            for t in sorted(linked, key=_cost):
                if peek(t) == "time" or t["id"] in headers:
                    break
    by_id = {d["id"]: d for d in dicts}
    for d in dicts:
        d["linked_resources"] = sorted(rid for rid, l in links.items() if l["dictionary"] == d["id"])
    for d in dicts:
        # a dictionary that cites another dataset's address (e.g. a template copied from it)
        other = [n for n in d.pop("declared_datasets", None) or [] if n not in (pkg["name"], pkg.get("id"))]
        if other:
            d["names_other_dataset"] = other
    broken = linker.broken_declared_links(dicts, {r["id"] for r in res_all})
    for did, missing in broken.items():
        by_id[did]["broken_declared_links"] = missing

    for t in tables:
        lk = links.get(t["id"])
        described = t.pop("_described", None)
        if lk is None and described:
            lk = {"dictionary": None, "part": None, "score": 1.0, "resource_id": t["described_from"],
                  "method": "description" if t["described_from"] == t["id"] else "description-sibling"}
        t["link"] = lk
        dentry = by_id.get(lk["dictionary"]) if lk else None
        t["level"] = level_of(t, dentry)
        if dentry and dentry.get("readable") and dentry["kind"] == "machine":
            part = parsed[dentry["id"]].parts[lk["part"]]
            declared = schemas.from_fields(part.fields, "declared", {
                "kind": "dictionary", "dictionary_id": dentry["id"], "dictionary_name": dentry["name"],
                "url": dentry["url"], "sha256": dentry.get("sha256"), "reader": dentry.get("reader"),
                "part": part.label, "link_method": lk["method"]})
            _write(pkg["name"], t, "declared", declared, written, events)
        elif described:
            _write(pkg["name"], t, "described", schemas.from_fields(described, "described", {
                "kind": "description", "resource_id": t["described_from"]}), written, events)

    levels = [t["level"] for t in tables]
    return {
        "name": pkg["name"], "title": pkg.get("title") or pkg["name"],
        "organization": (pkg.get("organization") or {}).get("title"),
        "url": f"{portal_url}/dataset/{pkg['name']}", "metadata_modified": pkg.get("metadata_modified"),
        "resources_total": len(res_all), "dictionaries": dicts, "tables": tables,
        # a dataset is as verifiable as its least documented table
        "level": min(levels) if levels else None,
    }


def run(validation: dict, packages: list[dict] | None = None, previous: dict | None = None) -> tuple[dict, list[dict]]:
    """(census, declared drift events). `previous` is the last census: a dataset whose dictionary
    server does not answer, even after the retries, keeps its last reading (see below)."""
    portal = config.portal()
    packages = packages if packages is not None else ckan.packages(portal["portal_url"])
    headers = {rid: v["header"] for rid, v in validation.items() if v.get("header")}
    written: set = set()
    events: list = []
    results: dict[int, tuple] = {}
    BREAKER.reset()
    HEADER_DEADLINE[0] = time.monotonic() + config.SURVEY_HEADER_MAX_MINUTES * 60

    def one(pkg: dict):
        # Each dataset has its own sets, merged below: nothing is shared between threads.
        own_written, own_events, t0 = set(), [], time.monotonic()
        ds = census_dataset(pkg, portal["portal_url"], headers, own_written, own_events)
        if time.monotonic() - t0 > 60:
            logger.info("slow dataset %s: %.0f s", pkg["name"], time.monotonic() - t0)
        return ds, own_written, own_events

    # The census is network-bound (API calls, dictionary downloads): several datasets at a time.
    with ThreadPoolExecutor(max_workers=config.CENSUS_WORKERS) as pool:
        for i, res in enumerate(pool.map(one, packages)):
            logger.info("[%d/%d] %s", i + 1, len(packages), res[0]["name"])
            results[i] = res
        # Portals' file servers go down for minutes or hours (Recife, 03/10/2026: 69 dictionaries
        # timed out in one survey and answered again later). A dictionary that did not answer is
        # asked again, with growing pauses, before the survey is written.
        for attempt in range(config.DICTIONARY_RETRY_ROUNDS):
            waiting = [i for i, (ds, _, _) in results.items() if unreachable(ds)]
            if not waiting:
                break
            pause = config.DICTIONARY_RETRY_WAIT_S * 2 ** attempt
            logger.warning("%d dataset(s) with a dictionary whose server did not answer; asking again in %d s",
                           len(waiting), pause)
            time.sleep(pause)
            BREAKER.reset()
            for i, res in zip(waiting, pool.map(one, [packages[i] for i in waiting])):
                results[i] = res
    # Still no answer: the dataset keeps its last reading (marked), and its committed schemas stay.
    # Otherwise the server's absence would read as the portal's: the declared schema removed (a false
    # drift issue), the file checked against a weaker schema, the dataset's level lowered.
    # With no reading yet, its files wait one run ("hold"). Neither lasts: a reading is kept for at
    # most ROTATION_DAYS, and a file waits once; a server that never answers is then the portal's fact.
    before = {d["name"]: d for d in (previous or {}).get("datasets") or []}
    now = datetime.now(timezone.utc)
    kept: set[str] = set()
    datasets = []
    for i in range(len(packages)):
        ds, own_written, own_events = results[i]
        missing = unreachable(ds)
        last = before.get(ds["name"])
        if missing:
            since = (last or {}).get("kept_from") or (previous or {}).get("generated_at")
            if last and not last.get("hold") and since                     and now - datetime.fromisoformat(since) <= timedelta(days=config.ROTATION_DAYS):
                ds = {**last, "kept_from": since, "unreachable": missing}
                kept.add(ds["name"])
            elif last is None:
                ds = {**ds, "unreachable": missing, "hold": True}
            else:
                ds = {**ds, "unreachable": missing}
        datasets.append(ds)
        written |= own_written
        events += own_events
    # Schemas the portal no longer declares are removed, so the Git history shows the change.
    for kind in MANAGED_KINDS:
        for p in config.SCHEMAS.glob(f"*/*.{kind}.json"):
            if p not in written and p.parent.name not in kept:
                rid = p.name.split(".")[0]
                events += drift.compare_declared(p.parent.name, {"id": rid}, kind, schemas.load(p), None)
                p.unlink()
    return {"portal": portal, "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "datasets": datasets}, events

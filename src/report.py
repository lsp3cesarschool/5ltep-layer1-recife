"""Layer 1 summary (for Layer 5), documentation findings, dashboard data and status badge.

Two numbers describe a portal, and they are kept apart on purpose:

- maturity (levels 0-4): how verifiable the structure the portal *declares* is;
- conformance (l1_rate): among the files that can be checked, the share that follows its
  declared schema. l1_pass = l1_rate >= L1_PASS_THRESHOLD is what Layer 5 reads.

The documentation findings measure the dictionaries themselves (formats, unreadable ones and
why, how many spellings of a type, how files and dictionaries are linked, how often they
disagree), recomputed every week, so the numbers in the dissertation come from a commit.
"""

import json
import os
import re
import platform
from collections import Counter
from datetime import datetime, timezone
from statistics import mean
from urllib.parse import urlparse

from src import config, dictionaries, drift, schemas, validate

LEVELS = (0, 1, 2, 3, 4)


def write_json(path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")


def table_level(t: dict, v: dict | None) -> int:
    conf = ((v or {}).get("summary") or {}).get("conformance") or {}
    return 4 if t["level"] == 3 and conf.get("pass") else t["level"]


def _share(n: int, d: int) -> float | None:
    return round(n / d, 4) if d else None


def not_a_table(v: dict | None) -> bool:
    """A resource published as data that holds no table (a zip of PDFs or maps): left out of the
    tabular universe and listed apart. Records before 02/10/2026 only have the message."""
    if not v or v.get("status") != "not-tabular":
        return False
    return v.get("not_tabular_kind") == "no-tables" or "without CSV members" in (v.get("error") or "") \
        or "without tables" in (v.get("error") or "")


def similar_of(record: dict) -> dict:
    """Pairs of alike names (declared -> file); records written before the rename used another key."""
    return (record or {}).get("similar_names") or (record or {}).get("probable_typos") or {}


def similar_name_pairs(census: dict, validation: dict) -> list[dict]:
    """Every pair of alike names, for the dashboard section where people can check them."""
    from src.pdf_extract import similarity

    out = []
    for ds in census["datasets"]:
        for t in ds["tables"]:
            v = validation.get(t["id"]) or {}
            c = (v.get("summary") or {}).get("conformance") or {}
            for declared, column in similar_of(c).items():
                out.append({"dataset": ds["name"], "title": ds["title"], "file": t["name"], "id": t["id"],
                            "declared": declared, "column": column, "schema_kind": v.get("schema_kind"),
                            "similarity": round(similarity(dictionaries.norm(declared), dictionaries.norm(column)), 3)})
    return sorted(out, key=lambda x: (-x["similarity"], x["dataset"], x["declared"]))


def _error_kind(error: str | None) -> str:
    """'HTTP 404', 'timeout', 'connection'... from the message of a failed download."""
    m = re.search(r"\b([45]\d\d) (Client|Server) Error", error or "")
    if m:
        return f"HTTP {m.group(1)}"
    if any(k in (error or "") for k in ("MissingSchema", "InvalidURL", "InvalidSchema")):
        return "no URL"                  # the resource has no usable download address
    if "TooManyRedirects" in (error or ""):
        return "redirect loop"           # the download link redirects to itself
    if "did not finish within the batch" in (error or ""):
        return "batch time limit"
    for key in ("Timeout", "ConnectionError", "SSLError", "ChunkedEncodingError"):
        if key in (error or ""):
            return key
    return "other"


def documentation_findings(census: dict, validation: dict, extraction: dict) -> dict:
    dicts = [d for ds in census["datasets"] for d in ds["dictionaries"]]
    tables = [t for ds in census["datasets"] for t in ds["tables"]]
    machine = [d for d in dicts if d["kind"] == "machine"]
    readable = [d for d in machine if d.get("readable")]
    spellings: Counter = Counter()
    for d in readable:
        spellings.update({k: v for k, v in (d.get("type_spellings") or {}).items()})
    unmapped = sorted({u for d in readable for u in d.get("unmapped_types") or []})
    fields_total = sum(spellings.values())
    fields_unmapped = sum(n for s, n in spellings.items() if s in unmapped or not s)
    dates = sum(d.get("date_fields", 0) for d in readable)
    dates_fmt = sum(d.get("date_fields_with_format", 0) for d in readable)

    checked = [(t, validation[t["id"]]) for t in tables if (validation.get(t["id"]) or {}).get("status") == "ok"]
    confs = [(t, v["summary"]["conformance"]) for t, v in checked if (v.get("summary") or {}).get("conformance")]
    inferred = Counter(k for _, c in confs for f in c.get("inferred_formats", {}).values() for k in f)
    encodings = Counter(e for _, v in checked for e in v["summary"].get("encodings", []))
    delimiters = Counter(d for _, v in checked for d in v["summary"].get("delimiters", []))
    pdf_recs = [r for r in extraction.values() if r.get("deterministic")]
    det_oracles = [r["deterministic"]["oracle"] for r in pdf_recs if r["deterministic"]["oracle"].get("available")]
    llm_oracles = [r["llm"]["oracle"] for r in pdf_recs if (r.get("llm") or {}).get("oracle", {}).get("available")]

    def avg(rows, key):
        vals = [r[key] for r in rows if r.get(key) is not None]
        return round(mean(vals), 4) if vals else None

    return {
        "dictionaries": {
            "total": len(dicts),
            "by_format": dict(Counter(d["format"] or "?" for d in dicts).most_common()),
            "machine_readable": len(machine), "human_readable": sum(d["kind"] == "human" for d in dicts),
            "machine_readable_and_read": len(readable),
            "unreadable_by_reason": dict(Counter(d.get("error_kind") or "other" for d in dicts
                                                 if d["kind"] == "machine" and not d.get("readable")).most_common()),
            "pdf_link_not_a_pdf": sum(d.get("format") == "PDF" and d.get("readable") is False for d in dicts),
            "orphans": sum(not d.get("linked_resources") for d in dicts),
            "declaring_resource_ids": sum(bool(d.get("declared_resource_ids")) for d in dicts),
            "broken_declared_links": sum(bool(d.get("broken_declared_links")) for d in dicts),
            "naming_another_dataset": sum(bool(d.get("names_other_dataset")) for d in dicts),
        },
        "links": {
            "tables": len(tables),
            "by_method": dict(Counter((t.get("link") or {}).get("method", "none") for t in tables).most_common()),
            "fields_listed_in_description": sum(bool(t.get("described")) for t in tables),
        },
        "types": {
            "fields_declared": fields_total,
            "distinct_spellings": len([s for s in spellings if s]),
            "fields_with_recognised_type": _share(fields_total - fields_unmapped, fields_total),
            "unrecognised_spellings": unmapped[:30],
            "top_spellings": dict(spellings.most_common(15)),
            "date_fields": dates, "date_fields_with_declared_format": _share(dates_fmt, dates),
        },
        "files_vs_dictionaries": {
            "checked": len(confs),
            "with_declared_fields_missing": sum(bool(c["missing"]) for _, c in confs),
            "with_undeclared_columns": sum(bool(c["undeclared"]) for _, c in confs),
            "with_spelling_differences": sum(bool(c.get("spelling")) for _, c in confs),
            "with_similar_names": sum(bool(similar_of(c)) for _, c in confs),
            "similar_names": sum(len(similar_of(c)) for _, c in confs),
            "declared_fields_missing": sum(len(c["missing"]) for _, c in confs),
            "formats_inferred_from_data": dict(inferred),
        },
        "files": {
            "validated": len(checked),
            "encodings": dict(encodings), "delimiters": dict(delimiters),
            "with_decode_errors": sum(v["summary"].get("decode_errors", 0) > 0 for _, v in checked),
            "with_ragged_rows": sum(v["summary"].get("ragged_rows", 0) > 0 for _, v in checked),
            "zips_with_several_headers": sum(v["summary"].get("distinct_headers", 1) > 1 for _, v in checked),
            "with_columns_without_name": sum(v["summary"].get("columns_without_name", 0) > 0 for _, v in checked),
            "not_tabular": sum((validation.get(t["id"]) or {}).get("status") == "not-tabular"
                               and not not_a_table(validation.get(t["id"])) for t in tables),
            "not_tables": sum(not_a_table(validation.get(t["id"])) for t in tables),
            "formats": dict(Counter(f for _, v in checked for f in v["summary"].get("formats", ["csv"]))),
            "unreachable_by_reason": dict(Counter(_error_kind((validation.get(t["id"]) or {}).get("error"))
                                                  for t in tables
                                                  if (validation.get(t["id"]) or {}).get("status") == "error").most_common()),
        },
        "pdf_extraction": {
            "pdf_dictionaries_linked": sum(d.get("format") == "PDF" and bool(d.get("linked_resources")) for d in dicts),
            "processed": len(pdf_recs),
            "by_outcome": dict(Counter(r.get("outcome") for r in pdf_recs)),
            "with_similar_names": sum(bool(similar_of(r["deterministic"]["oracle"])) for r in pdf_recs),
            "deterministic": {"with_oracle": len(det_oracles), "recall": avg(det_oracles, "recall"),
                              "precision": avg(det_oracles, "precision"),
                              "exact_match": avg(det_oracles, "exact_match"), "levenshtein": avg(det_oracles, "levenshtein")},
            "llm": {"with_oracle": len(llm_oracles), "recall": avg(llm_oracles, "recall"),
                    "precision": avg(llm_oracles, "precision"),
                    "exact_match": avg(llm_oracles, "exact_match"), "levenshtein": avg(llm_oracles, "levenshtein")},
        },
    }


def with_spelling(d: dict) -> dict:
    """A compared format whose columns differ from the table's only in spelling (Ano Debito / anoDebito)
    is reported as such, as in the validation: a difference of spelling is not a different structure."""
    if d.get("status") != "ok" or d.get("same_columns"):
        return d
    pairs, missing, extra = validate.pair_spelling(d.get("missing") or [], d.get("extra") or [])
    return {**d, "spelling": pairs, "spelling_only": not missing and not extra, "missing": missing, "extra": extra}


def distributions(tables: list[tuple[dict, dict | None]]) -> dict:
    """The same table in other formats: how many could be compared, and whether their columns match."""
    recs = [with_spelling(d) for _, v in tables for d in (v or {}).get("distributions") or []]
    ok = [d for d in recs if d.get("status") == "ok"]
    return {"tables_with_other_formats": sum(1 for t, _ in tables if t.get("distributions")),
            "other_formats": len(recs), "compared": len(ok),
            "same_columns": sum(1 for d in ok if d.get("same_columns")),
            "spelling_only": sum(1 for d in ok if d.get("spelling_only")),
            "different_columns": sum(1 for d in ok if not d.get("same_columns") and not d.get("spelling_only")),
            "not_compared": dict(Counter(d.get("status") for d in recs if d.get("status") != "ok")),
            "by_format": dict(Counter(d.get("format") for d in recs))}


def coverage(tables: list[tuple[dict, dict | None]]) -> dict:
    """From all tabular files to conformant ones, with the reason at every step (the dashboard's funnel)."""
    status = Counter((v or {}).get("status") or "pending" for _, v in tables)
    errors = [(t, v) for t, v in tables if (v or {}).get("status") == "error"]
    ok = [(t, v) for t, v in tables if (v or {}).get("status") == "ok"]
    checked = [(t, v) for t, v in ok if (v.get("summary") or {}).get("conformance")]
    failing = [v["summary"]["conformance"] for _, v in checked if not v["summary"]["conformance"]["pass"]]
    over = lambda c: c["error_rate"] > config.L1_MAX_ERROR_RATE
    return {
        "files": len(tables), "read": len(ok), "empty": status.get("empty", 0),
        "not_tabular": status.get("not-tabular", 0), "not_downloaded": len(errors), "pending": status.get("pending", 0),
        "not_downloaded_by_reason": dict(Counter(_error_kind(v.get("error")) for _, v in errors).most_common()),
        "not_downloaded_by_host": dict(Counter(f"{_error_kind(v.get('error'))} · {urlparse(t.get('url') or '').hostname or '—'}"
                                               for t, v in errors).most_common()),
        "read_without_schema": len(ok) - len(checked), "checked": len(checked),
        "conform": len(checked) - len(failing),
        "fail_missing_fields": sum(bool(c["missing"]) for c in failing),
        "fail_undeclared_columns": sum(bool(c["undeclared"]) for c in failing),
        "fail_cells_over_limit": sum(over(c) for c in failing),
        "fail_only_cells": sum(over(c) and not c["missing"] and not c["undeclared"] for c in failing),
    }


def network(tables: list[tuple[dict, dict | None]]) -> dict:
    """How fast and how reliably each server delivered the files (from the validation records).

    end_to_end_mb_s: bytes over the total time per file (download and validation together, since a
    CSV is validated while it streams); zip_download_mb_s: zips alone, which are downloaded whole
    before they are read (pure network); first_byte_s: median time until the server answered.
    """
    hosts: dict[str, dict] = {}
    for t, v in tables:
        if not v or v.get("status") not in ("ok", "empty", "not-tabular", "error"):
            continue
        h = hosts.setdefault(v.get("host") or urlparse(t.get("url") or "").hostname or "—",
                             {"files": 0, "bytes": 0, "seconds": 0.0, "zip_bytes": 0, "zip_seconds": 0.0,
                              "first_byte": [], "failed_files": 0, "failures": Counter()})
        h["files"] += 1
        if v.get("status") == "error":
            h["failed_files"] += 1
        h["failures"].update(v.get("network_failures") or {})
        if v.get("status") == "error" or not v.get("bytes") or not v.get("seconds"):
            continue
        h["bytes"] += v["bytes"]
        h["seconds"] += v["seconds"]
        timing = v.get("timing") or {}
        if timing.get("first_byte_s") is not None:
            h["first_byte"].append(timing["first_byte_s"])
        if v.get("kind") == "zip" and timing.get("download_s"):
            h["zip_bytes"] += v["bytes"]
            h["zip_seconds"] += timing["download_s"]

    def figures(h: dict) -> dict:
        fb = sorted(h["first_byte"])
        return {"files": h["files"], "failed_files": h["failed_files"], "gb": round(h["bytes"] / 1e9, 2),
                "minutes": round(h["seconds"] / 60, 1),
                "end_to_end_mb_s": round(h["bytes"] / h["seconds"] / 1e6, 2) if h["seconds"] else None,
                "zip_download_mb_s": round(h["zip_bytes"] / h["zip_seconds"] / 1e6, 2) if h["zip_seconds"] else None,
                "first_byte_s_median": fb[len(fb) // 2] if fb else None,
                "request_failures": dict(h["failures"])}

    total = {"files": 0, "bytes": 0, "seconds": 0.0, "zip_bytes": 0, "zip_seconds": 0.0, "first_byte": [],
             "failed_files": 0, "failures": Counter()}
    for h in hosts.values():
        for k in ("files", "bytes", "seconds", "zip_bytes", "zip_seconds", "failed_files"):
            total[k] += h[k]
        total["first_byte"] += h["first_byte"]
        total["failures"].update(h["failures"])
    return {"total": figures(total), "by_host": {k: figures(h) for k, h in sorted(hosts.items(), key=lambda x: -x[1]["bytes"])}}


def drift_baseline(validation: dict) -> dict:
    """Drift needs two observations: the first one of each file is its baseline."""
    seen = [v.get("validated_at") for v in validation.values() if v.get("status") == "ok" and v.get("header")]
    return {"files_with_baseline": len(seen), "first_baseline_at": min(seen) if seen else None,
            "last_observed_at": max(seen) if seen else None}


def build_summary(census: dict, validation: dict, extraction: dict, queue: list) -> dict:
    tables, per_dataset = [], []
    ds_levels: Counter = Counter()
    non_tables = []
    for ds in census["datasets"]:
        non_tables += [(ds, t) for t in ds["tables"] if not_a_table(validation.get(t["id"]))]
        ds = {**ds, "tables": [t for t in ds["tables"] if not not_a_table(validation.get(t["id"]))]}
        lv = [table_level(t, validation.get(t["id"])) for t in ds["tables"]]
        verifiable = [t for t in ds["tables"] if ((validation.get(t["id"]) or {}).get("summary") or {}).get("conformance")]
        ok = [t for t in verifiable if validation[t["id"]]["summary"]["conformance"]["pass"]]
        level = min(lv) if lv else None
        if level is not None:
            ds_levels[level] += 1
        per_dataset.append({"name": ds["name"], "level": level, "tables": len(ds["tables"]),
                            "verifiable": len(verifiable), "conformant": len(ok),
                            "l1_rate": _share(len(ok), len(verifiable))})
        tables += [(t, validation.get(t["id"])) for t in ds["tables"]]
    t_levels = Counter(table_level(t, v) for t, v in tables)
    validated = [(t, v) for t, v in tables if v and v.get("status") in ("ok", "empty", "not-tabular")]
    verifiable = [(t, v) for t, v in tables if ((v or {}).get("summary") or {}).get("conformance")]
    conformant = [(t, v) for t, v in verifiable if v["summary"]["conformance"]["pass"]]
    rate = _share(len(conformant), len(verifiable))
    log = drift.load()
    return {
        "layer": 1, "portal": census["portal"],
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "census_at": census.get("generated_at"),
        "method": config.method_parameters(),
        "environment": {"python": platform.python_version()},
        "datasets": {"total": len(census["datasets"]),
                     "with_tables": sum(1 for d in census["datasets"] if d["tables"]),
                     "by_level": {str(k): ds_levels.get(k, 0) for k in LEVELS}},
        "tables": {"total": len(tables), "by_level": {str(k): t_levels.get(k, 0) for k in LEVELS},
                   "validated": len(validated), "validation_coverage": _share(len(validated), len(tables)),
                   "errors": sum(1 for _, v in tables if (v or {}).get("status") == "error"),
                   "queue_remaining": len(queue)},
        "schema_sources": dict(Counter(v.get("schema_kind") for _, v in verifiable)),
        # Conformance by where the schema came from: DataStore types are often inferred by the portal from
        # the same data, so conformance against them is high by construction; compare like with like.
        "conformance_by_source": {k: {"verifiable": n, "conformant": sum(1 for _, v in conformant if v.get("schema_kind") == k),
                                      "l1_rate": _share(sum(1 for _, v in conformant if v.get("schema_kind") == k), n)}
                                  for k, n in Counter(v.get("schema_kind") for _, v in verifiable).items()},
        "verifiable": len(verifiable), "conformant": len(conformant),
        "l1_rate": rate, "l1_pass": rate is not None and rate >= config.L1_PASS_THRESHOLD,
        "drift": {"observed": sum(e["kind"] == "observed" for e in log),
                  "declared": sum(e["kind"] == "declared" for e in log), **drift_baseline(validation)},
        "coverage": coverage(tables),
        "not_tables": {"count": len(non_tables),
                       "resources": [{"dataset": ds["name"], "id": t["id"], "name": t["name"],
                                      "contents": (validation.get(t["id"]) or {}).get("error", "")[:200]}
                                     for ds, t in non_tables][:200]},
        "distributions": distributions(tables),
        "network": network(tables),
        "findings": documentation_findings(census, validation, extraction),
        "per_dataset": per_dataset,
    }


def history_row(census: dict, validation: dict, summary: dict, previous: dict | None) -> dict:
    """What one weekly chain measured, and what changed since the previous one (a few hundred bytes)."""
    start = census.get("generated_at") or ""
    ids = {t["id"] for ds in census["datasets"] for t in ds["tables"]}
    changed_now = lambda v: (v.get("pass_history") or [[""]])[-1][0] >= start[:10] and len(v.get("pass_history") or []) >= 2
    trans = Counter((tuple(p for _, p in v["pass_history"][-2:])) for rid, v in validation.items()
                    if rid in ids and changed_now(v))
    gone_total = sum(1 for rid in validation if rid not in ids)
    c = summary["coverage"]
    return {
        "at": start, "report_at": summary["generated_at"], "commit": (os.environ.get("GITHUB_SHA") or "")[:7] or None,
        "files": c["files"], "read": c["read"], "checked": c["checked"], "conform": c["conform"],
        "l1_rate": summary["l1_rate"], "not_downloaded": c["not_downloaded"],
        "levels": [summary["tables"]["by_level"][str(k)] for k in LEVELS],
        "dataset_levels": [summary["datasets"]["by_level"][str(k)] for k in LEVELS],
        "fixed": trans.get((False, True), 0), "broken": trans.get((True, False), 0),
        "new_files": sum(1 for rid, v in validation.items() if rid in ids and (v.get("first_seen") or "") >= start),
        "gone_files": max(0, gone_total - (previous or {}).get("gone_total", 0)), "gone_total": gone_total,
        "drift_observed": summary["drift"]["observed"], "drift_declared": summary["drift"]["declared"],
    }


def update_history(census: dict, validation: dict, summary: dict, path=None) -> list[dict]:
    """Append the row of this chain (or replace it, when the same chain reports again)."""
    path = path or config.HISTORY_FILE
    rows = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    if rows and rows[-1]["at"] == census.get("generated_at"):
        rows = rows[:-1]
    rows.append(history_row(census, validation, summary, rows[-1] if rows else None))
    write_json(path, rows)
    return rows


def dashboard_data(census: dict, validation: dict, extraction: dict, summary: dict) -> dict:
    drift_count = Counter(e["resource_id"] for e in drift.load())
    datasets = []
    for ds in census["datasets"]:
        dicts = {d["id"]: d for d in ds["dictionaries"]}
        page = lambda rid: f"{census['portal']['portal_url']}/dataset/{ds['name']}/resource/{rid}" if rid else None
        tables = []
        for t in ds["tables"]:
            v = validation.get(t["id"]) or {}
            s = v.get("summary") or {}
            c = s.get("conformance")
            lk = t.get("link") or {}
            d = dicts.get(lk.get("dictionary"), {})
            tables.append({
                "id": t["id"], "name": t["name"], "level": table_level(t, v), "url": t["url"],
                "dictionary": ({"name": d.get("name"), "format": d.get("format"), "method": lk.get("method"),
                                "readable": d.get("readable"), "error_kind": d.get("error_kind"), "url": d.get("url"),
                                "page": page(d["id"])} if d else
                               {"name": None, "format": "description", "method": lk.get("method"),
                                "page": page(lk.get("resource_id"))} if lk.get("method", "").startswith("description")
                               else None),
                "status": v.get("status"), "validated_at": v.get("validated_at"), "rows": s.get("rows"),
                "schema_kind": v.get("schema_kind"), "error": v.get("error"),
                "encodings": s.get("encodings"), "distinct_headers": s.get("distinct_headers"),
                "conformance": {k: c.get(k) for k in ("pass", "error_rate", "missing", "undeclared", "spelling", "similar_names",
                                                      "declared_fields", "inferred_formats")}
                | {"errors_by_field": {f: {k: e["count"] for k, e in kinds.items()}
                                       for f, kinds in c.get("errors_by_field", {}).items()}} if c else None,
                "drift_events": drift_count.get(t["id"], 0),
                "not_a_table": not_a_table(v),
                "distributions": [with_spelling(d) for d in v.get("distributions") or t.get("distributions") or []],
                # the Table Schemas of this file in the repository (declared, extracted, observed...)
                "schema_files": {k: schemas.path(ds["name"], t["id"], k).relative_to(config.ROOT).as_posix()
                                 for k in schemas.KINDS if schemas.path(ds["name"], t["id"], k).exists()},
            })
        datasets.append({"name": ds["name"], "title": ds["title"], "organization": ds.get("organization"),
                         "url": ds["url"], "level": next((p["level"] for p in summary["per_dataset"]
                                                          if p["name"] == ds["name"]), None),
                         "dictionaries": [{"name": d["name"], "format": d["format"], "kind": d["kind"],
                                           "readable": d.get("readable"), "error_kind": d.get("error_kind"),
                                           "linked": len(d.get("linked_resources") or []), "url": d.get("url"),
                                           "page": page(d["id"])} for d in ds["dictionaries"]],
                         "tables": tables})
    return {"summary": {k: summary[k] for k in ("portal", "generated_at", "census_at", "datasets", "tables",
                                                 "verifiable", "conformant", "l1_rate", "l1_pass", "drift",
                                                 "coverage", "not_tables", "distributions", "network", "schema_sources", "conformance_by_source",
                                                 "findings", "method")},
            "datasets": datasets, "unreadable": unreadable_files(census, validation),
            "pdf": pdf_dictionaries(census, extraction), "drift_events": drift_events(census),
            "similar_names": similar_name_pairs(census, validation),
            "history": json.loads(config.HISTORY_FILE.read_text(encoding="utf-8")) if config.HISTORY_FILE.exists() else []}


def unreadable_files(census: dict, validation: dict) -> list[dict]:
    out = []
    for ds in census["datasets"]:
        for t in ds["tables"]:
            v = validation.get(t["id"]) or {}
            if v.get("status") in ("error", "not-tabular", "empty"):
                out.append({"dataset": ds["name"], "title": ds["title"], "file": t["name"], "id": t["id"],
                            "url": t.get("url"), "host": urlparse(t.get("url") or "").hostname,
                            "status": v["status"],
                            "reason": _error_kind(v.get("error")) if v["status"] == "error"
                            else "not-a-table" if not_a_table(v) else v["status"],
                            "detail": (v.get("error") or "")[:200]})
    return out


def pdf_dictionaries(census: dict, extraction: dict) -> list[dict]:
    """Every PDF dictionary linked to a file, and what became of it (schema on main, or pull request)."""
    out = []
    for ds in census["datasets"]:
        for d in ds["dictionaries"]:
            if d.get("format") != "PDF" or not d.get("linked_resources"):
                continue
            rec = extraction.get(d["id"]) or {}
            stage = rec.get("stage")
            oracle = ((rec.get("llm") if stage == "llm" else rec.get("deterministic")) or {}).get("oracle") or {}
            first = d["linked_resources"][0]
            path = schemas.path(ds["name"], first, "extracted")
            status = (schemas.load(path) or {}).get("x5ltep", {}).get("status") if path.exists() else None
            out.append({"dataset": ds["name"], "title": ds["title"], "dictionary": d["name"], "url": d.get("url"),
                        "files": len(d["linked_resources"]), "outcome": rec.get("outcome") or "pending",
                        "stage": stage, "model": (rec.get("llm") or {}).get("model") if stage == "llm" else None,
                        "recall": oracle.get("recall"), "precision": oracle.get("precision"),
                        "similar_names": similar_of(oracle),
                        "schema": path.relative_to(config.ROOT).as_posix() if path.exists() else None,
                        "schema_status": status})
    return out


def drift_events(census: dict) -> list[dict]:
    names = {t["id"]: t["name"] for ds in census["datasets"] for t in ds["tables"]}
    return [{"kind": e["kind"], "dataset": e["dataset"], "resource_id": e["resource_id"],
             "file": e.get("resource_name") or names.get(e["resource_id"]), "at": e.get("at"),
             "changes": sorted(e.get("changes", {}))} for e in drift.load()[-100:]]


# --- status badge (shields.io endpoint), English and Portuguese ---------------------------
STATUS_TEXT = {
    "en": {"label": "Layer 1", "running": "running · started {date}",
           "validating": "running · {left} files left to check",
           "done": "done {date} · {conformant}/{verifiable} files conform",
           "interrupted": "interrupted {date} · see Actions"},
    "pt": {"label": "Camada 1", "running": "rodando · iniciada em {date}",
           "validating": "rodando · faltam {left} arquivos",
           "done": "concluída em {date} · {conformant}/{verifiable} arquivos conformes",
           "interrupted": "interrompida em {date} · ver Actions"},
}
STATUS_COLORS = {"running": "blue", "validating": "blue", "done": "brightgreen", "interrupted": "lightgrey"}


def status_paths() -> dict:
    base = config.ROOT / "docs" / "data"
    return {"en": base / "status.json", "pt": base / "status.pt.json"}


def write_status(state: str, **info) -> None:
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for lang, path in status_paths().items():
        t = STATUS_TEXT[lang]
        write_json(path, {"schemaVersion": 1, "label": t["label"],
                          "message": t[state].format(date=date, **info), "color": STATUS_COLORS[state]})


def status_from_summary(summary: dict, chain_continues: bool) -> tuple[str, dict]:
    left = summary["tables"]["queue_remaining"]
    if left and chain_continues:
        return "validating", {"left": left}
    return "done", {"conformant": summary["conformant"], "verifiable": summary["verifiable"]}

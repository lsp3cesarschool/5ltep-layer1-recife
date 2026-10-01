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
import re
import platform
from collections import Counter
from datetime import datetime, timezone
from statistics import mean

from src import config, drift

LEVELS = (0, 1, 2, 3, 4)


def write_json(path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")


def table_level(t: dict, v: dict | None) -> int:
    conf = ((v or {}).get("summary") or {}).get("conformance") or {}
    return 4 if t["level"] == 3 and conf.get("pass") else t["level"]


def _share(n: int, d: int) -> float | None:
    return round(n / d, 4) if d else None


def _error_kind(error: str | None) -> str:
    """'HTTP 404', 'timeout', 'connection'... from the message of a failed download."""
    m = re.search(r"\b([45]\d\d) (Client|Server) Error", error or "")
    if m:
        return f"HTTP {m.group(1)}"
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
            "with_probable_typos": sum(bool(c.get("probable_typos")) for _, c in confs),
            "probable_typos": sum(len(c.get("probable_typos") or {}) for _, c in confs),
            "declared_fields_missing": sum(len(c["missing"]) for _, c in confs),
            "formats_inferred_from_data": dict(inferred),
        },
        "files": {
            "validated": len(checked),
            "encodings": dict(encodings), "delimiters": dict(delimiters),
            "with_decode_errors": sum(v["summary"].get("decode_errors", 0) > 0 for _, v in checked),
            "with_ragged_rows": sum(v["summary"].get("ragged_rows", 0) > 0 for _, v in checked),
            "zips_with_several_headers": sum(v["summary"].get("distinct_headers", 1) > 1 for _, v in checked),
            "not_tabular": sum((validation.get(t["id"]) or {}).get("status") == "not-tabular" for t in tables),
            "unreachable_by_reason": dict(Counter(_error_kind((validation.get(t["id"]) or {}).get("error"))
                                                  for t in tables
                                                  if (validation.get(t["id"]) or {}).get("status") == "error").most_common()),
        },
        "pdf_extraction": {
            "pdf_dictionaries_linked": sum(d.get("format") == "PDF" and bool(d.get("linked_resources")) for d in dicts),
            "processed": len(pdf_recs),
            "by_outcome": dict(Counter(r.get("outcome") for r in pdf_recs)),
            "with_probable_typos": sum(bool(r["deterministic"]["oracle"].get("probable_typos")) for r in pdf_recs),
            "deterministic": {"with_oracle": len(det_oracles), "recall": avg(det_oracles, "recall"),
                              "precision": avg(det_oracles, "precision"),
                              "exact_match": avg(det_oracles, "exact_match"), "levenshtein": avg(det_oracles, "levenshtein")},
            "llm": {"with_oracle": len(llm_oracles), "recall": avg(llm_oracles, "recall"),
                    "precision": avg(llm_oracles, "precision"),
                    "exact_match": avg(llm_oracles, "exact_match"), "levenshtein": avg(llm_oracles, "levenshtein")},
        },
    }


def build_summary(census: dict, validation: dict, extraction: dict, queue: list) -> dict:
    tables, per_dataset = [], []
    ds_levels: Counter = Counter()
    for ds in census["datasets"]:
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
        "verifiable": len(verifiable), "conformant": len(conformant),
        "l1_rate": rate, "l1_pass": rate is not None and rate >= config.L1_PASS_THRESHOLD,
        "drift": {"observed": sum(e["kind"] == "observed" for e in log),
                  "declared": sum(e["kind"] == "declared" for e in log)},
        "findings": documentation_findings(census, validation, extraction),
        "per_dataset": per_dataset,
    }


def dashboard_data(census: dict, validation: dict, extraction: dict, summary: dict) -> dict:
    drift_count = Counter(e["resource_id"] for e in drift.load())
    datasets = []
    for ds in census["datasets"]:
        dicts = {d["id"]: d for d in ds["dictionaries"]}
        tables = []
        for t in ds["tables"]:
            v = validation.get(t["id"]) or {}
            s = v.get("summary") or {}
            c = s.get("conformance")
            lk = t.get("link") or {}
            d = dicts.get(lk.get("dictionary"), {})
            tables.append({
                "id": t["id"], "name": t["name"], "level": table_level(t, v), "url": t["url"],
                "dictionary": {"name": d.get("name"), "format": d.get("format"), "method": lk.get("method"),
                               "readable": d.get("readable"), "error_kind": d.get("error_kind")} if d else None,
                "status": v.get("status"), "validated_at": v.get("validated_at"), "rows": s.get("rows"),
                "schema_kind": v.get("schema_kind"), "error": v.get("error"),
                "encodings": s.get("encodings"), "distinct_headers": s.get("distinct_headers"),
                "conformance": {k: c.get(k) for k in ("pass", "error_rate", "missing", "undeclared", "spelling", "probable_typos",
                                                      "declared_fields", "inferred_formats")}
                | {"errors_by_field": {f: {k: e["count"] for k, e in kinds.items()}
                                       for f, kinds in c.get("errors_by_field", {}).items()}} if c else None,
                "drift_events": drift_count.get(t["id"], 0),
            })
        datasets.append({"name": ds["name"], "title": ds["title"], "organization": ds.get("organization"),
                         "url": ds["url"], "level": next((p["level"] for p in summary["per_dataset"]
                                                          if p["name"] == ds["name"]), None),
                         "dictionaries": [{"name": d["name"], "format": d["format"], "kind": d["kind"],
                                           "readable": d.get("readable"), "error_kind": d.get("error_kind"),
                                           "linked": len(d.get("linked_resources") or [])} for d in ds["dictionaries"]],
                         "tables": tables})
    return {"summary": {k: summary[k] for k in ("portal", "generated_at", "census_at", "datasets", "tables",
                                                 "verifiable", "conformant", "l1_rate", "l1_pass", "drift",
                                                 "schema_sources", "findings", "method")},
            "datasets": datasets}


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

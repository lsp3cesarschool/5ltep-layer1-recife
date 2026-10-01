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
from collections import Counter
from datetime import datetime, timezone

from src import ckan, config, dictionaries, drift, linker, schemas, tabular, types_map

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


def read_dictionary(res: dict) -> tuple[dict, dictionaries.Dictionary | None]:
    fmt = (res.get("format") or "").upper().strip(". ")
    entry = {"id": res["id"], "name": res.get("name") or "", "format": fmt, "url": res.get("url"),
             "kind": dictionaries.kind(fmt)}
    if entry["kind"] == "other" and (res.get("url") or "").lower().split("?")[0].endswith(".pdf"):
        entry["format"], entry["kind"] = "PDF", "human"
    if entry["kind"] == "machine" or entry["format"] == "PDF":
        try:
            data, sha = ckan.fetch_bytes(res["url"], config.MAX_DICTIONARY_BYTES)
        except ValueError as exc:
            entry.update(readable=False, error=str(exc), error_kind="too-large")
            return entry, None
        except Exception as exc:
            entry.update(readable=False, error=f"{type(exc).__name__}: {str(exc)[:160]}", error_kind="download-failed")
            return entry, None
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


def level_of(resource: dict, dict_entry: dict | None) -> int:
    if resource.get("attached") or (resource.get("datastore") or {}).get("typed"):
        return 3
    if dict_entry is None:
        return 1 if resource.get("described") else 0
    if dict_entry["kind"] == "machine" and dict_entry.get("readable"):
        return 2
    return 1


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
            t["_described"] = described

    link_input = [{"id": d["id"], "name": d["name"], "declared_resource_ids": d.get("declared_resource_ids"),
                   "parts": [{"label": p.label, "names": [f["name"] for f in p.fields]} for p in parsed[d["id"]].parts]
                   if d["id"] in parsed and parsed[d["id"]].parts else None}
                  for d in dicts]
    links = linker.link(link_input, tables, headers)
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
            lk = {"dictionary": None, "part": None, "method": "description", "score": 1.0}
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
                "kind": "description", "resource_id": t["id"]}), written, events)

    levels = [t["level"] for t in tables]
    return {
        "name": pkg["name"], "title": pkg.get("title") or pkg["name"],
        "organization": (pkg.get("organization") or {}).get("title"),
        "url": f"{portal_url}/dataset/{pkg['name']}", "metadata_modified": pkg.get("metadata_modified"),
        "resources_total": len(res_all), "dictionaries": dicts, "tables": tables,
        # a dataset is as verifiable as its least documented table
        "level": min(levels) if levels else None,
    }


def run(validation: dict, packages: list[dict] | None = None) -> tuple[dict, list[dict]]:
    """(census, declared drift events)."""
    portal = config.portal()
    packages = packages if packages is not None else ckan.packages(portal["portal_url"])
    headers = {rid: v["header"] for rid, v in validation.items() if v.get("header")}
    written: set = set()
    datasets, events = [], []
    for i, pkg in enumerate(packages, 1):
        logger.info("[%d/%d] %s", i, len(packages), pkg["name"])
        datasets.append(census_dataset(pkg, portal["portal_url"], headers, written, events))
    # Schemas the portal no longer declares are removed, so the Git history shows the change.
    for kind in MANAGED_KINDS:
        for p in config.SCHEMAS.glob(f"*/*.{kind}.json"):
            if p not in written:
                rid = p.name.split(".")[0]
                events += drift.compare_declared(p.parent.name, {"id": rid}, kind, schemas.load(p), None)
                p.unlink()
    return {"portal": portal, "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "datasets": datasets}, events

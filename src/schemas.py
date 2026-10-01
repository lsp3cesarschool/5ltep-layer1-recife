"""Schemas as versioned files: schemas/<dataset>/<resource id>.<kind>.json (Frictionless Table Schema).

Kinds, in the order a validation prefers them:

- attached:  a Table Schema the portal attaches to the resource (CKAN "schema" field);
- declared:  built from a machine-readable dictionary the portal publishes;
- extracted: built from a PDF dictionary (status "extracted" when the file's header confirms
             every name, "suggested" while awaiting review, "verified" after a person reviewed it);
- described: a field list written in the resource's description (names, and types when the
             text gives them);
- datastore: the types the CKAN DataStore exposes (often inferred by the portal's loader, so
             used only when nothing else exists);
- observed:  what the file itself shows (header, inferred types, delimiter, encoding).

Each file carries an "x5ltep" block with status and provenance (dictionary URL, SHA-256,
reader, extraction stage and model). Because they are committed, a change in what the portal
declares, or in what the file is, shows up as a diff in the Git history.
"""

import hashlib
import json
from pathlib import Path

from src import config, types_map

KINDS = ("attached", "declared", "extracted", "described", "datastore", "observed")
USABLE_EXTRACTED = {"extracted", "verified"}

DATASTORE_TYPES = {"text": "string", "varchar": "string", "numeric": "number", "float8": "number",
                   "float4": "number", "int": "integer", "int4": "integer", "int8": "integer",
                   "bigint": "integer", "timestamp": "datetime", "date": "date", "time": "time",
                   "bool": "boolean", "boolean": "boolean", "json": "object"}


def path(dataset: str, resource_id: str, kind: str, root: Path | None = None) -> Path:
    assert kind in KINDS
    return (root or config.SCHEMAS) / dataset / f"{resource_id}.{kind}.json"


def load(p: Path) -> dict | None:
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
    except ValueError:
        return None


def write(p: Path, schema: dict) -> bool:
    """Write only when the content changed (so unchanged schemas make no commit noise)."""
    text = json.dumps(schema, ensure_ascii=False, indent=1) + "\n"
    if p.exists() and p.read_text(encoding="utf-8") == text:
        return False
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")
    return True


def fingerprint(schema: dict | None) -> str | None:
    """Hash of what a validation depends on (names, types, formats, constraints), not of notes."""
    if not schema:
        return None
    keys = ("name", "type", "format", "decimalChar", "groupChar", "trueValues", "falseValues", "constraints")
    core = [{k: f.get(k) for k in keys if k in f} for f in schema.get("fields", [])]
    return hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest()[:16]


def from_fields(fields: list[dict], status: str, source: dict) -> dict:
    return {"fields": [types_map.field_descriptor(f["name"], f.get("type", ""), f.get("size"),
                                                  f.get("description", ""), f.get("allowed", ""))
                       for f in fields],
            "x5ltep": {"status": status, "source": source}}


def from_datastore(ds_fields: list[dict]) -> dict | None:
    """DataStore types as a schema; None when every field is text (nothing is declared)."""
    if not ds_fields or all((f.get("type") or "text") == "text" for f in ds_fields):
        return None
    fields = [{"name": f["id"], "type": DATASTORE_TYPES.get((f.get("type") or "").lower(), "any"),
               "declaredType": f.get("type") or ""} for f in ds_fields]
    return {"fields": fields, "x5ltep": {"status": "datastore", "source": {"kind": "datastore"}}}


def from_attached(raw) -> dict | None:
    """The resource's own "schema" field (ckanext-validation), if it is a usable Table Schema."""
    from frictionless import Schema

    try:
        descriptor = json.loads(raw) if isinstance(raw, str) else raw
        Schema.from_descriptor(descriptor)
    except Exception:
        return None
    if not isinstance(descriptor, dict) or not descriptor.get("fields"):
        return None
    return {**descriptor, "x5ltep": {"status": "attached", "source": {"kind": "attached"}}}


def select(dataset: str, resource_id: str, root: Path | None = None) -> tuple[str | None, dict | None]:
    """The schema a validation uses: attached > declared > extracted (if usable) > described > datastore."""
    for kind in ("attached", "declared", "extracted", "described", "datastore"):
        schema = load(path(dataset, resource_id, kind, root))
        if not schema:
            continue
        if kind == "extracted" and schema.get("x5ltep", {}).get("status") not in USABLE_EXTRACTED:
            continue
        return kind, schema
    return None, None

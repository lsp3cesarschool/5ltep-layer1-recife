"""Conformance of a published file to its declared schema, and the schema the file actually has.

For every CSV table of a resource:

- observed schema: header, delimiter, encoding and the types the first SAMPLE_ROWS rows fit
  (integer, number, date, datetime, boolean, else string), so that a resource without any
  dictionary still has a contract to compare against next week (drift);
- conformance, when a declared schema exists: declared fields missing from the file, file
  columns not declared, and every cell of the matched columns checked with the Frictionless
  Table Schema cell readers (type and constraints such as maxLength), streaming, in constant
  memory.

Privacy: only counts and row numbers are kept, never a cell value (the files may carry names
and CPF/CNPJ numbers).

Formats a dictionary does not declare (a date written 03/05/2022, a decimal comma) are
inferred from the sample and recorded as "inferred"; the check is then whether the values are
consistent with the declared type in one format, not whether they follow ISO 8601.
"""

import re
from datetime import datetime

from frictionless import Schema

from src import config, dictionaries

DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y", "%Y/%m/%d", "%d-%m-%Y", "%Y%m%d"]
DATETIME_FORMATS = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S.%f",
                    "%Y-%m-%dT%H:%M:%SZ", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%y %H:%M",
                    "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S%z"]
BOOLEAN_PAIRS = [({"S", "Sim", "SIM", "s"}, {"N", "Não", "NÃO", "Nao", "NAO", "n"}),
                 ({"true", "True", "TRUE"}, {"false", "False", "FALSE"}),
                 ({"1"}, {"0"}), ({"T", "t"}, {"F", "f"}), ({"Y", "y"}, {"N", "n"})]
LEADING_ZERO_RE = re.compile(r"^[+-]?0\d+$")
INT_RE = re.compile(r"^[+-]?(0|[1-9]\d*)$")
DOT_RE = re.compile(r"^[+-]?\d*\.\d+$|^[+-]?\d+$")
COMMA_RE = re.compile(r"^[+-]?(\d{1,3}(\.\d{3})+|\d*),\d+$|^[+-]?\d+$")


def _fits(values: list[str], fmt: str) -> float:
    ok = 0
    for v in values:
        try:
            datetime.strptime(v, fmt)
            ok += 1
        except ValueError:
            pass
    return ok / len(values) if values else 0.0


def best_format(values: list[str], formats: list[str], minimum: float = 0.5) -> tuple[str | None, float]:
    values = values[:500]
    scored = [(f, _fits(values, f)) for f in formats]
    fmt, share = max(scored, key=lambda x: x[1]) if scored else (None, 0.0)
    return (fmt, share) if share >= minimum else (None, share)


def infer_type(values: list[str]) -> dict:
    """The narrowest type every non-empty sampled value fits."""
    vals = [v for v in values if v != ""]
    if not vals:
        return {"type": "any"}
    if any(LEADING_ZERO_RE.match(v) for v in vals):
        return {"type": "string"}                 # codes such as CEP or IBGE ids keep their zeros
    if all(INT_RE.match(v) for v in vals):
        return {"type": "integer"}
    if all(DOT_RE.match(v) for v in vals):
        return {"type": "number"}
    if all(COMMA_RE.match(v) for v in vals):
        grouped = any(re.match(r"^[+-]?\d{1,3}(\.\d{3})+", v) for v in vals)
        return {"type": "number", "decimalChar": ",", **({"groupChar": "."} if grouped else {})}
    fmt, share = best_format(vals, DATE_FORMATS, 1.0)
    if fmt:
        return {"type": "date", "format": fmt}
    fmt, share = best_format(vals, DATETIME_FORMATS, 1.0)
    if fmt:
        return {"type": "datetime", "format": fmt}
    distinct = set(vals)
    for true, false in BOOLEAN_PAIRS:
        if distinct <= true | false and distinct & true and distinct & false:
            return {"type": "boolean", "trueValues": sorted(distinct & true), "falseValues": sorted(distinct & false)}
    return {"type": "string"}


MAX_NAME = 512


def observed_schema(header: list[str], sample: list[list[str]]) -> dict:
    """A valid Table Schema of what the file shows. A column without a name in the header (a finding
    in itself) gets the name _column_<n>; a name longer than MAX_NAME characters is cut; both are flagged."""
    fields = []
    for i, name in enumerate(header):
        col = [r[i] for r in sample if i < len(r)]
        empty = sum(1 for v in col if v == "")
        field = {"name": name, **infer_type(col), "sampleEmptyShare": round(empty / len(col), 4) if col else None}
        if not name:
            field.update(name=f"_column_{i + 1}", headerWithoutName=True)
        elif len(name) > MAX_NAME:
            field.update(name=name[:MAX_NAME], headerNameCut=len(name))
        fields.append(field)
    return {"fields": fields}


COMMA_DECIMAL_RE = re.compile(r"^[+-]?(\d{1,3}(\.\d{3})+|\d*),\d+$")
DOT_DECIMAL_RE = re.compile(r"^[+-]?(\d{1,3}(,\d{3})+|\d*)\.\d+$")
GROUPED_RE = re.compile(r"^[+-]?\d{1,3}(\.\d{3})+(,\d+)?$")


def complete_formats(declared: dict, header: list[str], sample: list[list[str]], matches: dict) -> tuple[dict, dict]:
    """Fill formats the dictionary leaves open with the one most sampled values follow.

    Majority, not unanimity: a format is a property of the column, and the values that do not
    follow it are exactly the errors the check must count.
    """
    col = {h: i for i, h in enumerate(header)}
    fields, inferred = [], {}
    for f in declared["fields"]:
        f = dict(f)
        target = f["name"] if f["name"] in col else matches["spelling"].get(f["name"])
        values = [r[col[target]] for r in sample if target is not None and col[target] < len(r)]
        values = [v for v in values if v != ""]
        if not values:
            fields.append(f)
            continue
        if f["type"] in ("date", "datetime") and "format" not in f:
            fmt, _ = best_format(values, DATE_FORMATS + DATETIME_FORMATS if f["type"] == "datetime" else DATE_FORMATS)
            if fmt is None and f["type"] == "date":
                fmt, _ = best_format(values, DATETIME_FORMATS)   # dates written with a time
                if fmt:
                    f["type"] = "datetime"
                    inferred.setdefault(f["name"], {})["type"] = "datetime (date values carry a time)"
            if fmt:
                f["format"] = fmt
                inferred.setdefault(f["name"], {})["format"] = fmt
        elif f["type"] == "number" and "decimalChar" not in f:
            comma = sum(bool(COMMA_DECIMAL_RE.match(v)) for v in values)
            dot = sum(bool(DOT_DECIMAL_RE.match(v)) for v in values)
            if comma > dot:
                f["decimalChar"] = ","
                if any(GROUPED_RE.match(v) for v in values):
                    f["groupChar"] = "."
                inferred[f["name"]] = {"decimalChar": ",", **({"groupChar": "."} if "groupChar" in f else {})}
        elif f["type"] == "boolean" and "trueValues" not in f:
            distinct = set(values)
            for true, false in BOOLEAN_PAIRS:
                if distinct & true and distinct & false:
                    f["trueValues"], f["falseValues"] = sorted(true), sorted(false)
                    inferred[f["name"]] = {"trueValues": f["trueValues"], "falseValues": f["falseValues"]}
                    break
        fields.append(f)
    return {**declared, "fields": fields}, inferred


def match_fields(declared_names: list[str], header: list[str]) -> dict:
    """Declared fields against the file's columns: exact, same after normalising, missing, extra."""
    exact = [n for n in declared_names if n in header]
    by_norm = {dictionaries.norm(h): h for h in header}
    spelling = {n: by_norm[dictionaries.norm(n)] for n in declared_names
                if n not in header and dictionaries.norm(n) in by_norm}
    matched = set(exact) | set(spelling)
    used = set(exact) | set(spelling.values())
    missing = [n for n in declared_names if n not in matched]
    undeclared = [h for h in header if h not in used]
    return {"exact": exact, "spelling": spelling, "missing": missing, "undeclared": undeclared,
            "probable_typos": probable_typos(missing, undeclared)}


def probable_typos(missing: list[str], undeclared: list[str], threshold: float = 0.8) -> dict[str, str]:
    """A declared name missing from the file and an undeclared column that differ by a small edit
    (IdeNuceloCEG / IdeNucleoCEG): most likely a typo in the dictionary, or in the file."""
    from src.pdf_extract import similarity

    out, free = {}, list(undeclared)
    for m in missing:
        scored = [(similarity(dictionaries.norm(m), dictionaries.norm(u)), u) for u in free]
        if scored:
            score, u = max(scored)
            if score >= threshold:
                out[m] = u
                free.remove(u)
    return out


TS_KEYS = {"name", "type", "format", "decimalChar", "groupChar", "trueValues", "falseValues", "constraints",
           "description", "title"}


def _readers(declared: dict, header: list[str], matches: dict) -> list[tuple[int, str, object]]:
    col = {h: i for i, h in enumerate(header)}
    out = []
    for f in declared["fields"]:
        target = f["name"] if f["name"] in col else matches["spelling"].get(f["name"])
        if target is None or f["type"] == "any":
            continue
        descriptor = {k: v for k, v in f.items() if k in TS_KEYS}
        try:
            field = Schema.from_descriptor({"fields": [descriptor]}).fields[0]
        except Exception:
            descriptor = {"name": f["name"], "type": f["type"]}
            field = Schema.from_descriptor({"fields": [descriptor]}).fields[0]
        out.append((col[target], f["name"], field.create_cell_reader()))
    return out


def check_table(table, declared: dict | None) -> dict:
    """Stream one table: observed schema always, conformance when a declared schema is given."""
    rows = table.rows
    try:
        header = [h.strip().lstrip("﻿") for h in next(rows)]
    except StopIteration:
        return {"member": table.member, "empty": True}
    sample = []
    for row in rows:
        sample.append(row)
        if len(sample) >= config.SAMPLE_ROWS:
            break
    observed = observed_schema(header, sample)
    result = {"member": table.member, "encoding": table.encoding, "delimiter": table.delimiter,
              "header": header, "observed": observed}
    checks, inferred, matches = [], {}, None
    if declared:
        matches = match_fields([f["name"] for f in declared["fields"]], header)
        completed, inferred = complete_formats(declared, header, sample, matches)
        checks = _readers(completed, header, matches)
    width = len(header)
    n_rows = cells = ragged = 0
    errors: dict[str, dict[str, dict]] = {}

    def check(row):
        nonlocal n_rows, cells, ragged
        n_rows += 1
        if len(row) != width:
            ragged += 1
        for idx, name, reader in checks:
            value = row[idx] if idx < len(row) else ""
            cells += 1
            if value == "":
                continue
            _, notes = reader(value)
            if notes:
                for kind in notes:
                    e = errors.setdefault(name, {}).setdefault(kind, {"count": 0, "rows": []})
                    e["count"] += 1
                    if len(e["rows"]) < config.ERROR_ROWS_KEPT:
                        e["rows"].append(n_rows)

    for row in sample:
        check(row)
    for row in rows:
        check(row)
    result.update(rows=n_rows, ragged_rows=ragged, decode_errors=table.decode_errors[0])
    if declared:
        bad_cells = sum(e["count"] for kinds in errors.values() for e in kinds.values())
        result["conformance"] = {
            "matches": matches, "inferred_formats": inferred, "cells_checked": cells,
            "cells_with_errors": bad_cells, "errors": errors,
        }
    return result


def summarise(tables: list[dict], declared: dict | None) -> dict:
    """One verdict per resource from its tables (a zip may have dozens)."""
    tables = [t for t in tables if not t.get("empty")]
    headers = {tuple(t["header"]) for t in tables}
    out = {"tables": len(tables), "rows": sum(t["rows"] for t in tables),
           "ragged_rows": sum(t["ragged_rows"] for t in tables),
           "decode_errors": max((t["decode_errors"] for t in tables), default=0),
           "distinct_headers": len(headers),
           "columns_without_name": max((sum(1 for h in t["header"] if not h) for t in tables), default=0),
           "encodings": sorted({t["encoding"] for t in tables}),
           "delimiters": sorted({t["delimiter"] for t in tables})}
    if not declared or not tables:
        return out
    confs = [t["conformance"] for t in tables]
    missing = sorted({m for c in confs for m in c["matches"]["missing"]})
    undeclared = sorted({u for c in confs for u in c["matches"]["undeclared"]})
    spelling = {k: v for c in confs for k, v in c["matches"]["spelling"].items()}
    typos = {k: v for c in confs for k, v in c["matches"].get("probable_typos", {}).items()}
    cells = sum(c["cells_checked"] for c in confs)
    bad = sum(c["cells_with_errors"] for c in confs)
    by_field: dict[str, dict] = {}
    for c in confs:
        for name, kinds in c["errors"].items():
            for kind, e in kinds.items():
                agg = by_field.setdefault(name, {}).setdefault(kind, {"count": 0, "rows": []})
                agg["count"] += e["count"]
                agg["rows"] = (agg["rows"] + e["rows"])[:config.ERROR_ROWS_KEPT]
    rate = bad / cells if cells else 0.0
    out["conformance"] = {
        "declared_fields": len(declared["fields"]), "missing": missing, "undeclared": undeclared,
        "spelling": spelling, "probable_typos": typos, "cells_checked": cells, "cells_with_errors": bad,
        "error_rate": round(rate, 6), "errors_by_field": by_field,
        "inferred_formats": {k: v for c in confs for k, v in c["inferred_formats"].items()},
        "pass": not missing and not undeclared and rate <= config.L1_MAX_ERROR_RATE,
    }
    return out

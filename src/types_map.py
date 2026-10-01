"""From the type a dictionary declares, in the publisher's own words, to a Table Schema field.

Dictionaries use many spellings for the same type ("TEXTO (STRING)", "Cadeia de caracteres",
"VARCHAR", "char"...). The mapping below is deliberately simple and auditable: a declared
type is matched by keywords, in a fixed order, and anything not recognised becomes "any"
with a note, so it is reported instead of guessed. A format written in the declared type
("DATA (DD/MM/AAAA)", "SEPARADOR PONTO") is kept; when the dictionary gives none, the
format is inferred from the data later and recorded as inferred (see validate.py).
"""

import re
import unicodedata

TABLE_SCHEMA_TYPES = {"string", "integer", "number", "boolean", "date", "datetime", "time", "object", "any"}

# (Table Schema type, pattern over the normalised declared type), first match wins.
RULES = [
    ("any", r"\b(MULTI)?(POLYGON|POINT|LINESTRING|GEOMETRY|GEOMETRIA|SHAPE|GEOJSON)\b"),
    ("datetime", r"DATETIME|DATATIME|TIMESTAMP|\bDATA ?(E|/)? ?HORA\b|\bDT ?HR\b"),
    ("date", r"\bDATE\b|\bDATA\b|\bDT\b"),
    ("time", r"\bTIME\b|\bHORA\b"),
    ("boolean", r"\bBOOL(EAN)?\b|\bLOGICO\b|\bS ?/ ?N\b"),
    ("integer", r"\b(BIG|SMALL|TINY)?INT(EGER|EIRO)?\b|\bNUMBER ?\( ?\d+ ?\)"),
    ("number", r"\bDECIMAL\b|\bFLOAT\b|\bDOUBLE\b|\bREAL\b|\bNUM(ERIC|ERICO|ERO|BER)?\b|\bMONETARIO\b|\bMOEDA\b|\bVALOR\b"),
    ("object", r"\bJSON\b"),
    ("string", r"\bSTRING\b|\bTEXT(O)?\b|\b(VAR)?CHAR(2|ACTER)?\b|\bCADEIA\b|\bCARACTER(ES)?\b|\bALFANUMERICO\b|\bCLOB\b|\bENUM\b"),
]

DATE_PARTS = [("DD", "%d"), ("MM", "%m"), ("AAAA", "%Y"), ("YYYY", "%Y"), ("AA", "%y"), ("YY", "%y")]


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", text.upper()).strip()


def _date_format(norm: str) -> str | None:
    """'DATA (DD/MM/AA)' -> '%d/%m/%y'; 'DD/MM/AAAA HH:MM' -> '%d/%m/%Y %H:%M'."""
    m = re.search(r"(DD|AAAA|YYYY)([/.-])(MM)\2(AAAA|YYYY|AA|YY|DD)", norm)
    if not m:
        return None
    fmt = m.group(0)
    for token, code in DATE_PARTS:
        fmt = fmt.replace(token, code)
    t = re.search(r"HH:MM(:SS)?", norm[m.end():])
    if t:
        fmt += " %H:%M" + (":%S" if t.group(1) else "")
    return fmt


def _size(size) -> int | None:
    m = re.match(r"^\s*(\d{1,6})\s*$", str(size or ""))
    return int(m.group(1)) if m and int(m.group(1)) > 0 else None


def map_type(declared: str) -> tuple[str, dict, str | None]:
    """(Table Schema type, extra descriptor keys, note) for a declared type."""
    norm = normalise(declared)
    if not norm:
        return "any", {}, "type not declared"
    for ts_type, pattern in RULES:
        if re.search(pattern, norm):
            break
    else:
        return "any", {}, f"declared type not recognised: {declared!r}"
    extra: dict = {}
    if ts_type in ("date", "datetime"):
        fmt = _date_format(norm)
        if fmt:
            if ts_type == "date" and "%H" in fmt:
                ts_type = "datetime"
            extra["format"] = fmt
    if ts_type == "number":
        if re.search(r"SEPARADOR (DECIMAL )?(PONTO|\.)", norm):
            extra["decimalChar"] = "."
        elif re.search(r"SEPARADOR (DECIMAL )?(VIRGULA|,)", norm):
            extra["decimalChar"] = ","
    note = "geometry: not checked" if ts_type == "any" else None
    return ts_type, extra, note


def field_descriptor(name: str, declared_type: str = "", size=None, description: str = "",
                     allowed: str = "") -> dict:
    """A Table Schema field for one declared field; what the dictionary said is kept alongside."""
    ts_type, extra, note = map_type(declared_type)
    field = {"name": name, "type": ts_type, **extra}
    desc = re.sub(r"\s+", " ", str(description or "")).strip()
    if allowed and str(allowed).strip():
        allowed_text = re.sub(r"\s+", " ", str(allowed)).strip()
        desc = (desc + " " if desc else "") + f"[Allowed values, as declared: {allowed_text}]"
    if desc:
        field["description"] = desc[:2000]
    n = _size(size)
    if n and ts_type == "string":
        field["constraints"] = {"maxLength": n}
    # What the publisher wrote, so a reviewer can check the mapping.
    field["declaredType"] = str(declared_type or "")[:200]
    if n:
        field["declaredSize"] = n
    if note:
        field["mappingNote"] = note
    return field

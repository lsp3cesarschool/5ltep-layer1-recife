"""Data dictionaries published on the portal: which resources are dictionaries, and reading them.

A reader is chosen by the file's *content*, not by the portal, so an instance for another
portal needs no code change when its dictionaries look like any of these:

- a table (CSV, XLSX) with one row per field and a header naming the columns, e.g. IBAMA's
  ``nome_entidade;nome_atributo;tipificacao;datatype;descricao``;
- JSON with a list of field objects, e.g. Recife's ``metadados.campos[{codigo, tipo, tamanho,
  descricao, valores_permitidos}]`` (which also names the resources it describes);
- XML with one repeated element per field;
- tables extracted from a PDF (see pdf_extract.py), which reuse ``fields_from_rows``;
- a list of fields written in the resource's own description (IBAMA: "Dicionário de dados:
  * SEQ_TAD – Chave que identifica..." or "- **UF**: Sigla da unidade federativa. Formato: texto;").

A dictionary that cannot be read (an HTML page instead of the file, malformed JSON, no header
we recognise) is reported as unreadable: it exists, but cannot be processed automatically.
"""

import csv
import io
import json
import re
import unicodedata
from dataclasses import dataclass, field

DICT_NAME_RE = re.compile(r"metadad|dicion[aá]rio|dicionario|dictionary|\besquema\b|\bschema\b|\blayout\b", re.I)
MACHINE_FORMATS = {"CSV", "JSON", "XML", "XLSX", "XLS", "ODS", "TXT"}
HUMAN_FORMATS = {"PDF", "HTML", "HTM", "DOC", "DOCX", "ODT", "RTF"}

# Column roles in a tabular dictionary, by header synonyms (normalised: lowercase, no accents,
# punctuation as spaces). The order inside each tuple is the order of preference.
ROLES = {
    "name": ("nome atributo", "nome do atributo", "nome do campo", "nome campo", "codigo", "campo",
             "nome da variavel", "variavel", "nome da coluna", "coluna", "atributo", "field name",
             "column name", "field", "column", "name", "nome"),
    "type": ("datatype", "data type", "tipo do dado", "tipo de dado", "tipo dado", "tipo do campo",
             "tipo", "type", "formato"),
    "size": ("tamanho do campo", "tamanho", "tam", "size", "length", "comprimento"),
    "description": ("descricao do campo", "descricao", "description", "significado", "definicao", "conteudo"),
    "allowed": ("valores permitidos", "dominio", "valores", "categorias", "allowed values"),
}
NAME_RE = re.compile(r"^[^\s].{0,127}$")


@dataclass
class Part:
    """One table described by a dictionary (an XLSX file may describe several, one per sheet)."""
    label: str
    fields: list[dict]


@dataclass
class Dictionary:
    reader: str | None = None
    parts: list[Part] = field(default_factory=list)
    error: str | None = None
    # Why it could not be read, as a fixed code (counted in the documentation findings):
    # html-page, malformed, no-field-table, format-not-read, too-large, download-failed, pdf-no-text.
    error_kind: str | None = None
    declared_resource_ids: list[str] = field(default_factory=list)
    declared_datasets: list[str] = field(default_factory=list)   # /dataset/<name> cited in the file

    @property
    def readable(self) -> bool:
        return self.error is None and any(p.fields for p in self.parts)


def norm(text) -> str:
    text = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def is_dictionary(resource: dict) -> bool:
    name = (resource.get("name") or "") + " " + (resource.get("url") or "").rsplit("/", 1)[-1]
    return bool(DICT_NAME_RE.search(name))


def kind(fmt: str) -> str:
    fmt = (fmt or "").upper().strip(". ")
    return "machine" if fmt in MACHINE_FORMATS else "human" if fmt in HUMAN_FORMATS else "other"


def decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1")


def _role_columns(header: list) -> dict[str, int]:
    cells = [norm(c) for c in header]
    found: dict[str, int] = {}
    for role, synonyms in ROLES.items():
        for syn in synonyms:
            idx = next((i for i, c in enumerate(cells) if c == syn and i not in found.values()), None)
            if idx is not None:
                found[role] = idx
                break
    return found


def fields_from_rows(rows: list[list], max_header_row: int = 15) -> list[dict] | None:
    """Fields of a tabular dictionary: find the header row, then one field per row.

    None when no header row names a field column together with a type or description column.
    """
    for h, header in enumerate(rows[:max_header_row]):
        roles = _role_columns(header)
        if "name" in roles and ({"type", "description"} & roles.keys()):
            break
    else:
        return None
    out, seen = [], set()
    for row in rows[h + 1:]:
        cell = lambda role: str(row[roles[role]]).strip() if role in roles and roles[role] < len(row) and row[roles[role]] is not None else ""
        name = cell("name")
        if not name or not NAME_RE.match(name) or norm(name) in {norm(header[roles["name"]])}:
            continue
        if name in seen:
            continue
        seen.add(name)
        out.append({"name": name, "type": cell("type"), "size": cell("size"),
                    "description": cell("description"), "allowed": cell("allowed")})
    return out


def _read_csv(text: str) -> list[list]:
    sample = text[:20000]
    try:
        delim = csv.Sniffer().sniff(sample, delimiters=";,\t|").delimiter
    except csv.Error:
        delim = ";" if sample.count(";") >= sample.count(",") else ","
    return list(csv.reader(io.StringIO(text), delimiter=delim))


def _json_field_lists(obj, path=""):
    """Every list of objects in a JSON document, with its path."""
    if isinstance(obj, list):
        if obj and all(isinstance(x, dict) for x in obj):
            yield path, obj
        for i, x in enumerate(obj):
            yield from _json_field_lists(x, f"{path}[{i}]")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _json_field_lists(v, f"{path}.{k}")


def _records_to_fields(records: list[dict]) -> list[dict] | None:
    keys = list(dict.fromkeys(k for r in records for k in r))
    rows = [keys] + [[r.get(k) for k in keys] for r in records]
    return fields_from_rows(rows, max_header_row=1)


DATASET_REF_RE = re.compile(r"/dataset/([a-z0-9][a-z0-9_-]{1,99})(?=[/\s\"']|$)")
RESOURCE_ID_RE = re.compile(r"/resource(?:_edit)?/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})")


def _read_json(text: str) -> Dictionary:
    doc = json.loads(text)
    best = None
    for path, records in _json_field_lists(doc):
        fields = _records_to_fields(records)
        if fields and (best is None or len(fields) > len(best[1])):
            best = (path, fields)
    if not best:
        return Dictionary(reader="json", error="no list of fields recognised", error_kind="no-field-table")
    # Resources the dictionary says it describes (e.g. Recife: metadados.recursos[].identificador).
    ids = list(dict.fromkeys(RESOURCE_ID_RE.findall(text)))
    datasets = list(dict.fromkeys(DATASET_REF_RE.findall(text)))
    return Dictionary(reader="json", parts=[Part(best[0].lstrip("."), best[1])], declared_resource_ids=ids,
                      declared_datasets=datasets)


def _read_xml(data: bytes) -> Dictionary:
    from defusedxml import ElementTree  # untrusted XML: no entity expansion

    root = ElementTree.fromstring(data)
    best = None
    for parent in root.iter():
        children = list(parent)
        if len(children) < 2:
            continue
        records = [{c.tag.split("}")[-1]: (c.text or "").strip() for c in child} for child in children]
        records = [r for r in records if r]
        if len(records) < 2:
            continue
        fields = _records_to_fields(records)
        if fields and (best is None or len(fields) > len(best)):
            best = fields
    if not best:
        return Dictionary(reader="xml", error="no repeated field element recognised", error_kind="no-field-table")
    return Dictionary(reader="xml", parts=[Part("", best)])


def _read_xlsx(data: bytes) -> Dictionary:
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    parts = []
    for ws in wb.worksheets:
        rows = [list(r) for _, r in zip(range(5000), ws.iter_rows(values_only=True))]
        fields = fields_from_rows(rows)
        if fields:
            parts.append(Part(ws.title, fields))
    if not parts:
        return Dictionary(reader="xlsx", error="no sheet with a recognised field table", error_kind="no-field-table")
    return Dictionary(reader="xlsx", parts=parts)


def read(data: bytes, fmt: str) -> Dictionary:
    """Read a machine-readable dictionary; the reader is chosen by content, then by format."""
    head = data[:2048].lstrip(b"\xef\xbb\xbf \r\n\t").lower()
    if head.startswith((b"<!doctype html", b"<html")):
        return Dictionary(error="the link returns an HTML page, not the dictionary file", error_kind="html-page")
    try:
        if data[:2] == b"PK":
            return _read_xlsx(data)
        if head.startswith((b"{", b"[")):
            return _read_json(decode(data))
        if head.startswith(b"<"):
            return _read_xml(data)
        if (fmt or "").upper() in ("XLS", "ODS"):
            return Dictionary(error=f"{fmt} dictionaries are not read yet", error_kind="format-not-read")
        rows = _read_csv(decode(data))
        fields = fields_from_rows(rows)
        if not fields:
            return Dictionary(reader="csv", error="no header with field and type/description columns", error_kind="no-field-table")
        return Dictionary(reader="csv", parts=[Part("", fields)])
    except Exception as exc:  # malformed files are a finding, not a crash
        return Dictionary(error=f"{type(exc).__name__}: {str(exc)[:160]}", error_kind="malformed")


# --- dictionaries written in the resource description (Markdown) ------------------

DESC_HEADING_RE = re.compile(r"dicion[aá]rio\s+de\s+dados|data\s+dictionary|descri[cç][aã]o\s+dos\s+campos", re.I)
BULLET = r"^\s*(?:[*\-•]|\d+[.)])\s+"
# Three ways portals write an item: "**Name:** text", "Name – text" (dash between spaces), "Name: text".
DESC_ITEM_RES = [
    re.compile(BULLET + r"\*\*(.+?)\*\*\s*:?\s*(.*)$"),
    re.compile(BULLET + r"`?([^\s`*].{0,80}?)`?\s+[–—-]\s+(.*)$"),
    re.compile(BULLET + r"`?([^:`*\s][^:`]{0,80}?)`?\s*:\s+(.*)$"),
]
DESC_TYPE_RE = re.compile(r"\b(?:formato|tipo)\s*:\s*([^;\n]{1,80})", re.I)


def from_description(text: str) -> list[dict] | None:
    """Fields listed after a "Dicionário de dados" heading in a description; None if fewer than 2."""
    m = DESC_HEADING_RE.search(text or "")
    if not m:
        return None
    out, seen = [], set()
    for line in text[m.end():].splitlines():
        item = next((r.match(line) for r in DESC_ITEM_RES if r.match(line)), None)
        if not item:
            continue
        name = item.group(1).strip().strip("`*").rstrip(":").strip()
        desc = item.group(2).strip()
        if not name or len(name) > 80 or name in seen:
            continue
        seen.add(name)
        t = DESC_TYPE_RE.search(desc)
        out.append({"name": name, "type": t.group(1).strip(" *_`.") if t else "", "size": "",
                    "description": desc, "allowed": ""})
    return out if len(out) >= 2 else None

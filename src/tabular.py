"""Reading a published table as a stream: no raw data is ever stored or committed.

The format is decided by the file's *content*, not by the format the portal declares:

  CSV, JSON, XML   read straight from the HTTP response, record by record, while the SHA-256 is
                   computed; nothing goes to disk;
  ZIP              downloaded to a temporary file (its directory is at the end); every member that
                   is a table is read (CSV/TXT, JSON, XML, spreadsheets, Parquet, and zips inside
                   the zip, one level deep); a zip with no table inside is not tabular data;
  XLSX, XLS, ODS   spreadsheets, downloaded to a temporary file; each sheet is a table;
  Parquet          downloaded to a temporary file and read in batches.

Every format becomes the same thing for the rest of the pipeline: a Table whose rows are lists of
strings, header first. JSON and XML are read as lists of records (an array of objects; repeated
elements under the root); a nested value becomes its JSON text. Encoding and delimiter of text
formats are detected from the first 64 KB; bytes that do not decode later are counted, not fatal.
"""

import codecs
import contextlib
import csv
import datetime as dt
import hashlib
import io
import json
import sys
import tempfile
import time
import zipfile
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

import requests

from src import ckan, config

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))   # geometry columns hold very long cells

PEEK = 1 << 16
HEADER_SAMPLE = 1000          # records of JSON/XML read to collect the column names
_decode_errors = [0]


def _count_and_replace(exc: UnicodeDecodeError):
    _decode_errors[0] += 1
    return "�", exc.end


codecs.register_error("l1count", _count_and_replace)


class NotTabular(Exception):
    """The resource holds no table. `kind`: "no-tables" (a container of documents or maps: not tabular
    data, left out of the tabular universe), "html" or "pdf" (the link returns a page or a document
    instead of the table: a failure of the link), "too-large"."""

    def __init__(self, message: str, kind: str = "no-tables"):
        super().__init__(message)
        self.kind = kind


class HashingReader(io.RawIOBase):
    """Wraps a byte stream, computing SHA-256 and size of everything read through it."""

    def __init__(self, raw):
        self.raw, self.sha, self.size = raw, hashlib.sha256(), 0

    def readable(self) -> bool:
        return True

    def readinto(self, b) -> int:
        data = self.raw.read(len(b))
        n = len(data)
        b[:n] = data
        self.sha.update(data)
        self.size += n
        return n


def detect_encoding(sample: bytes) -> str:
    if sample.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return "utf-16"
    cut = sample[:sample.rfind(b"\n") + 1] or sample
    try:
        cut.decode("utf-8")
        return "utf-8-sig" if sample.startswith(codecs.BOM_UTF8) else "utf-8"
    except UnicodeDecodeError as exc:
        # A multi-byte character cut at the end of the sample is not an error.
        if exc.start >= len(cut) - 3:
            return "utf-8"
        return "cp1252"


def detect_delimiter(text: str) -> str:
    lines = text.splitlines()[:50]
    try:
        return csv.Sniffer().sniff("\n".join(lines), delimiters=";,\t|").delimiter
    except csv.Error:
        first = lines[0] if lines else ""
        return max(";,\t|", key=first.count)


@dataclass
class Table:
    """One table of a resource: the resource itself, a member of its zip, or a sheet."""
    member: str | None
    encoding: str | None          # text formats only
    delimiter: str | None         # CSV only
    rows: object                  # iterator of lists of strings, header first
    decode_errors: list = field(default_factory=lambda: _decode_errors)
    fmt: str = "csv"


def cell(value) -> str:
    """Any value of any format as the text a CSV would hold."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else repr(value)
    if isinstance(value, (int, Decimal)):
        return str(value)
    if isinstance(value, (dt.datetime, dt.date, dt.time)):
        return value.isoformat()
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return str(value)


def sniff(sample: bytes) -> str:
    """csv, json, xml, zip, parquet or xls, from the first bytes; NotTabular for pages and documents."""
    if sample.startswith(b"PK\x03\x04"):
        return "zip"
    if sample.startswith(b"PAR1"):
        return "parquet"
    if sample.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        return "xls"
    if sample.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        text = sample.decode("utf-16", errors="ignore")
    else:
        text = sample.decode("utf-8", errors="ignore")
    head = text.lstrip("﻿ \r\n\t").lower()
    if head.startswith(("<!doctype html", "<html")):
        raise NotTabular("the link returns an HTML page, not a table", "html")
    if head.startswith("%pdf"):
        raise NotTabular("the link returns a PDF document, not a table", "pdf")
    if head.startswith("<"):
        return "xml"
    if head.startswith(("[", "{")):
        return "json"
    return "csv"


# --- text formats, streamed -----------------------------------------------------------

def _csv_table(buffered, member: str | None) -> Table:
    sample = buffered.peek(PEEK)[:PEEK]
    encoding = detect_encoding(sample)
    delimiter = detect_delimiter(sample.decode(encoding, errors="replace"))
    text = io.TextIOWrapper(buffered, encoding=encoding, errors="l1count", newline="")
    return Table(member, encoding, delimiter, csv.reader(text, delimiter=delimiter), fmt="csv")


def _records_to_rows(records):
    """Lists of strings, header first, from an iterator of dicts. The header is the union of the
    keys of the first HEADER_SAMPLE records; a later new key is left out (and the row counts as
    ragged, see validate.py)."""
    first, header, seen = [], [], set()
    for rec in records:
        first.append(rec)
        for k in rec:
            if k not in seen:
                seen.add(k)
                header.append(k)
        if len(first) >= HEADER_SAMPLE:
            break
    yield [str(h) for h in header]
    for rec in first:
        yield _row(rec, header)
    for rec in records:
        yield _row(rec, header)


def _row(rec: dict, header: list) -> list[str]:
    row = [cell(rec.get(h)) for h in header]
    if any(k not in header for k in rec):
        row.append("")                        # a key outside the header: the row is ragged
    return row


def _json_records(stream):
    """Records of a JSON document: the top-level array, or the first array under a top-level key."""
    import ijson

    target, builder, depth = None, None, 0
    for prefix, event, value in ijson.parse(stream):
        if builder is not None:
            builder.event(event, value)
            depth += event in ("start_map", "start_array")
            depth -= event in ("end_map", "end_array")
            if depth == 0:
                yield builder.value if isinstance(builder.value, dict) else {"value": builder.value}
                builder = None
            continue
        if target is None:
            if prefix == "" and event == "start_array":
                target = "item"
            elif event == "start_array" and prefix and "." not in prefix:
                target = prefix + ".item"
            continue
        if prefix == target and event in ("start_map", "start_array"):
            builder, depth = ijson.ObjectBuilder(), 1
            builder.event(event, value)
        elif prefix == target and event in ("string", "number", "boolean", "null"):
            yield {"value": value}


def _json_table(buffered, member: str | None) -> Table:
    sample = buffered.peek(PEEK)[:PEEK]
    encoding = detect_encoding(sample)
    if encoding == "utf-16":                  # ANEEL publishes JSON in UTF-16: transcode for the parser
        stream = io.TextIOWrapper(buffered, encoding="utf-16", errors="l1count")
    else:
        stream = buffered
    return Table(member, encoding, None, _records_to_rows(_json_records(stream)), fmt="json")


def _xml_records(stream):
    """Records of an XML document: the elements directly under the root; fields are their child
    elements (or, when there are none, their attributes)."""
    from defusedxml.ElementTree import iterparse

    depth = 0
    for event, elem in iterparse(stream, events=("start", "end")):
        if event == "start":
            depth += 1
            continue
        depth -= 1
        if depth == 1:
            children = list(elem)
            rec = {c.tag.split("}")[-1]: (c.text or "").strip() for c in children} if children else dict(elem.attrib)
            yield rec
            elem.clear()


def _xml_table(buffered, member: str | None) -> Table:
    encoding = detect_encoding(buffered.peek(PEEK)[:PEEK])
    return Table(member, encoding, None, _records_to_rows(_xml_records(buffered)), fmt="xml")


def _stream_table(buffered, kind: str, member: str | None) -> Table:
    return {"csv": _csv_table, "json": _json_table, "xml": _xml_table}[kind](buffered, member)


# --- formats read from a file on disk ---------------------------------------------------

def _xlsx_tables(path: Path, member: str | None):
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        for ws in wb.worksheets:
            rows = ([cell(v) for v in r] for r in ws.iter_rows(values_only=True))
            yield Table(_name(member, ws.title), None, None, rows, fmt="xlsx")
    finally:
        wb.close()


def _xls_tables(path: Path, member: str | None):
    import xlrd

    if path.stat().st_size > config.MAX_SHEET_BYTES:
        raise NotTabular("spreadsheet too large to read in memory", "too-large")
    book = xlrd.open_workbook(str(path), on_demand=True)
    for sheet in book.sheets():
        rows = ([cell(v) for v in sheet.row_values(i)] for i in range(sheet.nrows))
        yield Table(_name(member, sheet.name), None, None, rows, fmt="xls")


def _ods_tables(path: Path, member: str | None):
    import pandas as pd

    if path.stat().st_size > config.MAX_SHEET_BYTES:
        raise NotTabular("spreadsheet too large to read in memory", "too-large")
    sheets = pd.read_excel(path, engine="odf", sheet_name=None, header=None, dtype=object)
    for name, frame in sheets.items():
        rows = ([cell(None if (isinstance(v, float) and v != v) else v) for v in r]
                for r in frame.itertuples(index=False, name=None))
        yield Table(_name(member, str(name)), None, None, rows, fmt="ods")


def _parquet_tables(path: Path, member: str | None):
    import pyarrow.parquet as pq

    pf = pq.ParquetFile(path)
    names = pf.schema_arrow.names

    def rows():
        yield list(names)
        for batch in pf.iter_batches(batch_size=20000):
            cols = [batch.column(i).to_pylist() for i in range(batch.num_columns)]
            for values in zip(*cols):
                yield [cell(v) for v in values]

    yield Table(member, None, None, rows(), fmt="parquet")


def _name(member: str | None, sheet: str) -> str:
    return f"{member}#{sheet}" if member else sheet


def _container_kind(path: Path) -> str:
    """zip, xlsx or ods for a file that starts with PK."""
    with zipfile.ZipFile(path) as zf:
        names = set(zf.namelist())
        if "xl/workbook.xml" in names:
            return "xlsx"
        if "mimetype" in names and zf.read("mimetype").startswith(b"application/vnd.oasis.opendocument.spreadsheet"):
            return "ods"
    return "zip"


def _file_tables(path: Path, kind: str, member: str | None, tmp: str, depth: int, digest: dict):
    if kind == "zip":
        kind = _container_kind(path)
        if member is None:
            digest["kind"] = kind
    if kind in ("xlsx", "ods", "xls", "parquet") and path.suffix != f".{kind}":
        path = path.replace(path.with_name(f"{path.name}.{kind}"))   # some readers check the extension
    if kind == "xlsx":
        yield from _xlsx_tables(path, member)
    elif kind == "ods":
        yield from _ods_tables(path, member)
    elif kind == "xls":
        yield from _xls_tables(path, member)
    elif kind == "parquet":
        yield from _parquet_tables(path, member)
    else:
        yield from _zip_tables(path, member, tmp, depth, digest)


TABLE_EXTENSIONS = (".csv", ".txt", ".tsv", ".json", ".xml", ".xlsx", ".xls", ".ods", ".parquet", ".zip")


def _zip_tables(path: Path, outer: str | None, tmp: str, depth: int, digest: dict):
    with zipfile.ZipFile(path) as zf:
        infos = [i for i in zf.infolist() if not i.is_dir() and "__MACOSX/" not in i.filename
                 and i.filename.lower().endswith(TABLE_EXTENSIONS)]
        if depth > 0:                                       # a zip inside a zip: one level only
            infos = [i for i in infos if not i.filename.lower().endswith(".zip")]
        found = 0
        for info in sorted(infos, key=lambda i: i.filename):
            name = f"{outer}/{info.filename}" if outer else info.filename
            with zf.open(info) as raw:
                buffered = io.BufferedReader(raw, PEEK * 4)
                try:
                    kind = sniff(buffered.peek(PEEK)[:PEEK])
                except NotTabular:
                    continue
                if kind in ("csv", "json", "xml"):
                    found += 1
                    yield _stream_table(buffered, kind, name)
                    continue
                inner = Path(tmp) / f"member-{depth}-{found}"
                with open(inner, "wb") as fh:
                    while chunk := buffered.read(1 << 20):
                        fh.write(chunk)
            for table in _file_tables(inner, kind, name, tmp, depth + 1, digest):
                found += 1
                yield table
            inner.unlink(missing_ok=True)
        if outer is None:
            digest["members"] = found
        if not found and outer is None:
            names = [i.filename for i in zf.infolist()][:5]
            raise NotTabular(f"zip without tables (first entries: {names})", "no-tables")


# --- the resource ---------------------------------------------------------------------

@dataclass
class Source:
    tables: list            # generator of Table
    digest: dict            # filled when the whole file has been read: sha256, bytes, kind


DISK_KINDS = ("zip", "parquet", "xls")


@contextlib.contextmanager
def open_resource(url: str):
    """Yields a Source; `digest` is complete once every table has been read to the end."""
    _decode_errors[0] = 0
    t0 = time.monotonic()
    resp = ckan.get(url, stream=True, timeout=config.HTTP_TIMEOUT_S)
    # Network figures: time until the server answered (connection, retries, first byte) and, for a
    # file read from disk, the download alone (a text format is validated while it streams).
    timing = {"first_byte_s": round(time.monotonic() - t0, 2)}
    resp.raw.decode_content = True
    hashing = HashingReader(resp.raw)
    buffered = io.BufferedReader(hashing, PEEK * 4)
    h = resp.headers
    # Change signals of the server, compared with a HEAD request in later runs (work.py).
    digest: dict = {"timing": timing,
                    "http": {"etag": h.get("ETag"), "last_modified": h.get("Last-Modified"),
                             "content_length": int(h["Content-Length"]) if (h.get("Content-Length") or "").isdigit() else None}}
    try:
        kind = sniff(buffered.peek(PEEK)[:PEEK])
        if kind in DISK_KINDS:
            length = digest["http"]["content_length"] or 0
            if length > config.MAX_ZIP_BYTES:
                raise NotTabular(f"file of {length / 1e9:.1f} GB is above MAX_ZIP_BYTES", "too-large")
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "resource"
                with open(path, "wb") as fh:
                    while chunk := buffered.read(1 << 20):
                        fh.write(chunk)
                        if hashing.size > config.MAX_ZIP_BYTES:
                            raise NotTabular("file larger than MAX_ZIP_BYTES", "too-large")
                timing["download_s"] = round(time.monotonic() - t0, 2)
                digest.update(sha256=hashing.sha.hexdigest(), bytes=hashing.size, kind=kind)
                yield Source(_file_tables(path, kind, None, tmp, 0, digest), digest)
        else:
            def single():
                yield _stream_table(buffered, kind, None)
                # read whatever the reader left (e.g. a trailing newline) so the hash is complete
                try:
                    while buffered.read(1 << 20):
                        pass
                except ValueError:
                    pass       # a text wrapper that read to the end closed it: every byte was hashed
                digest.update(sha256=hashing.sha.hexdigest(), bytes=hashing.size, kind=kind)
            yield Source(single(), digest)
    finally:
        resp.close()


def peek_header(url: str, rows: int = 50) -> tuple[str, list[str]]:
    """(format, header) of a resource, reading as little as the format allows (another format of a
    table already validated in full: only its columns are compared)."""
    with open_resource(url) as src:
        for table in src.tables:
            it = iter(table.rows)
            header = [h.strip().lstrip("﻿") for h in next(it, [])]
            for _ in zip(range(rows), it):
                pass
            return table.fmt, header
    raise NotTabular("no table", "no-tables")


# --- which resources may hold a table (from the metadata) -------------------------------

FORMATS = {"CSV": "csv", "TSV": "csv", "TXT": "csv", "ZIP": "zip", "CSV.ZIP": "zip", "CSV-ZIP": "zip",
           "XLSX": "xlsx", "XLS": "xls", "ODS": "ods", "PARQUET": "parquet", "JSON": "json", "XML": "xml"}
GEO_WORDS = ("shp", "shape", "kmz", "kml", "geojson", "gpkg", "wms", "wmts")
# Order of preference when the same table is published in several formats: the first is validated
# in full, the others only for their columns.
PRIORITY = {"csv": 0, "zip": 1, "parquet": 2, "xlsx": 3, "ods": 4, "xls": 5, "json": 6, "xml": 7}


def is_candidate(resource: dict) -> str | None:
    """The format a resource declares, when it may hold a table; None otherwise (maps, pages, PDFs)."""
    fmt = (resource.get("format") or "").upper().strip(". ")
    url = (resource.get("url") or "").lower().split("?")[0]
    if any(w in url.rsplit("/", 1)[-1] for w in GEO_WORDS) or fmt in ("GEOJSON", "SHP", "KMZ", "KML", "WMS", "SHP-ZIP"):
        return None
    if url.endswith(".zip"):
        return "zip"
    if fmt in FORMATS:
        return FORMATS[fmt]
    for ext, kind in ((".csv", "csv"), (".parquet", "parquet"), (".xlsx", "xlsx"), (".xls", "xls"), (".ods", "ods")):
        if url.endswith(ext):
            return kind
    return None


def safe_get(url: str) -> requests.Response:  # re-exported for tests that patch the network
    return ckan.get(url, stream=True)

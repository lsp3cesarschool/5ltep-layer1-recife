"""Reading a published CSV as a stream: no raw data is ever stored or committed.

A plain CSV is read straight from the HTTP response, row by row, while its SHA-256 is
computed; nothing goes to disk. A zip must be read from disk (its directory is at the end),
so it is downloaded to a temporary file, hashed, and each CSV member is streamed from it.
Encoding and delimiter are detected from the first 64 KB; bytes that do not decode later in
the file are counted (encoding errors), not fatal.
"""

import codecs
import contextlib
import csv
import hashlib
import io
import sys
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import requests

from src import ckan, config

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))   # geometry columns hold very long cells

PEEK = 1 << 16
_decode_errors = [0]


def _count_and_replace(exc: UnicodeDecodeError):
    _decode_errors[0] += 1
    return "�", exc.end


codecs.register_error("l1count", _count_and_replace)


class NotTabular(Exception):
    """The resource is not a CSV (an HTML page, a zip without CSV members...)."""


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
    """One CSV inside a resource (the resource itself, or a member of its zip)."""
    member: str | None
    encoding: str
    delimiter: str
    rows: object               # iterator of lists of strings, header first
    decode_errors: list = field(default_factory=lambda: _decode_errors)


def _table(binary, member: str | None) -> Table:
    buffered = binary if isinstance(binary, io.BufferedReader) else io.BufferedReader(binary, PEEK * 4)
    sample = buffered.peek(PEEK)[:PEEK]
    head = sample.lstrip(codecs.BOM_UTF8 + b" \r\n\t").lower()
    if head.startswith((b"<!doctype html", b"<html")):
        raise NotTabular("the link returns an HTML page, not a CSV")
    if head.startswith(b"%pdf"):
        raise NotTabular("the file is a PDF, not a CSV")
    encoding = detect_encoding(sample)
    delimiter = detect_delimiter(sample.decode(encoding, errors="replace"))
    text = io.TextIOWrapper(buffered, encoding=encoding, errors="l1count", newline="")
    return Table(member, encoding, delimiter, csv.reader(text, delimiter=delimiter))


@dataclass
class Source:
    tables: list            # generator of Table
    digest: dict            # filled when the whole file has been read: sha256, bytes, kind


@contextlib.contextmanager
def open_resource(url: str):
    """Yields a Source; `digest` is complete once every table has been read to the end."""
    _decode_errors[0] = 0
    resp = ckan.get(url, stream=True, timeout=config.HTTP_TIMEOUT_S)
    resp.raw.decode_content = True
    hashing = HashingReader(resp.raw)
    buffered = io.BufferedReader(hashing, PEEK * 4)
    h = resp.headers
    # Change signals of the server, compared with a HEAD request in later runs (work.py).
    digest: dict = {"http": {"etag": h.get("ETag"), "last_modified": h.get("Last-Modified"),
                             "content_length": int(h["Content-Length"]) if (h.get("Content-Length") or "").isdigit() else None}}
    try:
        if buffered.peek(4)[:4] == b"PK\x03\x04":
            length = int(resp.headers.get("Content-Length") or 0)
            if length > config.MAX_ZIP_BYTES:
                raise NotTabular(f"zip of {length / 1e9:.1f} GB is above MAX_ZIP_BYTES")
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "resource.zip"
                with open(path, "wb") as fh:
                    while chunk := buffered.read(1 << 20):
                        fh.write(chunk)
                        if hashing.size > config.MAX_ZIP_BYTES:
                            raise NotTabular("zip larger than MAX_ZIP_BYTES")
                digest.update(sha256=hashing.sha.hexdigest(), bytes=hashing.size, kind="zip")
                yield Source(_zip_tables(path, digest), digest)
        else:
            def single():
                yield _table(buffered, None)
                # read whatever the CSV reader left (e.g. a trailing newline) so the hash is complete
                while buffered.read(1 << 20):
                    pass
                digest.update(sha256=hashing.sha.hexdigest(), bytes=hashing.size, kind="csv")
            yield Source(single(), digest)
    finally:
        resp.close()


def _zip_tables(path: Path, digest: dict):
    with zipfile.ZipFile(path) as zf:
        members = [i for i in zf.infolist() if not i.is_dir() and i.filename.lower().endswith((".csv", ".txt"))]
        digest["members"] = len(members)
        if not members:
            names = [i.filename for i in zf.infolist()][:5]
            raise NotTabular(f"zip without CSV members (first entries: {names})")
        for info in sorted(members, key=lambda i: i.filename):
            with zf.open(info) as raw:
                yield _table(io.BufferedReader(raw, PEEK * 4), info.filename)


def is_candidate(resource: dict) -> str | None:
    """'csv' or 'zip' when a resource may hold a CSV; None otherwise (decided from the metadata)."""
    fmt = (resource.get("format") or "").upper().strip(". ")
    url = (resource.get("url") or "").lower().split("?")[0]
    if fmt == "CSV" or url.endswith(".csv"):
        return "zip" if url.endswith(".zip") else "csv"
    if fmt in ("ZIP", "CSV.ZIP", "CSV-ZIP") and not any(w in url for w in ("shp", "shape", "kmz", "geojson")):
        return "zip"
    return None


def safe_get(url: str) -> requests.Response:  # re-exported for tests that patch the network
    return ckan.get(url, stream=True)

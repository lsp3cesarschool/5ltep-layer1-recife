"""Read-only access to a CKAN portal: the action API and the files it points to."""

import hashlib
import logging
import time

import requests

from src import config

logger = logging.getLogger(__name__)

USER_AGENT = "5ltep-layer1/0.1 (+https://github.com/lsp3cesarschool/5ltep-layer1)"
HEADERS = {"User-Agent": USER_AGENT}


def get(url: str, retries: int = 4, backoff: float = 10.0, **kwargs) -> requests.Response:
    """GET with retries: portals go down for minutes at a time."""
    kwargs.setdefault("timeout", config.HTTP_TIMEOUT_S)
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if attempt == retries or status in (401, 403, 404, 410):
                raise
            wait = backoff * 2 ** (attempt - 1)
            logger.warning("GET %s failed (%s); retrying in %.0fs", url, exc, wait)
            time.sleep(wait)
    raise AssertionError("unreachable")


def action(portal_url: str, name: str, **params) -> dict:
    return get(f"{portal_url}/api/3/action/{name}", params=params).json()["result"]


def packages(portal_url: str, rows: int = 1000) -> list[dict]:
    """Every public dataset of the portal, with its resources (package_search, paginated)."""
    out, start = [], 0
    while True:
        res = action(portal_url, "package_search", rows=rows, start=start)
        out += res["results"]
        start += rows
        if start >= res["count"] or not res["results"]:
            return sorted(out, key=lambda p: p["name"])


def datastore_fields(portal_url: str, resource_id: str) -> list[dict] | None:
    """Field ids and types the DataStore exposes for a resource (None if not readable)."""
    # include_total=false: only the fields, without counting the rows of a large table;
    # a short timeout and two attempts, so that a slow DataStore does not hold the census.
    try:
        res = get(f"{portal_url}/api/3/action/datastore_search", retries=2, backoff=5.0, timeout=60,
                  params={"resource_id": resource_id, "limit": 0, "include_total": "false"}).json()["result"]
    except (requests.RequestException, KeyError, ValueError) as exc:
        logger.info("DataStore of %s not readable: %s", resource_id, exc)
        return None
    return [{"id": f["id"], "type": f.get("type")} for f in res.get("fields", []) if f.get("id") != "_id"]


def head(url: str) -> dict:
    """Change signals the file server gives without a download (any of them may be missing)."""
    try:
        resp = requests.head(url, headers=HEADERS, timeout=60, allow_redirects=True)
    except requests.RequestException as exc:
        return {"error": str(exc)[:200]}
    h = resp.headers
    return {"status": resp.status_code, "etag": h.get("ETag"), "last_modified": h.get("Last-Modified"),
            "content_length": int(h["Content-Length"]) if (h.get("Content-Length") or "").isdigit() else None}


def fetch_bytes(url: str, limit: int) -> tuple[bytes, str]:
    """Small files (dictionaries): content and SHA-256; larger than `limit` raises ValueError."""
    resp = get(url, stream=True)
    sha, chunks, size = hashlib.sha256(), [], 0
    deadline = time.monotonic() + config.DICTIONARY_DEADLINE_S
    for chunk in resp.iter_content(1 << 16):
        if time.monotonic() > deadline:
            resp.close()
            raise requests.Timeout(f"still downloading after {config.DICTIONARY_DEADLINE_S} s")
        size += len(chunk)
        if size > limit:
            resp.close()
            raise ValueError(f"larger than {limit} bytes")
        sha.update(chunk)
        chunks.append(chunk)
    return b"".join(chunks), sha.hexdigest()

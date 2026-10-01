"""Safety checks between untrusted inputs and the repository.

Threat model (as in Layer 3, SECURITY section of the README): the portal's files, the PDF
dictionaries and the LLM are not trusted. So:

- the job that downloads files and runs the model has a read-only token and hands its results
  over as an artifact; the job that writes to the repository accepts only the expected paths,
  for datasets and resources that exist in the committed census, with the expected structure
  and bounded sizes (`accept_artifact`), and never runs the model;
- schemas must be valid Frictionless Table Schemas with bounded names and texts; schemas the
  model produced can only arrive as "suggested" (they go to a pull request, never to main);
- text that reaches a GitHub Issue is neutralised (`safe_markdown`); the dashboard escapes
  everything it shows.
"""

import json
import re
import shutil
from pathlib import Path

MAX_FILE_BYTES = 80_000_000
MAX_FIELDS = 3000
MAX_TEXT = 2000
DATASET_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,99}$")
RESOURCE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
VALIDATION_STATUS = {"ok", "empty", "error", "not-tabular"}
EXTRACTION_OUTCOMES = {"extracted", "suggested", "llm-needed", "failed"}
# Ollama tags (qwen3:8b, gemma3:4b-it-q4_K_M, namespace/model:tag): they reach a shell and $GITHUB_ENV.
MODEL_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}(/[a-z0-9][a-z0-9._-]{0,63})?(:[A-Za-z0-9][A-Za-z0-9._-]{0,63})?$")
DIGEST_RE = re.compile(r"^(sha256:)?[0-9a-f]{64}$")
THINK_VALUES = {"", "true", "false"}


def valid_model(name) -> bool:
    return isinstance(name, str) and bool(MODEL_RE.match(name))


def valid_digest(digest) -> bool:
    return digest in (None, "") or (isinstance(digest, str) and bool(DIGEST_RE.match(digest)))


CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f‪-‮⁦-⁩]")


def clean_text(text, limit: int) -> str:
    text = CONTROL_RE.sub("", str(text or ""))
    return text if len(text) <= limit else text[:limit] + " […]"


def safe_markdown(text, limit: int = 300) -> str:
    """Untrusted text inside a GitHub Issue: no HTML, links, images, mentions, references or tables."""
    text = clean_text(text, limit).replace("\r", " ").replace("\n", " ")
    text = (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                .replace("|", "/").replace("`", "'"))
    text = re.sub(r"!?\[([^\]]*)\]\(([^)]*)\)", r"\1 (\2)", text)
    text = re.sub(r"(?<![\w`])@(?=\w)", "@​", text)
    text = re.sub(r"(?<![\w&])#(?=\d)", "#​", text)
    text = re.sub(r"https?://", lambda m: m.group(0).replace("://", ":​//"), text)
    return text


def check_schema(schema: dict, status: set[str]) -> None:
    from frictionless import Schema

    if not isinstance(schema, dict) or not isinstance(schema.get("fields"), list):
        raise ValueError("schema: no field list")
    if len(schema["fields"]) > MAX_FIELDS:
        raise ValueError("schema: too many fields")
    if (schema.get("x5ltep") or {}).get("status") not in status:
        raise ValueError(f"schema: status must be one of {sorted(status)}")
    for f in schema["fields"]:
        for key, value in f.items():
            if isinstance(value, str) and (len(value) > MAX_TEXT or CONTROL_RE.search(value)):
                raise ValueError(f"schema: {key} too long or with control characters")
        if not isinstance(f.get("name"), str) or not 0 < len(f["name"]) <= 128:
            raise ValueError("schema: bad field name")
    Schema.from_descriptor({k: v for k, v in schema.items() if k != "x5ltep"})


def _known(census: dict) -> tuple[set, set, set]:
    pairs = {(ds["name"], t["id"]) for ds in census["datasets"] for t in ds["tables"]}
    dicts = {d["id"] for ds in census["datasets"] for d in ds["dictionaries"]}
    return pairs, {rid for _, rid in pairs}, dicts


def _schema_path(rel: str) -> tuple[str, str, str, str] | None:
    m = re.match(r"^(schemas|suggestions)/([^/]+)/([^/.]+)\.(observed|extracted)\.json$", rel)
    return m.groups() if m else None


def accept_artifact(src: Path, root: Path, census: dict, committed_drift: list[dict]) -> list[str]:
    """Validate the files handed over by the analysis job and copy them into `root`.

    Suggestions (schemas the LLM or a partial extraction produced) are copied to
    root/suggestions/, which is not committed: the workflow opens a pull request with them.
    """
    pairs, rids, dict_ids = _known(census)
    fixed = {"results/validation.json", "results/extraction.json", "results/drift.json",
             "results/run_log.jsonl", "results/done.json", "chain.json"}
    accepted = []
    for path in sorted(p for p in src.rglob("*") if p.is_file()):
        rel = path.relative_to(src).as_posix()
        if path.stat().st_size > MAX_FILE_BYTES:
            raise ValueError(f"{rel}: too large")
        parsed = _schema_path(rel)
        if rel not in fixed and not parsed:
            raise ValueError(f"artifact contains an unexpected file: {rel}")
        if parsed:
            folder, dataset, rid, kind = parsed
            if not DATASET_RE.match(dataset) or not RESOURCE_RE.match(rid):
                raise ValueError(f"{rel}: unexpected dataset or resource name")
            if (dataset, rid) not in pairs:
                continue    # a resource the portal removed since the census: never written
            if folder == "suggestions" and kind != "extracted":
                raise ValueError(f"{rel}: only extracted schemas can be suggested")
            status = {"observed"} if kind == "observed" else {"extracted"} if folder == "schemas" else {"suggested"}
            check_schema(json.loads(path.read_text(encoding="utf-8")), status)
        elif rel == "results/validation.json":
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("validation: not an object")
            for rid, v in data.items():
                if not RESOURCE_RE.match(rid) or not isinstance(v, dict) or v.get("status") not in VALIDATION_STATUS:
                    raise ValueError(f"validation: unexpected entry {rid!r}")
        elif rel == "results/extraction.json":
            data = json.loads(path.read_text(encoding="utf-8"))
            for did, rec in data.items():
                if did not in dict_ids and not RESOURCE_RE.match(did):
                    raise ValueError("extraction: unknown dictionary")
                if not isinstance(rec, dict) or rec.get("outcome") not in EXTRACTION_OUTCOMES:
                    raise ValueError(f"extraction: unexpected record {did!r}")
        elif rel == "results/drift.json":
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, list) or data[:len(committed_drift)] != committed_drift:
                raise ValueError("drift: the log is append-only")
            for e in data[len(committed_drift):]:
                if e.get("kind") != "observed" or e.get("resource_id") not in rids:
                    raise ValueError("drift: unexpected event")
        elif rel == "results/done.json":
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, list) or not all(isinstance(x, str) and RESOURCE_RE.match(x) for x in data):
                raise ValueError("done: not a list of resource ids")
        elif rel.endswith(".jsonl"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    json.loads(line)
        else:  # chain.json
            json.loads(path.read_text(encoding="utf-8"))
        dest = root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
        accepted.append(rel)
    return accepted

"""Method parameters and the portal this instance evaluates.

*Which* portal is evaluated lives in portal.json at the repository root: its
"portal_url" is the only value an instance for another CKAN portal has to
change. *How* it is evaluated is configured here. Every value is overridable by
an environment variable of the same name, so a GitHub Actions run can be tuned
without code changes; the values actually used are recorded in each summary.
"""

import json
import os
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
PORTAL_FILE = ROOT / "portal.json"


def _env(name: str, default):
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return type(default)(raw)


def portal() -> dict:
    """portal.json, with CKAN_PORTAL_URL (environment) taking precedence for local trials."""
    raw = json.loads(PORTAL_FILE.read_text(encoding="utf-8")) if PORTAL_FILE.exists() else {}
    url = (os.environ.get("CKAN_PORTAL_URL") or raw.get("portal_url") or "").rstrip("/")
    if not url.startswith(("https://", "http://")):
        raise ValueError("portal.json must give the portal's root URL in \"portal_url\"")
    host = urlparse(url).hostname or url
    return {"portal_url": url, "name": raw.get("name") or host, "title": raw.get("title") or host}


# --- Paths (all committed by the bot, except raw data, which is never stored) ----
RESULTS = ROOT / "results"
SCHEMAS = ROOT / "schemas"
CENSUS_FILE = RESULTS / "census.json"
VALIDATION_FILE = RESULTS / "validation.json"
EXTRACTION_FILE = RESULTS / "extraction.json"
QUEUE_FILE = RESULTS / "queue.json"
DRIFT_FILE = RESULTS / "drift.json"
SUMMARY_FILE = RESULTS / "layer1_summary.json"
HISTORY_FILE = RESULTS / "history.json"          # one compact row per weekly chain
RUN_LOG = RESULTS / "run_log.jsonl"
DASHBOARD_FILE = ROOT / "docs" / "data" / "layer1.json"

# --- Census -----------------------------------------------------------------
HTTP_TIMEOUT_S = _env("HTTP_TIMEOUT_S", 120)          # reading an answer
CONNECT_TIMEOUT_S = _env("CONNECT_TIMEOUT_S", 15)      # opening a connection
MAX_DICTIONARY_BYTES = _env("MAX_DICTIONARY_BYTES", 2_000_000_000)   # read in memory (runner: 16 GB RAM)
CHECK_DATASTORE = _env("CHECK_DATASTORE", "true").lower() == "true"
CENSUS_WORKERS = _env("CENSUS_WORKERS", 4)            # datasets read at the same time (network-bound; polite)
DICTIONARY_DEADLINE_S = _env("DICTIONARY_DEADLINE_S", 180)   # a dictionary that trickles longer is given up
# A dictionary whose server did not answer is asked again after 5, 10 and 20 minutes (35 in all).
DICTIONARY_RETRY_ROUNDS = _env("DICTIONARY_RETRY_ROUNDS", 3)
DICTIONARY_RETRY_WAIT_S = _env("DICTIONARY_RETRY_WAIT_S", 300)
UNREACHABLE_STREAK = _env("UNREACHABLE_STREAK", 8)     # failures in a row before the survey stops asking the file server
# Reading the headers of files never validated (a zip is downloaded whole) stops after this long: the
# survey runs in one job of at most 300 minutes, and its work is lost if the job is stopped.
SURVEY_HEADER_MAX_MINUTES = _env("SURVEY_HEADER_MAX_MINUTES", 180)
DELIVERY_PROBES = _env("DELIVERY_PROBES", 3)          # files per server asked for a byte range in each survey

# --- Validation ---------------------------------------------------------------
# Time budget of one batch (the GitHub job limit is 6 h; the rest of the job needs some minutes).
VALIDATE_MAX_MINUTES = _env("VALIDATE_MAX_MINUTES", 270.0)
# Files validated at the same time, each in its own process, from the disk (the validation of a zip
# is CPU-bound: 03/10/2026, downloaded at 6-23 MB/s, validated at 1.4-1.9 MB/s; the runner has 4
# vCPUs). Downloads are one at a time per server (work.run_batch): three at once made ANEEL's slower.
VALIDATE_WORKERS = _env("VALIDATE_WORKERS", 3)
# A resource unchanged on the portal is validated again after this many days anyway, so that
# every file is re-checked at least once a month even when the portal gives no change signal.
ROTATION_DAYS = _env("ROTATION_DAYS", 28)
SAMPLE_ROWS = _env("SAMPLE_ROWS", 5000)            # rows used to infer the observed types
# Zips, spreadsheets and Parquet are read from disk when they fit (runner: ~14 GB free); a zip that does
# not is read as it streams, member by member; a Parquet or a spreadsheet that does not cannot be read.
MAX_ZIP_BYTES = _env("MAX_ZIP_BYTES", 12_000_000_000)
ZIP_MAX_DEPTH = _env("ZIP_MAX_DEPTH", 5)    # zips inside zips (a guard against a zip that nests itself)
# The first members (this many) of a zip are read as it downloads. A zip is read to its end first;
# if its download fails and none of those members was a table, it is recorded as a container of
# documents by sample (a fail-safe: without byte ranges, as on Recife's server, only the whole zip
# proves it holds no table). ZIP_STOP_AT_SAMPLE=1 stops every such download at the sample instead.
# 0: no sample.
ZIP_DOCUMENTS_SAMPLE = _env("ZIP_DOCUMENTS_SAMPLE", 50)
ZIP_STOP_AT_SAMPLE = _env("ZIP_STOP_AT_SAMPLE", 0)
# Files of a dataset with the same name, declared size and file name are copies of one file (Recife
# publishes some three times). 0: every copy is downloaded and compared by its SHA-256; a copy whose
# download fails gets the first one's result, marked as such (a fail-safe). 1: only the first is
# downloaded, the others get its result.
COPIES_ONCE = _env("COPIES_ONCE", 0)

ERROR_ROWS_KEPT = _env("ERROR_ROWS_KEPT", 5)        # row numbers kept per field and error kind (never values)
# A resource conforms when every declared field is in the file, the file has no undeclared
# field, and at most this share of the checked cells breaks the declared type or constraints.
L1_MAX_ERROR_RATE = _env("L1_MAX_ERROR_RATE", 0.01)
# Layer 1 passes (for Layer 5) when this share of the verifiable resources conforms.
L1_PASS_THRESHOLD = _env("L1_PASS_THRESHOLD", 0.85)

# --- PDF dictionaries: deterministic, then LLM, then human review ------------
# The file's own header is the oracle: share of header columns found among the extracted
# names (recall) and of extracted names found in the header (precision).
ORACLE_ACCEPT = _env("ORACLE_ACCEPT", 1.0)          # deterministic result accepted without review
ORACLE_LLM_BELOW = _env("ORACLE_LLM_BELOW", 0.8)    # below this the LLM tries too
OLLAMA_URL = _env("OLLAMA_URL", "http://127.0.0.1:11434")
# "auto" (default): the model the Layer 1 model benchmark (5ltep-layer1-modeltest) approves, read
# from its public recommendation.json at the start of each run; a tag pins the model instead.
LLM_MODEL = _env("LLM_MODEL", "auto")
LLM_THINK = _env("LLM_THINK", "")
LLM_MODEL_SOURCE = _env("LLM_MODEL_SOURCE", "pinned" if LLM_MODEL != "auto" else "auto")
FALLBACK_MODEL = _env("FALLBACK_MODEL", "qwen3:8b")     # until the benchmark publishes, or if unreadable
FALLBACK_THINK = _env("FALLBACK_THINK", "false")
MODEL_RECOMMENDATION_URL = _env(
    "MODEL_RECOMMENDATION_URL",
    "https://raw.githubusercontent.com/lsp3cesarschool/5ltep-layer1-modeltest/main/results/recommendation.json")
LLM_SEED = _env("LLM_SEED", 42)
LLM_NUM_CTX = _env("LLM_NUM_CTX", 16384)
LLM_NUM_PREDICT = _env("LLM_NUM_PREDICT", 6000)
LLM_TIMEOUT_S = _env("LLM_TIMEOUT_S", 1800)
# A PDF goes to the model whole, in pieces of at most this many characters: ~7,000 tokens, which with the
# instructions and an answer of up to LLM_NUM_PREDICT tokens fits in LLM_NUM_CTX (Ollama would otherwise
# drop the start of the input). An answer cut by LLM_NUM_PREDICT is asked again with the piece in halves.
LLM_MAX_PDF_CHARS = _env("LLM_MAX_PDF_CHARS", 20000)
EXTRACT_MAX_MINUTES = _env("EXTRACT_MAX_MINUTES", 120.0)
# Bump when the extraction prompt changes meaning; earlier suggestions keep the version they had.
EXTRACTION_PROMPT_VERSION = "v1"
# Bump when the deterministic PDF reader reads more: every PDF is read again by it (v2, 03/10/2026: cells
# the table's grid does not draw, as Recife's "Campo" column; the type is the cell that is most a type).
PDF_READER_VERSION = "v2"

# --- Drift review (GitHub Issues) -------------------------------------------
ISSUE_LABEL = "layer1"
MAX_NEW_ISSUES = _env("MAX_NEW_ISSUES", 15)


def method_parameters() -> dict:
    names = ["ROTATION_DAYS", "SAMPLE_ROWS", "L1_MAX_ERROR_RATE", "L1_PASS_THRESHOLD", "ORACLE_ACCEPT",
             "ORACLE_LLM_BELOW", "LLM_MODEL", "LLM_SEED", "EXTRACTION_PROMPT_VERSION",
             "PDF_READER_VERSION", "ZIP_DOCUMENTS_SAMPLE", "ZIP_STOP_AT_SAMPLE", "COPIES_ONCE"]
    return {n.lower(): globals()[n] for n in names}

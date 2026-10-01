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
MAX_DICTIONARY_BYTES = _env("MAX_DICTIONARY_BYTES", 20_000_000)   # a dictionary larger than this is not read
CHECK_DATASTORE = _env("CHECK_DATASTORE", "true").lower() == "true"
CENSUS_WORKERS = _env("CENSUS_WORKERS", 4)            # datasets read at the same time (network-bound; polite)
DICTIONARY_DEADLINE_S = _env("DICTIONARY_DEADLINE_S", 180)   # a dictionary that trickles longer is given up

# --- Validation ---------------------------------------------------------------
# Time budget of one batch (the GitHub job limit is 6 h; the rest of the job needs some minutes).
VALIDATE_MAX_MINUTES = _env("VALIDATE_MAX_MINUTES", 270.0)
# A resource unchanged on the portal is validated again after this many days anyway, so that
# every file is re-checked at least once a month even when the portal gives no change signal.
ROTATION_DAYS = _env("ROTATION_DAYS", 28)
SAMPLE_ROWS = _env("SAMPLE_ROWS", 5000)            # rows used to infer the observed types
MAX_ZIP_BYTES = _env("MAX_ZIP_BYTES", 12_000_000_000)  # zip files must go to disk (runner: ~14 GB free)
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
LLM_MAX_PDF_CHARS = _env("LLM_MAX_PDF_CHARS", 30000)
EXTRACT_MAX_MINUTES = _env("EXTRACT_MAX_MINUTES", 120.0)
# Bump when the extraction prompt changes meaning; earlier suggestions keep the version they had.
EXTRACTION_PROMPT_VERSION = "v1"

# --- Drift review (GitHub Issues) -------------------------------------------
ISSUE_LABEL = "layer1"
MAX_NEW_ISSUES = _env("MAX_NEW_ISSUES", 15)


def method_parameters() -> dict:
    names = ["ROTATION_DAYS", "SAMPLE_ROWS", "L1_MAX_ERROR_RATE", "L1_PASS_THRESHOLD", "ORACLE_ACCEPT",
             "ORACLE_LLM_BELOW", "LLM_MODEL", "LLM_SEED", "EXTRACTION_PROMPT_VERSION"]
    return {n.lower(): globals()[n] for n in names}

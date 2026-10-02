"""Turning PDF dictionaries into schemas, stage by stage, with the file's header as the oracle.

For every PDF dictionary linked to at least one tabular resource (results/extraction.json
keeps one record per dictionary, keyed by the PDF's SHA-256, so a PDF is processed again only
when it changes):

  deterministic  agreement with the header >= ORACLE_ACCEPT  -> "extracted": used right away
                 ORACLE_LLM_BELOW <= agreement < ORACLE_ACCEPT -> "suggested": pull request
                 lower, or no table found                      -> "llm-needed"
  llm            the best of both stages                       -> "suggested": pull request
                 nothing extracted                             -> "failed" (stays at level 1)

The LLM never decides: whatever it produces goes to a pull request, and only a person turns
"suggested" into "verified" (the same rule as the event calendar of Layer 3). Agreement is
min(recall, precision) of the extracted names against the header (pdf_extract.oracle).
"""

import logging
import time
from collections import Counter

from src import ckan, config, pdf_extract, safety, schemas

logger = logging.getLogger(__name__)


def header_for(linked: list[str], validation: dict) -> tuple[list[str] | None, bool]:
    """(most common header among the linked resources, every linked resource already validated)."""
    headers = [tuple(validation[r]["header"]) for r in linked if (validation.get(r) or {}).get("header")]
    all_done = all(r in validation for r in linked)
    return (list(Counter(headers).most_common(1)[0][0]) if headers else None), all_done


def tasks(census: dict, validation: dict, extraction: dict, stage: str) -> list[dict]:
    out = []
    for ds in census["datasets"]:
        for d in ds["dictionaries"]:
            if d.get("format") != "PDF" or not d.get("sha256") or not d.get("linked_resources"):
                continue
            header, all_done = header_for(d["linked_resources"], validation)
            if header is None and not all_done:
                continue          # the oracle is not ready yet: wait for the validation
            rec = extraction.get(d["id"])
            if stage == "deterministic" and (not rec or rec.get("sha256") != d["sha256"]):
                out.append({"dataset": ds["name"], "dictionary": d, "header": header})
            elif (stage == "llm" and rec and rec.get("sha256") == d["sha256"] and rec.get("outcome") == "llm-needed"
                  and not ((rec.get("llm") or {}).get("model") == config.LLM_MODEL
                           and (rec.get("llm") or {}).get("prompt_version") == config.EXTRACTION_PROMPT_VERSION)):
                out.append({"dataset": ds["name"], "dictionary": d, "header": header})
    return out


def _schemas_for(task: dict, fields: list[dict], status: str, stage: str, oracle: dict, llm_info: dict | None) -> dict:
    d = task["dictionary"]
    source = {"kind": "pdf", "stage": stage, "dictionary_id": d["id"], "dictionary_name": d["name"],
              "url": d["url"], "sha256": d["sha256"],
              "oracle": {k: oracle.get(k) for k in ("recall", "precision", "exact_match", "levenshtein",
                                                    "missing_from_pdf", "not_in_file") if k in oracle}}
    if llm_info:
        source.update({k: llm_info.get(k) for k in ("model", "model_digest", "prompt_version", "ollama_version")})
    schema = schemas.from_fields(fields, status, source)
    return {(task["dataset"], rid): schema for rid in d["linked_resources"]}


def _pdf(task: dict) -> bytes:
    data, sha = ckan.fetch_bytes(task["dictionary"]["url"], config.MAX_DICTIONARY_BYTES)
    if sha != task["dictionary"]["sha256"]:
        logger.info("%s changed since the census; extracting the current version", task["dictionary"]["id"])
        task["dictionary"] = {**task["dictionary"], "sha256": sha}
    return data


def run_deterministic(todo: list[dict], extraction: dict) -> dict:
    """Returns {"extracted": {(dataset, rid): schema}, "suggested": {...}}; updates `extraction`."""
    out = {"extracted": {}, "suggested": {}}
    for task in todo:
        d = task["dictionary"]
        try:
            pdf = _pdf(task)
        except Exception as exc:
            extraction[d["id"]] = {"sha256": d["sha256"], "outcome": "failed", "error": str(exc)[:200]}
            continue
        fields = pdf_extract.deterministic(pdf)
        oracle = pdf_extract.oracle(fields, task["header"]) if task["header"] else {"available": False}
        agree = pdf_extract.agreement(oracle)
        if fields and oracle.get("available") and agree >= config.ORACLE_ACCEPT:
            outcome = "extracted"
        elif fields and (agree >= config.ORACLE_LLM_BELOW or not oracle.get("available")):
            outcome = "suggested"
        else:
            outcome = "llm-needed"
        rec = {"sha256": task["dictionary"]["sha256"], "dataset": task["dataset"], "linked_resources": d["linked_resources"],
               "outcome": outcome, "stage": "deterministic",
               "deterministic": {"fields": len(fields), "oracle": oracle}, "at": _now()}
        extraction[d["id"]] = rec
        if outcome in ("extracted", "suggested"):
            out[outcome].update(_schemas_for(task, fields, outcome, "deterministic", oracle, None))
            rec["fields"] = [f["name"] for f in fields]
        else:
            rec["candidate"] = fields      # kept for the LLM stage to compare with
    return out


def run_llm(todo: list[dict], extraction: dict, client, minutes: float) -> dict:
    out = {"suggested": {}}
    info = client.info()
    deadline = time.monotonic() + minutes * 60
    for task in todo:
        if time.monotonic() > deadline:
            break
        d = task["dictionary"]
        rec = extraction[d["id"]]
        try:
            fields, meta = pdf_extract.llm(_pdf(task), client)
        except Exception as exc:
            fields, meta = [], {"error": safety.error_text(exc, 200)}
        oracle = pdf_extract.oracle(fields, task["header"]) if task["header"] else {"available": False}
        rec["llm"] = {"model": config.LLM_MODEL, "model_source": config.LLM_MODEL_SOURCE,
                      "model_digest": info.get("model_digest"),
                      "ollama_version": info.get("ollama_version"), "prompt_version": config.EXTRACTION_PROMPT_VERSION,
                      "fields": len(fields), "oracle": oracle, **meta}
        det_fields = rec.pop("candidate", [])
        det_oracle = rec["deterministic"]["oracle"]
        use_llm = bool(fields) and pdf_extract.agreement(oracle) >= pdf_extract.agreement(det_oracle)
        best, best_oracle, stage = (fields, oracle, "llm") if use_llm else (det_fields, det_oracle, "deterministic")
        if best:
            rec.update(outcome="suggested", stage=stage, fields=[f["name"] for f in best])
            out["suggested"].update(_schemas_for(task, best, "suggested", stage, best_oracle,
                                                 {**rec["llm"], **info} if stage == "llm" else None))
        else:
            rec.update(outcome="failed")
    return out


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds")

"""Which LLM reads the PDF dictionaries in this run.

LLM_MODEL="auto" (default) follows the Layer 1 model benchmark (5ltep-layer1-modeltest): its public
recommendation.json has a "use" field, the model it approves for this task (it changes only when a
candidate beats the current one by a margin whose paired confidence interval is above zero). A tag
in LLM_MODEL pins the model instead. Until the benchmark has published, or if it cannot be read,
FALLBACK_MODEL is used, and every extraction records which model, and from where, produced it.
"""

import logging

import requests

from src import config, safety

logger = logging.getLogger(__name__)


def resolve() -> dict:
    """{"model", "think", "source", "digest"} for this run; also applied to src.config."""
    if config.LLM_MODEL != "auto":
        if not safety.valid_model(config.LLM_MODEL) or config.LLM_THINK.lower() not in safety.THINK_VALUES:
            raise ValueError(f"LLM_MODEL / LLM_THINK not valid: {config.LLM_MODEL!r} / {config.LLM_THINK!r}")
        out = {"model": config.LLM_MODEL, "think": config.LLM_THINK.lower(), "source": "pinned", "digest": ""}
    else:
        try:
            rec = requests.get(config.MODEL_RECOMMENDATION_URL, timeout=30).json()
            use = rec.get("use") or {}
            if not use.get("model"):
                raise ValueError("recommendation without a model")
            if use.get("backend", "ollama") != "ollama":
                raise ValueError(f"recommended back-end {use.get('backend')!r} does not run in production")
            if not safety.valid_model(use["model"]) or not safety.valid_digest(use.get("digest")):
                raise ValueError("recommended model name or digest does not match the expected pattern")
            think = (use.get("options") or {}).get("think")
            think = config.LLM_THINK or ("" if think is None else str(think).lower())
            if think not in safety.THINK_VALUES:
                raise ValueError("recommended think option not valid")
            out = {"model": use["model"], "think": think, "source": "benchmark", "digest": use.get("digest") or "",
                   "benchmark_generated_at": rec.get("generated_at")}
        except (requests.RequestException, ValueError) as exc:
            logger.warning("Model benchmark not readable (%s); using the fallback %s", exc, config.FALLBACK_MODEL)
            out = {"model": config.FALLBACK_MODEL, "think": config.LLM_THINK or config.FALLBACK_THINK,
                   "source": "fallback", "digest": ""}
    config.LLM_MODEL, config.LLM_THINK, config.LLM_MODEL_SOURCE = out["model"], out["think"], out["source"]
    return out

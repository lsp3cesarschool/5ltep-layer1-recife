"""Quality of the PDF dictionary extraction, per stage, against the oracle (the file's header).

Reads results/extraction.json and writes evaluation/results/pdf_extraction.{json,txt}:
for each stage (deterministic, LLM), how many PDFs had an oracle, and the mean recall,
precision, exact match (EM) and normalised Levenshtein similarity (LS) of the extracted
field names, the metrics of Al Hilmi et al. (2026), arXiv:2604.00003. Also the outcomes
(extracted, suggested, llm-needed, failed) and the share of PDFs each stage resolved.

    python evaluation/pdf_extraction.py
"""

import json
import sys
from pathlib import Path
from statistics import mean, median

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import config  # noqa: E402

METRICS = ("recall", "precision", "exact_match", "levenshtein")


def stage_stats(oracles: list[dict]) -> dict:
    with_oracle = [o for o in oracles if o.get("available")]
    out = {"pdfs": len(oracles), "with_oracle": len(with_oracle)}
    for m in METRICS:
        vals = [o[m] for o in with_oracle if o.get(m) is not None]
        out[m] = {"mean": round(mean(vals), 4) if vals else None,
                  "median": round(median(vals), 4) if vals else None,
                  "perfect": sum(v == 1.0 for v in vals)}
    return out


def main() -> None:
    extraction = json.loads(config.EXTRACTION_FILE.read_text(encoding="utf-8")) if config.EXTRACTION_FILE.exists() else {}
    recs = [r for r in extraction.values() if r.get("deterministic")]
    det = [r["deterministic"]["oracle"] for r in recs]
    llm = [r["llm"]["oracle"] for r in recs if (r.get("llm") or {}).get("oracle")]
    outcomes: dict[str, int] = {}
    for r in recs:
        outcomes[r["outcome"]] = outcomes.get(r["outcome"], 0) + 1
    result = {"portal": config.portal()["portal_url"], "pdfs": len(recs), "outcomes": outcomes,
              "deterministic": stage_stats(det), "llm": stage_stats(llm),
              "llm_models": sorted({r["llm"].get("model") for r in recs if r.get("llm")} - {None})}
    out_dir = ROOT / "evaluation" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "pdf_extraction.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    lines = [f"PDF dictionary extraction: {result['portal']}", f"PDFs processed: {len(recs)}  outcomes: {outcomes}", "",
             f"{'stage':<14}{'n':>5}{'oracle':>8}" + "".join(f"{m:>14}" for m in METRICS)]
    for name, s in (("deterministic", result["deterministic"]), ("llm", result["llm"])):
        lines.append(f"{name:<14}{s['pdfs']:>5}{s['with_oracle']:>8}"
                     + "".join(f"{(s[m]['mean'] if s[m]['mean'] is not None else '-'):>14}" for m in METRICS))
    text = "\n".join(lines) + "\n"
    (out_dir / "pdf_extraction.txt").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()

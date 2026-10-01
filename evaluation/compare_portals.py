"""Side-by-side comparison of the Layer 1 instances (IBAMA, ANEEL, Recife), from their public summaries.

Each instance publishes results/layer1_summary.json; this script reads them over HTTPS (no token,
the same "pull" contract Layer 5 uses) and prints one table with the maturity distribution,
conformance and the main documentation findings, ready for the thesis. Writes
evaluation/results/compare_portals.{json,md}.

    python evaluation/compare_portals.py
    python evaluation/compare_portals.py --local ../.trial/ibama ../.trial/aneel   # summaries on disk
"""

import argparse
import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
REPOS = {
    "IBAMA": "lsp3cesarschool/5ltep-layer1",
    "ANEEL": "lsp3cesarschool/5ltep-layer1-aneel",
    "Recife": "lsp3cesarschool/5ltep-layer1-recife",
}


def load(args) -> dict[str, dict]:
    if args.local:
        out = {}
        for folder in args.local:
            s = json.loads((Path(folder) / "results" / "layer1_summary.json").read_text(encoding="utf-8"))
            out[s["portal"]["name"]] = s
        return out
    out = {}
    for name, repo in REPOS.items():
        url = f"https://raw.githubusercontent.com/{repo}/main/results/layer1_summary.json"
        try:
            out[name] = requests.get(url, timeout=60).json()
        except (requests.RequestException, ValueError) as exc:
            print(f"{name}: not available ({exc})")
    return out


def pct(x) -> str:
    return "—" if x is None else f"{x * 100:.1f}%"


def rows(summaries: dict[str, dict]) -> list[tuple[str, list[str]]]:
    def get(s, *path, default=None):
        for p in path:
            s = (s or {}).get(p) if isinstance(s, dict) else None
        return default if s is None else s

    def share(s, n_path, d_path):
        n, d = get(s, *n_path, default=0), get(s, *d_path, default=0)
        return pct(n / d) if d else "—"

    spec = [
        ("Datasets", lambda s: str(get(s, "datasets", "total"))),
        ("Tabular files", lambda s: str(get(s, "tables", "total"))),
        *[(f"Files at level {lv}", (lambda lv: lambda s: share(s, ("tables", "by_level", str(lv)), ("tables", "total")))(lv))
          for lv in range(5)],
        ("Files validated", lambda s: pct(get(s, "tables", "validation_coverage"))),
        ("Verifiable files", lambda s: str(get(s, "verifiable"))),
        ("l1_rate (conformant / verifiable)", lambda s: pct(get(s, "l1_rate"))),
        ("Dictionaries", lambda s: str(get(s, "findings", "dictionaries", "total"))),
        ("  machine-readable and read", lambda s: str(get(s, "findings", "dictionaries", "machine_readable_and_read"))),
        ("  for people only", lambda s: str(get(s, "findings", "dictionaries", "human_readable"))),
        ("  unreadable, by reason", lambda s: json.dumps(get(s, "findings", "dictionaries", "unreadable_by_reason", default={}))),
        ("  naming the files they describe", lambda s: str(get(s, "findings", "dictionaries", "declaring_resource_ids"))),
        ("Links by method", lambda s: json.dumps(get(s, "findings", "links", "by_method", default={}))),
        ("Distinct spellings of a type", lambda s: str(get(s, "findings", "types", "distinct_spellings"))),
        ("Fields with a recognised type", lambda s: pct(get(s, "findings", "types", "fields_with_recognised_type"))),
        ("Date fields with a declared format", lambda s: pct(get(s, "findings", "types", "date_fields_with_declared_format"))),
        ("Files missing declared fields", lambda s: str(get(s, "findings", "files_vs_dictionaries", "with_declared_fields_missing"))),
        ("Files with undeclared columns", lambda s: str(get(s, "findings", "files_vs_dictionaries", "with_undeclared_columns"))),
        ("PDF extraction, recall (deterministic)", lambda s: pct(get(s, "findings", "pdf_extraction", "deterministic", "recall"))),
        ("PDF extraction, recall (LLM)", lambda s: pct(get(s, "findings", "pdf_extraction", "llm", "recall"))),
        ("Drift events (observed / declared)", lambda s: f"{get(s, 'drift', 'observed', default=0)} / {get(s, 'drift', 'declared', default=0)}"),
    ]
    return [(label, [fn(s) for s in summaries.values()]) for label, fn in spec]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--local", nargs="*", help="instance folders with results/layer1_summary.json")
    summaries = load(ap.parse_args())
    if not summaries:
        return
    table = rows(summaries)
    names = list(summaries)
    md = ["| | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    md += [f"| {label} | " + " | ".join(vals) + " |" for label, vals in table]
    md.append("")
    md.append("Summaries generated at: " + ", ".join(f"{n} {s.get('generated_at')}" for n, s in summaries.items()))
    out = ROOT / "evaluation" / "results"
    out.mkdir(parents=True, exist_ok=True)
    (out / "compare_portals.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    by_portal = {n: {label: vals[i] for label, vals in table} for i, n in enumerate(names)}
    (out / "compare_portals.json").write_text(json.dumps(by_portal, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()

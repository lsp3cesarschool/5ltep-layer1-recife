"""5L-TEP Layer 1 (Structural Contracts) pipeline.

Stages, each a sub-command so GitHub Actions can run them as separate steps:

  census           every dataset on the maturity scale; reads the dictionaries; writes the
                   declared schemas; plans the work queue
  validate         validate queued files against their schemas, for at most --minutes
  extract          PDF dictionaries: --stage deterministic, then --stage llm (Ollama)
  resolve-model    LLM_MODEL=auto -> the model the Layer 1 benchmark approves (exported to later steps)
  accept-artifact  (write job) accept what the read-only job handed over
  issues           open GitHub Issues for schema drift
  suggestions-pr   body of the pull request with suggested schemas
  report           summary for Layer 5, documentation findings, dashboard data
  status           status badge (running / interrupted)
  run              census + extract (deterministic) + validate + report, locally

Examples:
  python main.py census
  python main.py validate --minutes 30
  python main.py run --minutes 20
  CKAN_PORTAL_URL=https://dados.recife.pe.gov.br python main.py census   # try another portal
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from src import census as census_mod
from src import config, drift, extract, report, safety, schemas, work

logger = logging.getLogger("layer1")


def _load(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def _set_output(name: str, value) -> None:
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"{name}={value}\n")


def _log_run(stage: str, info: dict) -> None:
    config.RUN_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {"at": work.now_iso(), "stage": stage, "run_id": os.environ.get("GITHUB_RUN_ID", "local"), **info}
    with open(config.RUN_LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


def cmd_census(args) -> None:
    validation = _load(config.VALIDATION_FILE, {})
    census, events = census_mod.run(validation)
    report.write_json(config.CENSUS_FILE, census)
    new_events = drift.append(events)
    queue = work.plan(census, validation)
    report.write_json(config.QUEUE_FILE, queue)
    tables = sum(len(d["tables"]) for d in census["datasets"])
    logger.info("%d datasets, %d tabular resources, %d queued, %d declared drift events",
                len(census["datasets"]), tables, len(queue), new_events)
    _log_run("census", {"datasets": len(census["datasets"]), "tables": tables, "queued": len(queue),
                        "declared_drift": new_events})
    _set_output("queue_remaining", len(queue))


def cmd_validate(args) -> None:
    census = _load(config.CENSUS_FILE, None)
    if census is None:
        sys.exit("No census yet: run `python main.py census` first")
    queue = _load(config.QUEUE_FILE, [])
    validation = _load(config.VALIDATION_FILE, {})
    drift_before = drift.load()
    written = set()

    def save(out: dict) -> None:
        report.write_json(config.VALIDATION_FILE, validation)
        for (dataset, rid), obs in out["observed"].items():
            if (dataset, rid) not in written:
                schemas.write(schemas.path(dataset, rid, "observed"), obs)
                written.add((dataset, rid))
        report.write_json(config.DRIFT_FILE, drift_before)
        drift.append(out["drift"])
        report.write_json(config.RESULTS / "done.json", out["done"])

    out = work.run_batch(census, queue, validation, args.minutes, on_progress=save)
    save(out)
    new_events = len(drift.load()) - len(drift_before)
    left = len(queue) - len(out["done"])
    logger.info("validated %d resources; %d left in the queue; %d drift events", len(out["done"]), left, new_events)
    _log_run("validate", {"done": len(out["done"]), "left": left, "drift": new_events})
    _set_output("queue_remaining", left)


def _write_extracted(results: dict) -> int:
    for (dataset, rid), schema in results.get("extracted", {}).items():
        schemas.write(schemas.path(dataset, rid, "extracted"), schema)
    for (dataset, rid), schema in results.get("suggested", {}).items():
        schemas.write(config.ROOT / "suggestions" / dataset / f"{rid}.extracted.json", schema)
    return len(results.get("suggested", {}))


def cmd_extract(args) -> None:
    census = _load(config.CENSUS_FILE, None)
    validation = _load(config.VALIDATION_FILE, {})
    extraction = _load(config.EXTRACTION_FILE, {})
    todo = extract.tasks(census, validation, extraction, args.stage)
    if args.stage == "deterministic":
        results = extract.run_deterministic(todo, extraction)
    else:
        from src.pdf_extract import OllamaClient

        if config.LLM_MODEL == "auto":           # resolved by the workflow step; locally, resolve here
            from src import model_select
            model_select.resolve()
        results = extract.run_llm(todo, extraction, OllamaClient(model=config.LLM_MODEL), args.minutes)
    suggested = _write_extracted(results)
    report.write_json(config.EXTRACTION_FILE, extraction)
    llm_needed = len(extract.tasks(census, validation, extraction, "llm"))
    logger.info("%s stage: %d PDF dictionaries processed, %d schemas suggested, %d need the LLM",
                args.stage, len(todo), suggested, llm_needed)
    _log_run(f"extract-{args.stage}", {"processed": len(todo), "suggested": suggested, "llm_needed": llm_needed})
    _set_output("llm_needed", llm_needed)


def cmd_resolve_model(args) -> None:
    """Resolve LLM_MODEL=auto once per job and export it to the later steps of the workflow."""
    from src import model_select

    sel = model_select.resolve()
    print(json.dumps(sel))
    env = os.environ.get("GITHUB_ENV")
    if env:
        values = {"LLM_MODEL": sel["model"], "LLM_THINK": sel["think"], "LLM_MODEL_SOURCE": sel["source"],
                  "LLM_DIGEST": (sel.get("digest") or "").removeprefix("sha256:")}
        # These end up in shell commands of later steps: refuse anything unexpected.
        if not (safety.valid_model(values["LLM_MODEL"]) and values["LLM_THINK"] in safety.THINK_VALUES
                and values["LLM_MODEL_SOURCE"] in ("pinned", "benchmark", "fallback")
                and safety.valid_digest(values["LLM_DIGEST"])):
            sys.exit(f"Refusing an unexpected model selection: {values}")
        with open(env, "a", encoding="utf-8") as fh:
            for key, value in values.items():
                fh.write(f"{key}={value}\n")
    _set_output("model", sel["model"])


def cmd_accept_artifact(args) -> None:
    census = _load(config.CENSUS_FILE, None)
    accepted = safety.accept_artifact(Path(args.dir), config.ROOT, census, drift.load())
    done = set(_load(config.RESULTS / "done.json", []))
    queue = [q for q in _load(config.QUEUE_FILE, []) if q["id"] not in done]
    report.write_json(config.QUEUE_FILE, queue)
    (config.RESULTS / "done.json").unlink(missing_ok=True)
    chain = _load(config.ROOT / "chain.json", {})
    (config.ROOT / "chain.json").unlink(missing_ok=True)
    suggestions = len(list((config.ROOT / "suggestions").rglob("*.json")))
    logger.info("accepted %d files; %d left in the queue; %d suggested schemas", len(accepted), len(queue), suggestions)
    _set_output("queue_remaining", len(queue))
    _set_output("llm_needed", int(chain.get("llm_needed") or 0))
    _set_output("suggestions", suggestions)


def _dashboard_url() -> str:
    repo = os.environ.get("GITHUB_REPOSITORY", "lsp3cesarschool/5ltep-layer1")
    owner, name = repo.split("/")
    return f"https://{owner.lower()}.github.io/{name}/"


def cmd_issues(args) -> None:
    gh = drift.GitHub.from_env()
    opened, remaining = drift.open_issues(drift.load(), gh, config.portal()["portal_url"], _dashboard_url())
    logger.info("opened %d drift issues; %d wait for the next run", opened, remaining)
    _set_output("issues_remaining", remaining)


def cmd_suggestions_pr(args) -> None:
    """Pull request body: what was suggested, with the oracle's verdict, for the reviewer."""
    lines = ["Schemas extracted from PDF dictionaries that the file's own header did not fully confirm, "
             "or that a language model produced. They are not used until a person reviews them.", "",
             "**How to review:** open *Files changed*. For each schema, compare the fields with the PDF "
             "(link below); fix names, types or sizes if needed, set `\"status\": \"verified\"` in the "
             "`x5ltep` block, and merge. A schema left as `suggested` is ignored by the validation.", "",
             "| Dataset | Resource | Stage | Recall | Precision | Not in the file | Missing from the PDF |",
             "|---|---|---|---|---|---|---|"]
    for p in sorted((config.ROOT / "suggestions").rglob("*.extracted.json")):
        s = json.loads(p.read_text(encoding="utf-8"))["x5ltep"]["source"]
        o = s.get("oracle") or {}
        md = lambda xs: ", ".join(f"`{safety.safe_markdown(x, 80)}`" for x in (xs or [])[:8]) or "—"
        lines.append(f"| {p.parent.name} | [{p.stem.split('.')[0]}]({safety.safe_markdown(s.get('url'), 400)}) "
                     f"| {s.get('stage')}{' (' + safety.safe_markdown(s.get('model'), 60) + ')' if s.get('model') else ''} "
                     f"| {o.get('recall', '—')} | {o.get('precision', '—')} | {md(o.get('not_in_file'))} "
                     f"| {md(o.get('missing_from_pdf'))} |")
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")


def cmd_report(args) -> None:
    census = _load(config.CENSUS_FILE, None)
    if census is None:
        sys.exit("No census yet")
    validation = _load(config.VALIDATION_FILE, {})
    extraction = _load(config.EXTRACTION_FILE, {})
    queue = _load(config.QUEUE_FILE, [])
    summary = report.build_summary(census, validation, extraction, queue)
    report.write_json(config.SUMMARY_FILE, summary)
    if not queue:      # the weekly chain is complete: one row of history
        report.update_history(census, validation, summary)
    report.write_json(config.DASHBOARD_FILE, report.dashboard_data(census, validation, extraction, summary))
    state, info = report.status_from_summary(summary, args.chain_continues != "no")
    report.write_status(state, **info)
    logger.info("L1: %s/%s files conform (l1_rate=%s, pass=%s); tables by level %s",
                summary["conformant"], summary["verifiable"], summary["l1_rate"], summary["l1_pass"],
                summary["tables"]["by_level"])


def cmd_status(args) -> None:
    report.write_status(args.state)


def cmd_run(args) -> None:
    cmd_census(args)
    stage, args.stage = getattr(args, "stage", None), "deterministic"
    cmd_extract(args)
    args.stage = stage
    cmd_validate(args)
    cmd_report(args)


def main(argv=None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("census").set_defaults(fn=cmd_census)
    p = sub.add_parser("validate")
    p.add_argument("--minutes", type=float, default=config.VALIDATE_MAX_MINUTES)
    p.set_defaults(fn=cmd_validate)
    p = sub.add_parser("extract")
    p.add_argument("--stage", choices=["deterministic", "llm"], required=True)
    p.add_argument("--minutes", type=float, default=config.EXTRACT_MAX_MINUTES)
    p.set_defaults(fn=cmd_extract)
    p = sub.add_parser("accept-artifact")
    p.add_argument("--dir", required=True)
    p.set_defaults(fn=cmd_accept_artifact)
    sub.add_parser("issues").set_defaults(fn=cmd_issues)
    sub.add_parser("resolve-model").set_defaults(fn=cmd_resolve_model)
    p = sub.add_parser("suggestions-pr")
    p.add_argument("--out", required=True)
    p.set_defaults(fn=cmd_suggestions_pr)
    p = sub.add_parser("report")
    p.add_argument("--chain-continues", choices=["auto", "no"], default="no")
    p.set_defaults(fn=cmd_report)
    p = sub.add_parser("status")
    p.add_argument("--state", choices=["running", "interrupted"], required=True)
    p.set_defaults(fn=cmd_status)
    p = sub.add_parser("run")
    p.add_argument("--minutes", type=float, default=30.0)
    p.add_argument("--chain-continues", default="no")
    p.set_defaults(fn=cmd_run)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()

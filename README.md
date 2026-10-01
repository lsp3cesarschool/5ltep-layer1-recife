# 5LTEP-L1 · Recife instance (control experiment)

[![Tests](https://github.com/lsp3cesarschool/5ltep-layer1-recife/actions/workflows/tests.yml/badge.svg)](https://github.com/lsp3cesarschool/5ltep-layer1-recife/actions/workflows/tests.yml) [![Layer 1](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Flsp3cesarschool%2F5ltep-layer1-recife%2Fmain%2Fdocs%2Fdata%2Fstatus.json)](https://github.com/lsp3cesarschool/5ltep-layer1-recife/actions/workflows/layer1.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**English** · [Português](LEIAME.md)

**5L-TEP Layer 1 (structural contracts) applied to the open data portal of the City of Recife, Brazil:
a second instance of [5ltep-layer1](https://github.com/lsp3cesarschool/5ltep-layer1), set up by the
author as a control case for the IBAMA study, on a municipal portal.**

| Resource | What you find there |
|---|---|
| 📊 **Dashboard** | [lsp3cesarschool.github.io/5ltep-layer1-recife](https://lsp3cesarschool.github.io/5ltep-layer1-recife/?lang=en): maturity, documentation findings, every dataset and file |
| 🔀 **Schema drift** | [![drift issues](https://img.shields.io/github/issues/lsp3cesarschool/5ltep-layer1-recife/layer1?label=drift%20issues&color=0366d6)](https://github.com/lsp3cesarschool/5ltep-layer1-recife/issues?q=is%3Aissue+label%3Alayer1) |
| 🧑‍⚖️ **Suggested schemas** | [pull requests](https://github.com/lsp3cesarschool/5ltep-layer1-recife/pulls?q=is%3Apr+schemas+suggested) with schemas extracted from PDF dictionaries, waiting for a person |
| 🏛️ **Main instance** | [5ltep-layer1](https://github.com/lsp3cesarschool/5ltep-layer1): IBAMA, and the full documentation |
| 🔁 **Other control** | [5ltep-layer1-aneel](https://github.com/lsp3cesarschool/5ltep-layer1-aneel): the ANEEL portal |

> **Status: research demonstration.** This repository is not operated by, affiliated with or endorsed
> by the City of Recife or EMPREL; it only reads the city's open data. It shows that the toolkit can be
> reused on another portal. It does not assume that the city will review its results or adopt it.
> Suggested schemas and drift issues demonstrate the flow; the author does not act as their reviewer.

## Use case in one paragraph

The City of Recife publishes its open data on a CKAN portal, many datasets with a data dictionary in
more than one format. Suppose someone who reuses these data wants to know, before trusting a file, what
it should contain and whether it does. This instance reads every dictionary the portal publishes, links
each one to the files it describes, and checks every published CSV against its schema, week after week.

## Why a control experiment

The Layer 1 toolkit was built on IBAMA's portal, a federal agency. Recife is a municipality, with
another team, other habits and another documentation template. This repository runs **the same code**,
following the steps of *Running your own instance* of the main README: only `portal.json` (the portal's
URL) and the texts of this README changed. Where Recife's documentation differs from IBAMA's, the
difference shows up in the results, not in the code.

## How Recife documents its data

As observed when this instance was set up (01/10/2026); the dashboard has the current numbers.

- Many datasets have a **JSON dictionary** that follows one template (`metadados.campos` with code,
  type, size and allowed values) and that **names the resources it describes** by their identifiers:
  the dictionary-to-file link is declared by the publisher instead of guessed. The same dictionaries
  are often also published as PDF, and some as XLSX.
- A few JSON dictionaries are malformed, and at least one names a dataset other than its own: both
  are counted in the documentation findings.
- Most CSV files are loaded in the **DataStore** with real types (numbers, timestamps), which places
  them at level 3. Those types may have been inferred by the portal's loader rather than declared by
  the publisher, so validation prefers the dictionary when there is one.

## What changed from the main instance

| File | Change |
|---|---|
| `portal.json` | `portal_url` = `https://dados.recife.pe.gov.br` |
| `README.md`, `LEIAME.md`, `CITATION.cff` | this text and the citation of this repository |

Everything else is the code of `5ltep-layer1` at commit `1885c76`
([1885c7612bfdaadd9758fb66bd605727cde8694d](https://github.com/lsp3cesarschool/5ltep-layer1/commit/1885c7612bfdaadd9758fb66bd605727cde8694d)).

## Running it, and adapting it again

The workflow *5L-TEP Layer 1 Structural Contracts* runs every Monday and can be started by hand
(*Actions → Run workflow*). Locally:

```bash
pip install -r requirements.txt
python main.py run --minutes 10
```

To point it at yet another CKAN portal, change `portal_url` in `portal.json`; see the main README.

## Reproducibility

Each result records the SHA-256 of the file it validated, the fingerprint of the schema, the method
parameters and, for PDF extractions, the model, its digest and the prompt version. The code is the
upstream commit above; the schemas and results are committed by the workflow.

## Limitations

The limitations of the main instance apply. Specific to Recife: the portal does not answer partial
downloads, so every file is read from the start; the first run of the whole portal takes several
chained batches.

## Documentation and references

The full documentation (maturity scale, readers, validation, PDF stages, drift, findings, security,
configuration and references) is in the [main repository](https://github.com/lsp3cesarschool/5ltep-layer1#readme).

## License

MIT for the code ([LICENSE](LICENSE)). The city's data are published under the Open Database License
(ODbL); this repository stores only schemas and aggregate results derived from them.

# Evaluation

Scripts that turn the committed results into the numbers reported in the thesis. They only read
files of this repository (or the public summaries of the other instances); nothing here changes
the results.

| Script | What it measures | Output |
|---|---|---|
| `pdf_extraction.py` | quality of the PDF dictionary extraction per stage (deterministic, LLM) against the oracle: recall, precision, exact match and Levenshtein similarity of the field names (Al Hilmi et al., 2026) | `results/pdf_extraction.{json,txt}` |
| `compare_portals.py` | IBAMA × ANEEL × Recife side by side: maturity, conformance and documentation findings, read from each instance's public `layer1_summary.json` | `results/compare_portals.{json,md}` |

```bash
python evaluation/pdf_extraction.py
python evaluation/compare_portals.py
```

Every number carries the date of the summary it came from; cite it together with the commit of
each instance.

---

# Avaliação (português)

Scripts que transformam os resultados commitados nos números relatados na dissertação. Eles só leem
arquivos deste repositório (ou os resumos públicos das outras instâncias); nada aqui altera os
resultados.

- `pdf_extraction.py`: qualidade da extração de dicionários em PDF por etapa (determinística, LLM)
  contra o oráculo: revocação, precisão, correspondência exata e similaridade de Levenshtein dos nomes
  de campo (Al Hilmi et al., 2026).
- `compare_portals.py`: IBAMA × ANEEL × Recife lado a lado: maturidade, conformidade e achados de
  documentação, lidos do `layer1_summary.json` público de cada instância.

Cada número traz a data do resumo de onde veio; cite-o junto com o commit de cada instância.

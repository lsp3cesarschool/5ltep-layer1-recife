"""Which dictionary describes which file.

Portals rarely say it in a machine-readable way, so the link is found by the strongest
evidence available, and the method is recorded (it is itself a finding):

1. declared-id: the dictionary names the resource id (Recife's JSON dictionaries do);
2. header:      the dictionary's field names overlap the file's header (known after the first
                validation), Jaccard >= 0.5;
3. name:        the dictionary's name, without words such as "metadados" or "dicionário",
                shares most of its words with the resource's name (Jaccard >= 0.5; IBAMA:
                "Metadados - Termo de doação" describes "Termo de doação");
4. single:      the dataset has exactly one dictionary, with a generic name (or a single table),
                so it describes all its tables (ANEEL: one "Dicionário de dados" PDF per dataset).

A dictionary that names a resource id absent from the dataset is a broken declared link.
"""

from src import dictionaries

METHOD_RANK = {"declared-id": 4, "header": 3, "name": 2, "single": 1}
STOP = {"metadados", "metadado", "dicionario", "dicionarios", "de", "da", "do", "das", "dos", "dados", "e",
        "data", "dictionary", "csv", "json", "xml", "pdf", "xlsx", "xls", "variaveis", "variavel", "tabela",
        "tabelas", "campos", "arquivo", "the", "of", "schema", "esquema", "layout", "zip", "download"}


def tokens(text: str) -> set[str]:
    return {t for t in dictionaries.norm(text).split() if t not in STOP and not t.isdigit()}


def name_score(dict_name: str, resource_name: str) -> float:
    d, r = tokens(dict_name), tokens(resource_name)
    return len(d & r) / len(d) if d else 0.0


def jaccard(a: str, b: str) -> float:
    x, y = tokens(a), tokens(b)
    return len(x & y) / len(x | y) if x | y else 0.0


def header_score(fields: list[str], header: list[str]) -> float:
    a = {dictionaries.norm(x) for x in fields}
    b = {dictionaries.norm(x) for x in header}
    return len(a & b) / len(a | b) if a and b else 0.0


def link(dicts: list[dict], tables: list[dict], headers: dict[str, list[str]]) -> dict[str, dict]:
    """{resource id: {dictionary, part, method, score}} for the tabular resources of one dataset.

    dicts:   [{"id", "name", "parts": [{"label", "names"}], "declared_resource_ids"}]
    tables:  [{"id", "name"}]
    headers: observed header of a resource, from earlier validations (may be empty).
    """
    units = [(d, i, p) for d in dicts for i, p in enumerate(d.get("parts") or [{"label": "", "names": []}])]
    out: dict[str, dict] = {}
    for t in tables:
        best = None
        for d, i, part in units:
            cands = []
            if t["id"] in (d.get("declared_resource_ids") or []):
                cands.append(("declared-id", 1.0, 0.0))
            h = headers.get(t["id"])
            if h and part.get("names"):
                s = header_score(part["names"], h)
                if s >= 0.5:
                    cands.append(("header", round(s, 3), 0.0))
            label = (d["name"] + " " + part.get("label", "")).strip()
            s = max(jaccard(label, t["name"]), jaccard(part.get("label", ""), t["name"]) if part.get("label") else 0.0)
            if s >= 0.5:
                cands.append(("name", round(s, 3), name_score(label, t["name"])))
            # a lone dictionary with a generic name ("Dicionário de dados") describes every table;
            # one with a specific name describes only the tables its name matches
            if len(units) == 1 and (not tokens(label) or len(tables) == 1):
                cands.append(("single", 0.5, 0.0))
            for method, score, tie in cands:
                key = (METHOD_RANK[method], score, tie)
                if best is None or key > best[0]:
                    best = (key, {"dictionary": d["id"], "part": i, "method": method, "score": score})
        if best:
            out[t["id"]] = best[1]
    return out


def broken_declared_links(dicts: list[dict], resource_ids: set[str]) -> dict[str, list[str]]:
    return {d["id"]: [r for r in d.get("declared_resource_ids") or [] if r not in resource_ids]
            for d in dicts if any(r not in resource_ids for r in d.get("declared_resource_ids") or [])}

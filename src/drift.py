"""Schema drift: the structure of a file, or what the portal declares about it, changed.

Two kinds, both recorded in results/drift.json (append-only) and each sent to a GitHub Issue:

- observed: the file itself changed structure since the previous validation (columns added,
  removed or reordered; another delimiter or encoding; members of a zip with other headers);
- declared: the dictionary or schema the portal publishes for the file changed.

The first observation of a resource is a baseline, never a drift. Layer 4 detects changes in
the portal's *metadata* (SCHEMA_DRIFT of the resource list); this is the drift of the *files*.
"""

import hashlib
import json
import os

import requests

from src import config, safety

API = "https://api.github.com"
TRUSTED_AUTHORS = {"github-actions[bot]"}   # issues opened by the workflow's GITHUB_TOKEN


def _event_id(*parts) -> str:
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:16]


def compare(dataset: str, t: dict, before: dict | None, after: dict) -> list[dict]:
    if not before:
        return []
    b_names = [f["name"] for f in before.get("fields", [])]
    a_names = [f["name"] for f in after.get("fields", [])]
    bx, ax = before.get("x5ltep", {}), after.get("x5ltep", {})
    changes = {}
    added = [n for n in a_names if n not in b_names]
    removed = [n for n in b_names if n not in a_names]
    if added:
        changes["columns_added"] = added
    if removed:
        changes["columns_removed"] = removed
    if not added and not removed and a_names != b_names:
        changes["columns_reordered"] = True
    for key in ("delimiter", "encoding", "distinct_headers"):
        if bx.get(key) != ax.get(key) and bx.get(key) is not None:
            changes[key] = {"before": bx.get(key), "after": ax.get(key)}
    if not changes:
        return []
    return [{"id": _event_id("observed", t["id"], b_names, a_names, changes), "kind": "observed",
             "dataset": dataset, "resource_id": t["id"], "resource_name": t.get("name"),
             "at": ax.get("observed_at"), "before_sha256": bx.get("sha256"), "after_sha256": ax.get("sha256"),
             "changes": changes}]


def compare_declared(dataset: str, t: dict, kind: str, before: dict | None, after: dict | None) -> list[dict]:
    """A declared schema that changed, appeared after a baseline, or disappeared."""
    if before is None:
        return []
    b = {f["name"]: f.get("type") for f in before.get("fields", [])}
    a = {f["name"]: f.get("type") for f in (after or {}).get("fields", [])}
    if a == b:
        return []
    changes = {"fields_added": [n for n in a if n not in b], "fields_removed": [n for n in b if n not in a],
               "types_changed": {n: {"before": b[n], "after": a[n]} for n in a if n in b and a[n] != b[n]}}
    if after is None:
        changes["schema_removed"] = True
    changes = {k: v for k, v in changes.items() if v}
    return [{"id": _event_id("declared", t["id"], kind, b, a), "kind": "declared", "schema_kind": kind,
             "dataset": dataset, "resource_id": t["id"], "resource_name": t.get("name"), "changes": changes}]


def load(path=None) -> list[dict]:
    path = path or config.DRIFT_FILE
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def append(events: list[dict], path=None) -> int:
    path = path or config.DRIFT_FILE
    log = load(path)
    known = {e["id"] for e in log}
    new = [e for e in events if e["id"] not in known]
    if new:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(log + new, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return len(new)


# --- GitHub Issues --------------------------------------------------------------

class GitHub:
    def __init__(self, repo: str, token: str):
        self.repo = repo
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                                     "X-GitHub-Api-Version": "2022-11-28"})

    @classmethod
    def from_env(cls) -> "GitHub":
        repo, token = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_TOKEN")
        if not repo or not token:
            raise RuntimeError("GITHUB_REPOSITORY and GITHUB_TOKEN must be set")
        return cls(repo, token)

    def _req(self, method: str, path: str, **kwargs):
        resp = self.session.request(method, f"{API}/repos/{self.repo}{path}", timeout=30, **kwargs)
        resp.raise_for_status()
        return resp.json() if resp.content else None

    def issues(self) -> list[dict]:
        out, page = [], 1
        while True:
            batch = self._req("GET", "/issues", params={"labels": config.ISSUE_LABEL, "state": "all",
                                                        "per_page": 100, "page": page})
            out += [i for i in batch if "pull_request" not in i
                    and (i.get("user") or {}).get("login") in TRUSTED_AUTHORS]
            if len(batch) < 100:
                return out
            page += 1

    def ensure_labels(self, wanted: dict[str, tuple[str, str]]) -> None:
        existing = {lbl["name"] for lbl in self._req("GET", "/labels", params={"per_page": 100})}
        for name, (color, desc) in wanted.items():
            if name not in existing:
                self._req("POST", "/labels", json={"name": name, "color": color, "description": desc})

    def create_issue(self, title: str, body: str, labels: list[str]) -> dict:
        return self._req("POST", "/issues", json={"title": title, "body": body, "labels": labels})


LABELS = {
    config.ISSUE_LABEL: ("1d76db", "5L-TEP Layer 1 structural contract"),
    "drift:observed": ("fbca04", "The structure of a published file changed"),
    "drift:declared": ("c5def5", "The dictionary or schema the portal declares changed"),
}


def _md(text) -> str:
    return safety.safe_markdown(text, 300)


def issue_title(e: dict) -> str:
    what = "file structure changed" if e["kind"] == "observed" else "declared schema changed"
    return f"[L1] {_md(e['dataset'])} / {_md(e.get('resource_name') or e['resource_id'])}: {what}"[:240]


def issue_body(e: dict, portal_url: str, dashboard_url: str) -> str:
    lines = [f"<!-- l1-drift:{e['id']} -->",
             f"**Dataset:** [{_md(e['dataset'])}]({portal_url}/dataset/{e['dataset']})  ",
             f"**Resource:** {_md(e.get('resource_name'))} (`{e['resource_id']}`)  ",
             f"**Kind:** {'structure of the published file' if e['kind'] == 'observed' else 'schema declared by the portal (' + e.get('schema_kind', '') + ')'}",
             "", "**What changed:**", ""]
    for key, value in e["changes"].items():
        if isinstance(value, list):
            lines.append(f"- {key.replace('_', ' ')}: " + ", ".join(f"`{_md(v)}`" for v in value[:40])
                         + (" …" if len(value) > 40 else ""))
        elif isinstance(value, dict) and set(value) == {"before", "after"}:
            lines.append(f"- {key.replace('_', ' ')}: `{_md(value['before'])}` → `{_md(value['after'])}`")
        elif isinstance(value, dict):
            lines.append(f"- {key.replace('_', ' ')}: " + ", ".join(
                f"`{_md(k)}` {_md(v.get('before'))} → {_md(v.get('after'))}" for k, v in list(value.items())[:40]))
        else:
            lines.append(f"- {key.replace('_', ' ')}")
    lines += ["", f"Details and history: [dashboard]({dashboard_url}?resource={e['resource_id']}) · "
              f"`schemas/{e['dataset']}/{e['resource_id']}.*.json` in this repository.", "",
              "_Opened automatically by the Layer 1 workflow. A schema change is not necessarily an error: "
              "it may be a documented evolution. Closing the issue records that it was seen; a comment "
              "records the cause._"]
    return "\n".join(lines)


def open_issues(events: list[dict], gh: GitHub, portal_url: str, dashboard_url: str) -> tuple[int, int]:
    """One issue per drift event not yet issued; at most MAX_NEW_ISSUES per run. (opened, remaining)."""
    gh.ensure_labels(LABELS)
    known = {line.split("l1-drift:")[1].split(" ")[0] for i in gh.issues()
             for line in (i.get("body") or "").splitlines()[:1] if "l1-drift:" in line}
    pending = [e for e in events if e["id"] not in known]
    opened = 0
    for e in pending[:config.MAX_NEW_ISSUES]:
        gh.create_issue(issue_title(e), issue_body(e, portal_url, dashboard_url),
                        [config.ISSUE_LABEL, f"drift:{e['kind']}"])
        opened += 1
    return opened, len(pending) - opened

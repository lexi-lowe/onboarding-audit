"""Find findings that are already filed, so the report shows "Already filed" instead of a button.

Read-only. Each tracker needs read access:
  github: GITHUB_TOKEN (or gh CLI) for private repos; public repos work without one
  linear: LINEAR_API_KEY
  jira:   JIRA_EMAIL + JIRA_API_TOKEN
If a lookup fails, every finding keeps its button and the report says the check was skipped.
"""
from __future__ import annotations

import base64
import json
import os
import urllib.request
from typing import Callable

from .findings import Finding, extract_key

Fetch = Callable[[str, dict, bytes | None], object]  # (url, headers, body) -> parsed JSON


def http_json(url: str, headers: dict, body: bytes | None = None):
    req = urllib.request.Request(url, data=body, headers=headers, method="POST" if body else "GET")
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def github_existing(cfg: dict, fetch: Fetch = http_json) -> dict[str, dict]:
    headers = {"Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    label = cfg.get("dedupe_label", "signup-audit")
    url = f"https://api.github.com/repos/{cfg['repo']}/issues?state=all&labels={label}&per_page=100"
    out = {}
    for it in fetch(url, headers, None):
        if "pull_request" in it:
            continue
        k = extract_key(it.get("body") or "")
        if k:
            out[k] = {"id": f"#{it['number']}", "url": it["html_url"], "state": it["state"]}
    return out


def linear_existing(cfg: dict, fetch: Fetch = http_json) -> dict[str, dict]:
    q = """query($label:String!){ issues(first:100, filter:{labels:{name:{eq:$label}}}){
      nodes{ identifier url description state{ type } } } }"""
    body = json.dumps({"query": q, "variables": {"label": cfg.get("dedupe_label", "signup-audit")}}).encode()
    headers = {"Content-Type": "application/json", "Authorization": os.environ.get("LINEAR_API_KEY", "")}
    data = fetch("https://api.linear.app/graphql", headers, body)
    out = {}
    for n in data["data"]["issues"]["nodes"]:
        k = extract_key(n.get("description") or "")
        if k:
            closed = n["state"]["type"] in ("completed", "canceled")
            out[k] = {"id": n["identifier"], "url": n["url"], "state": "closed" if closed else "open"}
    return out


def jira_existing(cfg: dict, fetch: Fetch = http_json) -> dict[str, dict]:
    auth = base64.b64encode(f"{os.environ.get('JIRA_EMAIL','')}:{os.environ.get('JIRA_API_TOKEN','')}".encode()).decode()
    headers = {"Accept": "application/json", "Content-Type": "application/json", "Authorization": f"Basic {auth}"}
    jql = f'labels = "{cfg.get("dedupe_label", "signup-audit")}"'
    body = json.dumps({"jql": jql, "fields": ["description", "status"], "maxResults": 100}).encode()
    base = cfg["base_url"].rstrip("/")
    data = fetch(f"{base}/rest/api/3/search/jql", headers, body)
    out = {}
    for it in data.get("issues", []):
        desc = it["fields"].get("description")
        text = desc if isinstance(desc, str) else json.dumps(desc or "")  # Cloud returns rich-text JSON
        k = extract_key(text)
        if k:
            done = it["fields"]["status"]["statusCategory"]["key"] == "done"
            out[k] = {"id": it["key"], "url": f"{base}/browse/{it['key']}", "state": "closed" if done else "open"}
    return out


LOOKUPS = {"github": github_existing, "linear": linear_existing, "jira": jira_existing}


def mark_filed(findings: list[Finding], tracker: dict, fetch: Fetch = http_json) -> str:
    """Sets finding.filed for open issues. Returns a one-line note for the report."""
    try:
        existing = LOOKUPS[tracker["type"]](tracker, fetch)
    except Exception as e:  # network, auth, schema
        return f"Duplicate check skipped ({type(e).__name__}); every finding has a file button."
    already = returned = 0
    for f in findings:
        hit = existing.get(f.key)
        if not hit:
            continue
        if hit["state"] == "open":
            f.filed = hit
            already += 1
        else:
            f.filed = {**hit, "returned": True}  # closed but seen again: show a button, note it came back
            returned += 1
    return f"Duplicate check: {already} already filed, {returned} came back after being closed, {len(findings) - already - returned} new."

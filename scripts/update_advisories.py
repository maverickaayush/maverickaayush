#!/usr/bin/env python3
"""Refresh the "latest critical advisories" block in README.md.

Source: GitHub Advisory Database (official REST API, GitHub-reviewed advisories only).
Pure standard library. If the API is unreachable the README is left untouched and
the script exits 0, so a flaky run never breaks your profile.

README must contain these two markers:
  <!-- ADVISORIES:START -->
  <!-- ADVISORIES:END -->

Env vars:
  GITHUB_TOKEN  optional, raises the API rate limit
  README_PATH   file to update (default: README.md)
  ADV_COUNT     how many entries to show (default: 5)
"""
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone

README_PATH = os.environ.get("README_PATH", "README.md")
COUNT = int(os.environ.get("ADV_COUNT", "5"))
TOKEN = os.environ.get("GITHUB_TOKEN", "")
API = (
    "https://api.github.com/advisories"
    f"?severity=critical&type=reviewed&sort=published&direction=desc&per_page={COUNT}"
)
START = "<!-- ADVISORIES:START -->"
END = "<!-- ADVISORIES:END -->"


def fetch():
    req = urllib.request.Request(
        API,
        headers={"User-Agent": "profile-advisories", "Accept": "application/vnd.github+json"},
    )
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)


def clean(text, limit=95):
    """Keep one-line, markdown-safe text. Advisory summaries are third-party input."""
    text = re.sub(r"https?://\S+", "", text or "")  # no third-party links
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"[\[\]|`<>*_@]", "", text)
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


def render(advisories):
    lines = []
    for adv in advisories[:COUNT]:
        ident = adv.get("cve_id") or adv.get("ghsa_id") or "advisory"
        url = adv.get("html_url") or ""
        if not url.startswith("https://github.com/"):
            continue  # only link to GitHub-hosted advisory pages
        date = (adv.get("published_at") or "")[:10]
        lines.append(f"- `CRITICAL` [{clean(ident, 30)}]({url}) | {clean(adv.get('summary'))} | {date}")
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    footer = f"<sub>Source: GitHub Advisory Database | synced {stamp}</sub>"
    return "\n".join(lines + ["", footer])


def splice(readme, block):
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not pattern.search(readme):
        raise SystemExit(f"markers {START} / {END} not found in {README_PATH}")
    return pattern.sub(lambda _m: f"{START}\n{block}\n{END}", readme)


def main():
    try:
        advisories = fetch()
    except Exception as exc:
        print(f"warning: advisory fetch failed ({exc}); README left unchanged")
        return 0
    if not advisories:
        print("warning: API returned no advisories; README left unchanged")
        return 0
    with open(README_PATH, encoding="utf-8") as f:
        readme = f.read()
    updated = splice(readme, render(advisories))
    if updated != readme:
        with open(README_PATH, "w", encoding="utf-8") as f:
            f.write(updated)
        print(f"updated {README_PATH} with {min(len(advisories), COUNT)} advisories")
    else:
        print("no change")
    return 0


if __name__ == "__main__":
    sys.exit(main())

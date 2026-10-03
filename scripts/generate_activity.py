#!/usr/bin/env python3
"""Generate a terminal-style "activity" panel (assets/activity.svg).

Replaces the contribution-graph look with data that does not depend on commit
volume: a language breakdown across your public repos and your most recently
pushed repos. Pure standard library, static SVG (no animation except the cursor).

Reuses the theme and helpers from generate_card.py so both panels match.
If the GitHub API is unreachable the existing SVG is left untouched and the
script exits 0, so a flaky run never breaks the profile.

Env vars:
  GITHUB_LOGIN  GitHub username (default: maverickaayush)
  GITHUB_TOKEN  optional, raises API rate limits
  ACTIVITY_OUT  output file (default: assets/activity.svg)
"""
import os
import re
import sys
from html import escape

import generate_card as g

OUT = os.environ.get("ACTIVITY_OUT", "assets/activity.svg")
CARD = "assets/profile.svg"
MAX_LANGS = 6
MAX_REPOS = 6
BAR = 20
NAME_W = 24


def card_width(default=773):
    """Match the width of the main card so both scale identically in the README."""
    try:
        with open(CARD, encoding="utf-8") as f:
            m = re.search(r'<svg[^>]*\swidth="(\d+)"', f.read(1000))
        return int(m.group(1)) if m else default
    except OSError:
        return default


def collect():
    """Return (repos, lang_bytes) from the API, or None if unreachable."""
    try:
        repos = g.fetch_json(
            f"https://api.github.com/users/{g.LOGIN}/repos?per_page=100&type=owner&sort=pushed"
        )
    except Exception as exc:
        print(f"warning: could not fetch repos ({exc})")
        return None
    repos = [r for r in repos if not r.get("fork") and r.get("name", "").lower() != g.LOGIN.lower()]
    langs = {}
    for r in repos[:20]:
        try:
            data = g.fetch_json(f"https://api.github.com/repos/{g.LOGIN}/{r['name']}/languages")
        except Exception as exc:
            print(f"warning: languages for {r['name']} unavailable ({exc})")
            if r.get("language"):
                langs[r["language"]] = langs.get(r["language"], 0) + 1
            continue
        for lang, n in data.items():
            langs[lang] = langs.get(lang, 0) + n
    return repos, langs


def short(text, n):
    text = text or ""
    return text if len(text) <= n else text[: n - 3] + "..."


def build(repos, langs):
    W = card_width()
    FS, CW, LH, PAD, TITLE_H = g.FS, g.CW, g.LH, g.PAD, g.TITLE_H
    prompt = f"{g.HOST_PROMPT}:~$ "

    rows = []  # each row: list of (text, colour) segments
    rows.append([(g.HOST_PROMPT, g.GREEN), (":~$ ", g.WHITE), ("./lang-breakdown --public", g.WHITE)])
    total = sum(langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: kv[1], reverse=True)[:MAX_LANGS]
    name_w = max([len(k) for k, _ in top] + [8]) + 2
    if not top:
        rows.append([("no language data yet", g.DIM)])
    for lang, n in top:
        pct = 100.0 * n / total
        filled = max(1 if n else 0, round(BAR * pct / 100))
        rows.append([
            (short(lang, 18).ljust(name_w), g.YELLOW),
            ("[", g.DIM),
            ("#" * filled, g.GREEN),
            ("." * (BAR - filled), g.DIM),
            ("]", g.DIM),
            (f"  {pct:5.1f}%", g.CYAN),
        ])
    rows.append([("", g.WHITE)])
    rows.append([(g.HOST_PROMPT, g.GREEN), (":~$ ", g.WHITE), ("ls -lt repos/ | head -n %d" % MAX_REPOS, g.WHITE)])
    rows.append([("PUSHED".ljust(12) + "REPO".ljust(NAME_W + 2) + "LANG".ljust(14) + "STARS", g.CYAN)])
    recent = repos[:MAX_REPOS]
    if not recent:
        rows.append([("no public repos yet", g.DIM)])
    for r in recent:
        rows.append([
            ((r.get("pushed_at") or "")[:10].ljust(12), g.DIM),
            (short(r.get("name"), NAME_W).ljust(NAME_W + 2), g.WHITE),
            (short(r.get("language") or "-", 12).ljust(14), g.YELLOW),
            (str(r.get("stargazers_count", 0)), g.GREEN),
        ])
    rows.append([("", g.WHITE)])
    stars = sum(r.get("stargazers_count", 0) for r in repos)
    forks = sum(r.get("forks_count", 0) for r in repos)
    rows.append([(f"# {len(repos)} public repos | {stars} stars | {forks} forks", g.DIM)])

    y0 = TITLE_H + PAD + 4
    final_y = y0 + len(rows) * LH + 4
    H = int(final_y + PAD)

    p = []
    p.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'font-family="{g.FONT}" role="img" aria-label="Language breakdown and recent repositories for {escape(g.LOGIN)}">'
    )
    p.append(f"<title>{escape(g.LOGIN)} | activity</title>")
    langs_txt = ", ".join(f"{k} {100.0 * v / total:.0f}%" for k, v in top)
    repos_txt = ", ".join(r.get("name", "") for r in recent)
    p.append(f"<desc>Languages: {escape(langs_txt)}. Recently pushed: {escape(repos_txt)}.</desc>")
    p.append(f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="12" fill="{g.BG}" stroke="{g.BORDER}"/>')
    p.append(
        f'<path d="M0.5 {TITLE_H} V12.5 a12 12 0 0 1 12 -12 H{W - 12.5} a12 12 0 0 1 12 12 V{TITLE_H} Z" fill="{g.TITLEBAR}"/>'
    )
    p.append(f'<line x1="0.5" y1="{TITLE_H}" x2="{W - 0.5}" y2="{TITLE_H}" stroke="{g.BORDER}"/>')
    for i, col in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
        p.append(f'<circle cx="{22 + i * 20}" cy="{TITLE_H / 2}" r="6" fill="{col}"/>')
    p.append(
        f'<text x="{W / 2}" y="{TITLE_H / 2 + 5}" font-size="13" fill="{g.DIM}" text-anchor="middle">'
        f"{escape(g.HOST_PROMPT)}: ~/activity</text>"
    )
    for i, segs in enumerate(rows):
        el = g.text_el(PAD, y0 + i * LH, segs)
        if el:
            p.append(el)
    p.append(g.text_el(PAD, final_y, [(g.HOST_PROMPT, g.GREEN), (":~$ ", g.WHITE)]))
    p.append(
        f'<rect x="{PAD + len(prompt) * CW}" y="{final_y - FS + 1}" width="{CW}" height="{FS + 2}" fill="{g.GREEN}">'
        '<animate attributeName="opacity" values="1;0;1" dur="1.1s" repeatCount="indefinite"/></rect>'
    )
    p.append("</svg>")
    return "\n".join(p)


def main():
    data = collect()
    if data is None:
        print("activity panel left unchanged")
        return 0
    svg = build(*data)
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    try:
        with open(OUT, encoding="utf-8") as f:
            if f.read() == svg:
                print("no change")
                return 0
    except OSError:
        pass
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {OUT} ({len(svg)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

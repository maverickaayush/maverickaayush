#!/usr/bin/env python3
"""Generate an animated nmap-style terminal card as a self-contained SVG.

Pure standard library: no third-party packages, no external assets, no JavaScript.
The animation is SMIL inside the SVG, which GitHub renders when the file is
embedded with an <img> tag in a profile README.

Env vars:
  GITHUB_LOGIN  GitHub username (default: maverickaayush)
  GITHUB_TOKEN  optional, raises API rate limits for the live stats line
  OUT_PATH      output file (default: assets/profile.svg)
"""
import json
import os
import urllib.request
from datetime import datetime, timezone
from html import escape

LOGIN = os.environ.get("GITHUB_LOGIN", "maverickaayush")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT_PATH = os.environ.get("OUT_PATH", "assets/profile.svg")

# ----------------------------------------------------------------------------
# Edit this block to change what the card says
# ----------------------------------------------------------------------------
HOST_PROMPT = "aayush@kali"
COMMAND = f"nmap -sV -sC {LOGIN}"
LOCATION = "New Delhi, IN"
TAGLINE = "cybersecurity | vapt | open source | bennett university '29"
PORTS = [
    # (port, service, version / banner text)
    ("22/tcp", "whoami", "Aayush Yadav | B.Tech CSE (Cybersecurity), Bennett"),
    ("80/tcp", "building", "ONUS | AI-assisted VAPT, in OWASP tools directory"),
    ("443/tcp", "building", "Valsec | network config compliance auditor"),
    ("1337/tcp", "tryhackme", "maverickaayush | top 6% globally, 80 rooms"),
    ("2222/tcp", "bounty", "Kickbacks.ai | disclosed vuln, $100 reward"),
    ("3000/tcp", "founder", "Clinkl | AI adtech marketplace"),
    ("5000/tcp", "cabinet", "SCSET Student Cabinet | Deputy Minister, Digital Infra"),
    ("8080/tcp", "http-proxy", "tryonus.tech (hosted ONUS)"),
]

# ----------------------------------------------------------------------------
# Theme
# ----------------------------------------------------------------------------
BG = "#0a0e14"
TITLEBAR = "#131a24"
BORDER = "#1f2a37"
GREEN = "#00ff41"
DIM = "#7d8a99"
WHITE = "#d5dde6"
CYAN = "#39d0d8"
YELLOW = "#ffd166"
FONT = "'JetBrains Mono','Fira Code','DejaVu Sans Mono',Menlo,Consolas,monospace"

BANNER = r"""
   ###       ###    ##    ## ##     ##  ######  ##     ##
  ## ##     ## ##    ##  ##  ##     ## ##    ## ##     ##
 ##   ##   ##   ##    ####   ##     ## ##       ##     ##
##     ## ##     ##    ##    ##     ##  ######  #########
######### #########    ##    ##     ##       ## ##     ##
##     ## ##     ##    ##    ##     ## ##    ## ##     ##
##     ## ##     ##    ##     #######   ######  ##     ##
""".strip("\n").split("\n")

# ----------------------------------------------------------------------------
# Layout
# ----------------------------------------------------------------------------
FS = 14            # body font size
CW = 8.4           # body char width at FS (textLength keeps this exact)
LH = 21            # body line height
BFS = 14           # banner font size
BCW = 8.4
BLH = 16
PAD = 26
TITLE_H = 38


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "profile-card", "Accept": "application/vnd.github+json"})
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def live_stats():
    """Return (repos, followers, stars) or None if the API is unreachable."""
    try:
        user = fetch_json(f"https://api.github.com/users/{LOGIN}")
        repos = fetch_json(f"https://api.github.com/users/{LOGIN}/repos?per_page=100&type=owner")
        stars = sum(r.get("stargazers_count", 0) for r in repos)
        return user.get("public_repos", 0), user.get("followers", 0), stars
    except Exception as exc:  # network down, rate limit, etc.
        print(f"warning: could not fetch live stats ({exc})")
        return None


def text_el(x, y, segs, size=FS, cw=CW):
    """One <text> row made of coloured segments, width pinned with textLength."""
    n = sum(len(t) for t, _ in segs)
    if n == 0:
        return ""
    spans = "".join(f'<tspan fill="{c}">{escape(t)}</tspan>' for t, c in segs)
    return (
        f'<text x="{x}" y="{y}" font-size="{size}" textLength="{round(n * cw, 1)}" '
        f'lengthAdjust="spacing" xml:space="preserve" style="white-space:pre">{spans}</text>'
    )


def build():
    stats = live_stats()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # --- rows of the terminal output (segments of (text, colour)) -----------
    port_w = max(len(p[0]) for p in PORTS) + 2
    svc_w = max(len(p[1]) for p in PORTS) + 2
    rows = [
        [("Starting Nmap 7.95 ( https://nmap.org ) at " + now, WHITE)],
        [(f"Nmap scan report for ", WHITE), (LOGIN, GREEN), (f" ({LOCATION})", DIM)],
        [("Host is up (0.00042s latency).", WHITE)],
        [("", WHITE)],
        [("PORT".ljust(port_w) + "STATE ".ljust(7) + "SERVICE".ljust(svc_w) + "VERSION", CYAN)],
    ]
    for port, svc, ver in PORTS:
        rows.append([
            (port.ljust(port_w), WHITE),
            ("open".ljust(7), GREEN),
            (svc.ljust(svc_w), YELLOW),
            (ver, WHITE),
        ])
    rows.append([("", WHITE)])
    rows.append([("Host script results:", WHITE)])
    if stats:
        repos, followers, stars = stats
        parts_ = [f"public_repos={repos}"]
        if stars:
            parts_.append(f"stars={stars}")
        if followers:
            parts_.append(f"followers={followers}")
        rows.append([("| github-stats: ", DIM), (" ".join(parts_), GREEN)])
    else:
        rows.append([("| github-stats: ", DIM), ("n/a", DIM)])
    rows.append([("|_updated: ", DIM), (now + " (GitHub Actions, daily)", WHITE)])
    rows.append([("", WHITE)])
    rows.append([("Nmap done: 1 IP address (1 host up) scanned in 0.42 seconds", WHITE)])

    prompt_txt = f"{HOST_PROMPT}:~$ "
    max_chars = max(
        [len(prompt_txt) + len(COMMAND)]
        + [sum(len(t) for t, _ in r) for r in rows]
    )
    width = int(max(max_chars * CW, max(len(b) for b in BANNER) * BCW) + PAD * 2 + 24)

    # --- vertical positions -------------------------------------------------
    y = TITLE_H + PAD + 4
    banner_y0 = y
    y += len(BANNER) * BLH + 14
    tagline_y = y
    y += LH + 10
    cmd_y = y
    y += LH
    out_y0 = y
    y += len(rows) * LH + 4
    final_prompt_y = y
    height = int(y + PAD)

    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="{FONT}" role="img" '
        f'aria-label="Terminal card for {escape(LOGIN)}">'
    )
    parts.append(f"<title>{escape(LOGIN)} | nmap-style profile card</title>")
    parts.append(
        f'<desc>Animated terminal output describing {escape(LOGIN)}: '
        + "; ".join(f"{p[1]}: {p[2]}" for p in PORTS)
        + "</desc>"
    )

    # window chrome
    parts.append(f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="12" fill="{BG}" stroke="{BORDER}"/>')
    parts.append(
        f'<path d="M0.5 {TITLE_H} V12.5 a12 12 0 0 1 12 -12 H{width - 12.5} a12 12 0 0 1 12 12 V{TITLE_H} Z" fill="{TITLEBAR}"/>'
    )
    parts.append(f'<line x1="0.5" y1="{TITLE_H}" x2="{width - 0.5}" y2="{TITLE_H}" stroke="{BORDER}"/>')
    for i, col in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
        parts.append(f'<circle cx="{22 + i * 20}" cy="{TITLE_H / 2}" r="6" fill="{col}"/>')
    parts.append(
        f'<text x="{width / 2}" y="{TITLE_H / 2 + 5}" font-size="13" fill="{DIM}" text-anchor="middle">'
        f"{escape(HOST_PROMPT)}: ~</text>"
    )

    # banner (always visible)
    for i, line in enumerate(BANNER):
        parts.append(text_el(PAD, banner_y0 + i * BLH + 12, [(line, GREEN)], size=BFS, cw=BCW))
    parts.append(text_el(PAD, tagline_y + 4, [(TAGLINE, DIM)]))

    # prompt + typed command
    parts.append(text_el(PAD, cmd_y, [(HOST_PROMPT, GREEN), (":~$ ", WHITE)]))
    cmd_x = PAD + len(prompt_txt) * CW
    n = len(COMMAND)
    t0, dur = 0.7, 1.7
    values = ";".join(str(round(i * CW, 1)) for i in range(n + 1))
    key_times = ";".join(str(round(i / n, 4)) for i in range(n + 1))
    parts.append(
        f'<clipPath id="typed"><rect x="{cmd_x}" y="{cmd_y - FS - 2}" width="0" height="{LH + 4}">'
        f'<animate attributeName="width" values="{values}" keyTimes="{key_times}" calcMode="discrete" '
        f'begin="{t0}s" dur="{dur}s" fill="freeze"/></rect></clipPath>'
    )
    parts.append(f'<g clip-path="url(#typed)">{text_el(cmd_x, cmd_y, [(COMMAND, WHITE)])}</g>')

    # output rows appear one after another once the command is "run"
    start = t0 + dur + 0.35
    for i, segs in enumerate(rows):
        el = text_el(PAD, out_y0 + i * LH, segs)
        if not el:
            continue
        parts.append(
            f'<g opacity="0"><set attributeName="opacity" to="1" begin="{round(start + i * 0.16, 2)}s" fill="freeze"/>{el}</g>'
        )

    # final prompt with blinking cursor
    end = start + len(rows) * 0.16 + 0.2
    parts.append(
        f'<g opacity="0"><set attributeName="opacity" to="1" begin="{round(end, 2)}s" fill="freeze"/>'
        + text_el(PAD, final_prompt_y, [(HOST_PROMPT, GREEN), (":~$ ", WHITE)])
        + f'<rect x="{PAD + len(prompt_txt) * CW}" y="{final_prompt_y - FS + 1}" width="{CW}" height="{FS + 2}" fill="{GREEN}">'
        '<animate attributeName="opacity" values="1;0;1" dur="1.1s" repeatCount="indefinite"/></rect></g>'
    )

    parts.append("</svg>")
    return "\n".join(parts)


def main():
    svg = build()
    os.makedirs(os.path.dirname(OUT_PATH) or ".", exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {OUT_PATH} ({len(svg)} bytes)")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Generate an animated nmap-style terminal card as a self-contained SVG.

Pure standard library: no third-party packages, no external assets, no JavaScript.
The animation is SMIL inside the SVG, which GitHub renders when the file is
embedded with an <img> tag in a profile README.

Env vars:
  GITHUB_LOGIN  GitHub username (default: maverickaayush)
  GITHUB_TOKEN  optional, raises API rate limits for the live stats line
  OUT_PATH      output file (default: assets/profile.svg)
  METRICS_RAW   raw lowlighter/metrics "terminal" SVG (default: github-metrics.svg).
                If present, its whoami / languages / isometric calendar sections are
                continued inside this same terminal window. If missing or unreadable,
                the card is just the nmap section.
"""
import json
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html import escape

LOGIN = os.environ.get("GITHUB_LOGIN", "maverickaayush")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT_PATH = os.environ.get("OUT_PATH", "assets/profile.svg")
METRICS_RAW = os.environ.get("METRICS_RAW", "github-metrics.svg")

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

# Continuation of the session (needs github-metrics.svg from the Metrics workflow)
SHOW_METRICS_BANNER = False   # lowlighter's "ABSOLUTELY NO WARRANTY" header + "Connection reset" footer
CAL_WIDTH = 430               # on-screen width of the isometric calendar, in px

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

# lowlighter uses GitHub's light-mode green scale; map it to the card palette
COLOR_MAP = {
    "#ebedf0": "#243241",  # no contributions
    "#9be9a8": "#0b4a22",  # level 1
    "#40c463": "#0f7a30",  # level 2
    "#30a14e": "#16b343",  # level 3
    "#216e39": GREEN,      # level 4
}

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
    """One <text> row made of coloured segments, width pinned with textLength.

    A segment is (text, colour) or (text, colour, bold).
    """
    n = sum(len(seg[0]) for seg in segs)
    if n == 0:
        return ""
    spans = ""
    for seg in segs:
        weight = ' font-weight="700"' if len(seg) > 2 and seg[2] else ""
        spans += f'<tspan fill="{seg[1]}"{weight}>{escape(seg[0])}</tspan>'
    return (
        f'<text x="{x}" y="{y}" font-size="{size}" textLength="{round(n * cw, 1)}" '
        f'lengthAdjust="spacing" xml:space="preserve" style="white-space:pre">{spans}</text>'
    )


# ----------------------------------------------------------------------------
# Metrics section: parse lowlighter's terminal SVG into rows we can draw ourselves
# ----------------------------------------------------------------------------
CAL_TOKEN = "@@CAL@@"


def remap_color(c):
    return COLOR_MAP.get(c.lower(), c)


def _color_bars(segs):
    """Turn the '#' run inside [####    ] language bars green."""
    out = []
    for seg in segs:
        text, color = seg[0], seg[1]
        bold = len(seg) > 2 and seg[2]
        pos = 0
        for m in re.finditer(r"\[(#+)( *)\]", text):
            if m.start() > pos:
                out.append((text[pos:m.start()], color, bold))
            out.append(("[", color, bold))
            out.append((m.group(1), GREEN, bold))
            out.append((m.group(2) + "]", color, bold))
            pos = m.end()
        if pos < len(text):
            out.append((text[pos:], color, bold))
    return out


class _Lines:
    def __init__(self, base_color=WHITE):
        self.rows, self.cur, self.base = [], [], base_color
        self.skip_nl = False

    def newline(self):
        self.rows.append(_color_bars(self.cur))
        self.cur = []

    def add(self, text, style):
        if CAL_TOKEN in text:
            before, after = text.split(CAL_TOKEN, 1)
            self.add(before, style)
            if self.cur:
                self.newline()
            self.rows.append("CAL")
            self.skip_nl = True
            text = after
        if self.skip_nl and text:
            if text.startswith("\n"):
                text = text[1:]
            self.skip_nl = False
        parts = text.split("\n")
        for i, part in enumerate(parts):
            if i > 0:
                self.newline()
            if part:
                self.cur.append((part, style.get("color", self.base), bool(style.get("bold"))))

    def finish(self):
        if self.cur:
            self.newline()
        return self.rows


def _walk(node, style, lines):
    if node.text:
        lines.add(node.text, style)
    for ch in node:
        st = dict(style)
        tag = ch.tag.split("}")[-1]
        if tag == "b":
            st["bold"] = True
        elif tag == "span":
            m = re.search(r"color:\s*(#[0-9a-fA-F]{3,8})", ch.get("style", ""))
            if m:
                st["color"] = remap_color(m.group(1))
            cls = ch.get("class", "")
            if "ps1-path" in cls:
                st["color"] = GREEN
            elif "ps1-location" in cls:
                st["color"] = CYAN
        _walk(ch, st, lines)
        if ch.tail:
            lines.add(ch.tail, style)


def _matrix(transform):
    """Compose scale()/translate() into (sx, sy, tx, ty); ignores anything else."""
    m = (1.0, 1.0, 0.0, 0.0)
    for name, args in re.findall(r"(scale|translate)\(([^)]*)\)", transform or ""):
        v = [float(a) for a in re.split(r"[ ,]+", args.strip()) if a]
        if name == "scale":
            op = (v[0], v[1] if len(v) > 1 else v[0], 0.0, 0.0)
        else:
            op = (1.0, 1.0, v[0], v[1] if len(v) > 1 else 0.0)
        m = (m[0] * op[0], m[1] * op[1], m[0] * op[2] + m[2], m[1] * op[3] + m[3])
    return m


def _bbox(el, m, acc):
    tag = el.tag.split("}")[-1]
    if el is not None and el.get("transform"):
        t = _matrix(el.get("transform"))
        m = (m[0] * t[0], m[1] * t[1], m[0] * t[2] + m[2], m[1] * t[3] + m[3])
    if tag == "path":
        nums = [float(n) for n in re.findall(r"-?\d*\.?\d+", el.get("d", ""))]
        for x, y in zip(nums[0::2], nums[1::2]):
            X, Y = m[0] * x + m[2], m[1] * y + m[3]
            acc[0], acc[1] = min(acc[0], X), min(acc[1], Y)
            acc[2], acc[3] = max(acc[2], X), max(acc[3], Y)
    for ch in el:
        _bbox(ch, m, acc)


def load_metrics(path=None):
    """Return {"rows": [...], "cal": {...}|None} parsed from lowlighter's SVG, or None."""
    path = path or METRICS_RAW
    try:
        with open(path, encoding="utf-8") as f:
            raw = f.read()
        pre = re.search(r"<pre>(.*)</pre>", raw, re.S).group(1)
        cal = None
        cm = re.search(r'<div class="isocalendar">\s*(<svg\b[^>]*>)(.*?)</svg>\s*</div>', pre, re.S)
        if cm:
            body = cm.group(2)
            for old, new in COLOR_MAP.items():
                body = body.replace(old, new)
            acc = [1e9, 1e9, -1e9, -1e9]
            _bbox(ET.fromstring(cm.group(1) + cm.group(2) + "</svg>"), (1.0, 1.0, 0.0, 0.0), acc)
            if acc[2] > acc[0] and acc[3] > acc[1]:
                pad = 4
                cal = {"body": body, "vb": (acc[0] - pad, acc[1] - pad, acc[2] - acc[0] + 2 * pad, acc[3] - acc[1] + 2 * pad)}
            pre = pre[: cm.start()] + CAL_TOKEN + pre[cm.end():]
        root = ET.fromstring("<root>" + pre + "</root>")
    except Exception as exc:  # missing file, unexpected markup, ...
        print(f"note: metrics section skipped ({exc})")
        return None

    rows, first = [], True
    for el in root:
        cls = el.get("class", "")
        tag = el.tag.split("}")[-1]
        if tag == "div" and "banner" in cls:
            if SHOW_METRICS_BANNER:
                lines = _Lines(DIM)
                _walk(el, {}, lines)
                rows += lines.finish() + [[]]
            continue
        if tag == "footer":
            if SHOW_METRICS_BANNER:
                rows += [[], [("".join(el.itertext()), DIM)]]
            continue
        if tag == "div" and "stdin" in cls:
            cmd = "".join(el.itertext()).split("$ ", 1)[-1].strip()
            if not first:
                rows.append([])
            first = False
            rows.append([(HOST_PROMPT, GREEN), (":~$ ", WHITE), (cmd, WHITE)])
        elif tag == "div" and "stdout" in cls:
            lines = _Lines()
            _walk(el, {}, lines)
            rows += lines.finish()
    if not rows:
        return None
    if "CAL" in rows and not cal:
        rows = [r for r in rows if r != "CAL"]
    return {"rows": rows, "cal": cal}


def build():
    stats = live_stats()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    metrics = load_metrics()

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
    n_nmap_rows = len(rows)
    if metrics:  # same session continues: whoami / locale / ncal
        rows.append([("", WHITE)])
        rows.extend(metrics["rows"])

    prompt_txt = f"{HOST_PROMPT}:~$ "
    max_chars = max(
        [len(prompt_txt) + len(COMMAND)]
        + [sum(len(seg[0]) for seg in r) for r in rows if r != "CAL"]
    )
    width = int(max(max_chars * CW, max(len(b) for b in BANNER) * BCW) + PAD * 2 + 24)

    cal = metrics["cal"] if metrics else None
    if cal:
        vb_x, vb_y, vb_w, vb_h = cal["vb"]
        cal_w = min(CAL_WIDTH, width - PAD * 2)
        cal_h = round(cal_w * vb_h / vb_w, 1)
        cal_x = round((width - cal_w) / 2, 1)

    # --- vertical positions -------------------------------------------------
    y = TITLE_H + PAD + 4
    banner_y0 = y
    y += len(BANNER) * BLH + 14
    tagline_y = y
    y += LH + 10
    cmd_y = y
    y += LH
    out_y0 = y
    placed = []  # (row, baseline_y or calendar_top)
    cy = out_y0
    for r in rows:
        if r == "CAL":
            placed.append((r, cy - FS + 6))
            cy += cal_h + 12
        else:
            placed.append((r, cy))
            cy += LH
    final_prompt_y = cy + 4
    height = int(final_prompt_y + PAD)

    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="{FONT}" role="img" '
        f'aria-label="Terminal card for {escape(LOGIN)}">'
    )
    parts.append(f"<title>{escape(LOGIN)} | terminal profile card</title>")
    desc = "Animated terminal output describing " + escape(LOGIN) + ": " + "; ".join(f"{p[1]}: {p[2]}" for p in PORTS)
    if metrics:
        desc += ". Followed by language usage bars" + (" and an isometric GitHub contribution calendar." if metrics["cal"] else ".")
    parts.append(f"<desc>{desc}</desc>")

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
    t = t0 + dur + 0.35
    for i, (row, ypos) in enumerate(placed):
        step = 0.16 if i < n_nmap_rows else 0.11
        if row == "CAL":
            parts.append(
                f'<g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="{round(t, 2)}s" dur="0.9s" fill="freeze"/>'
                f'<svg x="{cal_x}" y="{ypos}" width="{cal_w}" height="{cal_h}" '
                f'viewBox="{vb_x:.1f} {vb_y:.1f} {vb_w:.1f} {vb_h:.1f}" overflow="visible">{cal["body"]}</svg></g>'
            )
            t += 0.9
            continue
        el = text_el(PAD, ypos, row)
        if el:
            parts.append(
                f'<g opacity="0"><set attributeName="opacity" to="1" begin="{round(t, 2)}s" fill="freeze"/>{el}</g>'
            )
        t += step

    # final prompt with blinking cursor
    end = t + 0.2
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

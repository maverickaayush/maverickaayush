#!/usr/bin/env python3
"""Convert a head-and-shoulders photo into the ASCII portrait used by the profile card.

Run this once on your own machine. It is NOT part of the daily GitHub Action, and the
photo itself is never committed: only the generated text file is.

    pip install opencv-python numpy
    python3 scripts/make_portrait.py ~/photo.png              # writes assets/portrait.txt
    python3 scripts/make_portrait.py ~/face.png --as-is --trim 0 --cols 56   # photo already cropped: use it exactly
    python3 scripts/make_portrait.py ~/photo.png --cols 72      # wide photo: auto-crop to the head, smaller block
    python3 scripts/make_portrait.py ~/photo.png --edges 0.9    # stronger outlines

--trim removes rows from the bottom so the portrait ends at the collar instead of the shoulders.

The face is found with OpenCV's Haar cascade, the subject is cut out with GrabCut so the
wall behind you stays empty, then brightness and edges are mapped onto a character ramp.
Light pixels get dense characters because the card has a dark background.
"""
import argparse
import os

import cv2
import numpy as np

RAMP = " .'`,:;-~=+*xoO#%@"  # must match RAMP in generate_card.py
CELL_ASPECT = 0.58           # character cell width / height


def subject_mask(crop, face, origin):
    """GrabCut seeded from the detected face box. Returns a soft 0..1 mask."""
    fx, fy, fw, fh = face
    x0, y0 = origin
    ch, cw = crop.shape[:2]
    m = np.full((ch, cw), cv2.GC_PR_BGD, np.uint8)
    # probable foreground: head column, then the torso below the chin
    m[max(0, int(fy - y0 - fh * 0.45)):, max(0, int(fx - x0 - fw * 0.1)):min(cw, int(fx - x0 + fw * 1.1))] = cv2.GC_PR_FGD
    m[int(fy - y0 + fh * 1.05):, int(cw * 0.08):int(cw * 0.92)] = cv2.GC_PR_FGD
    # sure foreground: the middle of the face
    m[int(fy - y0 + fh * 0.1):int(fy - y0 + fh * 0.95), int(fx - x0 + fw * 0.15):int(fx - x0 + fw * 0.85)] = cv2.GC_FGD
    # sure background: side margins and everything well above the hair
    m[:, : int(cw * 0.03)] = cv2.GC_BGD
    m[:, int(cw * 0.97):] = cv2.GC_BGD
    m[: int(max(2, (fy - y0) - fh * 0.5)), :] = cv2.GC_BGD
    cv2.grabCut(crop, m, None, np.zeros((1, 65)), np.zeros((1, 65)), 6, cv2.GC_INIT_WITH_MASK)
    fg = np.where((m == cv2.GC_FGD) | (m == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(fg)
    if n > 1:  # keep the biggest blob only
        fg = np.where(lab == 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA]), 255, 0).astype(np.uint8)
    return cv2.GaussianBlur(fg, (7, 7), 0).astype(np.float32) / 255.0


def build(path, cols, crop_w, top, bottom, gamma, edge_w, trim, floor=0.1, sigma=2.2, tone_w=0.6, dark=0.0, as_is=False):
    img = cv2.imread(path)
    if img is None:
        raise SystemExit(f"could not read image: {path}")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    casc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = casc.detectMultiScale(gray, 1.1, 6, minSize=(max(40, gray.shape[1] // 8),) * 2)
    if len(faces) == 0:
        raise SystemExit("no face found: use a front-facing, well lit, head-and-shoulders photo")
    fx, fy, fw, fh = sorted(faces, key=lambda f: -f[2] * f[3])[0]

    H, W = gray.shape
    cx = fx + fw / 2
    if as_is:  # the photo is already cropped the way you want: use every pixel of it
        x0, x1, y0, y1 = 0, W, 0, H
    else:
        x0, x1 = int(max(0, cx - fw * crop_w / 2)), int(min(W, cx + fw * crop_w / 2))
        y0, y1 = int(max(0, fy - fh * top)), int(min(H, fy + fh * bottom))
    crop = img[y0:y1, x0:x1]
    ch, cw = crop.shape[:2]

    inside = subject_mask(crop, (fx, fy, fw, fh), (x0, y0))

    g = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(6, 6)).apply(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY))
    tone = (g.astype(np.float32) / 255.0) ** gamma
    sel = inside > 0.5
    t_lo, t_hi = np.percentile(tone[sel], 5), np.percentile(tone[sel], 95)
    tone = np.clip((tone - t_lo) / (t_hi - t_lo + 1e-6), 0, 1)  # use the subject's full tonal range
    if dark:  # dark hair, beard and glasses get dense characters so they read as solid shapes, not holes
        raw = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0  # before CLAHE, which lifts dark hair
        lum = cv2.GaussianBlur(raw, (0, 0), 1.5)
        fy0, fx0 = int(fy - y0), int(fx - x0)  # median of the nose-bridge area = skin tone; dark means well below that
        skin = np.median(lum[fy0 + int(fh * 0.25):fy0 + int(fh * 0.5), fx0 + int(fw * 0.4):fx0 + int(fw * 0.6)])
        cut = 0.8 * skin
        d = np.clip((cut - lum) / (cut + 1e-6), 0, 1) ** 0.7
        tone = np.clip(tone * (1 - d), 0, 1)
    blur = cv2.GaussianBlur(g, (0, 0), sigma)
    edges = np.sqrt(cv2.Sobel(blur, cv2.CV_32F, 1, 0) ** 2 + cv2.Sobel(blur, cv2.CV_32F, 0, 1) ** 2)
    edges = np.clip(edges / (np.percentile(edges, 99) + 1e-6), 0, 1)
    comb = np.clip(tone * tone_w + edges * edge_w, 0, 1) * inside
    if dark:
        comb = np.maximum(comb, d * dark * inside)
    comb = np.where(inside > 0.5, np.maximum(comb, floor), comb)  # keeps the silhouette faintly visible

    rows = int(round(cols * (ch / cw) * CELL_ASPECT))
    small = cv2.resize(comb, (cols, rows), interpolation=cv2.INTER_AREA)
    ms = cv2.resize(inside, (cols, rows), interpolation=cv2.INTER_AREA)
    lo, hi = np.percentile(small[ms > 0.5], 2), np.percentile(small[ms > 0.5], 99)
    s = np.clip((small - lo) / (hi - lo + 1e-6), 0, 1)

    lines = []
    for r in range(rows):
        lines.append("".join(" " if ms[r, c] < 0.35 else RAMP[int(s[r, c] * (len(RAMP) - 1))] for c in range(cols)).rstrip())
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if trim:
        lines = lines[:-trim]
    margin = min(len(l) - len(l.lstrip()) for l in lines if l.strip())
    return [l[margin:] for l in lines]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("photo")
    ap.add_argument("--out", default="assets/portrait.txt")
    ap.add_argument("--cols", type=int, default=86, help="portrait width in characters")
    ap.add_argument("--crop-width", type=float, default=1.45, help="crop width as a multiple of the face width")
    ap.add_argument("--top", type=float, default=0.42, help="headroom above the face, in face heights")
    ap.add_argument("--bottom", type=float, default=1.10, help="space below the face top, in face heights")
    ap.add_argument("--gamma", type=float, default=0.8, help="lower = brighter midtones")
    ap.add_argument("--edges", type=float, default=0.9, help="edge strength, 0 to 1")
    ap.add_argument("--floor", type=float, default=0.1, help="minimum brightness of the subject, lifts dark hair and beard")
    ap.add_argument("--sigma", type=float, default=2.0, help="edge detail, lower = finer lines")
    ap.add_argument("--tone", type=float, default=0.5, help="weight of skin tone vs edges")
    ap.add_argument("--dark", type=float, default=1.1, help="density for dark hair and beard, 0 to turn off")
    ap.add_argument("--as-is", action="store_true", help="skip auto-crop, use the whole photo exactly as given")
    ap.add_argument("--trim", type=int, default=8, help="rows to cut from the bottom")
    a = ap.parse_args()

    lines = build(a.photo, a.cols, a.crop_width, a.top, a.bottom, a.gamma, a.edges, a.trim, a.floor, a.sigma, a.tone, a.dark, a.as_is)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {a.out}: {max(len(l) for l in lines)} cols x {len(lines)} rows")


if __name__ == "__main__":
    main()

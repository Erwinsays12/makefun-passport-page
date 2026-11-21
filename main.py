#!/usr/bin/env python3
"""The Passport Page of a Country That Isn't There.

A pure-stdlib program (no network, no third-party packages) that draws one
invented passport spread for the fictional Republic of Talveria and writes
it to /output/entry.png (PNG, 1024x700, under 1 MiB).

Everything is drawn procedurally: paper, guilloche, a coat of arms, a
stylised engraved portrait, bilingual data fields, a machine-readable zone
with real ICAO check digits, a visa sticker, and arrival/departure stamps
whose dates form one consistent travel history (nothing predates the
passport's issue, 12 MAR 2024).

The lettering uses a small original stroke font defined below (each glyph
is a list of polylines on a 6x9 grid; baseline y=7, cap top y=0).
"""

import math
import os
import struct
import zlib

SS = 2                    # supersampling factor (draw at 2x, downsample)
OUT_W, OUT_H = 1024, 700  # final image size in pixels
W, H = OUT_W * SS, OUT_H * SS

# ---------------------------------------------------------------- font ----
# Glyphs: "x,y x,y ..." polylines, grid x 0..6, y 0..9, baseline y=7.
FONT = {
    "A": ["0,7 3,0 6,7", "1.7,3.8 4.3,3.8"],
    "B": ["0,7 0,0", "0,0 3.5,0 5,1.3 4,3 0,3", "0,3 4,3 5.5,4.6 4.5,6.2 3,7 0,7"],
    "C": ["5.5,1.5 4,0 1.5,0 0,2 0,5 1.5,7 4,7 5.5,5.5"],
    "D": ["0,7 0,0", "0,0 3,0 5,1.5 5.5,3.5 5,5.5 3,7 0,7"],
    "E": ["0,7 0,0 5,0", "0,3.5 4,3.5", "0,7 5,7"],
    "F": ["0,7 0,0 5,0", "0,3.5 4,3.5"],
    "G": ["5.5,1.5 4,0 1.5,0 0,2 0,5 1.5,7 4,7 5.5,5.5 5.5,3.5 3.5,3.5"],
    "H": ["0,7 0,0", "6,7 6,0", "0,3.5 6,3.5"],
    "I": ["3,7 3,0", "1,0 5,0", "1,7 5,7"],
    "J": ["2,0 5,0", "5,0 5,5.5 4,7 2,7 0.8,5.8"],
    "K": ["0,7 0,0", "5.5,0 0,3.5", "1.8,3.8 5.5,7"],
    "L": ["0,7 0,0", "0,7 5,7"],
    "M": ["0,7 0,0 3,4.5 6,0 6,7"],
    "N": ["0,7 0,0 6,7 6,0"],
    "O": ["2,0 4,0 5.5,1.5 6,3.5 5.5,5.5 4,7 2,7 0.5,5.5 0,3.5 0.5,1.5 2,0"],
    "P": ["0,7 0,0", "0,0 3.5,0 5,1.3 4,3.5 0,3.5"],
    "Q": ["2,0 4,0 5.5,1.5 6,3.5 5.5,5.5 4,7 2,7 0.5,5.5 0,3.5 0.5,1.5 2,0",
          "4,5.5 6,7"],
    "R": ["0,7 0,0", "0,0 3.5,0 5,1.3 4,3.5 0,3.5", "2.5,3.5 5.5,7"],
    "S": ["5,1 4,0 1.5,0 0.5,1 0.5,2.5 2,3.5 4,3.5 5.5,4.5 5.5,6 4,7 1.5,7 0.5,6"],
    "T": ["0,0 6,0", "3,7 3,0"],
    "U": ["0,0 0,5 1,7 3,7 5,7 6,5 6,0"],
    "V": ["0,0 3,7 6,0"],
    "W": ["0,0 1.5,7 3,3.5 4.5,7 6,0"],
    "X": ["0,0 6,7", "6,0 0,7"],
    "Y": ["0,0 3,3.5 6,0", "3,7 3,3.5"],
    "Z": ["0,0 6,0 0,7 6,7"],
    "a": ["1.2,3.8 2.5,2.5 4.5,2.5 5.5,3.8 5.5,6 4.5,7 2.5,7 1.2,6 1.2,4.5",
          "5.5,2.5 5.5,7"],
    "b": ["1,9 1,0", "1,4.5 3,2.5 5,3.5 5,5.5 3,7 1,7"],
    "c": ["5,3.5 4,2.5 2,2.5 1,4 1,5.5 2,7 4,7 5,6"],
    "d": ["5,0 5,9", "1,4 2,2.5 4,2.5 5,4 5,5.5 4,7 2,7 1,5.5 1,4"],
    "e": ["5,4.5 4,2.5 2,2.5 1,4 1,5.5 2,7 4,7 5,6", "1,4.8 5,4.8"],
    "f": ["2,7 2,1.5 3,0.5", "1,3.5 3.5,3.5"],
    "g": ["1.2,3.8 2.5,2.5 4.5,2.5 5.5,3.8 5.5,6 4.5,7 2.5,7 1.2,6 1.2,4.5",
          "5.5,2.5 5.5,7.5 4,9 2,9"],
    "h": ["1,7 1,0", "1,4.5 2.5,2.5 4.5,2.5 5.5,4 5.5,7"],
    "i": ["3,7 3,2.5", "2.8,0.6 3.2,0.6"],
    "j": ["3.5,2.5 3.5,7.5 2.5,9 1.5,9", "3.2,0.6 3.8,0.6"],
    "k": ["1,7 1,0", "5,2.5 1,4.5", "2.5,5 5,7"],
    "l": ["3,7 3,0"],
    "m": ["0.8,7 0.8,2.5", "0.8,4.5 2,2.5 3.4,3.5 3.4,7",
          "3.4,4.5 4.6,2.5 5.8,3.8 5.8,7"],
    "n": ["1,7 1,2.5", "1,4.5 2.5,2.5 4.5,2.5 5.5,4 5.5,7"],
    "o": ["2,2.5 4,2.5 5.5,4 5.5,5.5 4,7 2,7 0.5,5.5 0.5,4 2,2.5"],
    "p": ["1,2.5 1,9", "1,4.5 3,2.5 5,3.5 5,5.5 3,7 1,7"],
    "q": ["5,2.5 5,9", "1,4.5 3,2.5 5,3.5 5,5.5 3,7 1,7"],
    "r": ["1,7 1,2.5", "1,4.5 2.5,2.5 4.5,2.5"],
    "s": ["5,3.5 4,2.5 2,2.5 1,3.5 1,4.8 2.5,5.5 4,5.5 5,6.3 4,7 2,7 1,6"],
    "t": ["3,7.5 3,0.5", "1.5,3.5 4.5,3.5"],
    "u": ["1,2.5 1,5.5 2,7 3.5,7 5,7 5.5,5.5 5.5,2.5"],
    "v": ["0.5,2.5 3,7 5.5,2.5"],
    "w": ["0.5,2.5 1.8,7 3,4.5 4.2,7 5.5,2.5"],
    "x": ["0.8,2.5 5.2,7", "5.2,2.5 0.8,7"],
    "y": ["0.8,2.5 3,7 5.2,2.5", "3,7 2.8,9 1.8,9"],
    "z": ["0.8,2.5 5.2,2.5 0.8,7 5.2,7"],
    "0": ["2,0 4,0 5.5,1.5 6,3.5 5.5,5.5 4,7 2,7 0.5,5.5 0,3.5 0.5,1.5 2,0",
          "1.5,5.5 4.5,1.5"],
    "1": ["3.5,7 3.5,0", "1.5,1.5 3.5,0", "1.5,7 5.5,7"],
    "2": ["1,1.5 2,0 4,0 5,1 5,2.5 2,5.5 0.8,7 5.5,7"],
    "3": ["1,1 2,0 4,0 5,1 4.5,3 3,3.5", "3,3.5 4.5,3.5 5.5,4.5 5,6.5 4,7 2,7 1,6"],
    "4": ["4.5,0 4.5,7", "0.5,4.5 5.5,4.5", "0.5,4.5 3.5,0"],
    "5": ["5,0 1,0 1,3.5 3.5,3.5 5,4.5 5,6 4,7 2,7 1,6"],
    "6": ["4.5,0.8 2.5,0 1,1.5 0.5,3.5 0.5,5 1.5,7 3.5,7 5,5.5 5,4 3.5,3 1.5,3.5"],
    "7": ["0.8,0 5.5,0 3,7"],
    "8": ["2,0 4,0 5,1.5 4,3.5 2,3.5 1,1.5 2,0",
          "1,4.5 2,3.5 4,3.5 5,4.5 5,5.5 4,7 2,7 1,5.5 1,4.5"],
    "9": ["2,0 4,0 5,1.5 5,3.5 4,5 2,5 1,3.5 1,2 2,0", "4.8,2.5 4.5,5.5 3.5,7"],
    ".": ["2.8,6.8 3.2,6.8"],
    ",": ["2.8,6.8 3.2,6.8", "3,7 2.5,8.5 2,9"],
    "-": ["0.8,3.5 5.2,3.5"],
    "/": ["5,0 1,7"],
    "(": ["3,0 1.5,1.5 1.5,5.5 3,7"],
    ")": ["3,0 4.5,1.5 4.5,5.5 3,7"],
    ":": ["2.8,2.8 3.2,2.8", "2.8,6 3.2,6"],
    "<": ["5,0 1,3.5 5,7"],
    ">": ["1,0 5,3.5 1,7"],
    "'": ["3,0 2.5,2"],
    '"': ["2,0 1.5,2", "4.5,0 4,2"],
    "+": ["0.8,3.5 5.2,3.5", "3,1 3,6"],
    "=": ["0.8,2.8 5.2,2.8", "0.8,4.8 5.2,4.8"],
    "!": ["3,0 3,5", "2.8,6.5 3.2,6.5"],
    "?": ["1.5,1.5 2,0 4,0 5,1.5 4.5,3 3.5,3.5 3.5,4.5", "2.8,6.5 3.2,6.5"],
    ";": ["2.8,2.8 3.2,2.8", "2.8,6 3.2,6", "3,6.8 2.5,8.5 2,9"],
    "_": ["0.5,7.8 5.5,7.8"],
    "#": ["2,0 2,7", "4,0 4,7", "0.5,2.5 5.5,2.5", "0.5,4.5 5.5,4.5"],
    "%": ["5,0 1,7", "1.2,0.8 2.8,0.8 2.8,2.6 1.2,2.6 1.2,0.8",
          "3.4,4.4 5,4.4 5,6.2 3.4,6.2 3.4,4.4"],
    "*": ["3,0.5 3,6.5", "0.8,2 5.2,5", "5.2,2 0.8,5"],
    " ": [],
}
ADVANCE = 6.6  # glyph advance in grid units


def _parse_font():
    out = {}
    for ch, strokes in FONT.items():
        parsed = []
        for s in strokes:
            pts = []
            for tok in s.split():
                x, y = tok.split(",")
                pts.append((float(x), float(y)))
            parsed.append(pts)
        out[ch] = parsed
    return out


FONT_P = _parse_font()

# ---------------------------------------------------------------- canvas ---
class Canvas:
    """RGB framebuffer in logical coordinates; everything is drawn at SSx
    supersampling and downsampled at the end for smooth edges."""

    def __init__(self):
        self.px = bytearray(W * H * 3)

    def _set(self, x, y, r, g, b, a):
        if 0 <= x < W and 0 <= y < H:
            i = (y * W + x) * 3
            if a >= 0.999:
                self.px[i] = r
                self.px[i + 1] = g
                self.px[i + 2] = b
            elif a > 0:
                ia = 1.0 - a
                self.px[i] = int(self.px[i] * ia + r * a)
                self.px[i + 1] = int(self.px[i + 1] * ia + g * a)
                self.px[i + 2] = int(self.px[i + 2] * ia + b * a)

    def disc(self, cx, cy, rad, color, a=1.0):
        """Filled disc centred at supersampled (cx, cy) with radius rad."""
        r, g, b = color
        rad_i = int(rad + 0.5)
        cx_i, cy_i = int(cx), int(cy)
        for dy in range(-rad_i, rad_i + 1):
            v = rad * rad - dy * dy
            dx_max = int(v ** 0.5) if v > 0 else 0
            for dx in range(-dx_max, dx_max + 1):
                self._set(cx_i + dx, cy_i + dy, r, g, b, a)

    def rect(self, x, y, w, h, color, a=1.0):
        r, g, b = color
        x0, y0 = int(x * SS), int(y * SS)
        x1, y1 = int((x + w) * SS), int((y + h) * SS)
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(W, x1)
        y1 = min(H, y1)
        if x1 <= x0 or y1 <= y0:
            return
        if a >= 0.999:
            row = bytes((r, g, b)) * (x1 - x0)
            for yy in range(y0, y1):
                i = (yy * W + x0) * 3
                self.px[i:i + len(row)] = row
        else:
            for yy in range(y0, y1):
                for xx in range(x0, x1):
                    self._set(xx, yy, r, g, b, a)

    def vgrad_rect(self, x, y, w, h, top, bottom):
        """Vertical gradient rectangle, logical coords."""
        for yy in range(int(h * SS)):
            t = yy / max(1, int(h * SS) - 1)
            c = tuple(int(top[k] + (bottom[k] - top[k]) * t) for k in range(3))
            self.rect(x, y + yy / SS, w, 1 / SS + 0.001, c)

    def line(self, x0, y0, x1, y1, width, color, a=1.0):
        """Thick line between logical points, width in logical px."""
        x0s, y0s, x1s, y1s = x0 * SS, y0 * SS, x1 * SS, y1 * SS
        length = math.hypot(x1s - x0s, y1s - y0s)
        steps = max(1, int(length / 0.6))
        rad = max(0.6, width * SS / 2.0)
        for s in range(steps + 1):
            t = s / steps
            self.disc(x0s + (x1s - x0s) * t, y0s + (y1s - y0s) * t, rad, color, a)

    def polyline(self, pts, width, color, a=1.0, closed=False):
        seq = list(pts)
        if closed and len(seq) > 1:
            seq = seq + [seq[0]]
        for i in range(len(seq) - 1):
            self.line(seq[i][0], seq[i][1], seq[i + 1][0], seq[i + 1][1],
                      width, color, a)

    def poly(self, pts, color, a=1.0):
        """Filled polygon (even-odd scanline), logical coords."""
        pts = [(x * SS, y * SS) for x, y in pts]
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        y0, y1 = int(max(0, min(ys))), int(min(H - 1, max(ys)))
        n = len(pts)
        for yy in range(y0, y1 + 1):
            xs = []
            for i in range(n):
                x0, y0e = pts[i]
                x1, y1e = pts[(i + 1) % n]
                if (y0e <= yy < y1e) or (y1e <= yy < y0e):
                    t = (yy - y0e) / (y1e - y0e)
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            for j in range(0, len(xs) - 1, 2):
                xa, xb = int(math.ceil(xs[j])), int(math.floor(xs[j + 1]))
                for xx in range(max(0, xa), min(W - 1, xb) + 1):
                    self._set(xx, yy, color[0], color[1], color[2], a)

    def ellipse(self, cx, cy, rx, ry, color, a=1.0):
        cx, cy, rx, ry = cx * SS, cy * SS, rx * SS, ry * SS
        y0, y1 = int(max(0, cy - ry)), int(min(H - 1, cy + ry))
        for yy in range(y0, y1 + 1):
            dy = (yy - cy) / ry
            if abs(dy) > 1:
                continue
            dx = rx * math.sqrt(1 - dy * dy)
            xa, xb = int(math.ceil(cx - dx)), int(math.floor(cx + dx))
            for xx in range(max(0, xa), min(W - 1, xb) + 1):
                self._set(xx, yy, color[0], color[1], color[2], a)

    def circle_outline(self, cx, cy, r, width, color, a=1.0):
        steps = max(24, int(2 * math.pi * r * SS / 2))
        pts = [(cx + r * math.cos(2 * math.pi * i / steps),
                cy + r * math.sin(2 * math.pi * i / steps))
               for i in range(steps)]
        self.polyline(pts, width, color, a, closed=True)

    def rect_outline(self, x, y, w, h, width, color, a=1.0):
        self.polyline([(x, y), (x + w, y), (x + w, y + h), (x, y + h)],
                      width, color, a, closed=True)

    def downsample_png(self):
        """Box-downsample SSx -> 1x and encode as PNG bytes."""
        raw = bytearray()
        for oy in range(OUT_H):
            row = bytearray()
            row.append(0)  # filter: None for now, chosen below per row
            for ox in range(OUT_W):
                sr = sg = sb = 0
                for dy in range(SS):
                    base = ((oy * SS + dy) * W + ox * SS) * 3
                    for dx in range(SS):
                        i = base + dx * 3
                        sr += self.px[i]
                        sg += self.px[i + 1]
                        sb += self.px[i + 2]
                n = SS * SS
                row += bytes((sr // n, sg // n, sb // n))
            raw += row
        # Re-encode with per-row filter choice (None vs Sub) for size.
        best = bytearray()
        stride = OUT_W * 3 + 1
        prev = bytes(OUT_W * 3)
        for oy in range(OUT_H):
            chunk = bytes(raw[oy * stride + 1:(oy + 1) * stride])
            sub = bytes((chunk[i] - (chunk[i - 3] if i >= 3 else 0)) & 0xFF
                        for i in range(len(chunk)))
            c_none = zlib.compress(b"\x00" + chunk, 6)
            c_sub = zlib.compress(b"\x01" + sub, 6)
            if len(c_sub) < len(c_none):
                best += b"\x01" + sub
            else:
                best += b"\x00" + chunk
            prev = chunk
        comp = zlib.compress(bytes(best), 6)

        def chunk(typ, data):
            c = struct.pack(">I", len(data)) + typ + data
            return c + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)

        ihdr = struct.pack(">IIBBBBB", OUT_W, OUT_H, 8, 2, 0, 0, 0)
        return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
                + chunk(b"IDAT", comp) + chunk(b"IEND", b""))


# ------------------------------------------------------------------ text ---
def text_width(s, size, spacing=0.0):
    unit = size / 7.0
    return (len(s) * ADVANCE + max(0, len(s) - 1) * spacing) * unit


def draw_text(cv, x, y, s, size, color, angle=0.0, shear=0.0, align="left",
              weight=1.0, spacing=0.0, alpha=1.0):
    """Draw text; (x, y) is the baseline start (or centre/left per align).
    size = cap height in logical px. angle in degrees, shear shifts x by
    shear * (distance above baseline) for a handwritten slant."""
    unit = size / 7.0
    w = text_width(s, size, spacing)
    if align == "center":
        x -= w / 2.0
    elif align == "right":
        x -= w
    th = math.radians(angle)
    ca, sa = math.cos(th), math.sin(th)
    lw = max(0.9, size * 0.16 * weight)
    cx, cy = x, y
    for ch in s:
        for stroke in FONT_P.get(ch, []):
            pts = []
            for gx, gy in stroke:
                px = gx * unit
                py = (gy - 7.0) * unit
                px += shear * (-py)
                rx = cx + px * ca - py * sa
                ry = cy + px * sa + py * ca
                pts.append((rx, ry))
            if len(pts) == 1:
                cv.disc(pts[0][0] * SS, pts[0][1] * SS, lw * SS / 2 + 0.4,
                        color, alpha)
            elif len(pts) > 1:
                cv.polyline(pts, lw, color, alpha)
        cx += (ADVANCE + spacing) * unit * ca
        cy += (ADVANCE + spacing) * unit * sa


def wrap_text(s, size, max_w, spacing=0.0):
    """Greedy word wrap; returns list of lines that fit max_w."""
    words = s.split(" ")
    lines, cur = [], ""
    for word in words:
        trial = (cur + " " + word).strip()
        if text_width(trial, size, spacing) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines

# ------------------------------------------------------------- palette -----
NAVY = (28, 47, 74)
NAVY_D = (18, 32, 54)
LABEL = (90, 107, 125)
PAPER_L = (247, 242, 230)
PAPER_R = (245, 239, 224)
BURG = (140, 47, 57)
BLUE = (46, 90, 140)
BLUE_L = (222, 232, 243)
GOLD = (166, 124, 46)
INK = (26, 26, 46)
HAND = (42, 77, 143)

PAGE_L = (14, 14, 491, 672)   # x, y, w, h of the left page
PAGE_R = (519, 14, 491, 672)  # x, y, w, h of the right page


# ------------------------------------------------------------ guilloche ----
def guilloche(cv, x, y, w, h, color, alpha=0.16):
    """Fine wavy security lines across a page rectangle."""
    yy = y + 8
    phase = 0.0
    while yy < y + h - 4:
        pts = []
        xx = x + 4
        while xx <= x + w - 4:
            pts.append((xx, yy + 2.2 * math.sin(xx / 26.0 + phase)))
            xx += 6
        cv.polyline(pts, 0.7, color, alpha)
        yy += 13
        phase += 0.9


def speckle(cv, seed=12345):
    """Deterministic paper fibre specks."""
    s = seed
    for _ in range(2600):
        s = (s * 1103515245 + 12345) & 0x7FFFFFFF
        x = 14 + (s % 996)
        s = (s * 1103515245 + 12345) & 0x7FFFFFFF
        yy = 14 + (s % 672)
        s = (s * 1103515245 + 12345) & 0x7FFFFFFF
        v = s % 3
        cv.disc(x * SS, yy * SS, 0.7, (120, 110, 90), 0.05 + 0.02 * v)


# --------------------------------------------------------- coat of arms ----
def star(cv, cx, cy, r, color, a=1.0):
    pts = []
    for i in range(10):
        rr = r if i % 2 == 0 else r * 0.42
        ang = -math.pi / 2 + i * math.pi / 5
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    cv.poly(pts, color, a)


def shield(cv, cx, cy, w, h, outline=NAVY, fill=(250, 246, 236), alpha=1.0):
    """Small coat of arms: shield, star above three waves, on a disc."""
    cv.ellipse(cx, cy, w * 0.62, h * 0.62, (233, 226, 205), 0.55 * alpha)
    cv.circle_outline(cx, cy, w * 0.62, 1.0, outline, 0.8 * alpha)
    hw, hh = w / 2, h / 2
    pts = [(cx - hw, cy - hh), (cx + hw, cy - hh),
           (cx + hw, cy + hh * 0.45),
           (cx + hw * 0.55, cy + hh),
           (cx, cy + hh * 1.05),
           (cx - hw * 0.55, cy + hh),
           (cx - hw, cy + hh * 0.45)]
    cv.poly(pts, fill, alpha)
    cv.polyline(pts, 1.4, outline, alpha, closed=True)
    star(cv, cx, cy - hh * 0.42, w * 0.16, GOLD, alpha)
    for k, wy in enumerate((0.05, 0.30, 0.55)):
        pts = []
        xx = cx - hw * 0.82
        while xx <= cx + hw * 0.82:
            t = (xx - (cx - hw * 0.82)) / (hw * 1.64)
            pts.append((xx, cy + hh * wy + 2.0 * math.sin(t * math.pi * 2.5)))
            xx += 3
        cv.polyline(pts, 1.1, BLUE, 0.9 * alpha)


# -------------------------------------------------------------- portrait ---
def portrait(cv, x, y, w, h, alpha=1.0):
    """Stylised engraved passport photo of the holder: a woman in her
    late thirties, dark hair in a low bun, navy jacket, white collar."""
    cx = x + w / 2
    cv.vgrad_rect(x, y, w, h, (201, 214, 226), (168, 184, 202))
    # shoulders / jacket
    cv.poly([(x - 4, y + h), (x - 4, y + h * 0.78),
             (cx - w * 0.30, y + h * 0.66), (cx - w * 0.16, y + h * 0.60),
             (cx + w * 0.16, y + h * 0.60), (cx + w * 0.30, y + h * 0.66),
             (x + w + 4, y + h * 0.78), (x + w + 4, y + h)],
            (44, 62, 85), alpha)
    # shirt + tie
    cv.poly([(cx - w * 0.13, y + h * 0.62), (cx, y + h * 0.72),
             (cx + w * 0.13, y + h * 0.62), (cx + w * 0.10, y + h),
             (cx - w * 0.10, y + h)], (240, 238, 230), alpha)
    cv.poly([(cx - w * 0.035, y + h * 0.70), (cx + w * 0.035, y + h * 0.70),
             (cx + w * 0.05, y + h * 0.86), (cx, y + h * 0.92),
             (cx - w * 0.05, y + h * 0.86)], (74, 47, 57), alpha)
    # neck
    cv.rect(cx - w * 0.075, y + h * 0.52, w * 0.15, h * 0.12, (206, 168, 132), alpha)
    # ears
    cv.ellipse(cx - w * 0.235, y + h * 0.30, w * 0.035, h * 0.045, (211, 173, 136), alpha)
    cv.ellipse(cx + w * 0.235, y + h * 0.30, w * 0.035, h * 0.045, (211, 173, 136), alpha)
    # head
    cv.ellipse(cx, y + h * 0.30, w * 0.235, h * 0.235, (217, 180, 140), alpha)
    # soft shading on the right side of the face
    cv.ellipse(cx + w * 0.13, y + h * 0.30, w * 0.11, h * 0.20, (198, 160, 122), 0.45 * alpha)
    # hair: cap + low bun
    cv.poly([(cx - w * 0.245, y + h * 0.34), (cx - w * 0.25, y + h * 0.16),
             (cx - w * 0.15, y + h * 0.055), (cx, y + h * 0.035),
             (cx + w * 0.15, y + h * 0.055), (cx + w * 0.25, y + h * 0.16),
             (cx + w * 0.245, y + h * 0.34), (cx + w * 0.20, y + h * 0.22),
             (cx + w * 0.13, y + h * 0.13), (cx, y + h * 0.10),
             (cx - w * 0.13, y + h * 0.13), (cx - w * 0.20, y + h * 0.22)],
            (74, 52, 40), alpha)
    cv.ellipse(cx, y + h * 0.075, w * 0.10, h * 0.045, (74, 52, 40), alpha)
    # eyebrows
    cv.line(cx - w * 0.155, y + h * 0.245, cx - w * 0.055, y + h * 0.235, 2.2, (74, 52, 40), alpha)
    cv.line(cx + w * 0.055, y + h * 0.235, cx + w * 0.155, y + h * 0.245, 2.2, (74, 52, 40), alpha)
    # eyes: open, with a dark pupil
    for ex in (cx - w * 0.105, cx + w * 0.105):
        cv.ellipse(ex, y + h * 0.285, w * 0.042, h * 0.016, (245, 242, 235), alpha)
        cv.disc(ex * SS, (y + h * 0.285) * SS, 1.9, (40, 32, 28), alpha)
    # nose
    cv.polyline([(cx + w * 0.005, y + h * 0.29), (cx - w * 0.01, y + h * 0.375),
                 (cx + w * 0.02, y + h * 0.395)], 1.6, (178, 140, 104), alpha)
    # mouth
    cv.polyline([(cx - w * 0.05, y + h * 0.45), (cx, y + h * 0.462),
                 (cx + w * 0.05, y + h * 0.45)], 1.8, (146, 96, 84), alpha)
    # faint engraving hatch across the face
    for k in range(9):
        hy = y + h * (0.12 + k * 0.045)
        cv.line(cx - w * 0.20, hy, cx + w * 0.20, hy, 0.5, (120, 95, 70), 0.10 * alpha)


# ---------------------------------------------------------------- stamps ---
def rect_stamp(cv, x, y, w, h, lines, color, angle=0.0, size=11.0):
    """Rectangular border-control stamp, rotated; lines = list of texts."""
    cx, cy = x + w / 2, y + h / 2
    th = math.radians(angle)
    ca, sa = math.cos(th), math.sin(th)

    def rot(px, py):
        dx, dy = px - cx, py - cy
        return (cx + dx * ca - dy * sa, cy + dx * sa + dy * ca)

    corners = [rot(x, y), rot(x + w, y), rot(x + w, y + h), rot(x, y + h)]
    cv.polyline(corners, 2.0, color, 0.85, closed=True)
    inset = [(rot(x + 5, y + 5)), (rot(x + w - 5, y + 5)),
             (rot(x + w - 5, y + h - 5)), (rot(x + 5, y + h - 5))]
    cv.polyline(inset, 0.9, color, 0.7, closed=True)
    n = len(lines)
    for i, txt in enumerate(lines):
        ly = y + (h / (n + 1)) * (i + 1) + size * 0.32
        draw_text(cv, cx, ly, txt, size, color, angle=angle,
                  align="center", alpha=0.9)


def circle_stamp(cv, cx, cy, r, top, bottom, centre, color, angle=0.0):
    """Circular date stamp with text around the rim and a date in the middle.
    Screen coords: y grows downward, so angle 0 is east, -90 is the top,
    +90 is the bottom. Top text reads left to right over the top with its
    tops pointing out; bottom text reads left to right under the bottom
    with its tops pointing in."""
    cv.circle_outline(cx, cy, r, 2.0, color, 0.85)
    cv.circle_outline(cx, cy, r - 6, 0.9, color, 0.7)
    # arc step from the letter advance, capped so a long inscription
    # never wraps past the bottom half onto the sides
    def arc_step(txt):
        natural = math.degrees((9.0 / 7.0 * ADVANCE + 3.0) / max(10.0, r - 13))
        return min(natural, 150.0 / max(1, len(txt)))

    # top arc: centred on -90 deg, letters in order, tops outward
    step = arc_step(top)
    span = step * len(top)
    for i, ch in enumerate(top):
        a = math.radians(-90 - span / 2 + i * step + angle)
        px = cx + (r - 13) * math.cos(a)
        py = cy + (r - 13) * math.sin(a)
        draw_text(cv, px, py, ch, 9.0, color,
                  angle=math.degrees(a) + 90, align="center", alpha=0.9)
    # bottom arc: centred on +90 deg, letters in order, tops inward
    step = arc_step(bottom)
    span = step * len(bottom)
    for i, ch in enumerate(bottom):
        a = math.radians(90 + span / 2 - i * step + angle)
        px = cx + (r - 13) * math.cos(a)
        py = cy + (r - 13) * math.sin(a)
        draw_text(cv, px, py, ch, 9.0, color,
                  angle=math.degrees(a) - 90, align="center", alpha=0.9)
    # centre: date lines with roomy spacing
    for i, txt in enumerate(centre):
        draw_text(cv, cx, cy - 14 + i * 16, txt, 10.5, color,
                  angle=angle, align="center", alpha=0.9)


# ------------------------------------------------------------------- MRZ ---
def _mrz_value(ch):
    if ch.isdigit():
        return int(ch)
    if ch == "<":
        return 0
    return ord(ch) - 55  # A=10 ... Z=35


def mrz_check(s):
    total = 0
    for i, ch in enumerate(s):
        total += _mrz_value(ch) * (7, 3, 1)[i % 3]
    return str(total % 10)


def build_mrz():
    """TD3 two-line MRZ for Mara Elin Aurell, all check digits computed."""
    line1 = "P<TLVAURELL<<MARA<ELIN"
    line1 = line1 + "<" * (44 - len(line1))
    doc = "TLV482913"
    dob = "881214"
    exp = "340312"
    personal = "<" * 14
    composite_src = (doc + mrz_check(doc) + "TAL" + dob + mrz_check(dob)
                     + "F" + exp + mrz_check(exp) + personal
                     + mrz_check(personal))
    line2 = composite_src + mrz_check(composite_src)
    assert len(line1) == 44 and len(line2) == 44, (len(line1), len(line2))
    return line1, line2

# ------------------------------------------------------------------ scene --
def field(cv, x, y, label, value, size=11.5, w=140):
    """One stacked label/value pair; value wraps inside w."""
    draw_text(cv, x, y, label, 6.5, LABEL, spacing=0.3)
    lines = wrap_text(value, size, w)
    for i, ln in enumerate(lines):
        draw_text(cv, x, y + 13 + i * (size + 2.5), ln, size, NAVY)
    return y + 13 + len(lines) * (size + 2.5)


def signature(cv, x, y, w):
    """Flowing ink signature of Mara Elin Aurell (sheared strokes)."""
    ink = (38, 52, 96)
    cv.polyline([(x + 4, y + 16), (x + 14, y + 2), (x + 22, y + 14),
                 (x + 30, y + 6), (x + 38, y + 15), (x + 52, y + 4),
                 (x + 62, y + 12), (x + 74, y + 5), (x + 86, y + 13)],
                1.6, ink, 0.95)
    cv.polyline([(x + 58, y + 22), (x + 70, y + 10), (x + 82, y + 20),
                 (x + 96, y + 8), (x + 108, y + 17)], 1.4, ink, 0.95)
    cv.line(x, y + 26, x + w, y + 26, 0.9, NAVY, 0.8)


def left_page(cv):
    x, y, w, h = PAGE_L
    cv.rect(x, y, w, h, PAPER_L)
    guilloche(cv, x, y, w, h, (90, 110, 140))
    # perforated document number along the top edge
    perf = "TLV482913"
    unit = 7.0 / 7.0
    px = x + 20
    for ch in perf:
        for stroke in FONT_P.get(ch, []):
            for i in range(len(stroke) - 1):
                ax, ay = stroke[i]
                bx, by = stroke[i + 1]
                steps = max(1, int(math.hypot(bx - ax, by - ay) * 2))
                for s in range(steps + 1):
                    t = s / steps
                    cv.disc((px + (ax + (bx - ax) * t) * 0.62) * SS,
                            (y + 8 + (ay + (by - ay) * t) * 0.62) * SS,
                            0.9, (90, 90, 90), 0.5)
        px += ADVANCE * 0.62
    # header
    shield(cv, x + w / 2, y + 46, 40, 46)
    draw_text(cv, x + w / 2, y + 92, "REPUBLIC OF TALVERIA", 16.5, NAVY,
              align="center", spacing=1.2)
    draw_text(cv, x + w / 2, y + 110, "PASSPORT  \u2022  PASSEPORT", 10.5, NAVY_D,
              align="center", spacing=0.8)
    draw_text(cv, x + w / 2, y + 124, "TRAVEL DOCUMENT", 6.8, LABEL,
              align="center", spacing=1.0)
    cv.line(x + 24, y + 134, x + w - 24, y + 134, 1.0, NAVY, 0.7)
    cv.line(x + 24, y + 137, x + w - 24, y + 137, 0.6, NAVY, 0.5)

    # photo
    px0, py0, pw, ph = x + 24, y + 152, 148, 192
    cv.rect(px0 - 3, py0 - 3, pw + 6, ph + 6, (255, 255, 255))
    cv.rect_outline(px0 - 3, py0 - 3, pw + 6, ph + 6, 1.6, NAVY, 0.9)
    portrait(cv, px0, py0, pw, ph)
    draw_text(cv, px0 + pw / 2, py0 + ph + 16, "PHOTOGRAPH", 6.5, LABEL,
              align="center", spacing=0.8)

    # data fields, two columns beside the photo
    col_a, col_b = x + 196, x + 344
    fy = y + 152
    fy = field(cv, col_a, fy, "SURNAME / NOM", "AURELL", w=126)
    fy = field(cv, col_a, fy + 8, "GIVEN NAMES / PRENOMS", "MARA ELIN", w=126)
    fy = field(cv, col_a, fy + 8, "NATIONALITY", "TALVERIAN", w=126)
    fy = field(cv, col_a, fy + 8, "DATE OF BIRTH", "14 DEC 1988", w=126)
    fy = field(cv, col_a, fy + 8, "PLACE OF BIRTH", "VOSTRA", w=126)
    fy = field(cv, col_a, fy + 8, "SEX / SEXE", "F", w=126)
    fy2 = y + 152
    fy2 = field(cv, col_b, fy2, "TYPE / TYPE", "P", w=120)
    fy2 = field(cv, col_b, fy2 + 8, "CODE / CODE", "TLV", w=120)
    fy2 = field(cv, col_b, fy2 + 8, "PASSPORT NO", "TLV482913", w=120)
    fy2 = field(cv, col_b, fy2 + 8, "DATE OF ISSUE", "12 MAR 2024", w=120)
    fy2 = field(cv, col_b, fy2 + 8, "DATE OF EXPIRY", "12 MAR 2034", w=120)
    fy2 = field(cv, col_b, fy2 + 8, "AUTHORITY",
                "MINISTRY OF THE INTERIOR, VOSTRA", size=10.5, w=120)

    # signature + holder note
    sy = y + 400
    draw_text(cv, col_a, sy, "HOLDER'S SIGNATURE / SIGNATURE DU TITULAIRE",
              6.4, LABEL, spacing=0.2)
    signature(cv, col_a, sy + 6, 150)
    draw_text(cv, col_a, sy + 52, "HEIGHT 168 CM  \u2022  EYES BROWN",
              7.5, LABEL, spacing=0.4)
    draw_text(cv, col_a, sy + 68, "OCCUPATION: FERRY CAPTAIN",
              7.5, LABEL, spacing=0.4)
    for i, ln in enumerate(wrap_text(
            "This passport is the property of the Republic of Talveria "
            "and must be returned on demand.", 7.5, x + w - 24 - col_a)):
        draw_text(cv, col_a, sy + 86 + i * 11, ln, 7.5, LABEL)

    # machine-readable zone
    line1, line2 = build_mrz()
    cv.rect(x + 18, y + 566, w - 36, 62, (238, 233, 220))
    cv.rect_outline(x + 18, y + 566, w - 36, 62, 0.8, NAVY, 0.5)
    draw_text(cv, x + w / 2, y + 592, line1, 9.5, INK, align="center",
              spacing=0.3)
    draw_text(cv, x + w / 2, y + 616, line2, 9.5, INK, align="center",
              spacing=0.3)
    draw_text(cv, x + w / 2, y + 652, "32 PAGES  \u2022  No. TLV482913",
              7.0, LABEL, align="center", spacing=0.4)


def right_page(cv):
    x, y, w, h = PAGE_R
    cv.rect(x, y, w, h, PAPER_R)
    guilloche(cv, x, y, w, h, (90, 110, 140))
    # faint watermark emblem
    shield(cv, x + w / 2, y + h / 2 + 40, 190, 210,
           outline=(150, 158, 172), fill=(245, 239, 224), alpha=0.12)

    draw_text(cv, x + w / 2, y + 34, "VISAS", 15, NAVY, align="center",
              spacing=2.0)
    draw_text(cv, x + w / 2, y + 50, "VISAS  \u2022  VISA", 7.0, LABEL,
              align="center", spacing=1.0)
    cv.line(x + 24, y + 60, x + w - 24, y + 60, 1.0, NAVY, 0.7)

    # ---- visa sticker: Karthia, single entry, tourist ----
    vx, vy, vw, vh = x + 24, y + 72, 268, 158
    cv.rect(vx, vy, vw, vh, BLUE_L)
    cv.rect_outline(vx, vy, vw, vh, 1.8, NAVY, 0.95)
    cv.rect_outline(vx + 5, vy + 5, vw - 10, vh - 10, 0.8, NAVY, 0.7)
    cv.rect(vx, vy, vw, 22, NAVY)
    draw_text(cv, vx + vw / 2, vy + 16, "VISA  \u2014  KARTHIA", 11.5,
              (245, 240, 228), align="center", spacing=1.0)
    vy2 = vy + 34
    draw_text(cv, vx + 12, vy2, "TYPE: TOURIST \u2014 SINGLE ENTRY", 9.5, NAVY)
    draw_text(cv, vx + 12, vy2 + 15, "VALID: 04 NOV 2025 \u2014 03 DEC 2025", 9.5, NAVY)
    draw_text(cv, vx + 12, vy2 + 30, "STAY: 30 DAYS", 9.5, NAVY)
    draw_text(cv, vx + 12, vy2 + 45, "ISSUED: VOSTRA, 28 OCT 2025", 9.5, NAVY)
    draw_text(cv, vx + 12, vy2 + 60, "No. KRT-884120", 9.5, NAVY)
    cond = ("CONDITION: Holder must register with the Harbour "
            "Master within 72 hours of arrival. Employment "
            "prohibited.")
    for i, ln in enumerate(wrap_text(cond, 8.2, vw - 24)):
        draw_text(cv, vx + 12, vy2 + 76 + i * 11.5, ln, 8.2, NAVY_D)
    # round fee stamp beside the visa sticker
    circle_stamp(cv, x + 400, y + 152, 46, "KARTHIA", "CONSULATE",
                 ["45", "TALER"], BURG, angle=-8)

    # ---- entry / exit stamps: one consistent journey ----
    # 28 AUG 2025 out of Talveria, 29 AUG into Ostmar, 11 SEP out of
    # Ostmar, 12 SEP back into Talveria, 03 NOV out again, 04 NOV into
    # Karthia on the visa above. Nothing predates issue (12 MAR 2024).
    rect_stamp(cv, x + 24, y + 250, 218, 88,
               ["DEPARTED", "VOSTRA \u2014 TALVERIA", "28 AUG 2025"],
               BURG, angle=-6, size=11.5)
    circle_stamp(cv, x + 392, y + 294, 48, "OSTMAR", "KALV BRIDGE",
                 ["ARRIVED", "29 AUG", "2025"], BLUE, angle=5)
    rect_stamp(cv, x + 24, y + 362, 218, 88,
               ["DEPARTED", "OSTMAR \u2014 KALV BRIDGE", "11 SEP 2025"],
               BURG, angle=5, size=10.5)
    circle_stamp(cv, x + 392, y + 406, 48, "TALVERIA", "VOSTRA",
                 ["ARRIVED", "12 SEP", "2025"], BLUE, angle=-4)
    rect_stamp(cv, x + 24, y + 474, 218, 88,
               ["DEPARTED", "VOSTRA \u2014 TALVERIA", "03 NOV 2025"],
               BURG, angle=3, size=11.5)
    circle_stamp(cv, x + 392, y + 518, 48, "KARTHIA", "NORD PASS",
                 ["ARRIVED", "04 NOV", "2025"], BLUE, angle=-6)

    # harbour fee stamp + officer's handwritten note
    rect_stamp(cv, x + 288, y + 588, 180, 42,
               ["HARBOUR FEE 12 TALER", "PAID"], BURG, angle=-3, size=8.5)
    draw_text(cv, x + 30, y + 654,
              "Mind the fog on the fjord road. \u2014 E.", 12.5, HAND,
              angle=-2, shear=0.28)
    draw_text(cv, x + w - 24, y + 668, "12", 8, LABEL, align="right")


def build():
    cv = Canvas()
    # desk / cover edge around the spread
    cv.rect(0, 0, OUT_W, OUT_H, (31, 42, 58))
    cv.rect(6, 6, OUT_W - 12, OUT_H - 12, (20, 28, 40))
    left_page(cv)
    right_page(cv)
    # centre gutter shadow
    for k in range(14):
        a = 0.28 * (1 - abs(k - 6.5) / 7.5)
        cv.rect(505 + k, 14, 1, 672, (10, 14, 22), a)
    cv.line(505, 14, 505, 686, 1.0, (10, 14, 22), 0.5)
    cv.line(519, 14, 519, 686, 1.0, (10, 14, 22), 0.5)
    speckle(cv)
    return cv


def main():
    cv = build()
    data = cv.downsample_png()
    out = os.environ.get("OUTPUT_PATH", "/output/entry.png")
    try:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "wb") as f:
            f.write(data)
    except OSError:
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "output", "entry.png")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "wb") as f:
            f.write(data)
    print(f"wrote {out}: {OUT_W}x{OUT_H}, {len(data)} bytes "
          f"(limit 1048576)")


if __name__ == "__main__":
    main()

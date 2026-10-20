"""Render the project cards shown on the profile README.

Each project in projects.json becomes a dark and a light SVG card: title,
two-line summary, tech chips, a status tag, and a small animated line
drawing that stands for the project (a voice waveform, a chain of tail
vertebrae, a robot chassis, a wristband). A GitHub Action runs this on every
change to card/ and publishes the SVGs to the `card-output` branch.

    python card/build.py --out dist

Standard library only, so the workflow needs no pip install.
"""

import argparse
import json
import math
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent

THEMES = {
    "dark": {"bg": "#0d1117", "border": "#30363d", "text": "#e6edf3",
             "muted": "#8b949e", "chip": "#161b22"},
    "light": {"bg": "#ffffff", "border": "#d0d7de", "text": "#1f2328",
              "muted": "#59636e", "chip": "#f6f8fa"},
}

W, H = 420, 200
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"


def text_width(s: str, size: float) -> float:
    """Rough width of sans-serif text; good enough to size chips."""
    return len(s) * size * 0.58


# --- motifs: small line drawings in the top-right corner -------------------
# Each returns SVG drawn in a 110x80 box whose top-left is (ox, oy).

def motif_wave(c: str, ox: float, oy: float) -> str:
    """Voice waveform: bars that pulse out of phase, like Denisse talking."""
    heights = [18, 34, 54, 40, 62, 30, 46, 22, 38, 14]
    out = []
    for i, h in enumerate(heights):
        x = ox + 6 + i * 10
        cy = oy + 40
        dur = 0.9 + (i % 4) * 0.17
        out.append(
            f'<rect x="{x}" y="{cy - h / 2}" width="5" height="{h}" rx="2.5" fill="{c}" '
            f'style="transform-box:fill-box;transform-origin:center;'
            f'animation:pulse {dur:.2f}s ease-in-out {i * 0.08:.2f}s infinite alternate"/>')
    return "".join(out)


def motif_tail(c: str, ox: float, oy: float) -> str:
    """Square vertebrae shrinking along a seahorse-style spiral, swaying
    slowly about the base segment."""
    cx, cy = ox + 62, oy + 36
    n = 12
    pts = []
    for i in range(n):
        t = i / (n - 1)
        th = math.pi * 0.95 + t * math.pi * 1.55      # sweep into a curl
        r = 36 * (1 - 0.62 * t)
        pts.append((cx + r * math.cos(th), cy - r * math.sin(th), 13 - 7 * t, th))
    bx, by = pts[0][0], pts[0][1]
    out = [f'<g style="transform-origin:{bx:.0f}px {by:.0f}px;'
           f'animation:sway 3.2s ease-in-out infinite alternate">']
    for x, y, s, th in pts:
        rot = -math.degrees(th)
        out.append(f'<rect x="{x - s / 2:.1f}" y="{y - s / 2:.1f}" width="{s:.1f}" height="{s:.1f}" '
                   f'rx="2" fill="none" stroke="{c}" stroke-width="2" '
                   f'transform="rotate({rot:.0f} {x:.1f} {y:.1f})"/>')
    out.append("</g>")
    return "".join(out)


def motif_robot(c: str, ox: float, oy: float) -> str:
    """Top-down chassis with four wheels and a sweeping heading arc (IMU)."""
    cx, cy = ox + 55, oy + 40
    out = [f'<rect x="{cx - 26}" y="{cy - 30}" width="52" height="60" rx="8" fill="none" stroke="{c}" stroke-width="2.2"/>',
           f'<rect x="{cx - 10}" y="{cy - 12}" width="20" height="16" rx="2" fill="none" stroke="{c}" stroke-width="1.6"/>']
    for wx in (cx - 36, cx + 26):
        for wy in (cy - 26, cy + 8):
            out.append(f'<rect x="{wx}" y="{wy}" width="10" height="18" rx="3" fill="{c}"/>')
    out.append(f'<g style="transform-origin:{cx}px {cy}px;animation:spin 4s linear infinite">'
               f'<path d="M{cx} {cy - 40} A40 40 0 0 1 {cx + 34.6} {cy - 20}" fill="none" stroke="{c}" '
               f'stroke-width="2" stroke-linecap="round" stroke-dasharray="2 5"/></g>')
    return "".join(out)


def motif_band(c: str, ox: float, oy: float) -> str:
    """Wristband with a sensor module and motion arcs radiating from it."""
    cx, cy = ox + 50, oy + 44
    out = [f'<ellipse cx="{cx}" cy="{cy}" rx="34" ry="22" fill="none" stroke="{c}" stroke-width="6" stroke-opacity=".35"/>',
           f'<rect x="{cx - 13}" y="{cy - 33}" width="26" height="18" rx="4" fill="{c}"/>']
    for i, r in enumerate((14, 22, 30)):
        out.append(f'<path d="M{cx + 18} {cy - 24 - r * 0.6} A{r} {r} 0 0 1 {cx + 18 + r * 0.6} {cy - 24}" '
                   f'fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" '
                   f'style="opacity:0;animation:ping 2.4s ease-out {i * 0.35:.2f}s infinite"/>')
    return "".join(out)


MOTIFS = {"wave": motif_wave, "tail": motif_tail, "robot": motif_robot, "band": motif_band}


def render(p: dict, theme: str) -> str:
    t = THEMES[theme]
    c = p["colour"]
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
           f'role="img" aria-label="{escape(p["name"])}: {escape(" ".join(p["lines"]))}">']
    out.append("""<style>
  @keyframes pulse { from { transform: scaleY(.35); } to { transform: scaleY(1); } }
  @keyframes sway  { from { transform: rotate(-4deg); } to { transform: rotate(5deg); } }
  @keyframes spin  { to { transform: rotate(360deg); } }
  @keyframes ping  { 0% { opacity: 0; } 30% { opacity: 1; } 100% { opacity: 0; } }
  @keyframes rise  { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: none; } }
  .body { animation: rise .6s ease-out both; }
  @media (prefers-reduced-motion: reduce) { * { animation: none !important; } }
</style>""")
    out.append(f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="10" fill="{t["bg"]}" stroke="{t["border"]}"/>')
    out.append(f'<rect x=".5" y="18" width="3" height="{H - 36}" rx="1.5" fill="{c}"/>')

    out.append(f'<g opacity=".9">{MOTIFS[p["motif"]](c, W - 132, 18)}</g>')

    out.append('<g class="body">')
    out.append(f'<text x="26" y="50" font-family="{FONT}" font-size="21" font-weight="600" '
               f'fill="{t["text"]}">{escape(p["name"])}</text>')
    for i, line in enumerate(p["lines"][:2]):
        out.append(f'<text x="26" y="{80 + i * 20}" font-family="{FONT}" font-size="13" '
                   f'fill="{t["muted"]}">{escape(line)}</text>')

    # Tech chips, bottom left
    x = 26
    for tag in p["tags"]:
        w = text_width(tag, 11.5) + 18
        out.append(f'<rect x="{x}" y="148" width="{w:.0f}" height="24" rx="12" fill="{t["chip"]}" stroke="{t["border"]}"/>'
                   f'<text x="{x + w / 2:.0f}" y="164" text-anchor="middle" font-family="{FONT}" '
                   f'font-size="11.5" fill="{t["text"]}">{escape(tag)}</text>')
        x += w + 8

    # Status, bottom right
    s = p["status"]
    sw = text_width(s, 11.5) + 30
    sx = W - 24 - sw
    out.append(f'<rect x="{sx:.0f}" y="148" width="{sw:.0f}" height="24" rx="12" fill="{c}" fill-opacity=".14" '
               f'stroke="{c}" stroke-opacity=".55"/>'
               f'<circle cx="{sx + 13:.0f}" cy="160" r="3.5" fill="{c}"/>'
               f'<text x="{sx + 22:.0f}" y="164" font-family="{FONT}" font-size="11.5" font-weight="600" '
               f'fill="{c}">{escape(s)}</text>')
    out.append("</g></svg>")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="dist")
    args = ap.parse_args()

    projects = json.loads((HERE / "projects.json").read_text(encoding="utf-8"))["projects"]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for p in projects:
        if p["motif"] not in MOTIFS:
            raise SystemExit(f"{p['id']}: unknown motif '{p['motif']}' (choose from {', '.join(MOTIFS)})")
        for line in p["lines"]:
            if text_width(line, 13) * 0.9 > W - 160:
                print(f"warning: {p['id']}: '{line}' may run under the drawing")
        for theme in THEMES:
            (out / f"{p['id']}-{theme}.svg").write_text(render(p, theme), encoding="utf-8")
    print(f"wrote {len(projects) * len(THEMES)} cards to {out}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

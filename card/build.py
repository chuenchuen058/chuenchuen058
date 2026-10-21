"""Render the project cards shown on the profile README.

Each project in projects.json becomes a dark and a light SVG card: title,
two-line summary, tech chips, a status tag, and an animated drawing of the
project working -- Denisse's breathing orb and targeting ring, a wave
running down the tail's vertebrae, the robot lapping a track, BlueBand
streaming x/y/z accelerometer traces. Every card also has a dot grid, a light sweep and a
highlight running round its border. A GitHub Action runs this on every
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


# --- motifs: animated drawings in the top-right of each card --------------
# Each draws inside a 125x112 box whose top-left is (ox, oy). `t` is the
# theme palette, so labels and frames follow light/dark mode.

MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,monospace"


def motif_wave(c: str, ox: float, oy: float, t: dict) -> str:
    """Denisse: her floating desktop orb (floating_orb.py) -- a glossy purple
    sphere breathing once every 1.2s inside a soft glow, with the JARVIS-style
    targeting ring turning once every 6s -- above a terminal line cycling
    through the real pipeline: listen, route tools, reply."""
    cx, cy, r = ox + 62, oy + 40, 22
    bright, accent, deep, ring2 = "#c9a3ff", "#a855f7", "#4c1d95", "#7c3aed"
    out = [f'<defs><radialGradient id="orbcore"><stop offset="0" stop-color="{bright}"/>'
           f'<stop offset="1" stop-color="{deep}"/></radialGradient>'
           f'<filter id="orbglow" x="-1" y="-1" width="3" height="3"><feGaussianBlur stdDeviation="5"/></filter>'
           f'<filter id="orbshine"><feGaussianBlur stdDeviation="2"/></filter>'
           f'<clipPath id="orbclip"><circle cx="{cx}" cy="{cy}" r="{r}"/></clipPath></defs>']
    # class="orb": the breath keeps running under prefers-reduced-motion (see STYLE)
    breathe = 'class="orb" style="transform-box:view-box;transform-origin:{0}px {1}px;animation:breathe .6s ease-in-out infinite alternate"'.format(cx, cy)
    # pulse waves: a halo leaves the orb on every in-breath and fades out
    for i in range(2):
        out.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{accent}" stroke-width="2" '
                   f'style="transform-box:view-box;transform-origin:{cx}px {cy}px;opacity:0;'
                   f'animation:halo 2.4s ease-out {i * 1.2:.1f}s infinite"/>')
    # glow: brighter and bigger on the in-breath, like the orb's 150->229 alpha swing
    out.append(f'<g {breathe}><circle cx="{cx}" cy="{cy}" r="{r * 1.2:.1f}" fill="{accent}" filter="url(#orbglow)" class="orb" '
               f'style="animation:glow .6s ease-in-out infinite alternate"/></g>')
    out.append(f'<g {breathe}><circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#orbcore)"/>'
               f'<circle cx="{cx - r * 0.62:.1f}" cy="{cy - r * 0.68:.1f}" r="{r * 0.42:.1f}" fill="#fff" fill-opacity=".51" '
               f'filter="url(#orbshine)" clip-path="url(#orbclip)"/></g>')
    rr = r + 8
    spin = f'class="orb" style="transform-box:view-box;transform-origin:{cx}px {cy}px;animation:spin 6s linear infinite"'
    out.append(f'<g {spin}>'
               f'<circle cx="{cx}" cy="{cy}" r="{rr}" fill="none" stroke="{bright}" stroke-width="3" stroke-linecap="round" '
               f'pathLength="360" stroke-dasharray="150 210"/>'
               f'<circle cx="{cx}" cy="{cy}" r="{rr}" fill="none" stroke="{ring2}" stroke-width="3" stroke-linecap="round" '
               f'pathLength="360" stroke-dasharray="60 300" stroke-dashoffset="-180"/></g>')
    # terminal line
    out.append(f'<rect x="{ox + 2}" y="{oy + 80}" width="121" height="24" rx="6" fill="{t["chip"]}" stroke="{t["border"]}"/>')
    for i, msg in enumerate(("listening\u2026", "route 33\u21926 tools", "reply in 1.0s")):
        out.append(f'<g style="opacity:0;animation:show 6s linear {i * 2}s infinite">'
                   f'<text x="{ox + 11}" y="{oy + 96}" font-family="{MONO}" font-size="10" fill="{c}">\u203a</text>'
                   f'<text x="{ox + 21}" y="{oy + 96}" font-family="{MONO}" font-size="10" fill="{t["text"]}">{escape(msg)}</text></g>')
    out.append(f'<rect x="{ox + 113}" y="{oy + 87}" width="5" height="10" fill="{c}" style="animation:blink 1s steps(1) infinite"/>')
    return "".join(out)


def motif_tail(c: str, ox: float, oy: float, t: dict) -> str:
    """Robotic tail: square vertebrae on a seahorse curl with a wave running
    down them, a tendon carrying tension pulses, and a servo at the base."""
    cx, cy = ox + 66, oy + 50
    n = 12
    pts = []
    for i in range(n):
        u = i / (n - 1)
        th = math.pi * 0.95 + u * math.pi * 1.55
        r = 42 * (1 - 0.62 * u)
        pts.append((cx + r * math.cos(th), cy - r * math.sin(th), 13 - 7 * u, th))
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y, _, _ in pts)
    out = [f'<polyline points="{line}" fill="none" stroke="{c}" stroke-opacity=".3" stroke-width="1.2"/>',
           f'<polyline points="{line}" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" '
           f'pathLength="100" stroke-dasharray="6 24" style="animation:flow 1.4s linear infinite"/>']
    for i, (x, y, s, th) in enumerate(pts):
        out.append(f'<g style="transform-box:fill-box;transform-origin:center;'
                   f'animation:wiggle 1.6s ease-in-out {i * 0.13:.2f}s infinite alternate">'
                   f'<rect x="{x - s / 2:.1f}" y="{y - s / 2:.1f}" width="{s:.1f}" height="{s:.1f}" rx="2" '
                   f'fill="{t["bg"]}" stroke="{c}" stroke-width="2" transform="rotate({-math.degrees(th):.0f} {x:.1f} {y:.1f})"/></g>')
    bx, by = pts[0][0], pts[0][1] + 20
    out.append(f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="8" fill="{t["chip"]}" stroke="{c}" stroke-width="1.8"/>'
               f'<line x1="{bx:.1f}" y1="{by:.1f}" x2="{bx:.1f}" y2="{by - 12:.1f}" stroke="{c}" stroke-width="2.5" '
               f'stroke-linecap="round" style="transform-origin:{bx:.1f}px {by:.1f}px;animation:horn 1.6s ease-in-out infinite alternate"/>'
               f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="2" fill="{c}"/>')
    return "".join(out)


def motif_robot(c: str, ox: float, oy: float, t: dict) -> str:
    """UnibotsMarkII: the robot drives laps of a track, turning to follow it,
    with a sensor cone sweeping ahead and waypoints lighting up."""
    x0, y0, w, h, r = ox + 14, oy + 10, 92, 92, 26
    track = (f"M{x0 + r} {y0} H{x0 + w - r} A{r} {r} 0 0 1 {x0 + w} {y0 + r} V{y0 + h - r} "
             f"A{r} {r} 0 0 1 {x0 + w - r} {y0 + h} H{x0 + r} A{r} {r} 0 0 1 {x0} {y0 + h - r} "
             f"V{y0 + r} A{r} {r} 0 0 1 {x0 + r} {y0} Z")
    out = [f'<path id="track" d="{track}" fill="none" stroke="{t["border"]}" stroke-width="10" stroke-linejoin="round"/>',
           f'<path d="{track}" fill="none" stroke="{c}" stroke-opacity=".5" stroke-width="1" stroke-dasharray="3 5"/>']
    for i, (wx, wy) in enumerate(((x0 + w / 2, y0), (x0 + w, y0 + h / 2), (x0 + w / 2, y0 + h), (x0, y0 + h / 2))):
        out.append(f'<circle cx="{wx}" cy="{wy}" r="3" fill="{c}" style="opacity:.25;animation:way 6s linear {i * 1.5:.1f}s infinite"/>')
    out.append(f'<g style="transform-box:fill-box;transform-origin:center;animation:pulse 1.2s ease-in-out infinite alternate">'
               f'<rect x="{ox + 43}" y="{oy + 46}" width="34" height="20" rx="3" fill="none" stroke="{c}" stroke-opacity=".5"/></g>'
               f'<text x="{ox + 60}" y="{oy + 59}" text-anchor="middle" font-family="{MONO}" font-size="8" fill="{t["muted"]}">IMU</text>')
    robot = (f'<path d="M10 0 L28 -11 L28 11 Z" fill="{c}" style="opacity:.18;animation:cone 1s ease-in-out infinite alternate"/>'
             f'<rect x="-11" y="-8" width="22" height="16" rx="4" fill="{t["bg"]}" stroke="{c}" stroke-width="2"/>'
             f'<rect x="-9" y="-12" width="7" height="4" rx="1.5" fill="{c}"/><rect x="2" y="-12" width="7" height="4" rx="1.5" fill="{c}"/>'
             f'<rect x="-9" y="8" width="7" height="4" rx="1.5" fill="{c}"/><rect x="2" y="8" width="7" height="4" rx="1.5" fill="{c}"/>'
             f'<circle cx="6" cy="0" r="2" fill="{c}"/>')
    out.append(f'<g>{robot}<animateMotion dur="6s" repeatCount="indefinite" rotate="auto"><mpath href="#track"/></animateMotion></g>')
    return "".join(out)


def motif_band(c: str, ox: float, oy: float, t: dict) -> str:
    """BlueBand: live x/y/z accelerometer traces scrolling across a plot,
    fed by the sensor module on the band, whose LED blinks as it samples."""
    px, py, pw, ph = ox + 4, oy + 2, 117, 50
    out = [f'<clipPath id="plot"><rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="5"/></clipPath>',
           f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="5" fill="{t["chip"]}" stroke="{t["border"]}"/>',
           f'<line x1="{px}" y1="{py + ph / 2}" x2="{px + pw}" y2="{py + ph / 2}" stroke="{t["border"]}" stroke-dasharray="2 3"/>']
    period = pw
    out.append(f'<g clip-path="url(#plot)"><g style="animation:scroll 2.6s linear infinite">')
    for k, (amp, cycles, phase, colour, op) in enumerate(((13, 2, 0.0, c, 1), (8, 3, 1.3, c, .55), (5, 5, 2.4, t["muted"], .9))):
        pts = []
        for i in range(0, 2 * period + 1, 2):
            v = math.sin(2 * math.pi * cycles * i / period + phase) + 0.3 * math.sin(2 * math.pi * cycles * 2 * i / period)
            pts.append(f"{px + i:.0f},{py + ph / 2 - amp * v:.1f}")
        out.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{colour}" stroke-opacity="{op}" stroke-width="1.6"/>')
    out.append("</g></g>")
    for k, (lab, colour) in enumerate((("x", c), ("y", c), ("z", t["muted"]))):
        out.append(f'<text x="{px + 6 + k * 11}" y="{py + 11}" font-family="{MONO}" font-size="8" fill="{colour}">{lab}</text>')
    bx, by = ox + 62, oy + 92
    out.append(f'<line x1="{bx}" y1="{by - 22}" x2="{bx}" y2="{py + ph}" stroke="{c}" stroke-width="1.5" '
               f'stroke-dasharray="3 3" style="animation:flow 0.8s linear infinite"/>')
    out.append(f'<ellipse cx="{bx}" cy="{by}" rx="44" ry="15" fill="none" stroke="{c}" stroke-width="6" stroke-opacity=".3"/>'
               f'<rect x="{bx - 15}" y="{by - 26}" width="30" height="18" rx="4" fill="{t["chip"]}" stroke="{c}" stroke-width="1.8"/>'
               f'<circle cx="{bx + 7}" cy="{by - 17}" r="2.6" fill="{c}" style="animation:blink .5s steps(1) infinite"/>'
               f'<rect x="{bx - 10}" y="{by - 20}" width="10" height="6" rx="1" fill="none" stroke="{c}" stroke-width="1"/>')
    return "".join(out)


MOTIFS = {"wave": motif_wave, "tail": motif_tail, "robot": motif_robot, "band": motif_band}

STYLE = """<style>
  @keyframes pulse  { from { transform: scaleY(.35); } to { transform: scaleY(1); } }
  @keyframes breathe { from { transform: scale(.74); } to { transform: scale(1.06); } }
  @keyframes glow   { from { opacity: .35; } to { opacity: 1; } }
  @keyframes halo   { 0% { transform: scale(.9); opacity: .8; } 100% { transform: scale(1.9); opacity: 0; } }
  @keyframes spin   { to { transform: rotate(360deg); } }
  @keyframes show   { 0% { opacity: 0; } 4% { opacity: 1; } 30% { opacity: 1; } 34% { opacity: 0; } 100% { opacity: 0; } }
  @keyframes blink  { 50% { opacity: 0; } }
  @keyframes wiggle { from { transform: rotate(-9deg) translateY(-1px); } to { transform: rotate(9deg) translateY(1px); } }
  @keyframes flow   { to { stroke-dashoffset: -30; } }
  @keyframes horn   { from { transform: rotate(-55deg); } to { transform: rotate(55deg); } }
  @keyframes way    { 0%, 100% { opacity: .25; } 8% { opacity: 1; } 25% { opacity: .25; } }
  @keyframes cone   { from { opacity: .08; } to { opacity: .3; } }
  @keyframes scroll { to { transform: translateX(-117px); } }
  @keyframes sweep  { from { transform: translateX(-160px); } to { transform: translateX(580px); } }
  @keyframes run    { to { stroke-dashoffset: -1000; } }
  @keyframes rise   { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: none; } }
  .body { animation: rise .6s ease-out both; }
  /* Reduced motion stops everything except Denisse's orb (.orb): its breath and its targeting
     ring turning once every 6s, both in place with no travel. Windows reports reduce whenever "Animation effects" is off, and
     with a plain * the orb never moved at all on Chuen's own PC (2026-10-21). */
  @media (prefers-reduced-motion: reduce) { *:not(.orb) { animation: none !important; } }
</style>"""


def render(p: dict, theme: str) -> str:
    t = THEMES[theme]
    c = p["colour"]
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
           f'role="img" aria-label="{escape(p["name"])}: {escape(" ".join(p["lines"]))}">', STYLE]
    out.append(f'<defs><clipPath id="card"><rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="10"/></clipPath>'
               f'<pattern id="dots" width="14" height="14" patternUnits="userSpaceOnUse">'
               f'<circle cx="1.5" cy="1.5" r="1" fill="{t["border"]}"/></pattern>'
               f'<linearGradient id="scan" x1="0" x2="1"><stop offset="0" stop-color="{c}" stop-opacity="0"/>'
               f'<stop offset=".5" stop-color="{c}" stop-opacity=".09"/><stop offset="1" stop-color="{c}" stop-opacity="0"/>'
               f'</linearGradient></defs>')
    out.append(f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="10" fill="{t["bg"]}"/>')
    out.append(f'<g clip-path="url(#card)">'
               f'<rect width="{W}" height="{H}" fill="url(#dots)" opacity=".55"/>'
               f'<rect width="140" height="{H}" fill="url(#scan)" style="animation:sweep 7s linear infinite"/></g>')
    out.append(f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="10" fill="none" stroke="{t["border"]}"/>')
    out.append(f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="10" fill="none" stroke="{c}" stroke-width="1.5" '
               f'pathLength="1000" stroke-dasharray="80 920" style="animation:run 8s linear infinite"/>')
    out.append(f'<rect x=".5" y="18" width="3" height="{H - 36}" rx="1.5" fill="{c}"/>')

    out.append(MOTIFS[p["motif"]](c, W - 140, 14, t))

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
               f'<circle cx="{sx + 13:.0f}" cy="160" r="3.5" fill="{c}" style="animation:blink 1.6s steps(1) infinite"/>'
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
            if len(line) > 38:
                print(f"warning: {p['id']}: '{line}' may run under the drawing")
        for theme in THEMES:
            (out / f"{p['id']}-{theme}.svg").write_text(render(p, theme), encoding="utf-8")
    print(f"wrote {len(projects) * len(THEMES)} cards to {out}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

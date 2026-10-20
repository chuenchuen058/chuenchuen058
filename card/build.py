"""Render the profile highlights card.

Pulls live numbers from the GitHub GraphQL API (contributions in the last
year, commits, public repos, language mix by bytes of code), combines them
with the hand-written list in achievements.json, and writes a dark and a
light SVG. A nightly GitHub Action runs this, so the numbers stay current
without anyone touching the README.

    python card/build.py --user chuenchuen058 --out dist
    python card/build.py --offline --out dist     # sample stats, no network

Standard library only, so the workflow needs no pip install.
"""

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent

THEMES = {
    "dark": {"bg": "#0d1117", "border": "#30363d", "text": "#e6edf3",
             "muted": "#8b949e", "line": "#30363d", "track": "#21262d"},
    "light": {"bg": "#ffffff", "border": "#d0d7de", "text": "#1f2328",
              "muted": "#59636e", "line": "#d0d7de", "track": "#eaeef2"},
}

# Tag colours: GitHub's own label palette, readable on both themes.
TAG_COLOURS = {
    "Internship": "#1f6feb", "Award": "#bf8700", "Project": "#8250df",
    "Competition": "#cf222e", "Hackathon": "#1a7f37", "Leadership": "#0969da",
}
DEFAULT_TAG = "#6e7781"

FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,monospace"

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      totalCommitContributions
      contributionCalendar { totalContributions }
    }
    repositories(ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false, first: 100) {
      totalCount
      nodes {
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""

SAMPLE_STATS = {
    "contributions": 74, "commits": 37, "repos": 2,
    "languages": [("Python", "#3572A5", 812000), ("PowerShell", "#012456", 9000),
                  ("C++", "#f34b7d", 6000)],
}


def fetch_stats(user: str, token: str) -> dict:
    body = json.dumps({"query": QUERY, "variables": {"login": user}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql", data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "profile-card"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    if data.get("errors"):
        raise RuntimeError(data["errors"][0].get("message", "GraphQL error"))
    u = data["data"]["user"]
    cc = u["contributionsCollection"]

    sizes: dict = {}
    for repo in u["repositories"]["nodes"]:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            colour = edge["node"]["color"] or DEFAULT_TAG
            prev = sizes.get(name, (colour, 0))
            sizes[name] = (colour, prev[1] + edge["size"])
    languages = sorted(((n, c, s) for n, (c, s) in sizes.items()), key=lambda t: -t[2])

    return {
        "contributions": cc["contributionCalendar"]["totalContributions"],
        "commits": cc["totalCommitContributions"],
        "repos": u["repositories"]["totalCount"],
        "languages": languages,
    }


def top_languages(langs: list, keep: int = 4) -> list:
    """Top `keep` languages plus an 'Other' bucket, as (name, colour, share)."""
    total = sum(s for _, _, s in langs) or 1
    head = [(n, c, s / total) for n, c, s in langs[:keep]]
    rest = sum(s for _, _, s in langs[keep:]) / total
    if rest > 0.005:
        head.append(("Other", DEFAULT_TAG, rest))
    return head


def text_width(s: str, size: float) -> float:
    """Rough width of sans-serif text; good enough to size pills."""
    return len(s) * size * 0.56


def render(stats: dict, items: list, title: str, theme: str, updated: str) -> str:
    t = THEMES[theme]
    W, pad = 840, 28
    row_h = 46
    stats_y = 86
    bar_y = stats_y + 74
    list_y = bar_y + 58
    H = list_y + row_h * len(items) + 18

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" role="img" aria-label="{escape(title)}">']
    out.append(f"""<style>
  .fade {{ opacity: 0; animation: up .6s ease-out forwards; }}
  .grow {{ transform-box: fill-box; transform-origin: left; transform: scaleX(0);
          animation: grow 1.1s cubic-bezier(.2,.7,.2,1) .3s forwards; }}
  @keyframes up {{ from {{ opacity: 0; transform: translateY(6px); }} to {{ opacity: 1; transform: none; }} }}
  @keyframes grow {{ to {{ transform: scaleX(1); }} }}
  @media (prefers-reduced-motion: reduce) {{
    .fade, .grow {{ animation: none; opacity: 1; transform: none; }}
  }}
</style>""")
    out.append(f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="10" '
               f'fill="{t["bg"]}" stroke="{t["border"]}"/>')

    # Title row
    out.append(f'<text x="{pad}" y="44" font-family="{FONT}" font-size="20" '
               f'font-weight="600" fill="{t["text"]}">{escape(title)}</text>')
    out.append(f'<text x="{W-pad}" y="44" text-anchor="end" font-family="{MONO}" '
               f'font-size="11" fill="{t["muted"]}">updated {escape(updated)}</text>')
    out.append(f'<line x1="{pad}" y1="62" x2="{W-pad}" y2="62" stroke="{t["line"]}"/>')

    # Stats strip
    blocks = [(f'{stats["contributions"]:,}', "contributions, last year"),
              (f'{stats["commits"]:,}', "commits, last year"),
              (f'{stats["repos"]:,}', "public repositories")]
    col = (W - 2 * pad) / len(blocks)
    for i, (num, label) in enumerate(blocks):
        x = pad + i * col
        out.append(f'<g class="fade" style="animation-delay:{0.1 * i:.1f}s">'
                   f'<text x="{x}" y="{stats_y + 24}" font-family="{FONT}" font-size="26" '
                   f'font-weight="600" fill="{t["text"]}">{num}</text>'
                   f'<text x="{x}" y="{stats_y + 44}" font-family="{FONT}" font-size="12" '
                   f'fill="{t["muted"]}">{escape(label)}</text></g>')

    # Language bar
    langs = top_languages(stats["languages"])
    bw = W - 2 * pad
    out.append(f'<rect x="{pad}" y="{bar_y}" width="{bw}" height="8" rx="4" fill="{t["track"]}"/>')
    out.append(f'<clipPath id="barclip"><rect x="{pad}" y="{bar_y}" width="{bw}" height="8" rx="4"/></clipPath>')
    out.append(f'<g clip-path="url(#barclip)"><g class="grow">')
    x = pad
    for name, colour, share in langs:
        w = bw * share
        out.append(f'<rect x="{x:.1f}" y="{bar_y}" width="{w:.1f}" height="8" fill="{colour}"/>')
        x += w
    out.append("</g></g>")
    lx = pad
    for name, colour, share in langs:
        label = f"{name} {share * 100:.1f}%"
        out.append(f'<circle cx="{lx + 4}" cy="{bar_y + 26}" r="4" fill="{colour}"/>'
                   f'<text x="{lx + 13}" y="{bar_y + 30}" font-family="{FONT}" font-size="12" '
                   f'fill="{t["muted"]}">{escape(label)}</text>')
        lx += 13 + text_width(label, 12) + 22

    # Timeline
    rail_x = pad + 6
    first = list_y + 14
    last = list_y + row_h * (len(items) - 1) + 14
    out.append(f'<line x1="{rail_x}" y1="{first}" x2="{rail_x}" y2="{last}" stroke="{t["line"]}" stroke-width="2"/>')
    # Every title starts in the same column, past the widest tag pill.
    pill_col = max(text_width(it.get("tag", ""), 11) + 16 for it in items)
    for i, item in enumerate(items):
        y = list_y + i * row_h
        colour = TAG_COLOURS.get(item.get("tag", ""), DEFAULT_TAG)
        delay = 0.5 + 0.12 * i
        tag = item.get("tag", "")
        tw = text_width(tag, 11) + 16
        tx = rail_x + 22
        title_x = tx + pill_col + 12
        out.append(f'<g class="fade" style="animation-delay:{delay:.2f}s">')
        out.append(f'<circle cx="{rail_x}" cy="{y + 14}" r="5" fill="{t["bg"]}" stroke="{colour}" stroke-width="2.5"/>')
        out.append(f'<rect x="{tx}" y="{y + 4}" width="{tw:.0f}" height="20" rx="10" '
                   f'fill="{colour}" fill-opacity=".15" stroke="{colour}" stroke-opacity=".5"/>')
        out.append(f'<text x="{tx + tw / 2:.0f}" y="{y + 18}" text-anchor="middle" font-family="{FONT}" '
                   f'font-size="11" font-weight="600" fill="{colour}">{escape(tag)}</text>')
        out.append(f'<text x="{title_x:.0f}" y="{y + 19}" font-family="{FONT}" font-size="14" '
                   f'font-weight="600" fill="{t["text"]}">{escape(item["title"])}</text>')
        if item.get("detail"):
            out.append(f'<text x="{title_x:.0f}" y="{y + 37}" font-family="{FONT}" font-size="12" '
                       f'fill="{t["muted"]}">{escape(item["detail"])}</text>')
        out.append("</g>")

    out.append("</svg>")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default=os.environ.get("GITHUB_REPOSITORY_OWNER", ""))
    ap.add_argument("--out", default="dist")
    ap.add_argument("--offline", action="store_true", help="use sample stats, no API call")
    args = ap.parse_args()

    data = json.loads((HERE / "achievements.json").read_text(encoding="utf-8"))
    items = data["items"]
    for it in items:  # long lines don't wrap in SVG; catch them before they overflow
        if len(it.get("detail", "")) > 80 or len(it["title"]) > 60:
            print(f"warning: '{it['title']}' is long and may overflow the card", file=sys.stderr)

    if args.offline:
        stats = SAMPLE_STATS
    else:
        token = os.environ.get("GITHUB_TOKEN")
        if not token or not args.user:
            print("need GITHUB_TOKEN and --user (or use --offline)", file=sys.stderr)
            return 2
        stats = fetch_stats(args.user, token)

    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for theme in THEMES:
        svg = render(stats, items, data.get("title", "Highlights"), theme, updated)
        (out / f"highlights-{theme}.svg").write_text(svg, encoding="utf-8")
    print(f"wrote {out}/highlights-dark.svg and highlights-light.svg "
          f"({stats['contributions']} contributions, {len(items)} highlights)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

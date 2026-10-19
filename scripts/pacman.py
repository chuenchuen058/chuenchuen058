"""Pac-Man eating the contribution graph: no ghosts, no walls.

Fetches the contribution calendar and writes a light and a dark animated SVG.
Usage: GITHUB_TOKEN=... python scripts/pacman.py <user> <out_dir>
"""
import json
import math
import os
import sys
import urllib.request

CELL, GAP = 10, 3
STEP = CELL + GAP
MARGIN = 16
SECONDS_PER_CELL = 0.09
END_PAUSE = 2.0

THEMES = {
    "": ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"],
    "-dark": ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"],
}
LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2,
          "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}

QUERY = """query($login: String!) { user(login: $login) { contributionsCollection {
  contributionCalendar { weeks { contributionDays { weekday contributionLevel } } } } } }"""


def fetch(user, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": user}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        data = json.load(r)
    if "errors" in data:
        sys.exit(f"GraphQL error: {data['errors']}")
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return {(x, d["weekday"]): LEVELS[d["contributionLevel"]]
            for x, w in enumerate(weeks) for d in w["contributionDays"]}


def plan_route(cells):
    """Eat the lightest squares first and the darkest last, like Platane/snk.

    Each step walks (breadth-first, one cell per step) to the nearest uneaten
    square of the current level, going around darker squares that aren't due
    yet. Pac-Man may walk one cell outside the grid, as the snake does.
    """
    weeks = max(x for x, _ in cells) + 1
    left = {c: lvl for c, lvl in cells.items() if lvl > 0}
    pos = (-1, -1)
    route = [pos]

    def walk(targets, max_lvl):
        prev, frontier = {pos: None}, [pos]
        while frontier:
            nxt = []
            for c in frontier:
                if c in targets:
                    path = []
                    while c != pos:
                        path.append(c)
                        c = prev[c]
                    return path[::-1]
                for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    n = (c[0] + d[0], c[1] + d[1])
                    if (-1 <= n[0] <= weeks and -1 <= n[1] <= 7 and n not in prev
                            and left.get(n, 0) <= max_lvl):
                        prev[n] = c
                        nxt.append(n)
            frontier = nxt
        return None

    for lvl in range(1, 5):
        while targets := {c for c, v in left.items() if v == lvl}:
            path = walk(targets, lvl) or walk(targets, 4)
            for c in path:
                left.pop(c, None)
            route += path
            pos = route[-1]
    return route


def centre(c):
    return MARGIN + c[0] * STEP + CELL / 2, MARGIN + c[1] * STEP + CELL / 2


def mouth(deg, r=6.5):
    a = math.radians(deg)
    x, y = r * math.cos(a), r * math.sin(a)
    return f"M0,0 L{x:.2f},{-y:.2f} A{r},{r} 0 1 0 {x:.2f},{y:.2f} Z"


def render(cells, route, palette):
    weeks = max(x for x, _ in cells) + 1
    width, height = 2 * MARGIN + weeks * STEP - GAP, 2 * MARGIN + 7 * STEP - GAP
    moving = (len(route) - 1) * SECONDS_PER_CELL
    total = moving + END_PAUSE
    eaten_at = {}
    for i, c in enumerate(route):
        eaten_at.setdefault(c, i * SECONDS_PER_CELL / total)

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
           f'viewBox="0 0 {width} {height}">']
    for (x, y), lvl in sorted(cells.items()):
        px, py = MARGIN + x * STEP, MARGIN + y * STEP
        rect = f'<rect x="{px}" y="{py}" width="{CELL}" height="{CELL}" rx="2" fill="{palette[lvl]}"'
        if lvl and (x, y) in eaten_at:
            out.append(f'{rect}><animate attributeName="fill" calcMode="discrete" '
                       f'values="{palette[lvl]};{palette[0]}" keyTimes="0;{eaten_at[(x, y)]:.5f}" '
                       f'dur="{total:.2f}s" repeatCount="indefinite"/></rect>')
        else:
            out.append(rect + "/>")

    points = [centre(c) for c in route]
    path = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in points)
    if len(points) == 1:
        path += f" L{points[0][0]:.1f},{points[0][1]:.1f}"
    out.append(
        f'<g><path fill="#ffd60a" d="{mouth(40)}">'
        f'<animate attributeName="d" values="{mouth(40)};{mouth(2)};{mouth(40)}" '
        f'dur="0.3s" repeatCount="indefinite"/></path>'
        f'<animateMotion path="{path}" rotate="auto" calcMode="linear" keyPoints="0;1;1" '
        f'keyTimes="0;{moving / total:.5f};1" dur="{total:.2f}s" repeatCount="indefinite"/></g>'
    )
    out.append("</svg>")
    return "\n".join(out)


def main():
    user, out_dir = sys.argv[1], sys.argv[2]
    cells = fetch(user, os.environ["GITHUB_TOKEN"])
    route = plan_route(cells)
    os.makedirs(out_dir, exist_ok=True)
    for suffix, palette in THEMES.items():
        with open(os.path.join(out_dir, f"pacman-contribution-graph{suffix}.svg"), "w") as f:
            f.write(render(cells, route, palette))
    print(f"{sum(1 for v in cells.values() if v)} cells to eat, {len(route) - 1} steps")


if __name__ == "__main__":
    main()

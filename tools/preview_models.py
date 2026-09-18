#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QA-рендер сконвертированных моделей: изометрия с цветами из текстур.
Usage: python3 tools/preview_models.py   (reads the built bundle jar)
Output: preview/*.png
"""
import io
import json
import math
import os
import zipfile

from PIL import Image, ImageDraw

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JAR = os.path.join(REPO, "ArcanaForge-1.20.1-v1.0.0.jar")
OUT = os.path.join(REPO, "preview")

MODELS = ["magic_wand", "ghost_knight_hat", "ancient_golem_figurine"]

# isometric-ish projection
ANG = math.radians(30)
COS_A, SIN_A = math.cos(ANG), math.sin(ANG)


def project(p, scale, cx, cy):
    x, y, z = p
    sx = (x - z) * COS_A
    sy = (x + z) * SIN_A - y
    return (cx + sx * scale, cy + sy * scale)


def rotate_point(p, origin, axis, angle_deg):
    a = math.radians(angle_deg)
    c, s = math.cos(a), math.sin(a)
    x, y, z = p[0] - origin[0], p[1] - origin[1], p[2] - origin[2]
    if axis == "x":
        y, z = y * c - z * s, y * s + z * c
    elif axis == "y":
        x, z = x * c + z * s, -x * s + z * c
    else:
        x, y = x * c - y * s, x * s + y * c
    return (x + origin[0], y + origin[1], z + origin[2])


CORNERS = {
    "down": [(0, 0, 1), (0, 0, 0), (1, 0, 0), (1, 0, 1)],
    "up": [(0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)],
    "north": [(1, 1, 0), (1, 0, 0), (0, 0, 0), (0, 1, 0)],
    "south": [(0, 1, 1), (0, 0, 1), (1, 0, 1), (1, 1, 1)],
    "west": [(0, 1, 0), (0, 0, 0), (0, 0, 1), (0, 1, 1)],
    "east": [(1, 1, 1), (1, 0, 1), (1, 0, 0), (1, 1, 0)],
}

SHADE = {"up": 1.0, "down": 0.55, "north": 0.8, "south": 0.8, "west": 0.65, "east": 0.65}


def avg_color(tex, uv):
    x1, y1, x2, y2 = [int(round(v)) for v in uv]
    x1, x2 = sorted((max(0, x1), min(tex.width, x2)))
    y1, y2 = sorted((max(0, y1), min(tex.height, y2)))
    if x2 <= x1 or y2 <= y1:
        return (255, 0, 255)
    crop = tex.crop((x1, y1, x2, y2)).convert("RGBA")
    px = list(crop.getdata())
    opaque = [p for p in px if p[3] > 8]
    if not opaque:
        return None  # fully transparent
    n = len(opaque)
    return (sum(p[0] for p in opaque) // n, sum(p[1] for p in opaque) // n, sum(p[2] for p in opaque) // n)


def render(model, tex, size=560):
    # gather world-space quads
    quads = []
    for e in model["elements"]:
        f, t = e["from"], e["to"]
        rot = e.get("rotation")
        for d, fc in e["faces"].items():
            col = avg_color(tex, fc["uv"])
            if col is None:
                continue
            pts = []
            for c in CORNERS[d]:
                p = (f[0] + (t[0] - f[0]) * c[0], f[1] + (t[1] - f[1]) * c[1], f[2] + (t[2] - f[2]) * c[2])
                if rot:
                    p = rotate_point(p, rot["origin"], rot["axis"], rot["angle"])
                pts.append(p)
            depth = sum(p[0] + p[1] * 0.35 + p[2] for p in pts)
            quads.append((depth, pts, col, SHADE[d]))
    quads.sort(key=lambda q: q[0])
    # fit
    all_pts = [p for q in quads for p in q[1]]
    xs = [(p[0] - p[2]) * COS_A for p in all_pts]
    ys = [(p[0] + p[2]) * SIN_A - p[1] for p in all_pts]
    span = max(max(xs) - min(xs), max(ys) - min(ys), 1e-6)
    scale = (size - 60) / span
    cx = size / 2 - (max(xs) + min(xs)) / 2 * scale
    cy = size / 2 - (max(ys) + min(ys)) / 2 * scale
    img = Image.new("RGBA", (size, size), (18, 18, 26, 255))
    dr = ImageDraw.Draw(img)
    for _, pts, col, sh in quads:
        col = tuple(max(0, min(255, int(c * sh))) for c in col)
        dr.polygon([project(p, scale, cx, cy) for p in pts], fill=col + (255,), outline=(0, 0, 0, 90))
    return img


def main():
    os.makedirs(OUT, exist_ok=True)
    with zipfile.ZipFile(JAR) as z:
        for name in MODELS:
            model = json.loads(z.read(f"assets/arcanaforge/models/item/{name}.json").decode("utf-8"))
            tex = Image.open(io.BytesIO(z.read(f"assets/arcanaforge/textures/item/{name}.png")))
            img = render(model, tex.convert("RGBA"))
            out = os.path.join(OUT, f"{name}.png")
            img.save(out)
            print(f"{out}  ({len(model['elements'])} elements)")


if __name__ == "__main__":
    main()

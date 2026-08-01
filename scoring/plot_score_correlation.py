#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

import numpy as np

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "scoring" / "data"
SCORES_FILE = DATA_DIR / "latent_label_scores.json"
OUT_FILE = DATA_DIR / "correlation_matrix.svg"
DIMENSIONS = ("heritage", "vibrancy", "nature", "adventure")


def color(value):
    value = max(-1.0, min(1.0, float(value)))
    if value < 0:
        t = value + 1
        r = round(49 + (247 - 49) * t)
        g = round(130 + (247 - 130) * t)
        b = round(189 + (247 - 189) * t)
    else:
        t = value
        r = round(247 + (202 - 247) * t)
        g = round(247 + (55 - 247) * t)
        b = round(247 + (75 - 247) * t)
    return f"rgb({r},{g},{b})"


def write_svg(path, dimensions, corr):
    cell = 92
    left = 116
    top = 72
    size = len(dimensions) * cell
    width = left + size + 32
    height = top + size + 48
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fff"/>',
        '<text x="20" y="32" font-family="Inter, Arial, sans-serif" font-size="20" font-weight="700">Score Correlation Matrix</text>',
    ]
    for index, dimension in enumerate(dimensions):
        x = left + index * cell + cell / 2
        y = top + index * cell + cell / 2
        lines.append(f'<text x="{x:.1f}" y="58" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="13">{dimension}</text>')
        lines.append(f'<text x="104" y="{y + 5:.1f}" text-anchor="end" font-family="Inter, Arial, sans-serif" font-size="13">{dimension}</text>')
    for y_index, row in enumerate(corr):
        for x_index, value in enumerate(row):
            x = left + x_index * cell
            y = top + y_index * cell
            text_color = "#fff" if abs(value) > 0.55 else "#1f2937"
            lines.extend(
                [
                    f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" fill="{color(value)}" stroke="#fff"/>',
                    f'<text x="{x + cell / 2:.1f}" y="{y + cell / 2 + 5:.1f}" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="17" font-weight="700" fill="{text_color}">{value:.2f}</text>',
                ]
            )
    lines.append("</svg>")
    path.write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scores", type=Path, default=SCORES_FILE)
    parser.add_argument("--out", type=Path, default=OUT_FILE)
    args = parser.parse_args()

    scores = json.loads(args.scores.read_text())
    first_row = next(iter(scores.values()))
    dimensions = [dimension for dimension in DIMENSIONS if dimension in first_row]
    dimensions += [dimension for dimension in first_row if dimension not in dimensions]
    values = np.array(
        [[row[dimension] for dimension in dimensions] for row in scores.values()],
        dtype=np.float64,
    )
    corr = np.corrcoef(values, rowvar=False)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_svg(args.out, dimensions, corr)
    print(f"Wrote {args.out.resolve().relative_to(PROJECT_DIR)}")
    print(json.dumps({dimension: corr[index].round(3).tolist() for index, dimension in enumerate(dimensions)}, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Redact sensitive regions and annotate click targets on a screenshot."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_dependencies():
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
    except ImportError as exc:
        raise SystemExit("Missing dependency. Install opencv-python in the active Python environment.") from exc
    return cv2, np


def parse_region(value: str, with_label: bool) -> tuple[int, int, int, int, str | None]:
    parts = [part.strip() for part in value.split(",")]
    expected = 5 if with_label else 4
    if len(parts) != expected:
        kind = "x1,y1,x2,y2,label" if with_label else "x1,y1,x2,y2"
        raise argparse.ArgumentTypeError(f"Expected {kind}: {value}")
    try:
        coords = tuple(int(part) for part in parts[:4])
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Coordinates must be integers: {value}") from exc
    return (*coords, parts[4] if with_label else None)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--redact", action="append", default=[], help="x1,y1,x2,y2; repeatable")
    parser.add_argument("--mark", action="append", default=[], help="x1,y1,x2,y2,label; repeatable")
    parser.add_argument("--redaction-style", choices=("solid", "blur"), default="solid")
    parser.add_argument("--redaction-color", default="#333333")
    parser.add_argument("--mark-color", default="#E53935")
    parser.add_argument("--line-width", type=int, default=0, help="0 chooses a size relative to the image")
    return parser.parse_args()


def clamp_region(region, width: int, height: int):
    x1, y1, x2, y2, label = region
    x1, x2 = sorted((max(0, min(width, x1)), max(0, min(width, x2))))
    y1, y2 = sorted((max(0, min(height, y1)), max(0, min(height, y2))))
    if x1 == x2 or y1 == y2:
        raise SystemExit(f"Empty region after clipping: {region}")
    return x1, y1, x2, y2, label


def read_image(path: Path, cv2, np):
    data = np.fromfile(str(path), dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def write_image(path: Path, image, cv2, params: list[int] | None = None) -> bool:
    extension = path.suffix.lower() or ".jpg"
    ok, encoded = cv2.imencode(extension, image, params or [])
    if not ok:
        return False
    encoded.tofile(str(path))
    return True


def main() -> int:
    args = parse_args()
    cv2, np = load_dependencies()
    if not args.input.is_file():
        raise SystemExit(f"Image not found: {args.input}")
    image = read_image(args.input, cv2, np)
    if image is None:
        raise SystemExit(f"Cannot read image: {args.input}")
    height, width = image.shape[:2]
    line_width = args.line_width or max(3, round(min(width, height) * 0.005))

    redactions = [clamp_region(parse_region(value, False), width, height) for value in args.redact]
    marks = [clamp_region(parse_region(value, True), width, height) for value in args.mark]

    for x1, y1, x2, y2, _ in redactions:
        if args.redaction_style == "solid":
            color = tuple(int(args.redaction_color.lstrip("#")[i : i + 2], 16) for i in (4, 2, 0))
            cv2.rectangle(image, (x1, y1), (x2, y2), color, thickness=-1)
        else:
            crop = image[y1:y2, x1:x2]
            kernel = max(15, (min(x2 - x1, y2 - y1) // 4) | 1)
            image[y1:y2, x1:x2] = cv2.GaussianBlur(crop, (kernel, kernel), 0)

    mark_color = tuple(int(args.mark_color.lstrip("#")[i : i + 2], 16) for i in (4, 2, 0))
    badge_size = max(24, line_width * 7)
    for x1, y1, x2, y2, label in marks:
        cv2.rectangle(image, (x1, y1), (x2, y2), mark_color, thickness=line_width)
        if label:
            center = (max(badge_size // 2, x1), max(badge_size // 2, y1))
            radius = badge_size // 2
            cv2.circle(image, center, radius, mark_color, thickness=-1, lineType=cv2.LINE_AA)
            scale = max(0.55, badge_size / 42)
            (text_width, text_height), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, scale, 2)
            origin = (center[0] - text_width // 2, center[1] + text_height // 2)
            cv2.putText(image, label, origin, cv2.FONT_HERSHEY_SIMPLEX, scale, (255, 255, 255), 2, cv2.LINE_AA)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    suffix = args.output.suffix.lower()
    params = [int(cv2.IMWRITE_JPEG_QUALITY), 94] if suffix in {".jpg", ".jpeg"} else []
    if not write_image(args.output, image, cv2, params):
        raise SystemExit(f"Failed to write image: {args.output}")
    print(json.dumps({"ok": True, "output": str(args.output), "redactions": len(redactions), "marks": len(marks)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

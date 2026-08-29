#!/usr/bin/env python3
"""Extract periodic and scene-change candidates from a software screen recording."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path


def load_dependencies():
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
    except ImportError as exc:
        raise SystemExit("Missing dependency. Install opencv-python in the active Python environment.") from exc
    return cv2, np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--interval", type=float, default=2.0, help="Periodic frame interval in seconds")
    parser.add_argument("--scan-step", type=float, default=0.4, help="Scene scan interval in seconds")
    parser.add_argument("--scene-threshold", type=float, default=0.04, help="Mean normalized frame difference")
    parser.add_argument("--min-gap", type=float, default=0.6, help="Minimum seconds between scene candidates")
    parser.add_argument("--max-frames", type=int, default=36)
    parser.add_argument("--thumb-width", type=int, default=320)
    parser.add_argument("--jpeg-quality", type=int, default=92)
    return parser.parse_args()


def timestamp_label(seconds: float) -> str:
    minutes = int(seconds // 60)
    whole = int(seconds % 60)
    millis = int(round((seconds - math.floor(seconds)) * 1000))
    if millis == 1000:
        whole += 1
        millis = 0
    return f"{minutes:02d}m{whole:02d}s{millis:03d}"


def evenly_reduce(items: list[dict], limit: int) -> list[dict]:
    if len(items) <= limit:
        return items
    if limit <= 1:
        return [items[0]]
    indices = {round(i * (len(items) - 1) / (limit - 1)) for i in range(limit)}
    return [items[i] for i in sorted(indices)]


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


def build_contact_sheet(entries: list[dict], output: Path, thumb_width: int, cv2, np) -> None:
    if not entries:
        return
    columns = min(4, max(1, math.ceil(math.sqrt(len(entries)))))
    label_height = 28
    thumbs = []
    max_height = 0
    for entry in entries:
        image = read_image(Path(entry["path"]), cv2, np)
        if image is None:
            raise SystemExit(f"Failed to read extracted frame: {entry['path']}")
        height = max(1, round(image.shape[0] * thumb_width / image.shape[1]))
        image = cv2.resize(image, (thumb_width, height), interpolation=cv2.INTER_AREA)
        thumbs.append(image)
        max_height = max(max_height, height)
    rows = math.ceil(len(thumbs) / columns)
    sheet = np.full((rows * (max_height + label_height), columns * thumb_width, 3), 255, dtype=np.uint8)
    for index, (entry, thumb) in enumerate(zip(entries, thumbs)):
        x = (index % columns) * thumb_width
        y = (index // columns) * (max_height + label_height)
        sheet[y : y + thumb.shape[0], x : x + thumb_width] = thumb
        reasons = ",".join(entry["reasons"])
        cv2.putText(
            sheet,
            f"{index + 1:02d}  {entry['timestamp']:.2f}s  {reasons}",
            (x + 6, y + max_height + 19),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            (0, 0, 0),
            1,
            cv2.LINE_AA,
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    if not write_image(output, sheet, cv2, [int(cv2.IMWRITE_JPEG_QUALITY), 90]):
        raise SystemExit(f"Failed to write contact sheet: {output}")


def main() -> int:
    args = parse_args()
    cv2, np = load_dependencies()
    if not args.video.is_file():
        raise SystemExit(f"Video not found: {args.video}")
    if args.interval <= 0 or args.scan_step <= 0 or args.max_frames < 2:
        raise SystemExit("interval and scan-step must be positive; max-frames must be at least 2")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    capture = cv2.VideoCapture(str(args.video))
    if not capture.isOpened():
        raise SystemExit(f"Cannot open video: {args.video}")

    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if fps <= 0 or frame_count <= 0:
        raise SystemExit("Video metadata is invalid or unsupported")
    duration = max(0.0, (frame_count - 1) / fps)
    scan_frames = max(1, round(args.scan_step * fps))

    candidates: dict[int, dict] = {}

    def add_candidate(frame_index: int, score: float, reason: str) -> None:
        item = candidates.setdefault(
            frame_index,
            {"frame_index": frame_index, "timestamp": frame_index / fps, "score": score, "reasons": []},
        )
        item["score"] = max(float(item["score"]), float(score))
        if reason not in item["reasons"]:
            item["reasons"].append(reason)

    add_candidate(0, 1.0, "first")
    next_periodic = args.interval
    previous_gray = None
    last_scene_time = -1e9
    frame_index = 0
    while frame_index < frame_count:
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = capture.read()
        if not ok:
            break
        small = cv2.resize(frame, (160, 90), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        score = 0.0
        if previous_gray is not None:
            score = float(cv2.absdiff(gray, previous_gray).mean() / 255.0)
        timestamp = frame_index / fps
        while timestamp + args.scan_step / 2 >= next_periodic and next_periodic < duration:
            periodic_index = min(frame_count - 1, round(next_periodic * fps))
            add_candidate(periodic_index, score, "periodic")
            next_periodic += args.interval
        if score >= args.scene_threshold and timestamp - last_scene_time >= args.min_gap:
            add_candidate(frame_index, score, "scene")
            last_scene_time = timestamp
        previous_gray = gray
        frame_index += scan_frames
    add_candidate(frame_count - 1, 1.0, "last")

    all_candidates = sorted(candidates.values(), key=lambda item: item["frame_index"])
    base = [item for item in all_candidates if "periodic" in item["reasons"] or "first" in item["reasons"] or "last" in item["reasons"]]
    base = evenly_reduce(base, args.max_frames)
    selected_by_index = {item["frame_index"]: item for item in base}
    if len(selected_by_index) < args.max_frames:
        extras = [item for item in all_candidates if item["frame_index"] not in selected_by_index]
        extras.sort(key=lambda item: (item["score"], -item["timestamp"]), reverse=True)
        for item in extras[: args.max_frames - len(selected_by_index)]:
            selected_by_index[item["frame_index"]] = item
    selected = sorted(selected_by_index.values(), key=lambda item: item["frame_index"])

    entries = []
    for output_index, item in enumerate(selected, start=1):
        capture.set(cv2.CAP_PROP_POS_FRAMES, item["frame_index"])
        ok, frame = capture.read()
        if not ok:
            continue
        filename = f"frame_{output_index:03d}_{timestamp_label(item['timestamp'])}.jpg"
        path = args.output_dir / filename
        if not write_image(path, frame, cv2, [int(cv2.IMWRITE_JPEG_QUALITY), args.jpeg_quality]):
            raise SystemExit(f"Failed to write frame: {path}")
        entries.append({**item, "file": filename, "path": str(path.resolve())})
    capture.release()

    metadata = {
        "video": str(args.video.resolve()),
        "fps": fps,
        "frame_count": frame_count,
        "duration_seconds": duration,
        "settings": {
            "interval": args.interval,
            "scan_step": args.scan_step,
            "scene_threshold": args.scene_threshold,
            "min_gap": args.min_gap,
            "max_frames": args.max_frames,
        },
        "frames": [{key: value for key, value in entry.items() if key != "path"} for entry in entries],
    }
    metadata_path = args.output_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    build_contact_sheet(entries, args.output_dir / "contact_sheet.jpg", args.thumb_width, cv2, np)
    print(json.dumps({"ok": True, "frames": len(entries), "metadata": str(metadata_path), "contact_sheet": str(args.output_dir / "contact_sheet.jpg")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

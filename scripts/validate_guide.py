#!/usr/bin/env python3
"""Validate structural and editorial invariants in a Feishu guide XML export."""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


PLACEHOLDER_PATTERN = re.compile(r"TODO|TBD|占位|待补|待插入|示例文本")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xml", type=Path)
    parser.add_argument("--button", action="append", default=[], help="Expected clickable label; repeatable")
    return parser.parse_args()


def node_text(node: ET.Element) -> str:
    return "".join(node.itertext()).strip()


def sequence_is_contiguous(values: list[int]) -> bool:
    return not values or values == list(range(values[0], values[0] + len(values)))


def main() -> int:
    args = parse_args()
    if not args.xml.is_file():
        raise SystemExit(f"XML file not found: {args.xml}")
    raw = args.xml.read_text(encoding="utf-8").strip()
    raw = re.sub(r"^<\?xml[^>]*>\s*", "", raw)
    try:
        root = ET.fromstring(f"<root>{raw}</root>")
    except ET.ParseError as exc:
        print(json.dumps({"ok": False, "errors": [f"XML parse error: {exc}"]}, ensure_ascii=False, indent=2))
        return 1

    titles = root.findall(".//title")
    headings = [node for level in range(1, 10) for node in root.findall(f".//h{level}")]
    h2_nodes = root.findall(".//h2")
    images = root.findall(".//img")
    plain_text = node_text(root)
    title_text = node_text(titles[0]) if titles else ""
    duplicate_title = any(node_text(node) == title_text for node in headings) if title_text else False

    step_numbers = []
    for node in h2_nodes:
        match = re.search(r"步骤\s*(\d+)", node_text(node))
        if match:
            step_numbers.append(int(match.group(1)))
    figure_numbers = []
    for image in images:
        match = re.search(r"图\s*(\d+)", image.attrib.get("caption", ""))
        if match:
            figure_numbers.append(int(match.group(1)))

    errors: list[str] = []
    warnings: list[str] = []
    if len(titles) != 1:
        errors.append(f"Expected exactly one title, found {len(titles)}")
    if duplicate_title:
        errors.append("Document title is duplicated as a body heading")
    if step_numbers and (step_numbers[0] != 1 or not sequence_is_contiguous(step_numbers)):
        errors.append(f"Step numbering is not continuous from 1: {step_numbers}")
    if figure_numbers and (figure_numbers[0] != 1 or not sequence_is_contiguous(figure_numbers)):
        errors.append(f"Figure numbering is not continuous from 1: {figure_numbers}")
    placeholders = sorted(set(PLACEHOLDER_PATTERN.findall(plain_text)))
    if placeholders:
        errors.append(f"Placeholder text remains: {placeholders}")

    result_phrase_hits = plain_text.count("完成后应该看到")
    if result_phrase_hits:
        warnings.append(f"Review {result_phrase_hits} routine result paragraph(s); the next step may already prove the result")

    button_results = []
    for button in args.button:
        escaped = re.escape(button)
        bold_bracket = bool(
            re.search(rf"【\s*<b>\s*{escaped}\s*</b>\s*】", raw)
            or re.search(rf"<b>\s*【\s*{escaped}\s*】\s*</b>", raw)
        )
        quoted = f"“{button}”" in raw
        button_results.append({"button": button, "bold_bracket": bold_bracket, "quoted": quoted})
        if quoted:
            warnings.append(f"Clickable label still uses quotation marks: {button}")
        if not bold_bracket:
            warnings.append(f"Clickable label is not present as bold 【button】: {button}")

    result = {
        "ok": not errors,
        "stats": {
            "titles": len(titles),
            "headings": len(headings),
            "steps": len(step_numbers),
            "images": len(images),
            "checkboxes": len(root.findall(".//checkbox")),
            "routine_result_phrases": result_phrase_hits,
        },
        "step_numbers": step_numbers,
        "figure_numbers": figure_numbers,
        "buttons": button_results,
        "errors": errors,
        "warnings": warnings,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())

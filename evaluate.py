#!/usr/bin/env python3
"""Score a scraper's output against the ground truth.

Point your scraper at the pages listed in ground-truth/manifest.json, write one
JSON file per task (e.g. out/quotes.json), then run:

    python3 evaluate.py <output-dir>

Both manifests are scored: ground-truth/manifest.json (static tasks) and
ground-truth/browser-manifest.json (dynamic tasks needing a headless browser).

Comparison rules: lists are order-insensitive (unless the task sets
"ordered": true), floats compare with a small tolerance, ground-truth values
of the form {"$regex": ...} match strings by regular expression, and missing
tasks are reported as skipped (not failed) so you can adopt tasks
incrementally.
"""
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFESTS = ["ground-truth/manifest.json", "ground-truth/browser-manifest.json"]


def is_regex_token(value):
    return isinstance(value, dict) and set(value.keys()) == {"$regex"}


def normalize(value, ordered=False):
    """Make values comparable: round floats, sort lists order-insensitively."""
    if isinstance(value, float):
        return round(value, 4)
    if isinstance(value, list):
        items = [normalize(v, ordered) for v in value]
        if ordered:
            return items
        return sorted(items, key=lambda v: json.dumps(v, sort_keys=True, ensure_ascii=False))
    if isinstance(value, dict):
        return {k: normalize(v, ordered) for k, v in value.items()}
    return value


def first_diff(expected, actual, path="$"):
    """Return a human-readable description of the first difference found."""
    if is_regex_token(expected):
        if not isinstance(actual, str) or not re.fullmatch(expected["$regex"], actual):
            return f"{path}: expected match for /{expected['$regex']}/, got {actual!r}"
        return None
    if type(expected) is not type(actual):
        return f"{path}: expected {type(expected).__name__}, got {type(actual).__name__}"
    if isinstance(expected, dict):
        for key in expected.keys() | actual.keys():
            if key not in actual:
                return f"{path}.{key}: missing"
            if key not in expected:
                return f"{path}.{key}: unexpected extra key"
            d = first_diff(expected[key], actual[key], f"{path}.{key}")
            if d:
                return d
        return None
    if isinstance(expected, list):
        if len(expected) != len(actual):
            return f"{path}: expected {len(expected)} items, got {len(actual)}"
        for i, (e, a) in enumerate(zip(expected, actual)):
            d = first_diff(e, a, f"{path}[{i}]")
            if d:
                return d
        return None
    if isinstance(expected, float) and isinstance(actual, float):
        if not math.isclose(expected, actual, abs_tol=1e-4):
            return f"{path}: expected {expected}, got {actual}"
        return None
    if expected != actual:
        return f"{path}: expected {expected!r}, got {actual!r}"
    return None


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    out_dir = Path(sys.argv[1])

    tasks = {}
    for manifest_path in MANIFESTS:
        manifest = json.loads((ROOT / manifest_path).read_text(encoding="utf-8"))
        tasks.update(manifest["tasks"])

    passed, failed, skipped = [], [], []
    for task, spec in tasks.items():
        candidate_file = out_dir / f"{task}.json"
        if not candidate_file.exists():
            skipped.append(task)
            continue
        ordered = spec.get("ordered", False)
        expected = normalize(
            json.loads((ROOT / spec["ground_truth"]).read_text(encoding="utf-8")), ordered)
        try:
            actual = normalize(json.loads(candidate_file.read_text(encoding="utf-8")), ordered)
        except json.JSONDecodeError as e:
            failed.append((task, f"invalid JSON: {e}"))
            continue
        diff = first_diff(expected, actual)
        if diff:
            failed.append((task, diff))
        else:
            passed.append(task)

    for task in passed:
        print(f"  PASS  {task}")
    for task, diff in failed:
        print(f"  FAIL  {task}  ({diff})")
    for task in skipped:
        print(f"  SKIP  {task}  (no {task}.json in {out_dir})")

    total = len(passed) + len(failed)
    print(f"\nScore: {len(passed)}/{total} attempted"
          f" ({len(skipped)} of {len(tasks)} tasks not attempted)")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()

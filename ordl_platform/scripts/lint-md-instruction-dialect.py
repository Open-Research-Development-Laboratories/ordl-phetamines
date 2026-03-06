#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path


REQUIRED_SECTIONS = [
    "## Intent",
    "## Inputs",
    "## Constraints",
    "## Tool Policy",
    "## Output Contract",
    "## Failure Handling",
    "## Acceptance Criteria",
]


def _check_file(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    if not text.lstrip().startswith("# "):
        errors.append("missing top-level title (# ...)")
    last_pos = -1
    for section in REQUIRED_SECTIONS:
        pos = text.find(section)
        if pos < 0:
            errors.append(f"missing required section: {section}")
            continue
        if pos < last_pos:
            errors.append(f"section out of order: {section}")
        last_pos = max(last_pos, pos)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint markdown files against ORDL OpenAI instruction dialect.")
    parser.add_argument("paths", nargs="+", help="Files or directories to lint.")
    args = parser.parse_args()

    files: list[Path] = []
    for p in args.paths:
        path = Path(p).resolve()
        if path.is_file() and path.suffix.lower() == ".md":
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(path.rglob("*.md")))

    failures = 0
    for file in files:
        errors = _check_file(file)
        if errors:
            failures += 1
            print(f"[FAIL] {file}")
            for err in errors:
                print(f"  - {err}")
        else:
            print(f"[OK]   {file}")

    print(f"Checked markdown files: {len(files)}")
    print(f"Failures: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())


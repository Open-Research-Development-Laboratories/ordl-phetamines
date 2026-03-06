#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")
TOKEN_RE = re.compile(
    r"\b(?P<method>GET|POST|PUT|PATCH|DELETE)(?:/(?P<method2>GET|POST|PUT|PATCH|DELETE))*\s+(?P<path>/v1/[^\s`|]+)"
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _extract_required_routes(matrix_text: str) -> set[tuple[str, str]]:
    required: set[tuple[str, str]] = set()
    for line in matrix_text.splitlines():
        for match in TOKEN_RE.finditer(line):
            path = match.group("path")
            m1 = match.group("method")
            required.add((m1, path))
            m2 = match.group("method2")
            if m2:
                required.add((m2, path))
    return required


def _load_actual_routes(contract_json: Path) -> set[tuple[str, str]]:
    payload = json.loads(contract_json.read_text(encoding="utf-8"))
    rows = payload.get("routes", [])
    routes: set[tuple[str, str]] = set()
    for row in rows:
        method = str(row.get("method", "")).upper()
        path = str(row.get("path", ""))
        if method in METHODS and path.startswith("/v1/"):
            routes.add((method, path))
    return routes


def _write_markdown(path: Path, missing: list[tuple[str, str]], present: list[tuple[str, str]]) -> None:
    lines = [
        "# Revision 8 Contract Review",
        "",
        "Comparison between declared Rev8 contract matrix and generated backend `/v1` contract.",
        "",
        f"- required routes parsed: `{len(missing) + len(present)}`",
        f"- present routes: `{len(present)}`",
        f"- missing routes: `{len(missing)}`",
        "",
        "## Missing Routes",
        "",
        "| Method | Path |",
        "|---|---|",
    ]
    for method, route in missing:
        lines.append(f"| `{method}` | `{route}` |")
    lines.extend(["", "## Present Routes", "", "| Method | Path |", "|---|---|"])
    for method, route in present:
        lines.append(f"| `{method}` | `{route}` |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare Rev8 contract matrix to backend /v1 contract.")
    parser.add_argument(
        "--matrix",
        default=str(
            _repo_root()
            / "ordl_platform"
            / "docs"
            / "faceplate"
            / "revision-8-js-files"
            / "ORDL_CONTRACT_MATRIX.md"
        ),
    )
    parser.add_argument(
        "--contract-json",
        default=str(
            _repo_root() / "ordl_platform" / "docs" / "contracts" / "api-v1-contract.json"
        ),
    )
    parser.add_argument(
        "--out-json",
        default=str(
            _repo_root()
            / "ordl_platform"
            / "state"
            / "reports"
            / "revision-8-contract-review.json"
        ),
    )
    parser.add_argument(
        "--out-md",
        default=str(
            _repo_root()
            / "ordl_platform"
            / "docs"
            / "faceplate"
            / "revision-8-js-files"
            / "REVISION_8_CONTRACT_REVIEW.md"
        ),
    )
    args = parser.parse_args()

    matrix_path = Path(args.matrix).resolve()
    contract_path = Path(args.contract_json).resolve()

    required = _extract_required_routes(matrix_path.read_text(encoding="utf-8"))
    actual = _load_actual_routes(contract_path)

    missing = sorted(required - actual)
    present = sorted(required & actual)

    report = {
        "matrix": str(matrix_path),
        "contract_json": str(contract_path),
        "required_count": len(required),
        "present_count": len(present),
        "missing_count": len(missing),
        "missing_routes": [{"method": m, "path": p} for m, p in missing],
        "present_routes": [{"method": m, "path": p} for m, p in present],
    }

    out_json = Path(args.out_json).resolve()
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    _write_markdown(Path(args.out_md).resolve(), missing, present)

    print(f"Matrix: {matrix_path}")
    print(f"Contract: {contract_path}")
    print(f"Required routes: {len(required)}")
    print(f"Present routes: {len(present)}")
    print(f"Missing routes: {len(missing)}")
    print(f"JSON report: {out_json}")
    print(f"Markdown report: {Path(args.out_md).resolve()}")
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())

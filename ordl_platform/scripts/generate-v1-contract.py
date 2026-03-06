#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _backend_root() -> Path:
    return _project_root() / "ordl_platform" / "backend"


def _load_app() -> Any:
    import sys

    backend_root = _backend_root()
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))

    from app.main import app  # pylint: disable=import-error

    return app


def _filter_v1_paths(openapi: dict[str, Any]) -> dict[str, Any]:
    paths = openapi.get("paths", {})
    return {path: value for path, value in paths.items() if path.startswith("/v1")}


def _route_table(v1_paths: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path, methods in sorted(v1_paths.items()):
        for method, operation in sorted(methods.items()):
            op = operation if isinstance(operation, dict) else {}
            rows.append(
                {
                    "path": path,
                    "method": method.upper(),
                    "operation_id": op.get("operationId"),
                    "tags": op.get("tags", []),
                    "summary": op.get("summary") or "",
                }
            )
    return rows


def _write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        "# ORDL Backend /v1 Route Contract",
        "",
        "Generated from FastAPI OpenAPI source. `/v1` is the source of truth for frontend wiring.",
        "",
        "| Method | Path | Operation ID | Tags | Summary |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        tags = ", ".join(row["tags"]) if row["tags"] else ""
        summary = row["summary"].replace("|", "\\|")
        op_id = (row["operation_id"] or "").replace("|", "\\|")
        lines.append(
            f"| {row['method']} | `{row['path']}` | `{op_id}` | `{tags}` | {summary} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate ORDL /v1 API contract artifacts.")
    parser.add_argument(
        "--out-json",
        default=str(
            _project_root()
            / "ordl_platform"
            / "docs"
            / "contracts"
            / "api-v1-contract.json"
        ),
        help="Output JSON file path.",
    )
    parser.add_argument(
        "--out-md",
        default=str(
            _project_root()
            / "ordl_platform"
            / "docs"
            / "contracts"
            / "api-v1-routes.md"
        ),
        help="Output Markdown file path.",
    )
    args = parser.parse_args()

    app = _load_app()
    openapi = app.openapi()
    v1_paths = _filter_v1_paths(openapi)
    rows = _route_table(v1_paths)

    output = {
        "title": openapi.get("info", {}).get("title", "ORDL Platform API"),
        "version": openapi.get("info", {}).get("version", "unknown"),
        "v1_path_count": len(v1_paths),
        "routes": rows,
        "paths": v1_paths,
    }

    out_json = Path(args.out_json).resolve()
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(output, indent=2), encoding="utf-8")

    _write_markdown(Path(args.out_md).resolve(), rows)

    print(f"Wrote /v1 JSON contract: {out_json}")
    print(f"Wrote /v1 route table: {Path(args.out_md).resolve()}")
    print(f"Discovered /v1 paths: {len(v1_paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

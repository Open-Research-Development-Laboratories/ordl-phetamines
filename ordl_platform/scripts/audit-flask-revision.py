#!/usr/bin/env python
from __future__ import annotations

import argparse
import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


URL_FOR_PATTERN = re.compile(r"url_for\(\s*['\"]([a-zA-Z0-9_.-]+)['\"]")
FETCH_PATTERN = re.compile(r"fetch\(\s*['\"]([^'\"]+)['\"]")
TODO_PATTERN = re.compile(r"(?i)\bTODO\b")


@dataclass(frozen=True)
class Finding:
    file: str
    line: int
    message: str


def _iter_files(root: Path, pattern: str) -> Iterable[Path]:
    if not root.exists():
        return []
    excluded = {"node_modules", ".venv", "__pycache__", ".git", "dist", "build"}
    return [
        p
        for p in root.rglob(pattern)
        if not any(part in excluded for part in p.parts)
    ]


def _scan_flask_endpoints(root: Path) -> set[str]:
    endpoints: set[str] = {"static"}
    blueprint_names: dict[str, str] = {}

    for py_file in _iter_files(root, "*.py"):
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        except Exception:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                if not isinstance(node.value, ast.Call):
                    continue
                func = node.value.func
                if not (isinstance(func, ast.Name) and func.id == "Blueprint"):
                    continue
                if not node.targets:
                    continue
                target = node.targets[0]
                if not isinstance(target, ast.Name):
                    continue
                if not node.value.args:
                    continue
                first_arg = node.value.args[0]
                if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                    blueprint_names[target.id] = first_arg.value

        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            fn_name = node.name
            for dec in node.decorator_list:
                if not isinstance(dec, ast.Call):
                    continue
                func = dec.func
                if not isinstance(func, ast.Attribute):
                    continue
                if func.attr not in {"route", "get", "post", "put", "patch", "delete"}:
                    continue
                if not isinstance(func.value, ast.Name):
                    continue
                owner = func.value.id

                endpoint_kw = None
                for kw in dec.keywords:
                    if kw.arg == "endpoint" and isinstance(kw.value, ast.Constant) and isinstance(
                        kw.value.value, str
                    ):
                        endpoint_kw = kw.value.value
                        break

                if owner == "app":
                    endpoints.add(endpoint_kw or fn_name)
                    continue

                if owner in blueprint_names:
                    bp_name = blueprint_names[owner]
                    endpoint = endpoint_kw or fn_name
                    if "." in endpoint:
                        endpoints.add(endpoint)
                    else:
                        endpoints.add(f"{bp_name}.{endpoint}")

    return endpoints


def _scan_url_for_refs(root: Path) -> tuple[set[str], list[Finding]]:
    refs: set[str] = set()
    findings: list[Finding] = []
    for html in _iter_files(root, "*.html"):
        text = html.read_text(encoding="utf-8")
        for match in URL_FOR_PATTERN.finditer(text):
            endpoint = match.group(1)
            refs.add(endpoint)
            line = text.count("\n", 0, match.start()) + 1
            findings.append(Finding(str(html), line, endpoint))
    return refs, findings


def _scan_js_todos(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    js_root = root / "static" / "js"
    for js_file in _iter_files(js_root, "*.js"):
        p = str(js_file).replace("\\", "/")
        if "/governance/" not in p and "/security/" not in p:
            continue
        for idx, line in enumerate(js_file.read_text(encoding="utf-8").splitlines(), start=1):
            if TODO_PATTERN.search(line):
                findings.append(Finding(str(js_file), idx, line.strip()))
    return findings


def _scan_forbidden_api_refs(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    js_root = root / "static" / "js"
    for js_file in _iter_files(js_root, "*.js"):
        text = js_file.read_text(encoding="utf-8")
        for match in FETCH_PATTERN.finditer(text):
            url = match.group(1)
            if url.startswith("/api/"):
                line = text.count("\n", 0, match.start()) + 1
                findings.append(
                    Finding(str(js_file), line, f"Forbidden API path '{url}', expected /v1/*")
                )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Flask revision quality gates.")
    parser.add_argument("--revision-root", required=True, help="Path to Flask revision root.")
    parser.add_argument(
        "--out-json",
        default="",
        help="Optional output JSON report path.",
    )
    args = parser.parse_args()

    root = Path(args.revision_root).resolve()
    if not root.exists():
        raise SystemExit(f"Revision root not found: {root}")

    endpoints = _scan_flask_endpoints(root)
    ref_set, url_ref_findings = _scan_url_for_refs(root)
    unresolved_refs = [f for f in url_ref_findings if f.message not in endpoints]
    todo_findings = _scan_js_todos(root)
    forbidden_api_findings = _scan_forbidden_api_refs(root)

    report = {
        "revision_root": str(root),
        "endpoint_count": len(endpoints),
        "url_for_ref_count": len(url_ref_findings),
        "unresolved_url_for_count": len(unresolved_refs),
        "js_todo_count": len(todo_findings),
        "forbidden_api_ref_count": len(forbidden_api_findings),
        "unresolved_url_for": [f.__dict__ for f in unresolved_refs],
        "js_todos": [f.__dict__ for f in todo_findings],
        "forbidden_api_refs": [f.__dict__ for f in forbidden_api_findings],
    }

    if args.out_json:
        out_path = Path(args.out_json).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Wrote audit report: {out_path}")

    print("== Flask Revision Audit ==")
    print(f"Revision root: {root}")
    print(f"Endpoints discovered: {len(endpoints)}")
    print(f"url_for references: {len(url_ref_findings)}")
    print(f"Unresolved url_for refs: {len(unresolved_refs)}")
    print(f"Governance/Security TODOs: {len(todo_findings)}")
    print(f"Forbidden /api/* fetch refs: {len(forbidden_api_findings)}")

    if unresolved_refs:
        print("\n[unresolved-url_for]")
        for finding in unresolved_refs[:50]:
            print(f"{finding.file}:{finding.line}: {finding.message}")
    if todo_findings:
        print("\n[js-todos]")
        for finding in todo_findings[:50]:
            print(f"{finding.file}:{finding.line}: {finding.message}")
    if forbidden_api_findings:
        print("\n[forbidden-api-refs]")
        for finding in forbidden_api_findings[:50]:
            print(f"{finding.file}:{finding.line}: {finding.message}")

    if unresolved_refs or todo_findings or forbidden_api_findings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

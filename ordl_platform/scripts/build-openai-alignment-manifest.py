#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse


URL_RE = re.compile(r"https?://[^\s)>\]`\"']+")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(_repo_root()).as_posix()
    except ValueError:
        return path.name


def _extract_urls(text: str) -> list[str]:
    return sorted(set(URL_RE.findall(text)))


def _classify_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()

    if "developers.openai.com" in host or "platform.openai.com" in host:
        if "/codex" in path:
            return "codex"
        if "/apps-sdk" in path:
            return "apps_sdk"
        if "/cookbook" in path:
            return "cookbook"
        if "/docs/guides/evals" in path or "/eval" in path:
            return "evals"
        if "/fine" in path:
            return "fine_tuning"
        if "/models" in path:
            return "models"
        if "/guides/" in path or "/docs/" in path:
            return "api_guides"
        return "openai_other"

    if "github.com/openai" in url.lower():
        return "openai_github"

    return "external"


def _build_backlog(categories: Counter[str]) -> list[dict[str, str]]:
    backlog: list[dict[str, str]] = []
    if categories["api_guides"] or categories["models"]:
        backlog.append(
            {
                "id": "OPENAI-001",
                "title": "Responses API and model policy alignment",
                "priority": "high",
                "deliverable": "codified API usage policy, model pinning policy, schema output policy",
            }
        )
    if categories["evals"]:
        backlog.append(
            {
                "id": "OPENAI-002",
                "title": "Evaluation-first release gating",
                "priority": "high",
                "deliverable": "mandatory eval gates in release flow with regression thresholds",
            }
        )
    if categories["fine_tuning"]:
        backlog.append(
            {
                "id": "OPENAI-003",
                "title": "Fine-tuning governance workflow",
                "priority": "high",
                "deliverable": "dataset provenance, runbook templates, and promotion controls",
            }
        )
    if categories["codex"] or categories["apps_sdk"]:
        backlog.append(
            {
                "id": "OPENAI-004",
                "title": "Agent/tool instruction dialect standardization",
                "priority": "high",
                "deliverable": "instruction dialect spec and markdown templates for workers and system files",
            }
        )
    if categories["cookbook"] or categories["openai_github"]:
        backlog.append(
            {
                "id": "OPENAI-005",
                "title": "Reference implementation ingestion process",
                "priority": "medium",
                "deliverable": "repeatable import/evaluate/adopt workflow for examples and recipes",
            }
        )
    return backlog


def _write_backlog_md(path: Path, categories: Counter[str], backlog: list[dict[str, str]]) -> None:
    lines = [
        "# OpenAI Alignment Backlog",
        "",
        "Generated from `openai_developers_comprehensive_report.md` URL extraction.",
        "",
        "## Category Totals",
        "",
    ]
    for key, count in sorted(categories.items()):
        lines.append(f"- `{key}`: {count}")
    lines.extend(["", "## Backlog Items", ""])
    for item in backlog:
        lines.extend(
            [
                f"### {item['id']} - {item['title']}",
                f"- priority: `{item['priority']}`",
                f"- deliverable: {item['deliverable']}",
                "",
            ]
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build OpenAI alignment manifest/backlog from report URLs.")
    parser.add_argument(
        "--input",
        default=str(
            _repo_root()
            / "ordl_platform"
            / "docs"
            / "research"
            / "openai_developers_comprehensive_report.md"
        ),
    )
    parser.add_argument(
        "--out-json",
        default=str(
            _repo_root() / "ordl_platform" / "docs" / "research" / "openai-url-manifest.json"
        ),
    )
    parser.add_argument(
        "--out-backlog",
        default=str(
            _repo_root() / "ordl_platform" / "docs" / "research" / "openai-adoption-backlog.md"
        ),
    )
    args = parser.parse_args()

    in_path = Path(args.input).resolve()
    text = in_path.read_text(encoding="utf-8")
    urls = _extract_urls(text)

    rows: list[dict[str, str]] = []
    categories = Counter()
    for url in urls:
        category = _classify_url(url)
        categories[category] += 1
        rows.append({"url": url, "category": category, "host": urlparse(url).netloc.lower()})

    backlog = _build_backlog(categories)
    out_json = Path(args.out_json).resolve()
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(
        json.dumps(
            {
                "source": _display_path(in_path),
                "url_count": len(urls),
                "categories": dict(categories),
                "urls": rows,
                "backlog": backlog,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    _write_backlog_md(Path(args.out_backlog).resolve(), categories, backlog)

    print(f"Source: {in_path}")
    print(f"URLs discovered: {len(urls)}")
    print(f"Manifest: {out_json}")
    print(f"Backlog: {Path(args.out_backlog).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

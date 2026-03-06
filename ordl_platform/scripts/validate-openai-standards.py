#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


@dataclass
class CheckResult:
    id: str
    status: str
    message: str
    evidence: str = ""


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _check_exists(checks: list[CheckResult], *, check_id: str, path: Path, label: str) -> None:
    if path.exists():
        checks.append(CheckResult(id=check_id, status="pass", message=f"{label} exists", evidence=str(path)))
    else:
        checks.append(CheckResult(id=check_id, status="fail", message=f"{label} missing", evidence=str(path)))


def _contains_all(text: str, required: list[str]) -> tuple[bool, list[str]]:
    missing = [token for token in required if token not in text]
    return len(missing) == 0, missing


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate OpenAI standards implementation artifacts.")
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
        help="ORDL platform root (defaults to ordl_platform directory).",
    )
    parser.add_argument(
        "--out-json",
        default="state/reports/openai-standards-validation.json",
        help="Output JSON report path.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on warnings in addition to failures.",
    )
    parser.add_argument(
        "--skip-dialect-lint",
        action="store_true",
        help="Skip running markdown dialect lint check.",
    )
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    out_json = Path(args.out_json)
    if not out_json.is_absolute():
        out_json = (root / out_json).resolve()
    out_json.parent.mkdir(parents=True, exist_ok=True)

    checks: list[CheckResult] = []

    report_md = root / "docs/research/openai_developers_comprehensive_report.md"
    manifest_json = root / "docs/research/openai-url-manifest.json"
    backlog_md = root / "docs/research/openai-adoption-backlog.md"
    dialect_md = root / "docs/security/openai-instruction-dialect-v1.md"
    lifecycle_md = root / "docs/security/openai-model-lifecycle-standard-v1.md"
    providers_py = root / "backend/app/providers.py"
    release_gate_ps1 = root / "scripts/release-gate.ps1"
    templates_dir = root / "docs/templates"

    _check_exists(checks, check_id="OAI-ART-001", path=report_md, label="OpenAI comprehensive report")
    _check_exists(checks, check_id="OAI-ART-002", path=manifest_json, label="OpenAI URL manifest")
    _check_exists(checks, check_id="OAI-ART-003", path=backlog_md, label="OpenAI adoption backlog")
    _check_exists(checks, check_id="OAI-ART-004", path=dialect_md, label="Instruction dialect standard")
    _check_exists(checks, check_id="OAI-ART-005", path=lifecycle_md, label="Model lifecycle standard")

    if manifest_json.exists():
        try:
            parsed = json.loads(_read_text(manifest_json))
            url_count = int(parsed.get("url_count", 0))
            categories = parsed.get("categories", {})
            has_required_categories = isinstance(categories, dict) and (
                "api_guides" in categories and "models" in categories and "evals" in categories
            )
            if url_count > 0 and has_required_categories:
                checks.append(
                    CheckResult(
                        id="OAI-MAN-001",
                        status="pass",
                        message="OpenAI URL manifest is populated",
                        evidence=f"url_count={url_count}",
                    )
                )
            else:
                checks.append(
                    CheckResult(
                        id="OAI-MAN-001",
                        status="fail",
                        message="OpenAI URL manifest missing required categories or URLs",
                        evidence=f"url_count={url_count}",
                    )
                )
        except json.JSONDecodeError as exc:
            checks.append(
                CheckResult(
                    id="OAI-MAN-001",
                    status="fail",
                    message="OpenAI URL manifest is not valid JSON",
                    evidence=str(exc),
                )
            )

    if backlog_md.exists():
        backlog_text = _read_text(backlog_md)
        backlog_required = ["OPENAI-001", "OPENAI-002", "OPENAI-003", "OPENAI-004", "OPENAI-005"]
        ok, missing = _contains_all(backlog_text, backlog_required)
        checks.append(
            CheckResult(
                id="OAI-BKL-001",
                status="pass" if ok else "fail",
                message="OpenAI adoption backlog includes required baseline items"
                if ok
                else "OpenAI adoption backlog missing required baseline items",
                evidence=", ".join(missing) if missing else "baseline items present",
            )
        )

    if providers_py.exists():
        providers_text = _read_text(providers_py)
        tokens = [
            "https://api.openai.com/v1/responses",
            "_build_responses_body",
            '"instructions"',
            '"reasoning"',
            '"text"',
            "json_schema",
        ]
        ok, missing = _contains_all(providers_text, tokens)
        checks.append(
            CheckResult(
                id="OAI-API-001",
                status="pass" if ok else "fail",
                message="OpenAI adapter includes Responses API and standards request-shaping hooks"
                if ok
                else "OpenAI adapter missing required standards request-shaping hooks",
                evidence=", ".join(missing) if missing else "adapter tokens found",
            )
        )

    if release_gate_ps1.exists():
        gate_text = _read_text(release_gate_ps1)
        ok, missing = _contains_all(
            gate_text,
            [
                "build-openai-alignment-manifest.py",
                "validate-openai-standards.py",
            ],
        )
        checks.append(
            CheckResult(
                id="OAI-GATE-001",
                status="pass" if ok else "warn",
                message="Release gate wires OpenAI alignment + standards validation"
                if ok
                else "Release gate missing one or more OpenAI standards checks",
                evidence=", ".join(missing) if missing else "release gate hooks present",
            )
        )

    required_templates = [
        templates_dir / "SYSTEM_INSTRUCTIONS.template.md",
        templates_dir / "WORKER_DISPATCH.template.md",
        templates_dir / "MODEL_OPTIMIZATION_RUNBOOK.template.md",
    ]
    missing_templates = [str(path) for path in required_templates if not path.exists()]
    checks.append(
        CheckResult(
            id="OAI-TPL-001",
            status="pass" if not missing_templates else "fail",
            message="OpenAI-aligned markdown templates are present"
            if not missing_templates
            else "One or more OpenAI-aligned templates are missing",
            evidence=", ".join(missing_templates) if missing_templates else "all templates present",
        )
    )

    if not args.skip_dialect_lint:
        lint_script = root / "scripts/lint-md-instruction-dialect.py"
        if lint_script.exists():
            proc = subprocess.run(
                [sys.executable, str(lint_script), str(templates_dir)],
                cwd=str(root),
                capture_output=True,
                text=True,
            )
            checks.append(
                CheckResult(
                    id="OAI-LINT-001",
                    status="pass" if proc.returncode == 0 else "fail",
                    message="Instruction dialect lint passes for templates"
                    if proc.returncode == 0
                    else "Instruction dialect lint failed for templates",
                    evidence=(proc.stdout or proc.stderr).strip()[:1200],
                )
            )
        else:
            checks.append(
                CheckResult(
                    id="OAI-LINT-001",
                    status="fail",
                    message="Instruction dialect lint script not found",
                    evidence=str(lint_script),
                )
            )

    fail_count = sum(1 for c in checks if c.status == "fail")
    warn_count = sum(1 for c in checks if c.status == "warn")
    status = "pass"
    if fail_count > 0:
        status = "fail"
    elif args.strict and warn_count > 0:
        status = "fail"

    report: dict[str, Any] = {
        "repo_root": str(root),
        "status": status,
        "fail_count": fail_count,
        "warn_count": warn_count,
        "pass_count": sum(1 for c in checks if c.status == "pass"),
        "checks": [asdict(c) for c in checks],
    }
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"OpenAI standards status: {status}")
    print(f"Checks: pass={report['pass_count']} warn={warn_count} fail={fail_count}")
    print(f"Report: {out_json}")
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())


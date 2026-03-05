from __future__ import annotations

import re
from dataclasses import dataclass


RESPONSE_SECTIONS = ("Summary", "Risks", "Action List", "Open Questions")
REQUEST_HEADERS = (
    "Objective:",
    "Inputs (exact filenames):",
    "Constraints / Invariants:",
    "Output format",
)


@dataclass
class ValidationResult:
    ok: bool
    mode: str
    issues: list[str]


def build_dispatch(objective: str, inputs: list[str], constraints: list[str], quality_bar: str = "strict") -> str:
    input_lines = "\n".join(f"- {x}" for x in inputs) if inputs else "- <input-file>"
    constraint_lines = "\n".join(f"- {x}" for x in constraints) if constraints else "- <constraint>"
    return (
        "Objective:\n"
        f"{objective.strip()}\n\n"
        "Inputs (exact filenames):\n"
        f"{input_lines}\n\n"
        "Constraints / Invariants:\n"
        f"{constraint_lines}\n"
        f"- Quality bar: {quality_bar.strip() or 'strict'}\n\n"
        "Output format (strict order):\n"
        "1) Summary\n"
        "2) Risks\n"
        "3) Action List\n"
        "4) Open Questions\n"
    )


def validate_request(text: str) -> ValidationResult:
    text = text.lstrip("\ufeff")
    issues: list[str] = []
    lowered = text.lower()
    for h in REQUEST_HEADERS:
        if h.lower() not in lowered:
            issues.append(f"missing request section: {h}")

    positions = _find_section_positions(text, RESPONSE_SECTIONS)
    issues.extend(_order_issues(positions, RESPONSE_SECTIONS, "request"))
    return ValidationResult(ok=not issues, mode="request", issues=issues)


def validate_response(text: str) -> ValidationResult:
    text = text.lstrip("\ufeff")
    positions = _find_section_positions(text, RESPONSE_SECTIONS)
    issues = _order_issues(positions, RESPONSE_SECTIONS, "response")
    return ValidationResult(ok=not issues, mode="response", issues=issues)


def _find_section_positions(text: str, names: tuple[str, ...]) -> dict[str, int]:
    out: dict[str, int] = {}
    for name in names:
        m = re.search(rf"(?im)^\s*(?:[-*]|\d+[.)])?\s*{re.escape(name)}\s*:?.*$", text)
        out[name] = m.start() if m else -1
    return out


def _order_issues(positions: dict[str, int], names: tuple[str, ...], mode: str) -> list[str]:
    issues: list[str] = []
    missing = [n for n in names if positions[n] == -1]
    if missing:
        issues.append(f"missing {mode} sections: {', '.join(missing)}")
        return issues
    ordered_values = [positions[n] for n in names]
    if ordered_values != sorted(ordered_values):
        issues.append("sections out of order; expected: Summary, Risks, Action List, Open Questions")
    return issues


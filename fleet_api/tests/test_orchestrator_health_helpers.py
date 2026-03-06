from __future__ import annotations

from datetime import datetime, timezone

from fleet_api.fleet_api.orchestrator import (
    _evaluate_pairings,
    _normalize_signal_lines,
    _summarize_worker_signals,
)


def test_normalize_signal_lines_extracts_json_message() -> None:
    raw = (
        '/tmp/openclaw/openclaw-2026-03-05.log:'
        '{"0":"{\\"subsystem\\":\\"gateway\\"}","1":"[kimi-bridge] [gateway] handshake complete",'
        '"time":"2026-03-05T23:05:39.818-05:00"}'
    )
    out = _normalize_signal_lines([raw])
    assert len(out) == 1
    assert out[0].startswith("2026-03-05T23:05:39.818-05:00")
    assert "handshake complete" in out[0]


def test_summarize_worker_signals_ignores_stale_pairing_error_before_latest_success() -> None:
    lines = [
        "2026-03-05T17:30:55.802-05:00 gateway connect failed: pairing required",
        "2026-03-05T23:05:17.839-05:00 [kimi-bridge] [gateway] handshake complete",
        "2026-03-05T23:05:17.842-05:00 [kimi-bridge] local gateway connected url=ws://10.0.0.48:18789",
    ]
    now = datetime.fromisoformat("2026-03-06T03:10:00+00:00").astimezone(timezone.utc)
    summary = _summarize_worker_signals(lines, max_age_seconds=30 * 60, now=now)

    assert summary["has_handshake"] is True
    assert summary["has_local_gateway"] is True
    assert summary["recent_handshake"] is True
    assert summary["recent_local_gateway"] is True
    assert summary["has_critical_errors"] is False


def test_evaluate_pairings_marks_missing_hosts() -> None:
    paired = [{"remoteIp": "10.0.0.28"}]
    result = _evaluate_pairings(paired, expected_hosts=["10.0.0.28", "10.0.0.27"])
    assert result["all_paired"] is False
    assert result["missing_hosts"] == ["10.0.0.27"]

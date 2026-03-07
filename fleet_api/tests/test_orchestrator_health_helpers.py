from __future__ import annotations

from datetime import datetime, timezone

from fleet_api.fleet_api.orchestrator import (
    _evaluate_pairings,
    _order_gateway_candidates,
    _order_roles_for_canary,
    _line_timestamp,
    _normalize_signal_lines,
    _summarize_worker_signals,
)


def test_normalize_signal_lines_extracts_json_message() -> None:
    raw = (
        '/tmp/ordlctl/ordlctl-2026-03-05.log:'
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
        "2026-03-05T23:05:17.842-05:00 [kimi-bridge] local gateway connected url=ws://198.51.100.48:18789",
    ]
    now = datetime.fromisoformat("2026-03-06T03:10:00+00:00").astimezone(timezone.utc)
    summary = _summarize_worker_signals(lines, max_age_seconds=30 * 60, now=now)

    assert summary["has_handshake"] is True
    assert summary["has_local_gateway"] is True
    assert summary["recent_handshake"] is True
    assert summary["recent_local_gateway"] is True
    assert summary["has_critical_errors"] is False


def test_evaluate_pairings_marks_missing_hosts() -> None:
    paired = [{"remoteIp": "198.51.100.28"}]
    result = _evaluate_pairings(paired, expected_hosts=["198.51.100.28", "198.51.100.27"])
    assert result["all_paired"] is False
    assert result["missing_hosts"] == ["198.51.100.27"]


def test_line_timestamp_parses_prefixed_worker_log_line() -> None:
    line = "/home/winsock/ordlctl-worker.log:2026-03-06T09:07:40.190Z [gateway] [kimi-bridge] [gateway] handshake complete"
    ts = _line_timestamp(line)
    assert ts is not None
    assert ts.isoformat().startswith("2026-03-06T09:07:40.190")


def test_summarize_worker_signals_treats_auth_failed_as_warning_only() -> None:
    now = datetime.fromisoformat("2026-03-06T09:09:00+00:00").astimezone(timezone.utc)
    lines = [
        "2026-03-06T09:08:05.271Z [gateway] [kimi-bridge] [gateway] handshake complete",
        "2026-03-06T09:08:05.272Z [gateway] [kimi-bridge] local gateway connected url=ws://198.51.100.48:18789",
        "2026-03-06T09:08:06.432Z [gateway] [kimi-bridge] [bridge-acp] auth failed (http 401), will not retry",
    ]
    summary = _summarize_worker_signals(lines, max_age_seconds=5 * 60, now=now)

    assert summary["has_handshake"] is True
    assert summary["has_local_gateway"] is True
    assert summary["recent_handshake"] is True
    assert summary["recent_local_gateway"] is True
    assert summary["has_critical_errors"] is False
    assert summary["has_warning_errors"] is True


def test_order_gateway_candidates_prioritizes_last_success() -> None:
    ordered = _order_gateway_candidates(
        "ws://198.51.100.48:18789",
        ["wss://fleet.example.org", "ws://198.51.100.48:18789"],
    )
    assert ordered[0] == "ws://198.51.100.48:18789"
    assert ordered[1] == "wss://fleet.example.org"


def test_order_roles_for_canary() -> None:
    roles = ["worker-build-laptop", "worker-batch-server"]
    ordered = _order_roles_for_canary(roles, "worker-batch-server")
    assert ordered == ["worker-batch-server", "worker-build-laptop"]

"""Test cho phần dựng dashboard runtime (`scripts/dashboard.py`).

Trọng tâm là panel `errors`: trước đây khi không có `request_failed` trong time
range thì panel không có series nào và gắn nhầm log `request_received` vào
`<pre>`, nhìn như panel bị lỗi. Các test dưới đây khóa lại hành vi mới.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts.dashboard import (
    _threshold_state,
    compute_panel,
    load_events,
    render_panel_html,
    render_text,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _panels() -> dict[str, dict[str, Any]]:
    payload = yaml.safe_load((REPO_ROOT / "config" / "dashboard.yaml").read_text(encoding="utf-8"))
    return {panel["id"]: panel for panel in payload["dashboard"]["panels"]}


def _received(ts: str, correlation_id: str = "req-00000001") -> dict[str, Any]:
    return {
        "service": "api",
        "event": "request_received",
        "ts": ts,
        "level": "info",
        "correlation_id": correlation_id,
        "user_id_hash": "abc123abc123",
        "session_id": "s01",
        "feature": "qa",
        "model": "gpt-4o-mini",
        "env": "dev",
    }


def _sent(ts: str, latency_ms: int = 200, tool_success: bool = True) -> dict[str, Any]:
    return {
        "service": "api",
        "event": "response_sent",
        "ts": ts,
        "level": "info",
        "correlation_id": "req-00000001",
        "latency_ms": latency_ms,
        "ttft_ms": 50,
        "tokens_in": 30,
        "tokens_out": 100,
        "cost_usd": 0.001,
        "quality_score": 0.9,
        "tool_name": "retrieval",
        "tool_success": tool_success,
        "env": "dev",
        "model": "gpt-4o-mini",
        "feature": "qa",
        "session_id": "s01",
        "user_id_hash": "abc123abc123",
    }


def _failed(ts: str, error_type: str = "RuntimeError") -> dict[str, Any]:
    return {
        "service": "api",
        "event": "request_failed",
        "ts": ts,
        "level": "error",
        "correlation_id": "req-00000002",
        "error_type": error_type,
        "tool_name": "retrieval",
        "tool_success": False,
        "env": "dev",
        "model": "gpt-4o-mini",
        "feature": "qa",
        "session_id": "s01",
        "user_id_hash": "abc123abc123",
    }


@pytest.fixture()
def errors_panel() -> dict[str, Any]:
    return _panels()["errors"]


def test_errors_panel_without_failures_is_explicit_not_blank(errors_panel: dict[str, Any]) -> None:
    events = [_received("2026-09-29T13:00:00Z"), _sent("2026-09-29T13:00:01Z")]

    rendered = compute_panel(errors_panel, events)

    stats = dict(rendered["stats"])
    assert stats["Số request_failed"] == "0"
    assert stats["Error rate"] == "0.0 %"
    assert stats["Retrieval success"] == "100.0 %"
    # Phải có series (kể cả phút không lỗi) để panel không trông như hỏng.
    series = dict(rendered["series"])
    assert series["Error theo phút"] == [("13:00", 0.0)]
    assert series["Error breakdown"] == [("(không có lỗi trong time range)", 0.0)]
    # Không được gắn log request_received (dòng không phải lỗi) vào panel lỗi.
    assert rendered["sample"] is None
    assert rendered["note"] and "Không có request_failed" in rendered["note"]


def test_errors_panel_with_failures_reports_breakdown_and_retrieval_rate(
    errors_panel: dict[str, Any],
) -> None:
    events = [
        _received("2026-09-29T13:00:00Z"),
        _sent("2026-09-29T13:00:01Z"),
        _received("2026-09-29T13:01:00Z", "req-00000002"),
        _failed("2026-09-29T13:01:01Z"),
    ]

    rendered = compute_panel(errors_panel, events)

    stats = dict(rendered["stats"])
    assert stats["Số request_failed"] == "1"
    assert stats["Error rate"] == "50.0 %"
    assert stats["Retrieval success"] == "50.0 %"
    assert dict(rendered["series"])["Error breakdown"] == [("RuntimeError", 1.0)]
    assert rendered["sample"] is not None
    assert rendered["sample"]["event"] == "request_failed"
    assert rendered["note"] is None


def test_errors_panel_honours_time_range_window(tmp_path: Path) -> None:
    """`request_failed` ngoài 60 phút cuối không được tính vào panel."""
    log = tmp_path / "logs.jsonl"
    log.write_text(
        "\n".join(
            [
                '{"event": "request_failed", "ts": "2026-09-29T09:00:00Z",'
                ' "error_type": "AttributeError", "tool_success": false}',
                '{"event": "request_received", "ts": "2026-09-29T14:00:00Z",'
                ' "correlation_id": "req-1"}',
                '{"event": "response_sent", "ts": "2026-09-29T14:00:01Z",'
                ' "latency_ms": 200, "tool_success": true}',
            ]
        ),
        encoding="utf-8",
    )

    events = load_events(log, 60)

    assert len(events) == 2
    rendered = compute_panel(_panels()["errors"], events)
    assert dict(rendered["stats"])["Số request_failed"] == "0"


def test_threshold_state_reports_ok_and_breach() -> None:
    latency = _panels()["latency"]
    events = [_sent("2026-09-29T13:00:00Z", latency_ms=120) for _ in range(5)]

    ok_breached, ok_text = _threshold_state(latency, compute_panel(latency, events)["metrics"])
    assert ok_breached is False
    assert "OK" in ok_text and "p95=120 ms" in ok_text

    slow = [_sent("2026-09-29T13:00:00Z", latency_ms=5000) for _ in range(5)]
    breached, breach_text = _threshold_state(latency, compute_panel(latency, slow)["metrics"])
    assert breached is True
    assert "BREACH" in breach_text


def test_render_html_marks_ok_threshold_and_shows_note() -> None:
    events = [_received("2026-09-29T13:00:00Z"), _sent("2026-09-29T13:00:01Z")]

    markup = render_panel_html(_panels()["errors"], events)

    assert 'class="thr ok"' in markup
    assert "OK" in markup
    assert "Không có request_failed" in markup
    # Không được nhúng log của request thành công vào panel lỗi.
    assert "<pre>" not in markup


def test_render_text_includes_threshold_state() -> None:
    payload = yaml.safe_load((REPO_ROOT / "config" / "dashboard.yaml").read_text(encoding="utf-8"))
    events = [_received("2026-09-29T13:00:00Z"), _sent("2026-09-29T13:00:01Z")]

    text = render_text(payload["dashboard"], payload["dashboard"]["panels"], events)

    assert "[errors] Error rate and retrieval success" in text
    assert "Error rate: 0.0 %" in text
    assert "OK — Threshold: error_rate_pct lte 2 percent; measured error_rate_pct=0 percent" in text
    assert "Error breakdown: (không có lỗi trong time range)=0" in text
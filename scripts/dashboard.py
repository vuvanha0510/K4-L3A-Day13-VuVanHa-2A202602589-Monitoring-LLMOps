"""Dựng dashboard 6 panel cho CP2 từ `data/logs.jsonl` + `config/dashboard.yaml`.

Dashboard chạy hoàn toàn bằng thư viện chuẩn của Python (không thêm
dependency mới): sinh một file HTML tĩnh mở được bằng trình duyệt, có đủ
time range, đơn vị và threshold/SLO line cho từng panel. Đây là runtime
evidence cho `11-dashboard-overview`.

Cách dùng:

```bash
python scripts/dashboard.py                            # in tóm tắt ở terminal
python scripts/dashboard.py --html out/dashboard.html  # xuất HTML
python scripts/dashboard.py --save-text out/dashboard.txt
```

Script chỉ đọc log; không gọi API và không sửa `config/dashboard.yaml`.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio
from scripts.validate_dashboard import (
    REQUIRED_PANEL_IDS,
    DashboardConfigError,
    load_dashboard_config,
)


def percentile(values: list[float], p: float) -> float:
    """Percentile kiểu nearest-rank, khớp với app/metrics.py để số liệu nhất quán."""
    if not values:
        return 0.0
    items = sorted(values)
    idx = max(0, min(len(items) - 1, math.ceil(p / 100 * len(items)) - 1))
    return float(items[idx])


def _mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def _parse_ts(value: Any) -> datetime:
    if not isinstance(value, str):
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)


def load_events(path: Path, time_range_minutes: int) -> list[dict[str, Any]]:
    """Đọc logs.jsonl và chỉ giữ các bản ghi trong time range của dashboard."""
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy log: {path}")

    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            events.append(record)

    if not events:
        return []

    latest = max(_parse_ts(event.get("ts")) for event in events)
    cutoff = latest - timedelta(minutes=time_range_minutes)
    return [event for event in events if _parse_ts(event.get("ts")) >= cutoff]


def _bucket_count(events: list[dict[str, Any]]) -> list[tuple[str, float]]:
    buckets: Counter[str] = Counter(_parse_ts(e.get("ts")).strftime("%H:%M") for e in events)
    return sorted(buckets.items())


def _bucket_sum(events: list[dict[str, Any]], field: str) -> list[tuple[str, float]]:
    buckets: dict[str, float] = defaultdict(float)
    for event in events:
        minute = _parse_ts(event.get("ts")).strftime("%H:%M")
        value = event.get(field)
        if isinstance(value, (int, float)):
            buckets[minute] += float(value)
    return sorted(buckets.items())


def _series_from(pairs: list[tuple[str, float]]) -> list[tuple[str, float]]:
    return [(name, value) for name, value in pairs if value]


def _series_keep_zero(pairs: list[tuple[str, float]]) -> list[tuple[str, float]]:
    """Giữ cả giá trị 0.

    Panel `errors` cần hiện cả những phút không có lỗi, nếu không sẽ không có
    dòng series nào và panel trông như bị lỗi khi hệ thống đang ổn.
    """
    return list(pairs)


def _fmt(value: float) -> str:
    return str(int(value)) if value == int(value) else f"{value:.4g}"


def _threshold_state(panel: dict[str, Any], metrics: dict[str, float]) -> tuple[bool | None, str]:
    """Đánh giá threshold của panel: (có vi phạm hay không, chuỗi hiển thị).

    Trả `None` khi không xác định được giá trị metric (thiếu dữ liệu) để phân
    biệt "đạt" với "không đo được" trong ảnh evidence.
    """
    threshold = panel.get("threshold", {})
    aggregation = str(threshold.get("aggregation"))
    operator = str(threshold.get("operator"))
    limit = threshold.get("value")
    actual = metrics.get(aggregation)

    head = f"Threshold: {aggregation} {operator} {limit} {panel.get('unit')}"
    if actual is None or not isinstance(limit, (int, float)):
        return None, f"⚠ {head} (chưa đủ dữ liệu để đánh giá)"

    breached = actual > limit if operator == "lte" else actual < limit
    mark = "⚠ BREACH" if breached else "✅ OK"
    return breached, f"{mark} — {head}; measured {aggregation}={_fmt(float(actual))} {panel.get('unit')}"


def compute_panel(panel: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    """Tính số liệu cho một panel từ `events`, bám theo fields trong contract."""
    panel_id = panel["id"]
    by_event: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        by_event[str(event.get("event"))].append(event)

    if panel_id == "latency":
        responses = by_event.get("response_sent", [])
        latency = [float(e["latency_ms"]) for e in responses if "latency_ms" in e]
        ttft = [float(e["ttft_ms"]) for e in responses if "ttft_ms" in e]
        return {
            "stats": [
                ("P50 latency", f"{percentile(latency, 50):.0f} ms"),
                ("P95 latency", f"{percentile(latency, 95):.0f} ms"),
                ("P99 latency", f"{percentile(latency, 99):.0f} ms"),
                ("TTFT P95", f"{percentile(ttft, 95):.0f} ms"),
            ],
            "series": [("Latency theo phút", _series_from(_bucket_sum(responses, "latency_ms")))],
            "sample": responses[-1] if responses else None,
            "metrics": {"p95": percentile(latency, 95), "p50": percentile(latency, 50)},
        }

    if panel_id == "traffic":
        received = by_event.get("request_received", [])
        counts = _bucket_count(received)
        rate = round(len(received) / 60.0, 3) if received else 0.0
        return {
            "stats": [
                ("Tổng request", f"{len(received)}"),
                ("Request/phút (TB)", f"{rate}"),
                ("Số phút có traffic", f"{len(counts)}"),
            ],
            "series": [("Request/phút", counts)],
            "sample": received[-1] if received else None,
            "metrics": {"rate_per_minute": rate},
        }

    if panel_id == "errors":
        received = by_event.get("request_received", [])
        failed = by_event.get("request_failed", [])
        error_rate = round(100.0 * len(failed) / len(received), 3) if received else 0.0
        by_error = Counter(str(e.get("error_type")) for e in failed if e.get("error_type"))
        tool_events = [e for e in events if e.get("tool_success") is not None]
        tool_ok = [e for e in tool_events if e.get("tool_success") is True]
        retrieval = round(100.0 * len(tool_ok) / len(tool_events), 2) if tool_events else 0.0
        failed_series = _bucket_count(failed)
        # Giữ cả phút không có lỗi để panel luôn có series, kể cả khi hệ thống ổn.
        if failed_series:
            error_minutes = failed_series
        elif received:
            error_minutes = [
                (minute, 0.0) for minute in sorted({_parse_ts(e.get("ts")).strftime("%H:%M") for e in received})
            ]
        else:
            error_minutes = []
        breakdown = (
            [(name, float(count)) for name, count in sorted(by_error.items())]
            if by_error
            else [("(không có lỗi trong time range)", 0.0)]
        )
        return {
            "stats": [
                ("Error rate", f"{error_rate} %"),
                ("Số request_received", f"{len(received)}"),
                ("Số request_failed", f"{len(failed)}"),
                ("Số lần gọi tool", f"{len(tool_events)}"),
                ("Retrieval success", f"{retrieval} %"),
            ],
            "series": [
                ("Error theo phút", _series_keep_zero(error_minutes)),
                ("Error breakdown", breakdown),
            ],
            # Không fallback sang request_received: panel lỗi phải nói rõ là không
            # có lỗi, không gắn nhầm log của request thành công vào panel errors.
            "sample": failed[-1] if failed else None,
            "note": (
                None
                if failed
                else (
                    f"Không có request_failed trong {len(received)} request của time range "
                    "→ error rate 0%, hệ thống đang bình thường."
                )
            ),
            "metrics": {"error_rate_pct": error_rate, "tool_success_rate_pct": retrieval},
        }

    if panel_id == "cost":
        responses = by_event.get("response_sent", [])
        costs = [float(e["cost_usd"]) for e in responses if "cost_usd" in e]
        return {
            "stats": [
                ("Tổng cost", f"{sum(costs):.4f} USD"),
                ("Cost TB/request", f"{_mean(costs):.6f} USD"),
                ("Số request có cost", f"{len(costs)}"),
            ],
            "series": [("Cost theo phút (USD)", _series_from(_bucket_sum(responses, "cost_usd")))],
            "sample": responses[-1] if responses else None,
            "metrics": {"total": round(sum(costs), 6)},
        }

    if panel_id == "tokens":
        responses = by_event.get("response_sent", [])
        tokens_in = [int(e["tokens_in"]) for e in responses if "tokens_in" in e]
        tokens_out = [int(e["tokens_out"]) for e in responses if "tokens_out" in e]
        return {
            "stats": [
                ("Tổng tokens_in", f"{sum(tokens_in)}"),
                ("Tổng tokens_out", f"{sum(tokens_out)}"),
                ("Tổng tất cả", f"{sum(tokens_in) + sum(tokens_out)}"),
            ],
            "series": [
                ("tokens_in theo phút", _series_from(_bucket_sum(responses, "tokens_in"))),
                ("tokens_out theo phút", _series_from(_bucket_sum(responses, "tokens_out"))),
            ],
            "sample": responses[-1] if responses else None,
            "metrics": {"sum_by_field": sum(tokens_in) + sum(tokens_out)},
        }

    responses = by_event.get("response_sent", [])
    quality = [float(e["quality_score"]) for e in responses if "quality_score" in e]
    return {
        "stats": [
            ("Quality proxy TB", f"{_mean(quality)}"),
            ("Số request có điểm", f"{len(quality)}"),
            ("Điểm thấp nhất", f"{min(quality):.2f}" if quality else "0"),
        ],
        "series": [("Quality theo phút", _series_from(_bucket_sum(responses, "quality_score")))],
        "sample": responses[-1] if responses else None,
        "metrics": {"mean": _mean(quality)},
    }


STYLE = (
    "body{font-family:Segoe UI,Arial,sans-serif;background:#0f172a;color:#e2e8f0;margin:24px}"
    "h1{font-size:20px}h2{font-size:15px;margin:0 0 6px}"
    ".meta{color:#94a3b8;font-size:12px;margin-bottom:18px}"
    ".grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(430px,1fr));gap:16px}"
    ".panel{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:14px}"
    ".unit{color:#94a3b8;font-size:11px;margin-bottom:8px}"
    "table.stats{width:100%;border-collapse:collapse;font-size:13px}"
    "table.stats td{padding:3px 0;border-bottom:1px solid #263449}"
    "table.stats td:last-child{text-align:right;font-weight:600}"
    ".thr{margin-top:8px;font-size:11px;color:#f59e0b}"
    ".thr.ok{color:#4ade80}"
    ".note{margin-top:6px;font-size:11px;color:#94a3b8}"
    ".series{margin-top:6px;font-size:11px;color:#7dd3fc;word-break:break-all}"
    "pre{background:#0b1220;padding:8px;font-size:10px;overflow:auto;max-height:130px;color:#94a3b8}"
)


def render_panel_html(panel: dict[str, Any], events: list[dict[str, Any]]) -> str:
    """Một panel: tên, đơn vị, số liệu, threshold line và series theo phút."""
    rendered = compute_panel(panel, events)
    breached, threshold_text = _threshold_state(panel, rendered.get("metrics", {}))

    rows = "".join(
        f"<tr><td>{html.escape(label)}</td><td>{html.escape(value)}</td></tr>"
        for label, value in rendered["stats"]
    )
    series = []
    for series_title, points in rendered["series"]:
        if points:
            body = ", ".join(f"{name}={_fmt(value)}" for name, value in points[-12:])
            series.append(
                f'<div class="series"><b>{html.escape(series_title)}:</b> {html.escape(body)}</div>'
            )
    note = ""
    if rendered.get("note"):
        note = f'<div class="note">ℹ️ {html.escape(str(rendered["note"]))}</div>'
    sample = ""
    if rendered.get("sample"):
        sample = html.escape(json.dumps(rendered["sample"], ensure_ascii=False))
    thr_class = "thr" if breached is not False else "thr ok"
    meta = (
        f'unit: {html.escape(str(panel.get("unit")))} | '
        f"events: {html.escape(', '.join(panel.get('events', [])))} | "
        f"fields: {html.escape(', '.join(panel.get('fields', [])))}"
    )
    return (
        '<div class="panel">'
        f"<h2>{html.escape(str(panel.get('id')))} &mdash; {html.escape(str(panel.get('title')))}</h2>"
        f'<div class="unit">{meta}</div>'
        f'<table class="stats">{rows}</table>'
        f'<div class="{thr_class}">{html.escape(threshold_text)}</div>'
        + "".join(series)
        + note
        + (f"<pre>{sample}</pre>" if sample else "")
        + "</div>"
    )


def render_html(
    dashboard_cfg: dict[str, Any],
    panels: list[dict[str, Any]],
    events: list[dict[str, Any]],
    path: Path,
) -> None:
    """Sinh dashboard HTML tĩnh: mỗi panel có time range, đơn vị và threshold line."""
    title = str(dashboard_cfg.get("title", "Dashboard"))
    parts = [
        "<!doctype html>",
        '<html lang="vi"><head><meta charset="utf-8">',
        f"<title>{html.escape(title)}</title>",
        f"<style>{STYLE}</style></head><body>",
        f"<h1>{html.escape(title)}</h1>",
        f'<div class="meta">Time range: {dashboard_cfg.get("time_range_minutes")} phút cuối'
        f' &nbsp;|&nbsp; Refresh: {dashboard_cfg.get("refresh_seconds")}s'
        " &nbsp;|&nbsp; Source: data/logs.jsonl"
        f" &nbsp;|&nbsp; Contract: config/dashboard.yaml ({len(panels)}/6 panel)"
        f" &nbsp;|&nbsp; Records in range: {len(events)}</div>",
        '<div class="grid">',
    ]
    parts.extend(render_panel_html(panel, events) for panel in panels)
    parts.append("</div></body></html>")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts), encoding="utf-8")


def render_text(
    dashboard_cfg: dict[str, Any],
    panels: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> str:
    """Bản text để lưu làm evidence kèm ảnh dashboard."""
    lines = [
        "=" * 78,
        f"DASHBOARD RUNTIME - {dashboard_cfg.get('title')}",
        f"Time range: {dashboard_cfg.get('time_range_minutes')} phút cuối | "
        f"Refresh: {dashboard_cfg.get('refresh_seconds')}s | Source: data/logs.jsonl",
        f"Panel: {len(panels)}/6 | Bản ghi trong time range: {len(events)}",
        "=" * 78,
    ]
    for panel in panels:
        rendered = compute_panel(panel, events)
        _, threshold_text = _threshold_state(panel, rendered.get("metrics", {}))
        lines.append("")
        lines.append(f"[{panel['id']}] {panel['title']}")
        lines.append(f"  unit={panel['unit']}  events={panel['events']}  fields={panel['fields']}")
        for label, value in rendered["stats"]:
            lines.append(f"  - {label}: {value}")
        lines.append(f"  {threshold_text}")
        if rendered.get("note"):
            lines.append(f"  i {rendered['note']}")
        for series_title, points in rendered["series"]:
            if points:
                body = ", ".join(f"{name}={_fmt(value)}" for name, value in points[-8:])
                lines.append(f"  ~ {series_title}: {body}")
    return "\n".join(lines)


def main() -> int:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Dựng dashboard 6 panel từ data/logs.jsonl")
    parser.add_argument(
        "--config",
        type=Path,
        default=REPO_ROOT / "config" / "dashboard.yaml",
        help="Đường dẫn dashboard contract",
    )
    parser.add_argument(
        "--logs",
        type=Path,
        default=REPO_ROOT / "data" / "logs.jsonl",
        help="Đường dẫn structured log",
    )
    parser.add_argument(
        "--html",
        type=Path,
        default=REPO_ROOT / "out" / "dashboard.html",
        help="Nơi xuất dashboard HTML",
    )
    parser.add_argument(
        "--no-html",
        action="store_true",
        help="Chỉ in bản text, không xuất file HTML",
    )
    parser.add_argument(
        "--save-text",
        type=Path,
        default=None,
        help="Lưu bản text dashboard vào file (dùng làm evidence)",
    )
    args = parser.parse_args()

    try:
        payload = load_dashboard_config(args.config)
    except DashboardConfigError as exc:
        print(f"KHÔNG HỢP LỆ: {exc}")
        return 1

    dashboard_cfg = payload["dashboard"]
    panels = dashboard_cfg["panels"]
    found_ids = {panel["id"] for panel in panels}
    if found_ids != REQUIRED_PANEL_IDS:
        print(f"KHÔNG HỢP LỆ: thiếu panel {sorted(REQUIRED_PANEL_IDS - found_ids)}")
        return 1

    try:
        events = load_events(args.logs, int(dashboard_cfg["time_range_minutes"]))
    except FileNotFoundError as exc:
        print(f"KHÔNG ĐỦ DỮ LIỆU: {exc}")
        return 1

    if not events:
        print("KHÔNG ĐỦ DỮ LIỆU: không có bản ghi nào trong time range. Hãy chạy load test trước.")
        return 1

    text = render_text(dashboard_cfg, panels, events)
    print(text)

    if args.save_text:
        args.save_text.parent.mkdir(parents=True, exist_ok=True)
        args.save_text.write_text(text, encoding="utf-8")
        print(f"\nĐã lưu bản text: {args.save_text}")

    if not args.no_html:
        render_html(dashboard_cfg, panels, events, args.html)
        print(f"Đã xuất dashboard HTML: {args.html}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

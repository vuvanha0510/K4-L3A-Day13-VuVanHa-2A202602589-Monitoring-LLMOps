# Alert và Runbook — K4-L3A Day 13

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

Nguồn dữ liệu chung của cả ba alert là `data/logs.jsonl` (đúng nguồn của dashboard trong `config/dashboard.yaml`), nên có thể tái hiện toàn bộ bằng `python scripts/load_test.py` rồi đọc log.

## Alert 1

- **Tên:** `high_p95_latency`
- **Severity:** critical
- **Duration:** 5m (duy trì liên tục 3 cửa sổ đánh giá)
- **Kênh thông báo:** Slack — `#k4-l3a-alerts-latency`
- **SLI/SLO liên quan:** `fast_successful_requests` — P95 latency ≤ 3000ms (`config/slo.yaml`)
- **Điều kiện và thời gian duy trì:** `percentile(latency_ms, 95)` của event `response_sent` > 3000 trong 5 phút liên tục
- **Baseline tham chiếu:** P50 = 156ms, P95 = 1202ms, P99 = 1725ms, TTFT P95 = 50ms
- **Ảnh hưởng tới người dùng:** Người dùng chờ >3s mới có câu trả lời; ở mức này RAG thường chiếm phần lớn thời gian.
- **Ba bước kiểm tra đầu tiên:**
  1. Mở dashboard panel `latency`, xác nhận P95 tăng và xác định khoảng thời gian bắt đầu.
  2. Lọc `data/logs.jsonl` lấy vài `correlation_id` có `latency_ms > 3000`.
  3. Mở trace cùng `correlation_id` trên Langfuse, so sánh span `rag-retrieve` với `llm-generate` để biết chậm ở bước nào.
- **Mitigation tạm thời:**
  - Tắt nguồn chậm: `python scripts/inject_incident.py --scenario rag_slow --disable`.
  - Giảm số doc đưa vào prompt (rút ngắn `Docs={{docs}}`).
  - Nếu độ trễ do prompt dài, rollback label `production` về version 1.
- **Owner:** Vũ Văn Hà (2A202602589)

## Alert 2

- **Tên:** `elevated_error_rate`
- **Severity:** critical
- **Duration:** 3m (duy trì liên tục 2 cửa sổ)
- **Kênh thông báo:** Slack — `#k4-l3a-alerts-errors`
- **SLI/SLO liên quan:** `fast_successful_requests` — error budget 0.5%, guardrail `error_rate_pct_max: 2`
- **Điều kiện và thời gian duy trì:** `count(event == "request_failed") / count(event == "request_received") * 100 > 2` trong 3 phút
- **Baseline tham chiếu:** Error rate baseline = 9.09%, do 10 lỗi `AttributeError` khi code cũ gọi `update_current_observation` (API không tồn tại trong Langfuse SDK v4). Đã sửa tại `app/tracing.py` và `app/agent.py`; sau khi sửa kỳ vọng < 2%.
- **Ảnh hưởng tới người dùng:** Request thất bại hoàn toàn — người dùng không nhận được câu trả lời nào.
- **Ba bước kiểm tra đầu tiên:**
  1. Panel `errors`: xem `count_by(error_type)` để biết nhóm lỗi chiếm đa số.
  2. Lọc `event == "request_failed"` trong `data/logs.jsonl`, đọc `payload.detail` và `correlation_id`.
  3. Mở trace có cùng `correlation_id`, kiểm tra span nào `level=ERROR`.
- **Mitigation tạm thời:**
  - Tắt feature lỗi qua incident switch.
  - Rollback deploy gần nhất nếu lỗi do code.
  - Bật lại Langfuse keys nếu lỗi là `Unauthorized` (telemetry không được làm sập request).
- **Owner:** Vũ Văn Hà (2A202602589)

## Alert 3

- **Tên:** `retrieval_success_drop`
- **Severity:** warning
- **Duration:** 5m (duy trì liên tục 3 cửa sổ)
- **Kênh thông báo:** Slack — `#k4-l3a-alerts-rag`
- **SLI/SLO liên quan:** Guardrail `retrieval_success_rate_pct_min: 90`
- **Điều kiện và thời gian duy trì:** `count(tool_success == true) / count(tool_success != null) * 100 < 90` trong 5 phút
- **Baseline tham chiếu:** Retrieval success baseline = 100%
- **Ảnh hưởng tới người dùng:** Câu trả lời mất ngữ cảnh, chất lượng giảm dù request vẫn trả về 200 — người dùng khó nhận ra ngay.
- **Ba bước kiểm tra đầu tiên:**
  1. Panel `errors`: xác nhận `tool_success_rate_pct` giảm trong khoảng thời gian nào.
  2. Lọc log có `tool_name == "retrieval"` và `tool_success == false`, lấy `correlation_id`.
  3. Mở trace, xem span `rag-retrieve` có `level=ERROR` và `status_message` là gì.
- **Mitigation tạm thời:**
  - Tắt nguồn lỗi: `python scripts/inject_incident.py --scenario tool_fail --disable`.
  - Nếu do prompt version mới, rollback `production` về version 1.
  - Giảm traffic vào feature bị ảnh hưởng.
- **Owner:** Vũ Văn Hà (2A202602589)

## Cách kiểm chứng cả ba alert

```bash
# 1. Tạo dữ liệu baseline
python scripts/load_test.py --concurrency 5

# 2. Bật từng triệu chứng rồi chạy lại để thấy metric dịch chuyển đúng hướng
python scripts/inject_incident.py --scenario rag_slow
python scripts/inject_incident.py --scenario tool_fail
python scripts/load_test.py --concurrency 5

# 3. Tắt lại sau khi chụp evidence
python scripts/inject_incident.py --scenario rag_slow --disable
python scripts/inject_incident.py --scenario tool_fail --disable
```

Kết quả mong đợi: `rag_slow` làm P95 latency vượt 3000ms (Alert 1); `tool_fail` làm error rate vượt 2% (Alert 2) và đồng thời kéo retrieval success xuống dưới 90% (Alert 3).

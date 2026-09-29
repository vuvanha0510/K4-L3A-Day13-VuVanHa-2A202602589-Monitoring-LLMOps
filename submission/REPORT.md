# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Vũ Văn Hà
- **MSSV:** 2A202602589
- **Lớp:** K4-L3A
- **Repository URL:**https://github.com/vuvanha0510/K4-L3A-Day13-VuVanHa-2A202602589-Monitoring-LLMOps.git
- **Commit SHA cuối:** `107f9109b6d52126eb17293fb9e1b4ac84b44914` (điền lại sau khi commit evidence CP3)
- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1` (cohort K4, `incident: rag_slow`, `seed: 1311`, `affected_feature: monitoring`, `latency_threshold_ms: 2000`) — file do Lab Coach gửi riêng, nằm ở `config/challenge.json` và được `.gitignore` (không commit/push).
- **Tên project Langfuse cá nhân:** `day13-k4-l3a-2A202602589`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.txt` |
| Log validator | `evidence/02-log-validator.txt` |
| Dashboard validator | `evidence/03-dashboard-validator.txt` |
| Structured log | `evidence/04-structured-log.png` |
| PII redaction | `evidence/05-pii-redaction.png` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08-trace-metadata.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt rollback | `evidence/10-prompt-rollback.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

Ghi chú về hình thức evidence:
- `01`–`03` là output của tests/validators nên lưu dạng **output text `.txt`**, được phép theo `docs/SUBMISSION.md` ("*Test/validator có thể lưu dạng ảnh `.png` hoặc output text `.txt`*").
- `04`–`14` là **ảnh chụp màn hình** lấy từ terminal, trình duyệt và project Langfuse cá nhân `day13-k4-l3a-2A202602589`.
- Thư mục `evidence/raw/` chứa **dữ liệu gốc đính kèm** (output text và dashboard HTML) để giảng viên kiểm chứng lại: mỗi ảnh đều có file text tương ứng ghi rõ lệnh đã chạy, ID và giá trị thật. Danh sách: `evidence/raw/README.md`.
- Hướng dẫn chụp từng ảnh kèm giá trị phải đối chiếu: `evidence/CAPTURE-GUIDE.md`.

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | Chưa đạt (repo starter còn TODO) | **100/100** — 371 records, 0 thiếu field, 0 thiếu enrichment, 183 correlation ID, **0 PII leak** | Vượt ngưỡng 80/100 của CP1 |
| `validate_dashboard.py` | Chưa đạt | **HỢP LỆ: 6/6 panel** | Đủ 6 panel theo `config/dashboard.yaml` |
| `pytest` | — | **28 passed** (4.36s) | Chạy trên commit cuối |
| Số traces hợp lệ | 0 (chưa có Langfuse) | **26 trace** có `prompt_version` từ Langfuse (v1/baseline: 5, v2/candidate: 21), tổng **30 trace** `lab-agent-run` trong 48h | Vượt yêu cầu ≥10 trace tự tạo; không dùng trace của người khác |
| Số PII leak | — | **0** (email, điện thoại VN, CCCD, thẻ, passport, địa chỉ) | `user_id_hash` SHA-256 12 ký tự |
| Latency P95 / TTFT P95 | P95 **673 ms** / TTFT P95 **50 ms** | Bình thường **151–158 ms**; khi sự cố **P95 2663 ms** / TTFT P95 **50 ms** | TTFT P95 bất biến là dấu hiệu thời gian mất ở RAG chứ không ở LLM |
| Retrieval success rate | 100% | **100%** — `tool_success=true` ở **mọi** request trong cửa sổ sự cố CP3 (error rate 0%) | Xem ghi chú bên dưới về các lần chạy `tool_fail` để dựng evidence |

> **Ghi chú về `request_failed` trong `data/logs.jsonl`:** file log hiện có 20 dòng `request_failed`, và đó là **có chủ đích**, không phải lỗi tồn đọng:
> - **10 dòng `error_type=AttributeError`** (lúc 09:01) — ký vọng của bug `update_current_observation` đã sửa ở mục 8; tôi giữ lại để `slo.yaml` và `docs/alerts.md` còn baseline 9.09% làm căn cứ.
> - **10 dòng `error_type=RuntimeError`** (`Vector store timeout`) — sinh ra khi tôi cố tình bật `inject_incident.py --scenario tool_fail` để **dựng evidence 11**: nếu không có lỗi thật, panel `errors` chỉ hiện `Error rate 0%` và không chứng minh được việc đọc đúng `error_type` / `tool_success`. Đây cũng chính là cách tôi kiểm chứng Alert 2 và Alert 3.
>
> **Trong đúng cửa sổ sự cố CP3** (5 request lúc `13:57:27Z → 13:57:37Z`) thì **không có** `request_failed` nào và `tool_success=true` ở cả 5 — đây mới là số liệu dùng để kết luận "không phải lỗi" ở mục 7.

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** `CorrelationIdMiddleware` trong `app/middleware.py` chạy `clear_contextvars()` trước mỗi request để không rò dữ liệu giữa các request, sau đó lấy header `x-request-id` nếu client gửi, còn lại tự sinh theo format `req-<8-hex>` bằng `uuid.uuid4().hex[:8]`. ID được `bind_contextvars(correlation_id=...)`, lưu vào `request.state.correlation_id`, truyền vào `LabAgent.run(correlation_id=...)` để ghi vào trace metadata, trả lại qua **response header `x-request-id`** (kèm `x-response-time-ms`) và trong body `ChatResponse.correlation_id`.
- **Các metadata được ghi vào structured log:** `app/main.py` bind contextvars trước khi log `request_received`: `user_id_hash` (SHA-256 12 ký tự, không bao giờ ghi `user_id` thô), `session_id`, `feature`, `model`, `env`. Mỗi dòng JSON có `event`, `ts` (ISO-8601 UTC), `level`, `service` và `correlation_id`; các trường đo lường gắn ở event `response_sent`: `latency_ms`, `ttft_ms`, `tokens_in`, `tokens_out`, `cost_usd`, `quality_score`, `tool_name`, `tool_success`.
- **Cách bảo đảm PII được scrub trước khi ghi:** processor `scrub_event` trong `app/logging_config.py` nằm **trong `structlog.configure(processors=[...])`**, đặt *trước* `JsonlFileProcessor` (bước ghi file) và *trước* `JSONRenderer` (bước render). Nhờ vậy dữ liệu đã bị scrub khi serialize/ghi xuống `data/logs.jsonl`, không phụ thuộc thứ tự log handler. Ngoài ra `app/main.py` không log message thô mà dùng `summarize_text()` (scrub + cắt 80 ký tự) cho `message_preview`/`answer_preview`, và `user_id` chỉ tồn tại dạng hash. `app/pii.py` có 6 pattern: email, điện thoại VN, CCCD (12 số), thẻ thanh toán (16 số), passport, địa chỉ VN.
- **Cách kiểm chứng kết quả:** `python scripts/validate_logs.py` báo **100/100** trên 371 records — `Records with missing required fields: 0`, `Records with missing enrichment: 0`, `Potential PII leaks detected: 0`, `Unique correlation IDs found: 183`. Evidence: `evidence/02-log-validator.txt`, `evidence/04-structured-log.png`, `evidence/05-pii-redaction.png`.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** tôi tạo project Langfuse `day13-k4-l3a-2A202602589` và điền key của chính tôi vào `.env` (`.env` nằm trong `.gitignore`, không commit). Mọi workload đều chạy bằng `scripts/load_test.py` trên localhost nên toàn bộ trace phát sinh từ máy tôi và nằm trong project này. Tôi truy vấn lại bằng `GET /api/public/v2/observations` (scope đúng project trong key) và thấy **30 trace** `lab-agent-run` trong 48h, trong đó **26 trace** có `prompt_source=langfuse`; không trace nào lấy từ project dùng chung.
- **Cấu trúc root/retrieval/generation observations:** dùng API observation của Langfuse Python SDK v4 (`@observe`) với đúng quan hệ cha–con trong `app/agent.py`:
  - root `lab-agent-run` (`as_type="agent"`), bọc trong `propagate_attributes(...)` để gắn `user_id`, `session_id`, `tags`, `environment`, `metadata` (`feature`, `model`, `correlation_id`);
  - child `rag-retrieve` (`as_type="retriever"`) — có `mark_error()` khi retrieval lỗi;
  - child `llm-generate` (`as_type="generation"`) — có `model`, `usage_details` (input/output/total) và `cost_details` tính theo `INPUT_COST_PER_MTOK=3.0`, `OUTPUT_COST_PER_MTOK=15.0`.
  Cả hai child đặt `capture_input=False, capture_output=False` để **không đẩy raw prompt/output (có thể chứa PII)** lên Langfuse; chỉ ghi `query_preview` đã scrub và `doc_count`. Số đo khớp giữa trace và log: ví dụ trace `3c529d95daf777e0ea1d217ad44fc008` có usage `input=43, output=81`, cost `0.001344 USD` — log `req-66f9c679` ghi `tokens_in=43, tokens_out=81, cost_usd=0.001344`.
- **Cách nối trace với log:** `correlation_id` là khoá nối duy nhất. Middleware sinh ID → bind vào structlog (mọi dòng log có nó) → truyền vào `LabAgent.run(correlation_id=...)` → `propagate_attributes(metadata={"correlation_id": correlation_id})` ghi vào metadata của mọi observation trong trace. Nhờ vậy lọc log theo `correlation_id` là tìm được đúng trace, và ngược lại. Ví dụ: log `req-66f9c679` ↔ trace `3c529d95daf777e0ea1d217ad44fc008` (cả hai đều có `feature=monitoring`, `session_id=k4-l3a-challenge-s05`).
- **Prompt name:** `day13-chat` (text prompt trong project cá nhân, đọc qua biến môi trường `LANGFUSE_PROMPT_NAME`). Cả hai version giữ đúng ba biến `{{feature}} {{docs}} {{message}}` theo `docs/PROMPT_VERSIONING.md`.
- **Version/label baseline:** version **1**, labels `baseline` + `production`; nội dung thêm câu *"Answer briefly and cite the docs."*
- **Version/label candidate:** version **2**, label `candidate`; thêm system instruction *"You are a concise support assistant."* và yêu cầu *"Answer in at most three sentences and only use the docs above."*
- **Trace ID của mỗi version:**
  - **v1 / baseline** (5 trace): `2f79b4c2c993bc5b541af1b59d949cfa` (s04), `e1ea045d09dc6b471705e18791f8bd50` (s01), `418e0880ab910357e8797795a1ff34a9` (s05) — ví dụ cost `0.002745 / 0.001608 / 0.001455 USD`.
  - **v2 / candidate** (21 trace): `164e96a3aa522592d5f122be0d02e626`, `5781d0d000ae0d13667e78506acf1dd2`, `74b1658b539c13a3c15c27ab536195cc`, và `3c529d95daf777e0ea1d217ad44fc008` (trace dùng cho điều tra CP3).
  - Cùng bộ input `data/sample_queries.jsonl` và cùng bộ query challenge được chạy cho cả hai label, nên so sánh được.
- **Cách promote và rollback `production`:** dùng `scripts/prompt_versions.py` (bọc `client.update_prompt(name="day13-chat", version=N, new_labels=["production"])`):
  ```bash
  python scripts/prompt_versions.py create      # tạo v1 (baseline+production), v2 (candidate)
  python scripts/prompt_versions.py promote --version 2   # production -> v2
  python scripts/prompt_versions.py rollback              # production -> v1
  python scripts/prompt_versions.py list
  ```
  Sau khi rollback, `list` xác nhận: `production: version 1`, `baseline: version 1`, `candidate: version 2`. Nhờ vậy nếu prompt v2 gây hỏng chất lượng/độ trễ thì chỉ cần đổi label, không sửa code hay deploy lại.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** `python scripts/dashboard.py --html out/dashboard.html` dựng dashboard runtime **6/6 panel** đúng contract `config/dashboard.yaml`, đọc cùng nguồn `data/logs.jsonl`:
  1. `latency` — P50/P95/P99 + TTFT P95, đơn vị `ms`, threshold `p95 ≤ 3000`;
  2. `traffic` — tổng request và request/phút, đơn vị `requests_per_minute`, threshold `≥ 1`;
  3. `errors` — error rate %, breakdown theo `error_type` và **retrieval success %**, đơn vị `percent`, threshold `error_rate_pct ≤ 2`;
  4. `cost` — tổng cost USD theo phút, đơn vị `usd`, threshold `≤ 2.5`;
  5. `tokens` — tổng `tokens_in`/`tokens_out`, đơn vị `tokens`, threshold `≤ 50000`;
  6. `quality` — mean `quality_score`, đơn vị `score_0_to_1`, threshold `≥ 0.75`.
  Mỗi panel ghi rõ **time range 60 phút** và **refresh 30s**, và có đường threshold tương ứng. `python scripts/validate_dashboard.py` báo `HỢP LỆ: 6/6 panel`. Evidence: `evidence/03-dashboard-validator.txt`, `evidence/11-dashboard-overview.png`; nếu ảnh không đọc rõ thì tách `evidence/11a-dashboard-latency-errors.png` và `evidence/11b-dashboard-cost-token-quality.png`. Ba bản HTML mở được bằng trình duyệt nằm ở `evidence/raw/`, sinh ở 3 trạng thái khác nhau: `11b-dashboard-baseline.html` (tắt hết incident, P95 ~635 ms), `11a-dashboard-incident-latency.html` (bật `rag_slow`, P95 2656 ms) và `11-dashboard-overview.html` (bật `tool_fail`, error rate 33.33% + `Error breakdown: RuntimeError=10`).
- **Hai cải tiến tôi làm cho panel `errors` sau khi xem lại ảnh chụp:** (1) **mỗi panel giờ in trạng thái threshold thật** `✅ OK — Threshold: p95 lte 3000 ms; measured p95=2656 ms` hoặc `⚠ BREACH — ...` thay vì luôn in ký hiệu `⚠` trang trí — nhờ vậy ảnh chứng minh được ngưỡng có/không bị vượt chứ không chỉ nêu con số; (2) khi **không có** `request_failed` trong time range, panel in rõ *"Không có `request_failed` trong N request của time range → error rate 0%, hệ thống đang bình thường"* và vẫn hiện series `Error theo phút` (kể cả phút = 0 lỗi) thay vì để trống, đồng thời **không** gắn nhầm log của một request thành công vào panel lỗi. Tôi khóa hành vi này bằng `tests/test_dashboard_runtime.py` (6 test: không lỗi, có lỗi, ngoài time range, threshold OK/BREACH, render HTML, render text).
- **SLO và lý do chọn:** `config/slo.yaml` định nghĩa SLO chính `fast_successful_requests`, cửa sổ 28d, mục tiêu **99.5%**, SLI là `event == "response_sent" and latency_ms <= 3000` trên tổng `event == "request_received"`. Ngưỡng **3000 ms** không bịa: lấy từ baseline thật của tôi (P50 156 ms, P95 1202 ms, P99 1725 ms, max 2263 ms), tức đặt ở khoảng 1.7× P99 để có headroom nhưng vẫn bắt sự cố sớm. Ngưỡng này cũng được dùng lại làm threshold của panel `latency` và guardrail để metric, dashboard và alert không lệch nhau. Baseline đo được 110 request / 100 `response_sent` = 90.91% — thấp hơn 99.5% vì còn 10 lỗi `AttributeError` do bug đã sửa (xem mục 8), nên sau khi sửa tôi tính lại error budget từ đầu.
- **Cách tính error budget:** `error_budget_percent = 100 − 99.5 = 0.5%`. Công thức: `allowed_bad = total_request_trong_28d × 0.5 / 100`; ví dụ 100 000 request/28d thì được phép **500** request chậm hoặc lỗi. Tôi đặt hai ngưỡng burn-rate: **14.4** (tiêu hết 1% ngân sách trong 1 giờ) và **6.0** (tiêu hết 5% trong 6 giờ) — burn rate > 1 nghĩa là ngân sách hết sớm hơn 28d nên phải dừng release; > 14.4 trong 1h thì paging ngay. Với lưu lượng thực tế của lab (~110 request/phiên load test) thì 0.5% tương đương dưới 1 request lỗi, nên tôi bổ sung **guardrail** thực dụng hơn trong `config/slo.yaml`: `error_rate_pct_max: 2`, `daily_cost_usd_max: 2.5`, `quality_score_avg_min: 0.75`, `retrieval_success_rate_pct_min: 90` (baseline đo được: error 9.09% → sau khi sửa < 2%, cost 0.2088 USD/phiên, quality 0.88, retrieval success 100%).
- **Ba alert và runbook tương ứng:** khai báo đầy đủ trong `config/alert_rules.yaml`, runbook chi tiết trong `docs/alerts.md` (mỗi alert có severity, duration, số cửa sổ duy trì, owner, Slack channel, baseline tham chiếu, ảnh hưởng người dùng, 3 bước kiểm tra đầu tiên và mitigation). Cả ba đều là **symptom-based**, bám vào triệu chứng người dùng/SLO chứ không vào tên implementation, và cùng đọc `data/logs.jsonl` nên tái hiện được bằng `load_test.py`:
  1. `high_p95_latency` — critical, `percentile(latency_ms,95) > 3000` trong **5m**/3 cửa sổ, Slack `#k4-l3a-alerts-latency`, gắn SLO `fast_successful_requests`; mitigation: tắt nguồn chậm, giảm số doc trong prompt, rollback prompt nếu do prompt dài.
  2. `elevated_error_rate` — critical, `request_failed/request_received*100 > 2` trong **3m**/2 cửa sổ, Slack `#k4-l3a-alerts-errors`; mitigation: lọc theo `error_type`, mở trace cùng `correlation_id`, rollback deploy nếu do code.
  3. `retrieval_success_drop` — warning, `tool_success=true / tool_success!=null *100 < 90` trong **5m**/3 cửa sổ, Slack `#k4-l3a-alerts-rag`; mitigation: kiểm tra vector store, tắt feature lỗi, rollback prompt.
  Tôi đã kiểm chứng cơ chế bằng `inject_incident.py --scenario rag_slow` / `tool_fail` rồi `--disable` (xem `docs/alerts.md` phần cuối) và đó chính là kịch bản dùng cho CP3.

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1` (cohort K4, `incident: rag_slow`, `seed: 1311`, `affected_feature: monitoring`, `latency_threshold_ms: 2000`). File `config/challenge.json` do Lab Coach gửi riêng, nằm trong `.gitignore`, tôi không sửa/commit/push/chia sẻ.
- **Khoảng thời gian điều tra:** `2026-09-29T13:57:27Z → 13:57:37Z` (20:57:27–20:57:37 giờ VN), gói trong **1 phút**. Quy trình đã chạy: `python scripts/inject_incident.py` (đọc incident từ `config/challenge.json`) → `python scripts/load_test.py --challenge --concurrency 5`.
- **Triệu chứng từ metrics:** panel `latency` của dashboard (`data/logs.jsonl`, time range 60 phút) cho P95 tăng từ **673 ms (baseline) lên 2663 ms**, vượt cả ngưỡng SLO **3000 ms** lẫn ngưỡng **2000 ms** của challenge. Biểu đồ theo phút nhảy từ `13:56 = 2061 ms` lên `13:57 = 13287 ms`; `GET /metrics` cho `latency_p95=2663.0`. Điểm mấu chốt: **TTFT P95 giữ nguyên 50 ms**, error rate 0% và retrieval success 100% → không phải lỗi và không phải LLM chậm, mà là thời gian mất **trước** khi LLM bắt đầu sinh token. Evidence: `evidence/12-incident-metric.png` (kèm `evidence/11a-dashboard-latency-errors.png`).
- **Log line và correlation ID liên quan:** lọc `event == "response_sent" and latency_ms > 2000` được 5 dòng đều `feature=monitoring`; chọn `correlation_id = req-66f9c679`:
  ```json
  {"service":"api","latency_ms":2655,"ttft_ms":50,"tokens_in":43,"tokens_out":81,"cost_usd":0.001344,"quality_score":0.8,"tool_name":"retrieval","tool_success":true,"event":"response_sent","feature":"monitoring","correlation_id":"req-66f9c679","user_id_hash":"ed72e61117f6","session_id":"k4-l3a-challenge-s05","env":"dev","model":"gpt-4o-mini","ts":"2026-09-29T13:57:32.410708Z"}
  ```
  `session_id=k4-l3a-challenge-s05` khớp query thứ 5 trong `config/challenge.json`, `latency_ms=2655` > 2000 nhưng `ttft_ms=50` **bằng baseline**, và `tool_success=true` (không phải lỗi). Evidence: `evidence/13-incident-log.png`.
- **Trace ID và span gây ảnh hưởng:** trace `3c529d95daf777e0ea1d217ad44fc008` (metadata `correlation_id=req-66f9c679` — khớp đúng log trên). Waterfall:
  | span | type | bắt đầu | thời lượng | tỉ trọng |
  |---|---|---:|---:|---:|
  | `lab-agent-run` (root) | AGENT | 0.000 s | 2.667 s | 100% |
  | **`rag-retrieve`** | RETRIEVER | 0.000 s | **2.514 s** | **94.3%** |
  | `llm-generate` | GENERATION | 2.514 s | 0.153 s | 5.7% |
  Span gây ảnh hưởng là **`rag-retrieve`**. Evidence: `evidence/14-incident-trace.png`.
- **Root cause:** span **retrieval (`rag-retrieve`)** chiếm 2.514 s / 94.3% tổng thời gian request, tức nguồn chậm nằm ở **vector store / tầng truy xung ngữ cảnh**, không phải ở LLM — đúng với incident `rag_slow` mà challenge bật (`time.sleep(2.5)` trong `app/mock_rag.py::retrieve`). Bằng chứng độc lập cùng chỉ một nguyên nhân: metric (P95 ↑ nhưng TTFT P95 đi ngang) + log (`latency_ms` ↑, `ttft_ms` đi ngang, `tool_success=true`) + trace (94.3% thời gian nằm trong `rag-retrieve`). Chi phí và chất lượng không đổi (`cost_usd=0.001344`, `quality=0.8`) nên không liên quan prompt hay LLM.
- **Fix action:** chạy `python scripts/inject_incident.py --disable` để tắt nguồn chậm, rồi chạy lại `python scripts/load_test.py --challenge --concurrency 5` để xác minh. Kết quả: **latency server trở về 151–158 ms** (client quan sát 500–837 ms) — tức P95 về dưới cả hai ngưỡng. Với hệ thống thật thì bước tương ứng là: tăng timeout + retry có backoff cho vector store, cache kết quả truy xuống theo `query_hash`, giảm số doc đưa vào prompt, hoặc failover sang fallback retrieval. Cần lưu ý: `app/incidents.py` lưu state **trong tiến trình**, nên phải bật/tắt qua API (`POST /incidents/{name}/enable|disable`) chứ không sửa file.
- **Preventive measure:** (1) alert `high_p95_latency` đã khai báo sẵn (`config/alert_rules.yaml`, runbook `docs/alerts.md#alert-1`) với điều kiện đúng như sự cố này — P95 > 3000 ms trong 5m/3 cửa sổ, nên sự cố được bắt trước khi thành SLO vi phạm kéo dài; (2) tách panel/metric riêng cho tầng truy xuồng: tôi đề xuất ghi thêm `retrieval_ms` vào cả log và span, và thêm guardrail `rag_latency_ms_p95_max` để phân biệt "chậm ở RAG" với "chậm ở LLM" ngay trên dashboard mà không cần mở trace; (3) thêm `retrieval_duration_ms` vào SLO như một SLI con, để burn-rate alert được gắn đúng thành phần gây sự cố; (4) canary/probe định kỳ cho vector store để phát hiện sớm trước khi người dùng lên phút độ trễ; (5) vì `ttft_ms` đã chứng minh giá trị như một "dấu hiệu phân định" (bất biến khi RAG chậm), tôi đề xuất hiển thị `ttft_p95` cạnh `latency_p95` trên cảnh báo để kỹ sự có hướng điều tra ngay.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** chọn ngưỡng SLO **3000 ms** cho `latency_threshold_ms` dựa trên **baseline thật đo được** thay vì chọn con số "cho đẹp". Baseline của tôi là P50 156 ms, P95 1202 ms, P99 1725 ms, max 2263 ms, nên 3000 ms ≈ 1.7× P99: đủ headroom để không báo động giả dưới tải bình thường, nhưng vẫn bắt được sự cố sớm. Con số này còn được tái sử dụng cho **cùng một ngưỡng** ở panel `latency` trong `config/dashboard.yaml` và guardrail trong `config/slo.yaml`, để metric, dashboard, SLO và alert không lệch nhau — nếu mỗi nơi một ngưỡng thì khi có sự cố sẽ không xác định được cái nào "đúng". Một quyết định nữa là đặt PII processor (`scrub_event`) **trước** `JsonlFileProcessor` và `JSONRenderer` trong chuỗi processor của structlog, để redaction xảy ra trước mọi bước serialize/ghi file thay vì phụ thuộc thứ tự handler.
- **Một lỗi/blocker đã gặp:** (1) **Sai API khiến mọi request trả 500 với `AttributeError`** — code ban đầu gọi `client.update_current_observation(...)`, hàm **không tồn tại** trong Langfuse Python SDK v4 (`4.15.6`). Lỗi này đẩy error rate baseline lên **9.09%** (10 lỗi trên 110 request) và khiến SLO 99.5% không thể đạt. Tôi sửa bằng cách bọc mọi lệnh update qua `app/tracing.py::_safe_update()`, ánh xạ sang đúng API v4 (`update_current_span` / `update_current_generation`) và **nuốt exception trả về boolean** — vì telemetry không được phép làm hỏng request chính. Sau khi sửa, error rate về 0%. (2) **Blocker khi thu evidence CP3:** `GET /api/public/traces` trả **HTTP 410** `LEGACY_API_UNAVAILABLE_FOR_NEW_ORGANIZATION` (tổ chức tạo sau 16/09/2026 không dùng được legacy API), còn `GET /api/public/v2/observations/<id>` trả 404. Tôi đọc message lỗi để tìm endpoint thay thế: `GET /api/public/v2/observations?fromStartTime=...&toStartTime=...` kèm `traceId=` và `fields=`. Ngoài ra endpoint này mặc định **không trả `metadata`**, phải yêu cầu tường minh qua `fields=id,metadata,usage,totalCost,...` mới lấy được `correlation_id` để nối trace với log. (3) Lưu ý vận hành: `app/incidents.py` giữ state trong **tiến trình** nên `inject_incident.py` bắt buộc phải POST tới API đang chạy; và phải chạy `scripts/dashboard.py` **sau** `load_test.py` (chạy song song sẽ đọc file log rỗng).
- **Cách tìm nguyên nhân và xử lý:** tôi đi đúng thứ tự **Metrics → Logs → Traces**. (1) Trên dashboard, thấy panel `latency` nhảy `13:56=2061` → `13:57=13287` nhưng `ttft_p95` đi ngang 50 ms và error/retrieval vẫn tốt — suy ra thời gian mất **trước** lúc sinh token, tức ở tầng truy xuồng. (2) Lọc `data/logs.jsonl` theo ngưỡng `latency_ms > 2000` (ngưỡng trong challenge) để lấy `correlation_id=req-66f9c679`, xác nhận `feature=monitoring` khớp `affected_feature` và `session_id=k4-l3a-challenge-s05` khớp query chính thức. (3) Tra cùng `correlation_id` trên Langfuse, mở trace `3c529d95daf777e0ea1d217ad44fc008`: `rag-retrieve` chiếm 2.514 s / 94.3% còn `llm-generate` chỉ 0.153 s → khoanh vùng đúng span. (4) Kiểm chứng bằng cách `--disable` incident rồi chạy lại workload: latency về 151–158 ms. Kết luận chỉ được chấp nhận khi **cả ba tín hiệu cùng chỉ một nguyên nhân** và hành động xử lý **kiểm chứng được bằng đo lại**.
- **Cách hiểu luồng Metrics → Logs → Traces:** metric trả lời **"có vấn đề gì và từ khi nào"** nhưng không nói là request nào; log trả lời **"request nào, ai gọi, ngữ cảnh gì"** nhưng không nói thời gian bị mất ở đâu; trace (waterfall + span) trả lời **"thời gian mất ở bước nào"**. Ba tầng nối với nhau bằng `correlation_id`: metric phát hiện bất thường → lọc log theo khoảng thời gian đó để lấy `correlation_id` → tra ID đó trên Langfuse để mở đúng trace và đọc waterfall. Nếu thiếu mắt xích này thì hoặc là điều tra trùng lặp (mở từng trace), hoặc kết luận sai (đoán nguyên nhân từ metric). Trong bài này `correlation_id` được ghi vào **cả** structured log (qua structlog contextvars) **và** metadata của mọi observation trong trace — đó là điều kiện tiên quyết để chuỗi này hoạt động. Việc có `ttft_ms` riêng cho LLM là ví dụ rõ của "metric có sẵn dấu hiệu phân định": TTFT bất biến đã gần như chỉ tên thành phần gây sự cố ngay từ dashboard, rồi trace chỉ cần xác nhận.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:** *Prompt version* biến việc đổi câu chữ thành việc đổi **label**, có `name/version/label` ghi thẳng vào trace metadata nên sau mỗi request tôi biết chính xác prompt nào đã sinh ra nó — quan trọng vì cùng một câu hỏi với prompt khác nhau có thể cho chất lượng và độ dài output khác nhau, và không có version thì không quy được lỗi. *Token/cost* là thước đo vận hành: tôi ghi `tokens_in/out` và `cost_usd` **giống nhau ở cả log lẫn generation observation** (cùng đơn giá 3.0/15.0 USD per 1M token) để dashboard và Langfuse không lệch số, và panel `cost`/`tokens` có ngưỡng chặn chi phí trước khi thành sự cố tài chính. *SLO/error budget* biến "hệ thống có chậm không" thành câu hỏi có trả lời được: đo 99.5% trong 28d, ngân sách lỗi 0.5%, burn rate > 1 thì dừng release, > 14.4 thì paging — nhờ đó quyết định *dừng hay tiếp tục* dựa trên số thay vì cảm tính. *Rollback* là cơ chế khôi phục nhanh nhất: chỉ đổi label `production` về version 1 là mọi request dùng lại prompt cũ mà không cần sửa code, build hay deploy lại — tôi đã dùng đúng cơ chế này và xác nhận `production: version 1` sau rollback.
- **Điều quan trọng nhất đã học:** một kết luận incident chỉ đáng tin khi **ba tín hiệu độc lập cùng chỉ một nguyên nhân**. Nếu chỉ nhìn metric tôi sẽ kết luận "LLM chậm" và sửa sai chỗ; chính việc `ttft_ms` đi ngang trong khi `latency_ms` tăng gấp 4 mới chỉ ra thời gian mất nằm ở RAG, và trace waterfall mới chỉ ra chính xác span nào. Kèm theo đó là bài học về kỹ thuật: với SDK/API có version, phải kiểm tra API thực sự tồn tại (bug `update_current_observation` đã làm hỏng 9.09% request chỉ vì gọi một hàm không có trong SDK v4), và khi API trả lỗi kiểu "legacy" thì **đọc message lỗi** thay vì đoán (`410` chỉ rõ endpoint thay thế và tham số cần dùng).
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:** (1) Ba evidence đầu (`01`–`03`) tôi nộp bằng **output text `.txt`** vì `docs/SUBMISSION.md` cho phép rõ ràng; các mục còn lại nộp bằng **ảnh chụp màn hình `.png`**. Song song với mỗi ảnh tôi đặt thêm một file text/HTML tương ứng trong `evidence/raw/` ghi rõ lệnh đã chạy, ID và giá trị thật, để giảng viên kiểm chứng lại độc lập thay vì chỉ tin ảnh. (2) `app/metrics.py` hiện lưu số liệu **trong bộ nhớ tiến trình** (`list`/`Counter`), nên metric mất khi restart API và chưa có cửa sổ trượt theo thời gian; dashboard vì vậy tính percentile trên toàn bộ bản ghi trong time range thay vì trên cửa sổ cố định. (3) Sự cố CP3 là do incident mô phỏng `time.sleep(2.5)`; tôi chưa tái hiện được sự cố "thật" như vector store timeout hay prompt quá dài, và chưa đo được burn-rate theo thời gian thực. (4) Chưa làm phần bonus audit log riêng có schema/retention/truy vấn minh hoạ. (5) `pytest` in cảnh báo `401 Unauthorized` khi xuất span vì `.env` không được nạp vào process test — không ảnh hưởng kết quả (**28 pass**) và không ảnh hưởng trace thật qua API, nhưng thừa nhận là chưa sạch.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs. (Việc nộp trên LMS do tôi thực hiện ngoài repo.)

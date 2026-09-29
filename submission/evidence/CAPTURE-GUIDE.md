# Hướng dẫn chụp evidence (CP0–CP3)

Tài liệu này dùng khi chụp ảnh `.png` cho `submission/evidence/`. Mỗi mục ghi **lệnh cần chạy** và **giá trị phải nhìn thấy** trong ảnh. Các ảnh phải thuộc project Langfuse cá nhân `day13-k4-l3a-2A202602589`, không chụp trang API Keys và không lộ PII.

> `01`–`03` đã nộp bằng file `.txt` (được phép theo `docs/SUBMISSION.md`: *"Test/validator có thể lưu dạng ảnh `.png` hoặc output text `.txt`"*). Chỉ cần chụp **11 ảnh** dưới đây.

---

## Điểm danh dùng chung (đối chiếu khi chụp)

| Thành phần | Giá trị |
|---|---|
| Challenge ID | `day13-k4-l3a-monitoring-llmops-v1` |
| Correlation ID của sự cố | `req-66f9c679` |
| Trace ID của sự cố | `3c529d95daf777e0ea1d217ad44fc008` |
| Session | `k4-l3a-challenge-s05` |
| Span gây ảnh hưởng | `rag-retrieve` — 2.514 s / 94.3% tổng 2.667 s |
| Ngưỡng SLO / challenge | 3000 ms / 2000 ms |

---

## Chuẩn bị

```powershell
# 1. API phải đang chạy (app/incidents.py lưu state trong tiến trình)
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 2. Kiểm tra
curl.exe -s http://127.0.0.1:8000/health
#   -> {"ok":true,"tracing_enabled":true,...}
```

---

## 04 — Structured log → `04-structured-log.png`

**Nguồn:** terminal hoặc `data/logs.jsonl`.

```powershell
# 1. Gửi 1 request thật với correlation_id cố định để ảnh dễ đọc
curl.exe -s -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" `
  -H "x-request-id: req-evidence04" `
  -d '{\"user_id\":\"u_student_01\",\"session_id\":\"s_evidence_01\",\"feature\":\"monitoring\",\"message\":\"Describe how to prove a slow span is the root cause. Email an.nguyen@gmail.com\"}'

# 2. In đúng 2 dòng log của request đó (request_received + response_sent)
Get-Content data\logs.jsonl | Select-String 'req-evidence04'
```

**Phải nhìn thấy:** `event`, `ts`, `correlation_id`, `feature`, `model`, `env`, `latency_ms`, `user_id_hash`, `session_id`.
**Kiểm tra:** `user_id_hash` là hash 12 ký tự, **không** có `user_id` thô.

> ⚠ **Không dùng `Get-Content data\logs.jsonl -Tail 2`.** Ngay sau khi khởi động
> server, 2 dòng cuối là event `app_started` (chỉ có `service`, `env`, `payload`,
> `event`, `level`, `ts`) — không có `correlation_id`/`user_id_hash`/`latency_ms`
> nên **không chứng minh được** enrichment. Hãy gửi request trước rồi lọc theo
> `correlation_id` như trên.
>
> **Tránh wrap dòng** (mỗi record dài ~1 dòng nhưng PowerShell wrap thành 3):
> ```powershell
> Get-Content data\logs.jsonl | Select-String 'req-evidence04' | ForEach-Object { $_.Line }
> ```

---

## 05 — PII redaction → `05-pii-redaction.png`

**Nguồn:** terminal.

```powershell
.\.venv\Scripts\python.exe -c "from app.pii import scrub_text; print(scrub_text('email an.nguyen@gmail.com | SD 0912345678 | CCCD 001202012345 | the 4242 4242 4242 4242'))"
```

**Phải nhìn thấy** (output thật đã kiểm chứng):

```text
email [REDACTED_EMAIL] | SD [REDACTED_PHONE_VN] | CCCD [REDACTED_CCCD] | the [REDACTED_CREDIT_CARD]
```

Nên kèm thêm 1 dòng log thật đã scrub để chứng minh đã áp dụng trong app.

---

## 06 — Trace list → `06-trace-list.png`

**Nguồn:** Langfuse → menu **Tracing** → tab **Traces** (project `day13-k4-l3a-2A202602589`).

**Phải nhìn thấy:** tên project + **≥10 trace** do bạn tự tạo.
**Số liệu đối chiếu:** tổng 30 trace `lab-agent-run`; 26 trace có `prompt_version` (v1/baseline: 5, v2/candidate: 21).

---

## 07 — Trace waterfall → `07-trace-waterfall.png`

**Nguồn:** Langfuse → mở trace `3c529d95daf777e0ea1d217ad44fc008`.

**Phải nhìn thấy** quan hệ cha–con và thời lượng:

| span | type | thời lượng |
|---|---|---:|
| `lab-agent-run` (root) | AGENT | 2.667 s |
| `rag-retrieve` | RETRIEVER | **2.514 s (94.3%)** |
| `llm-generate` | GENERATION | 0.153 s (5.7%) |

---

## 08 — Trace metadata → `08-trace-metadata.png`

**Nguồn:** cùng trace, tab **Metadata** (và phần model/token/cost).

**Phải nhìn thấy:** `correlation_id=req-66f9c679`, `feature=monitoring`, `model=claude-sonnet-4-5`, `prompt_name=day13-chat`, `prompt_version=2`, `prompt_label=candidate`, `prompt_source=langfuse`, `doc_count=1`, `ttft_ms=50`, token `input=43 output=81`, cost `0.001344 USD`.
**Kiểm tra:** không có PII thô.

---

## 09 — Prompt versions → `09-prompt-versions.png`

**Nguồn:** Langfuse → **Prompts** → `day13-chat`.

**Phải nhìn thấy:** version **1** (labels `baseline`, `production`) và version **2** (label `candidate`); cả hai giữ `{{feature}} {{docs}} {{message}}`.

Đối chiếu nhanh bằng lệnh:

```powershell
.\.venv\Scripts\python.exe scripts\prompt_versions.py list
# -> production: version 1 / baseline: version 1 / candidate: version 2
```

---

## 10 — Prompt rollback → `10-prompt-rollback.png`

**Nguồn:** Langfuse → **Prompts** → `day13-chat` (trạng thái sau rollback).

**Phải nhìn thấy:** label `production` đang trỏ **version 1**, `candidate` vẫn là version 2.
**Trace ID hai version** (đã ghi trong `REPORT.md` mục 5):
- v1/baseline: `2f79b4c2c993bc5b541af1b59d949cfa`, `e1ea045d09dc6b471705e18791f8bd50`
- v2/candidate: `164e96a3aa522592d5f122be0d02e626`, `5781d0d000ae0d13667e78506acf1dd2`

---

## 11 / 11a / 11b — Dashboard runtime

**Nguồn:** mở bằng trình duyệt các file trong `submission/evidence/raw/`:

| File | Nội dung |
|---|---|
| `11-dashboard-overview.html` | 6 panel đầy đủ, có cả lỗi `tool_fail` (error rate 33.3%) |
| `11a-dashboard-incident-latency.html` | Dashboard lúc sự cố `rag_slow` (P95 2656 ms) |
| `11b-dashboard-baseline.html` | Dashboard baseline (trước sự cố) |

**Phải nhìn thấy:** đủ **6 panel** (`latency`, `traffic`, `errors`, `cost`, `tokens`, `quality`), **time range 60 phút**, **đơn vị** và **threshold**; panel `latency` có TTFT, panel `errors` có retrieval success.
**Mỗi panel có dòng trạng thái threshold** `✅ OK` hoặc `⚠ BREACH` kèm giá trị đo được — không còn dòng `⚠` "trang trí" ở mọi panel.
**Chia nhỏ nếu ảnh không đọc rõ:** `11a-dashboard-latency-errors.png` và `11b-dashboard-cost-token-quality.png`.

**Cách sinh lại 3 file (đúng thứ tự, phải chạy sau khi API đã chạy):**

```powershell
chcp 65001   # để tiếng Việt trong terminal/HTML đọc được

# 11b — baseline: tắt hết incident, chạy workload, sinh HTML
.\.venv\Scripts\python.exe scripts\inject_incident.py --scenario rag_slow --disable
.\.venv\Scripts\python.exe scripts\inject_incident.py --scenario tool_fail --disable
.\.venv\Scripts\python.exe scripts\load_test.py --concurrency 3
.\.venv\Scripts\python.exe scripts\dashboard.py --html submission\evidence\raw\11b-dashboard-baseline.html

# 11a — sự cố latency: bật rag_slow, chạy workload, sinh HTML
.\.venv\Scripts\python.exe scripts\inject_incident.py --scenario rag_slow
.\.venv\Scripts\python.exe scripts\load_test.py --concurrency 3
.\.venv\Scripts\python.exe scripts\dashboard.py --html submission\evidence\raw\11a-dashboard-incident-latency.html

# 11 — tổng hợp: thêm sự cố tool_fail để panel errors có dữ liệu thật
.\.venv\Scripts\python.exe scripts\inject_incident.py --scenario tool_fail
.\.venv\Scripts\python.exe scripts\load_test.py
.\.venv\Scripts\python.exe scripts\dashboard.py --html submission\evidence\raw\11-dashboard-overview.html
.\.venv\Scripts\python.exe scripts\inject_incident.py --scenario tool_fail --disable
```

> **Vì sao phải bật `tool_fail` khi sinh file 11:** khi hệ thống không có lỗi,
> panel `errors` chỉ hiện `Error rate 0%` và dòng
> *"Không có `request_failed` trong N request của time range"*. Đó là trạng thái
> **đúng** (hệ thống khoẻ), nhưng không chứng minh được panel đọc được
> `error_type` / `tool_success` thật. Bật `tool_fail` một lượt để có
> `Error breakdown: RuntimeError=10` và `Retrieval success 66.67%` — khớp với
> Alert 2 và Alert 3 trong `docs/alerts.md`.

---

## 12 — Incident metric → `12-incident-metric.png`

**Nguồn:** dashboard lúc sự cố (`raw/11a-dashboard-incident-latency.html`) + output `/metrics`.

```powershell
# Phải chạy load test TRƯỚC, nếu không /metrics trả toàn 0 (state nằm trong RAM)
curl.exe -s http://127.0.0.1:8000/metrics
```

**Phải nhìn thấy:** P95 tăng **673 ms → 2663 ms** (vượt ngưỡng 3000), biểu đồ theo phút `13:56=2061` → `13:57=13287`, và **TTFT P95 giữ nguyên 50 ms** (dấu hiệu thời gian mất ở RAG chứ không ở LLM).

---

## 13 — Incident log → `13-incident-log.png`

**Nguồn:** terminal, `data/logs.jsonl`.

```powershell
Get-Content data\logs.jsonl | Select-String 'req-66f9c679'
```

**Phải nhìn thấy:** dòng `response_sent` có `latency_ms=2655`, `ttft_ms=50`, `feature=monitoring`, `session_id=k4-l3a-challenge-s05`, `tool_success=true`.

---

## 14 — Incident trace → `14-incident-trace.png`

**Nguồn:** Langfuse → trace `3c529d95daf777e0ea1d217ad44fc008`.

**Phải nhìn thấy:** cùng `correlation_id` với `13` (`req-66f9c679`) và span `rag-retrieve` chiếm ~2.5 s.
**Bắt buộc:** ảnh `13` và `14` phải cùng `correlation_id` — đây là điều kiện Rubric mục E ("Metric, log và trace cùng chỉ sự cố").

---

## Trước khi lưu ảnh

- [ ] Che mọi secret/API key; không chụp trang API Keys của Langfuse.
- [ ] Không có PII thô (chỉ `user_id_hash`).
- [ ] Ảnh đọc được tên panel/screen, giá trị, time range và ID liên quan.
- [ ] Tên project `day13-k4-l3a-2A202602589` nhìn thấy trong ảnh Langfuse.
- [ ] Tất cả evidence thuộc đúng commit SHA được nộp.
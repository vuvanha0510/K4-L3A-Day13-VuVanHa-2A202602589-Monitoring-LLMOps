# Dữ liệu gốc đính kèm cho evidence

Thư mục này chứa **dữ liệu gốc** (output text và dashboard HTML) của các ảnh chụp ở thư mục `../`.

## Vì sao có thư mục này?

Ảnh chụp màn hình (`.png`) là evidence chính thức theo yêu cầu của `docs/SUBMISSION.md`. Song song với mỗi ảnh, tôi lưu thêm **file text/HTML tương ứng** tại đây, ghi rõ:

- lệnh/API đã chạy để tạo ra dữ liệu;
- các ID, correlation ID, trace ID và giá trị đo được;
- cách diễn giải số liệu.

Mục đích là để giảng viên **kiểm chứng lại độc lập** thay vì chỉ tin vào ảnh, và để tôi có thể tái hiện đúng kết quả trong Q&A.

## Liên hệ giữa ảnh và dữ liệu gốc

| Ảnh (evidence chính) | File dữ liệu gốc (tại đây) |
|---|---|
| `04-structured-log.png` | `04-structured-log.txt` |
| `05-pii-redaction.png` | `05-pii-redaction.txt` |
| `06-trace-list.png` | `06-trace-list.txt` |
| `07-trace-waterfall.png` | `07-trace-waterfall.txt` |
| `08-trace-metadata.png` | `08-trace-metadata.txt` |
| `09-prompt-versions.png` | `09-prompt-versions.txt` |
| `10-prompt-rollback.png` | `10-prompt-rollback.txt` |
| `11-dashboard-overview.png` | `11-dashboard-overview.html` |
| `11a-dashboard-latency-errors.png` | `11a-dashboard-incident-latency.html` |
| `11b-dashboard-cost-token-quality.png` | `11b-dashboard-baseline.html` |
| `12-incident-metric.png` | `12-incident-metric.txt` |
| `13-incident-log.png` | `13-incident-log.txt` |
| `14-incident-trace.png` | `14-incident-trace.txt` |

## Cách tái hiện các file này

```powershell
# Log / PII — gửi request trước, rồi lọc theo correlation_id (đừng dùng -Tail 2)
curl.exe -s -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" `
  -H "x-request-id: req-evidence04" `
  -d '{\"user_id\":\"u_student_01\",\"session_id\":\"s_evidence_01\",\"feature\":\"monitoring\",\"message\":\"Describe how to prove a slow span is the root cause.\"}'
Get-Content data\logs.jsonl | Select-String 'req-evidence04'

.\.venv\Scripts\python.exe -c "from app.pii import scrub_text; print(scrub_text('email an.nguyen@gmail.com | SD 0912345678 | CCCD 001202012345 | the 4242 4242 4242 4242'))"

# Dashboard — chạy theo thứ tự baseline → rag_slow → tool_fail
# (xem CAPTURE-GUIDE.md mục 11/11a/11b để có lệnh đầy đủ)
.\.venv\Scripts\python.exe scripts\load_test.py --concurrency 3
.\.venv\Scripts\python.exe scripts\dashboard.py --html submission\evidence\raw\11-dashboard-overview.html

# Prompt version
.\.venv\Scripts\python.exe scripts\prompt_versions.py list
```

## Ghi chú về 3 file dashboard

`scripts/dashboard.py` chỉ đọc 60 phút cuối của `data/logs.jsonl`, tính từ dòng
log mới nhất. Vì vậy:

| File | Trạng thái khi sinh | Đặc điểm nhìn thấy |
|---|---|---|
| `11b-dashboard-baseline.html` | `rag_slow=false, tool_fail=false` | P95 ~635 ms, `✅ OK` ở mọi panel |
| `11a-dashboard-incident-latency.html` | `rag_slow=true` | P95 2656 ms, `Latency theo phút` nhảy 2028 → 26558 |
| `11-dashboard-overview.html` | `tool_fail=true` | `Error rate 33.33%`, `Error breakdown: RuntimeError=10`, `Retrieval success 66.67%` |

Khi **không** có `request_failed` trong time range, panel `errors` in rõ
*"Không có `request_failed` trong N request của time range → error rate 0%,
hệ thống đang bình thường"* thay vì để trống — đó là trạng thái đúng, không
phải panel lỗi.

Hướng dẫn chụp từng ảnh kèm giá trị phải đối chiếu: [`../CAPTURE-GUIDE.md`](../CAPTURE-GUIDE.md).

Các file này được sinh từ dữ liệu thật của project cá nhân `day13-k4-l3a-2A202602589`, không chứa secret, API key hay PII thô.
# Evidence cá nhân

Đặt ảnh hoặc output text dùng để chấm vào thư mục này. Danh sách đầy đủ xem tại [docs/SUBMISSION.md](../../docs/SUBMISSION.md).

## Cấu trúc thư mục

```text
submission/evidence/
├── 01-pytest.txt              # output text (được phép)
├── 02-log-validator.txt       # output text (được phép)
├── 03-dashboard-validator.txt # output text (được phép)
├── 04-…png … 14-…png         # ảnh chụp màn hình = evidence chính thức
├── CAPTURE-GUIDE.md           # hướng dẫn chụp từng ảnh + giá trị phải đối chiếu
├── raw/                       # dữ liệu gốc đính kèm (text/HTML) của các ảnh
│   ├── README.md
│   └── 04-…txt … 14-…txt, 11-*.html
└── README.md
```

## Quy tắc áp dụng

- `01`–`03`: dùng **output text `.txt`** vì `docs/SUBMISSION.md` ghi rõ *"Test/validator có thể lưu dạng ảnh `.png` hoặc output text `.txt`"*.
- `04`–`14`: dùng **ảnh chụp `.png`**. Ảnh `04`, `05`, `13` lấy từ terminal hoặc `data/logs.jsonl`; ảnh `06`–`10`, `14` lấy từ project Langfuse cá nhân `day13-k4-l3a-<MSSV>` và **phải nhìn thấy tên project**. Không mở/chụp trang API Keys.
- Có thể tách dashboard thành nhiều ảnh nếu một ảnh không đọc rõ: `11a-dashboard-latency-errors.png`, `11b-dashboard-cost-token-quality.png`.
- Mỗi ảnh có một file dữ liệu gốc tương ứng trong `raw/` để kiểm chứng lại độc lập — xem [`raw/README.md`](raw/README.md).
- Hướng dẫn chụp: [`CAPTURE-GUIDE.md`](CAPTURE-GUIDE.md).

Từ `submission/REPORT.md`, dẫn ảnh bằng đường dẫn tương đối:

```markdown
![Trace waterfall](evidence/07-trace-waterfall.png)
```

Không commit secret, API key, PII thô hoặc evidence của học viên/lớp khác.

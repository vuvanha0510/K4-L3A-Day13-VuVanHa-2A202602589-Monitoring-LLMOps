from __future__ import annotations

import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Clear contextvars để tránh rò rỉ dữ liệu giữa các request
        clear_contextvars()

        # 2. Lấy x-request-id từ headers nếu có, nếu không thì tạo mới dạng req-<8-char-hex>
        header_id = request.headers.get("x-request-id")
        if header_id:
            correlation_id = header_id
        else:
            correlation_id = f"req-{uuid.uuid4().hex[:8]}"

        # 3. Bind correlation_id vào structlog contextvars
        bind_contextvars(correlation_id=correlation_id)

        request.state.correlation_id = correlation_id

        start = time.perf_counter()
        response = await call_next(request)

        # Tính thời gian xử lý (ms)
        process_time_ms = (time.perf_counter() - start) * 1000

        # 4. Thêm correlation_id và processing time vào response headers
        response.headers["x-request-id"] = correlation_id
        response.headers["x-response-time-ms"] = f"{process_time_ms:.2f}"

        return response

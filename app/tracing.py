from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any

try:
    from langfuse import get_client, observe, propagate_attributes

    LANGFUSE_SDK_AVAILABLE = True
except ImportError:  # pragma: no cover - chỉ dùng khi chưa cài requirements
    LANGFUSE_SDK_AVAILABLE = False

    def observe(*args: Any, **kwargs: Any):
        def decorator(func):
            return func

        return decorator

    class _DummyClient:
        def update_current_span(self, **kwargs: Any) -> None:
            return None

        def update_current_generation(self, **kwargs: Any) -> None:
            return None

    def get_client():
        return _DummyClient()

    @contextmanager
    def propagate_attributes(**kwargs: Any):
        yield


def get_langfuse_client():
    return get_client()


def _safe_update(client: Any, method_name: str, **kwargs: Any) -> bool:
    """Gọi API update của Langfuse SDK một cách an toàn.

    Telemetry không được phép làm hỏng request chính, và client giả lập trong
    test có thể không implement đủ method. Vì vậy mọi lỗi đều bị nuốt và ghi
    lại bằng cờ boolean để test/caller biết span đã được enrich hay chưa.
    """
    method = getattr(client, method_name, None)
    if not callable(method):
        return False
    try:
        method(**kwargs)
    except Exception:  # pragma: no cover - phụ thuộc trạng thái mạng Langfuse
        return False
    return True


def update_span(client: Any, **kwargs: Any) -> bool:
    """Cập nhật span đang active (retrieval span hoặc root span)."""
    return _safe_update(client, "update_current_span", **kwargs)


def update_generation(client: Any, **kwargs: Any) -> bool:
    """Cập nhật generation đang active với model, token và cost."""
    return _safe_update(client, "update_current_generation", **kwargs)


def mark_error(client: Any, *, message: str, generation: bool = False) -> bool:
    """Đánh dấu observation lỗi để waterfall hiển thị đúng mức độ ảnh hưởng."""
    method = "update_current_generation" if generation else "update_current_span"
    return _safe_update(
        client,
        method,
        level="ERROR",
        status_message=message[:200],
    )


def tracing_enabled() -> bool:
    return LANGFUSE_SDK_AVAILABLE and bool(
        os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")
    )

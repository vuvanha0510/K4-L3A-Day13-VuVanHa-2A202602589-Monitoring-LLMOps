"""Thiết lập môi trường tất định cho toàn bộ test.

Máy của học viên có thể đang export sẵn LANGFUSE_* trong shell hoặc trong
`.env`. Nếu không cô lập, test sẽ phụ thuộc vào máy (và có thể gọi mạng
Langfuse thật). Fixture autouse dưới đây đặt lại về giá trị mặc định của
README/PROMPT_VERSIONING.md trước mỗi test.
"""

from __future__ import annotations

import pytest

LANGFUSE_ENV_DEFAULTS = {
    "LANGFUSE_PUBLIC_KEY": "",
    "LANGFUSE_SECRET_KEY": "",
    "LANGFUSE_BASE_URL": "https://cloud.langfuse.com",
    "LANGFUSE_PROMPT_NAME": "day13-chat",
    "LANGFUSE_PROMPT_LABEL": "production",
}


@pytest.fixture(autouse=True)
def _isolated_langfuse_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in LANGFUSE_ENV_DEFAULTS.items():
        monkeypatch.setenv(key, value)
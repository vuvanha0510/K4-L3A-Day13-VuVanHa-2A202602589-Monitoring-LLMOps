"""Tạo và điều khiển prompt version trên Langfuse cho CP2.

Thực hiện đúng quy trình trong `docs/PROMPT_VERSIONING.md`:

1. `create` — tạo version 1 (labels `baseline` + `production`) và version 2
   (label `candidate`). Cả hai giữ đúng ba biến `{{feature}} {{docs}} {{message}}`.
2. `promote` — chuyển label `production` sang version 2.
3. `rollback` — chuyển label `production` về version 1.
4. `list` — in ra version/labels hiện có để đối chiếu với ảnh evidence.

Script dùng đúng key trong `.env` của project cá nhân (`day13-k4-l3a-<MSSV>`).

```bash
python scripts/prompt_versions.py create
python scripts/prompt_versions.py list
python scripts/prompt_versions.py promote --version 2
python scripts/prompt_versions.py rollback
```
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio
from app.tracing import get_langfuse_client, tracing_enabled

PROMPT_V1 = "Feature={{feature}}\nDocs={{docs}}\nQuestion={{message}}\nAnswer briefly and cite the docs."
PROMPT_V2 = (
    "You are a concise support assistant.\n"
    "Feature={{feature}}\n"
    "Docs={{docs}}\n"
    "Question={{message}}\n"
    "Answer in at most three sentences and only use the docs above."
)


def _require_tracing() -> None:
    if not tracing_enabled():
        print(
            "KHÔNG CÓ LANGFUSE KEYS: hãy điền LANGFUSE_PUBLIC_KEY/LANGFUSE_SECRET_KEY "
            "của project cá nhân vào .env trước khi tạo prompt version."
        )
        raise SystemExit(1)


def cmd_create(_: argparse.Namespace) -> int:
    _require_tracing()
    client = get_langfuse_client()

    v1 = client.create_prompt(
        name="day13-chat",
        prompt=PROMPT_V1,
        labels=["baseline", "production"],
        type="text",
        commit_message="CP2 v1: prompt nền, giữ 3 biến theo PROMPT_VERSIONING.md",
    )
    print(f"Đã tạo version {v1.version} (labels: baseline, production)")

    v2 = client.create_prompt(
        name="day13-chat",
        prompt=PROMPT_V2,
        labels=["candidate"],
        type="text",
        commit_message="CP2 v2: rút gọn format và yêu cầu trả lời ngắn",
    )
    print(f"Đã tạo version {v2.version} (labels: candidate)")

    print("Bước tiếp theo: chạy load test với LANGFUSE_PROMPT_LABEL=baseline rồi candidate.")
    return 0


def cmd_list(_: argparse.Namespace) -> int:
    _require_tracing()
    client = get_langfuse_client()
    for label in ("production", "baseline", "candidate"):
        prompt = client.get_prompt("day13-chat", label=label, type="text")
        version = getattr(prompt, "version", "?")
        if getattr(prompt, "is_fallback", False):
            print(f"{label:>10}: chưa có version nào (đang dùng local fallback)")
            continue
        print(f"{label:>10}: version {version}")
    return 0


def cmd_promote(args: argparse.Namespace) -> int:
    _require_tracing()
    client = get_langfuse_client()
    client.update_prompt(name="day13-chat", version=args.version, new_labels=["production"])
    print(f"Đã chuyển label production sang version {args.version}")
    return 0


def cmd_rollback(args: argparse.Namespace) -> int:
    _require_tracing()
    client = get_langfuse_client()
    client.update_prompt(name="day13-chat", version=args.version, new_labels=["production"])
    print(f"Đã rollback label production về version {args.version}")
    return 0


def main() -> int:
    configure_utf8_stdio()
    load_dotenv(REPO_ROOT / ".env", override=False)

    parser = argparse.ArgumentParser(description="Quản lý prompt version trên Langfuse")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("create", help="Tạo v1 (baseline+production) và v2 (candidate)").set_defaults(
        func=cmd_create
    )
    sub.add_parser("list", help="In version theo từng label").set_defaults(func=cmd_list)

    promote = sub.add_parser("promote", help="Chuyển label production sang version")
    promote.add_argument("--version", type=int, required=True)
    promote.set_defaults(func=cmd_promote)

    rollback = sub.add_parser("rollback", help="Đưa label production về version cũ")
    rollback.add_argument("--version", type=int, default=1)
    rollback.set_defaults(func=cmd_rollback)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

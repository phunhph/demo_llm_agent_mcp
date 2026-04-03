# main.py — điểm vào: Agent (stdio MCP) + LLM + DB
import argparse
import asyncio
import os
import sys

from pathlib import Path

from dotenv import load_dotenv

# override=True: ưu tiên file .env trong project hơn biến môi trường Windows (tránh key cũ / hết hạn).
load_dotenv(Path(__file__).resolve().parent / ".env", override=True)

from agent_orchestrator.inventory_agent import run_autonomous_warehouse_agent
from database.seed import seed_demo_iphone

_EXIT_WORDS = frozenset(
    {"exit", "quit", "q", "thoát", "bye", "end", "stop", "thoat"}
)
_DEMO = "Kiểm tra mã hàng IPHONE-15 xem tình hình thế nào?"


def _print_gemini_api_help(exc: BaseException) -> None:
    print("\n[!] Lỗi gọi API Google Gemini.")
    print(f"    {exc}")
    print(
        "\n    • Nếu báo API key expired / INVALID: tạo key mới tại "
        "https://aistudio.google.com/apikey rồi cập nhật GEMINI_API_KEY trong .env"
    )
    print(
        "    • Đảm bảo key bật dịch vụ Generative Language API (AI Studio) cho đúng dự án."
    )
    print(
        "    • Nếu curl OK mà Python báo expired: xóa GOOGLE_API_KEY / GEMINI_API_KEY "
        "trong System Environment (Windows) hoặc dùng .env với override=True (đã bật trong project)."
    )


def _print_gemini_overload_help(exc: BaseException) -> None:
    print("\n[!] Gemini tạm quá tải (503 / high demand) hoặc lỗi phía Google.")
    print(f"    {exc}")
    print(
        "\n    • Chạy lại sau vài phút; chương trình đã tự retry vài lần với chờ giữa các lần."
    )
    print(
        "    • Hoặc đổi GEMINI_MODEL trong .env (ví dụ gemini-2.0-flash, gemini-2.5-flash)."
    )


def _print_db_connection_help(exc: BaseException) -> None:
    print("\n❌ Không kết nối được database.")
    print(f"   Chi tiết: {exc}")
    print(
        "\n   • Nếu đang dùng PostgreSQL: sửa DATABASE_URL trong .env "
        "(đúng user, password, host, port, tên DB)."
    )
    print(
        "   • Hoặc xóa/comment DATABASE_URL trong .env, hoặc thêm "
        "WAREHOUSE_SQLITE_DEMO=1 để ép dùng SQLite (file warehouse_demo.db)."
    )


async def _agent_turn(user_query: str, *, debug: bool) -> None:
    try:
        report = await run_autonomous_warehouse_agent(user_query, debug=debug)
    except Exception as e:
        from google.genai.errors import ClientError, ServerError

        if isinstance(e, ServerError):
            _print_gemini_overload_help(e)
            sys.exit(1)
        if isinstance(e, ClientError) and getattr(e, "code", None) == 429:
            _print_gemini_overload_help(e)
            sys.exit(1)
        if isinstance(e, ClientError):
            _print_gemini_api_help(e)
            sys.exit(1)
        raise
    print("\n" + "=" * 50)
    print("📋 Trả lời")
    print("=" * 50)
    print(report or "(rỗng)")


async def _run_session(args: argparse.Namespace) -> None:
    if args.seed or args.seed_only:
        try:
            msg = await seed_demo_iphone()
        except OSError as e:
            _print_db_connection_help(e)
            raise SystemExit(1) from e
        except Exception as e:
            err = str(e).lower()
            if "password" in err or "authentication" in err or "invalidpassword" in err.replace(
                " ", ""
            ):
                _print_db_connection_help(e)
                raise SystemExit(1) from e
            raise
        print(f"🌱 {msg}")
        if args.seed_only:
            return

    if not os.getenv("GEMINI_API_KEY"):
        print("❌ Thiếu GEMINI_API_KEY trong môi trường hoặc file .env")
        sys.exit(1)

    from database.db_config import DATABASE_URL, IS_SQLITE

    db_label = "SQLite (warehouse_demo.db)" if IS_SQLITE else "PostgreSQL"
    print(
        f"🚀 Hệ thống: Gemini → Agent (ReAct) → MCP stdio → Warehouse Server → DB ({db_label})\n"
        f"   DATABASE_URL: {DATABASE_URL}\n"
    )

    # Câu đầu tiên
    if args.query is not None:
        first = args.query.strip() or _DEMO
    else:
        print()
        print("💬 Gõ câu hỏi rồi Enter (để trống = dùng mẫu demo IPHONE-15):")
        try:
            first = input("> ").strip()
        except EOFError:
            print("\nThoát.")
            return
        if not first:
            first = _DEMO

    await _agent_turn(first, debug=args.debug)

    if args.once:
        return

    # Chat nhiều lượt
    while True:
        print()
        print("💬 Hỏi tiếp (exit / quit / thoát / q = thoát):")
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nThoát.")
            break
        if not line:
            continue
        if line.lower() in _EXIT_WORDS:
            print("Tạm biệt.")
            break
        await _agent_turn(line, debug=args.debug)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    p = argparse.ArgumentParser(
        description="Demo kho ảo: policy từ file, MCP tools, chat nhiều lượt."
    )
    p.add_argument(
        "--query",
        "-q",
        default=None,
        metavar="TEXT",
        help="Câu đầu tiên (tuỳ chọn). Không dùng --once thì sau đó vẫn hỏi tiếp trong terminal.",
    )
    p.add_argument(
        "--once",
        action="store_true",
        help="Chỉ xử lý một câu (từ -q hoặc lần nhập đầu) rồi thoát — không lặp chat.",
    )
    p.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="In log [LLM] / [Agent] / [MCP] để gỡ lỗi luồng.",
    )
    p.add_argument(
        "--seed",
        action="store_true",
        help="Seed/reset dữ liệu demo (IPHONE-15, MACBOOK-AIR, đơn DH-2025-*) trước khi chạy agent.",
    )
    p.add_argument(
        "--seed-only",
        action="store_true",
        help="Chỉ seed DB rồi thoát (không gọi LLM).",
    )
    args = p.parse_args()

    try:
        asyncio.run(_run_session(args))
    except KeyboardInterrupt:
        print("\n\nThoát (Ctrl+C).")
        sys.exit(130)


if __name__ == "__main__":
    main()

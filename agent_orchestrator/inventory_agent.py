# agent_orchestrator/inventory_agent.py
"""
Luồng quan hệ (demo):
- LLM (Gemini): đọc chính sách + tin nhắn, chọn tool và tham số.
- Agent: vòng ReAct — gọi Gemini → nếu có function_call thì gọi MCP → đưa FunctionResponse lại cho Gemini.
- MCP: stdio tới Warehouse Server (list_tools / call_tool).
- Warehouse Server: FastMCP + SQLAlchemy → DB.

Không dùng if-else nghiệp vụ trong Python; quy tắc trong warehouse_policy.txt + system_instruction.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import ClientError, ServerError
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env", override=True)

_POLICY_PATH = Path(__file__).resolve().parent / "warehouse_policy.txt"

# Khớp REST: v1beta/models/gemini-flash-latest — đổi qua GEMINI_MODEL trong .env nếu cần
_DEFAULT_MODEL = "gemini-flash-latest"


def _gemini_api_key() -> str:
    """Chỉ dùng GEMINI_API_KEY (không lẫn GOOGLE_API_KEY hệ thống). Chuẩn hoá dấu ngoặc/khoảng trắng."""
    raw = (os.getenv("GEMINI_API_KEY") or "").strip().strip('"').strip("'")
    if not raw:
        raise ValueError("Thiếu GEMINI_API_KEY trong .env (hoặc đang trống sau khi chuẩn hoá).")
    return raw


def _client() -> genai.Client:
    return genai.Client(api_key=_gemini_api_key())


def _model_id() -> str:
    return (os.getenv("GEMINI_MODEL") or _DEFAULT_MODEL).strip()


def _load_policy_text() -> str:
    if _POLICY_PATH.is_file():
        return _POLICY_PATH.read_text(encoding="utf-8").strip()
    return (
        "Nếu tồn kho < ngưỡng an toàn, nhập thêm 100 đơn vị (gọi execute_stock_update)."
    )


def _retryable_gemini_error(exc: Exception) -> bool:
    """503/429/500 hoặc thông báo quá tải — nên thử lại sau vài giây."""
    code = getattr(exc, "code", None)
    if code in (429, 500, 503):
        return True
    msg = str(exc).lower()
    return any(
        s in msg
        for s in (
            "unavailable",
            "high demand",
            "overloaded",
            "resource exhausted",
            "try again later",
        )
    )


async def _generate_content_with_retry(
    client: genai.Client,
    *,
    model: str,
    contents: list,
    config,
    debug: bool,
) -> Any:
    max_retries = max(1, int(os.getenv("GEMINI_MAX_RETRIES", "5")))
    base = float(os.getenv("GEMINI_RETRY_BASE_SECONDS", "1.5"))
    for attempt in range(max_retries):
        try:
            return await client.aio.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
        except (ClientError, ServerError) as e:
            if not _retryable_gemini_error(e) or attempt >= max_retries - 1:
                raise
            wait = base * (2**attempt)
            _dbg(
                debug,
                "LLM",
                f"API tạm thất bại (thử {attempt + 1}/{max_retries}), chờ {wait:.1f}s",
                str(e)[:300],
            )
            await asyncio.sleep(wait)
    raise RuntimeError("Gemini: hết số lần retry mà không trả response")


def _dbg(enabled: bool, layer: str, message: str, extra: str | None = None) -> None:
    if not enabled:
        return
    line = f"[{layer}] {message}"
    if extra:
        line = f"{line} | {extra}"
    print(line, flush=True)


def _mcp_tools_to_gemini(
    mcp_tools,
) -> list[types.FunctionDeclaration]:
    out: list[types.FunctionDeclaration] = []
    for t in mcp_tools.tools:
        decl = types.FunctionDeclaration(
            name=t.name,
            description=t.description or "",
        )
        schema = getattr(t, "inputSchema", None) or getattr(t, "input_schema", None)
        if isinstance(schema, dict) and schema:
            decl.parameters_json_schema = schema
        out.append(decl)
    return out


async def run_autonomous_warehouse_agent(query: str, *, debug: bool = False) -> str:
    policy = _load_policy_text()
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_servers.warehouse_server"],
        cwd=str(_ROOT),
    )

    system_instruction = (
        "Bạn là nhân viên kho ảo. Bạn chỉ được dùng các tool đã liệt kê để đọc/ghi dữ liệu thực.\n\n"
        "=== CHÍNH SÁCH (tuân thủ nghiêm) ===\n"
        f"{policy}\n"
    )

    client = _client()
    model = _model_id()

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            mcp_tools = await session.list_tools()
            declarations = _mcp_tools_to_gemini(mcp_tools)

            _dbg(
                debug,
                "MCP",
                f"Đã kết nối Warehouse Server; {len(declarations)} tool(s): "
                + ", ".join(d.name or "?" for d in declarations),
            )

            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=[types.Tool(function_declarations=declarations)],
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=True
                ),
            )

            contents: list[types.Content] = [
                types.Content(
                    role="user",
                    parts=[types.Part(text=query)],
                )
            ]

            while True:
                _dbg(debug, "LLM", "Gọi Gemini", model)
                response = await _generate_content_with_retry(
                    client,
                    model=model,
                    contents=contents,
                    config=config,
                    debug=debug,
                )

                if not response.candidates:
                    fb = response.prompt_feedback
                    raise RuntimeError(
                        f"Gemini không trả candidate (prompt_feedback={fb})"
                    )

                cand = response.candidates[0]
                fcs = response.function_calls
                if not fcs:
                    final = response.text or ""
                    _dbg(debug, "LLM", "Kết thúc (không còn function_call)", final[:500])
                    return final

                if cand.content:
                    contents.append(cand.content)

                parts_out: list[types.Part] = []
                for fc in fcs:
                    name = fc.name or ""
                    args = fc.args if isinstance(fc.args, dict) else {}
                    _dbg(debug, "Agent", f"Tool call: {name}", str(args))

                    result = await session.call_tool(name, args)
                    text = ""
                    if result.content:
                        text = result.content[0].text
                    _dbg(debug, "MCP", f"Kết quả {name}", (text or "")[:800])

                    parts_out.append(
                        types.Part(
                            function_response=types.FunctionResponse(
                                id=fc.id,
                                name=name,
                                response={"result": text},
                            )
                        )
                    )

                contents.append(types.Content(role="user", parts=parts_out))

# mcp_servers/warehouse_server.py — MCP "Tay chân": chỉ thực thi truy vấn/ghi DB, không suy luận
import os
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from sqlalchemy import select, update

from database.db_config import AsyncSessionLocal
from database.models import Inventory, Order
from mcp_servers.validators import check_reorder_logic

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env", override=True)

mcp = FastMCP("Smart_Warehouse_System")

_MCP_DEBUG = os.getenv("WAREHOUSE_MCP_DEBUG", "").lower() in ("1", "true", "yes")


def _dbg(msg: str) -> None:
    if _MCP_DEBUG:
        print(f"[MCP-SERVER] {msg}", flush=True)


@mcp.tool()
async def list_all_inventory() -> str:
    """Liệt kê toàn bộ mặt hàng trong kho: SKU, tên, số lượng, ngưỡng an toàn, vị trí kho."""
    _dbg("list_all_inventory()")
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Inventory).order_by(Inventory.sku))
        rows = result.scalars().all()
        if not rows:
            return "INFO: Kho đang trống (chưa có SKU nào)."
        lines = ["INFO: Danh sách tồn kho:"]
        for it in rows:
            lines.append(
                f"  • {it.sku} | {it.item_name} | tồn {it.quantity} | "
                f"ngưỡng {it.min_threshold} | {it.warehouse_loc}"
            )
        return "\n".join(lines)


@mcp.tool()
async def list_orders(status_filter: str = "") -> str:
    """Liệt kê mã đơn hàng. Tham số status_filter: pending, preparing, shipped, completed — để trống = tất cả."""
    _dbg(f"list_orders(status_filter={status_filter!r})")
    async with AsyncSessionLocal() as session:
        q = select(Order).order_by(Order.created_at.desc())
        sf = (status_filter or "").strip().lower()
        if sf:
            q = q.where(Order.status == sf)
        result = await session.execute(q)
        rows = result.scalars().all()
        if not rows:
            return "INFO: Không có đơn hàng nào khớp bộ lọc." if sf else "INFO: Chưa có đơn hàng."
        lines = ["INFO: Danh sách đơn hàng (mã đơn | SKU | SL | trạng thái | ghi chú):"]
        for o in rows:
            note = o.note or ""
            lines.append(
                f"  • {o.order_code} | {o.sku} x{o.qty} | {o.status} | {note}"
            )
        return "\n".join(lines)


@mcp.tool()
async def get_order_detail(order_code: str) -> str:
    """Xem chi tiết một đơn hàng theo mã đơn (order_code), ví dụ DH-2025-001."""
    _dbg(f"get_order_detail(order_code={order_code!r})")
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Order).where(Order.order_code == order_code.strip())
        )
        o = result.scalar_one_or_none()
        if not o:
            return f"ERROR: Không tìm thấy đơn {order_code!r}."
        return (
            f"INFO: Đơn {o.order_code}\n"
            f"  SKU: {o.sku}, số lượng: {o.qty}\n"
            f"  Trạng thái: {o.status}\n"
            f"  Ghi chú: {o.note or '(không)'}"
        )


@mcp.tool()
async def get_inventory_status(sku: str) -> str:
    """Đọc tồn kho và ngưỡng an toàn (min_threshold) cho một SKU."""
    _dbg(f"get_inventory_status(sku={sku!r})")
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Inventory).where(Inventory.sku == sku))
        item = result.scalar_one_or_none()
        if item:
            return (
                f"INFO: {item.item_name} (SKU {sku}) còn {item.quantity} đơn vị. "
                f"Ngưỡng an toàn: {item.min_threshold}."
            )
        return f"ERROR: SKU {sku} không tồn tại."


@mcp.tool()
async def execute_stock_update(sku: str, amount: int) -> str:
    """Cộng thêm số lượng vào tồn kho sau khi kiểm tra nghiệp vụ (amount > 0)."""
    _dbg(f"execute_stock_update(sku={sku!r}, amount={amount!r})")
    if not check_reorder_logic(amount):
        return "ERROR: Số lượng nhập không hợp lệ (phải là số nguyên > 0)."

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Inventory).where(Inventory.sku == sku))
        item = result.scalar_one_or_none()
        if not item:
            return f"ERROR: SKU {sku} không tồn tại — không thể cập nhật."

        await session.execute(
            update(Inventory)
            .where(Inventory.sku == sku)
            .values(quantity=Inventory.quantity + amount)
        )
        await session.commit()
        return f"SUCCESS: Đã nhập thêm {amount} đơn vị cho SKU {sku}."


if __name__ == "__main__":
    mcp.run(transport="stdio")

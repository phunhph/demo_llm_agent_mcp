# database/seed.py — dữ liệu demo: tồn kho + đơn hàng mẫu
from sqlalchemy import select

from database.db_config import AsyncSessionLocal, ensure_demo_schema
from database.models import Inventory, Order


async def seed_demo_iphone() -> str:
    await ensure_demo_schema()
    async with AsyncSessionLocal() as session:
        # --- Inventory ---
        for sku, name, qty, thr, loc in (
            ("IPHONE-15", "iPhone 15", 5, 10, "WH-001"),
            ("MACBOOK-AIR", "MacBook Air 13\"", 12, 5, "WH-001"),
        ):
            r = await session.execute(select(Inventory).where(Inventory.sku == sku))
            row = r.scalar_one_or_none()
            if row:
                row.item_name = name
                row.quantity = qty
                row.min_threshold = thr
                row.warehouse_loc = loc
            else:
                session.add(
                    Inventory(
                        sku=sku,
                        item_name=name,
                        quantity=qty,
                        min_threshold=thr,
                        warehouse_loc=loc,
                    )
                )

        await session.commit()

        # --- Orders (mã đơn hàng) ---
        demo_orders = (
            ("DH-2025-001", "IPHONE-15", 2, "preparing", "Đơn lẻ"),
            ("DH-2025-002", "MACBOOK-AIR", 1, "pending", "Khách doanh nghiệp"),
            ("DH-2025-003", "IPHONE-15", 5, "shipped", "Giao miền Nam"),
        )
        for code, sku, q, st, note in demo_orders:
            r = await session.execute(select(Order).where(Order.order_code == code))
            o = r.scalar_one_or_none()
            if o:
                o.sku = sku
                o.qty = q
                o.status = st
                o.note = note
            else:
                session.add(
                    Order(
                        order_code=code,
                        sku=sku,
                        qty=q,
                        status=st,
                        note=note,
                    )
                )

        await session.commit()

    return (
        "Đã seed/reset demo: IPHONE-15 (tồn 5), MACBOOK-AIR (tồn 12); "
        "đơn DH-2025-001, DH-2025-002, DH-2025-003."
    )

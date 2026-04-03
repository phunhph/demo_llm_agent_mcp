# database/models.py
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Inventory(Base):
    __tablename__ = "inventory"

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    item_name: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    min_threshold: Mapped[int] = mapped_column(Integer, default=10)
    warehouse_loc: Mapped[str] = mapped_column(String(50))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class Order(Base):
    """Đơn hàng xuất / đặt hàng (demo)."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    sku: Mapped[str] = mapped_column(String(50), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
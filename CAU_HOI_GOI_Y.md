# Hệ thống có thể trả lời những gì? (gợi ý câu hỏi)

Tài liệu mô tả **phạm vi demo** kho ảo: dữ liệu nằm trong DB (SQLite/PostgreSQL), AI chỉ trả lời dựa trên **công cụ MCP** đã kết nối — không có dữ liệu ngoài bảng `inventory` và `orders`.

---

## 1. Tồn kho & mặt hàng

| Công cụ (MCP) | Ý nghĩa |
|---------------|---------|
| `list_all_inventory` | Liệt kê **toàn bộ** SKU: tên, số lượng, ngưỡng an toàn, vị trí kho |
| `get_inventory_status` | Xem **một SKU** cụ thể |
| `execute_stock_update` | **Nhập thêm** số lượng cho một SKU (theo chính sách trong `warehouse_policy.txt`) |

**Ví dụ câu hỏi tự nhiên (tiếng Việt):**

- “Trong kho đang có những mặt hàng nào?”
- “Liệt kê toàn bộ tồn kho.”
- “IPHONE-15 còn bao nhiêu cái?”
- “Kiểm tra tồn MACBOOK-AIR.”
- “Mặt hàng nào đang dưới ngưỡng an toàn?” (AI sẽ cần đọc tồn rồi so sánh.)
- “Nhập thêm hàng cho IPHONE-15” / “Cần nhập bổ sung nếu thiếu” (agent sẽ đọc chính sách + gọi tool phù hợp.)

**Lưu ý:** Chính sách nhập bổ sung (số lượng, điều kiện) được cấu hình trong `agent_orchestrator/warehouse_policy.txt`, không hard-code trong code Python.

---

## 2. Đơn hàng (mã đơn)

| Công cụ (MCP) | Ý nghĩa |
|---------------|---------|
| `list_orders` | Liệt kê đơn: mã đơn, SKU, số lượng, trạng thái, ghi chú. Có thể lọc theo trạng thái |
| `get_order_detail` | Chi tiết **một** đơn theo `order_code` |

**Trạng thái dùng cho lọc:** `pending`, `preparing`, `shipped`, `completed` (để trống = tất cả.)

**Ví dụ câu hỏi:**

- “Tôi đang có những mã đơn hàng nào?”
- “Liệt kê đơn đang pending.”
- “Chi tiết đơn DH-2025-001.”
- “Đơn nào đã shipped?”

---

## 3. Dữ liệu mẫu sau `python main.py --seed`

Sau khi chạy kèm `--seed`, DB demo thường có:

**Tồn kho**

| SKU | Gợi ý |
|-----|--------|
| `IPHONE-15` | iPhone 15 — tồn thấp hơn ngưỡng (phù hợp kịch bản “nhập thêm”) |
| `MACBOOK-AIR` | MacBook Air 13" |

**Đơn hàng**

| Mã đơn | Gợi ý |
|--------|--------|
| `DH-2025-001` | preparing |
| `DH-2025-002` | pending |
| `DH-2025-003` | shipped |

(Có thể thay đổi nếu bạn sửa `database/seed.py`.)

---

## 4. Những thứ hệ thống *không* có sẵn

- Không có công cụ cho: **nhân sự**, **CRM**, **thanh toán**, **vận chuyển thật**, **email**, **web search**.
- Không có bảng khác ngoài `inventory` và `orders` — hỏi “doanh thu tháng này” sẽ không có dữ liệu thật trong DB.
- Mọi con số về kho/đơn cần đến từ **kết quả tool**; nếu không gọi được tool, AI không nên bịa số liệu (theo policy).

---

## 5. Cách hỏi trong terminal

- Chạy `python main.py` (có thể thêm `--seed`, `--debug`): nhập câu đầu → nhận trả lời → **hỏi tiếp** tại dòng `> `.
- Thoát vòng chat: gõ `exit`, `quit`, `thoát`, `q`, `bye`, … hoặc **Ctrl+C**.
- Một câu rồi thoát: thêm `--once` (ví dụ `python main.py --once -q "Liệt kê đơn hàng"`).

---

## 6. File liên quan

| File | Vai trò |
|------|---------|
| `agent_orchestrator/warehouse_policy.txt` | Chính sách kho (ưu tiên nhập bổ sung, v.v.) |
| `mcp_servers/warehouse_server.py` | Định nghĩa tool MCP thực tế |
| `database/seed.py` | Dữ liệu demo |

---

*Tài liệu phản ánh trạng thái codebase tại thời điểm tạo file; nếu thêm tool/bảng mới, nên cập nhật mục tương ứng.*

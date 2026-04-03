/smart-warehouse-ai
│
├── /database               # Tầng dữ liệu (Data Persistence Layer)
│   ├── models.py           # Định nghĩa các bảng (SQLAlchemy Models)
│   └── db_config.py        # Cấu hình kết nối Async Engine
│
├── /migrations             # Thư mục chứa lịch sử Migration (Alembic)
│   └── env.py              # Cấu hình Alembic để nhận diện Models
│
├── /mcp_servers            # Tầng hạ tầng & Công cụ (Infrastructure Layer)
│   ├── warehouse_server.py # MCP Server: Bridge giữa AI và DB
│   └── validators.py       # Business Logic: Kiểm tra điều kiện nhập/xuất
│
├── /      # Tầng điều phối (Reasoning Layer)
│   └── inventory_agent.py  # Agent: Bộ não xử lý ReAct Loop
│
├── alembic.ini             # File cấu hình của Alembic
├── main.py                 # Điểm khởi chạy hệ thống (Entry Point)
├── .env                    # Biến môi trường (DB_URL, API_KEYS)
└── requirements.txt        # Thư viện: mcp, sqlalchemy, alembic, asyncpg, openai
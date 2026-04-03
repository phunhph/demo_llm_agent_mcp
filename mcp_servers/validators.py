# mcp_servers/validators.py — kiểm tra điều kiện nghiệp vụ (không chứa logic LLM/Agent)


def check_reorder_logic(amount: int) -> bool:
    """Số lượng nhập phải là số nguyên dương."""
    return isinstance(amount, int) and amount > 0

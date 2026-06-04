from database import (
    add_stock_log,
    get_inventory_item,
    get_product,
    init_db,
    list_low_stock_products,
    list_alerts,
    list_inventory,
    list_logs,
    sync_low_stock_alerts,
    set_inventory_quantity,
    upsert_product,
)


def ensure_database() -> None:
    init_db()


def resolve_product_id(raw_value) -> str:
    return str(raw_value or "").strip()


def _to_positive_int(value, field_name: str):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None, f"{field_name}는 숫자로 입력해야 합니다."

    if parsed <= 0:
        return None, f"{field_name}는 1 이상의 값이어야 합니다."

    return parsed, None


def register_product(product_id: str, name: str, min_quantity=0):
    product_id = resolve_product_id(product_id)
    name = str(name or "").strip()

    if not product_id:
        return {"ok": False, "message": "상품 ID를 입력하세요."}
    if not name:
        return {"ok": False, "message": "상품명을 입력하세요."}

    try:
        min_quantity_value = int(min_quantity)
        if min_quantity_value < 0:
            raise ValueError
    except (TypeError, ValueError):
        return {"ok": False, "message": "최소 수량은 0 이상의 숫자여야 합니다."}

    upsert_product(product_id, name, min_quantity_value)
    sync_low_stock_alerts()
    return {"ok": True, "message": f"상품 {product_id} 등록 또는 수정이 완료되었습니다."}


def adjust_stock(product_id: str, action: str, quantity=1, username: str = "system"):
    product_id = resolve_product_id(product_id)
    if not product_id:
        return {"ok": False, "message": "상품 ID를 입력하세요."}

    product = get_product(product_id)
    if not product:
        return {"ok": False, "message": "등록된 상품이 아닙니다. 먼저 상품을 등록하세요."}

    parsed_quantity, error_message = _to_positive_int(quantity, "수량")
    if error_message:
        return {"ok": False, "message": error_message}

    current_item = get_inventory_item(product_id)
    current_quantity = current_item["quantity"] if current_item else 0

    normalized_action = str(action or "").lower().strip()
    if normalized_action not in {"in", "out"}:
        return {"ok": False, "message": "입고 또는 출고 동작을 선택하세요."}

    if normalized_action == "out" and current_quantity < parsed_quantity:
        return {"ok": False, "message": f"재고가 부족합니다. 현재 재고: {current_quantity}"}

    next_quantity = current_quantity + parsed_quantity if normalized_action == "in" else current_quantity - parsed_quantity
    set_inventory_quantity(product_id, next_quantity)

    change_type = "IN" if normalized_action == "in" else "OUT"
    add_stock_log(product_id, change_type, parsed_quantity, username=username)

    sync_low_stock_alerts()

    action_text = "입고" if normalized_action == "in" else "출고"
    return {
        "ok": True,
        "message": f"{product['name']} {action_text} 처리 완료. 현재 재고: {next_quantity}",
    }


def get_inventory_rows():
    return list_inventory()


def get_logs():
    return list_logs()


def get_alerts():
    return list_alerts()


def get_dashboard_counts():
    inventory_rows = list_inventory()
    low_stock_count = len(list_low_stock_products())

    return {
        "products": len(inventory_rows),
        "low_stock": low_stock_count,
        "logs": len(list_logs(limit=1000)),
        "alerts": len(list_alerts(limit=1000)),
    }
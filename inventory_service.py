from database import fetch_records_by_material, insert_record


def get_stock(material, unit):
    records = fetch_records_by_material(material, unit)

    current_stock = 0

    for item in records:
        if item["type"] == "入库":
            current_stock += item["quantity"]
        elif item["type"] == "出库":
            current_stock -= item["quantity"]

    return {
        "material": material,
        "unit": unit,
        "current_stock": current_stock,
        "records": records
    }


def create_inventory_record(material, type, quantity, unit):

    if type not in ["入库", "出库"]:
        return {
            "success": False,
            "message": "类型必须是入库或出库"
        }

    if quantity <= 0:
        return {
            "success": False,
            "message": "数量必须大于0"
        }

    if type == "出库":
        stock_result = get_stock(material, unit)

        if quantity > stock_result["current_stock"]:
            return {
                "success": False,
                "message": "库存不足，无法出库"
            }

    insert_record(
        material,
        type,
        quantity,
        unit
    )

    return {
        "success": True,
        "message": "库存记录保存成功",
        "material": material,
        "type": type,
        "quantity": quantity,
        "unit": unit
    }
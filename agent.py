import os
import json

from openai import OpenAI
from inventory_service import get_stock, create_inventory_record


client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)


# 暂存“等待用户确认”的写操作
pending_action = None


tools = [
    {
        "type": "function",
        "name": "get_stock",
        "description": (
            "只用于查询库存。"
            "用户询问当前库存、还有多少库存时调用。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "material": {"type": "string"},
                "unit": {"type": "string"}
            },
            "required": ["material", "unit"]
        }
    },
    {
        "type": "function",
        "name": "create_inventory_record",
        "description": (
            "用于入库或出库。"
            "用户明确要求新增入库或出库记录时调用。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "material": {"type": "string"},
                "type": {
                    "type": "string",
                    "enum": ["入库", "出库"]
                },
                "quantity": {"type": "number"},
                "unit": {"type": "string"}
            },
            "required": ["material", "type", "quantity", "unit"]
        }
    }
]


def ask_agent(user_message):
    global pending_action

    # 1. 如果已经有等待确认的操作
    if pending_action:

        if user_message in ["确认", "确认执行", "继续"]:
            result = create_inventory_record(
                pending_action["material"],
                pending_action["type"],
                pending_action["quantity"],
                pending_action["unit"]
            )

            pending_action = None
            return result["message"]

        if user_message in ["取消", "取消执行"]:
            pending_action = None
            return "操作已取消"

        return "当前有一条待确认操作，请回复“确认”或“取消”。"

    # 2. 没有待确认操作时，让模型判断工具
    response = client.responses.create(
        model="deepseek-flash",
        instructions=(
            "你是库存助手。"
            "查询库存使用 get_stock。"
            "入库或出库使用 create_inventory_record。"
        ),
        input=user_message,
        tools=tools,
        reasoning={"effort": "none"}
    )

    for item in response.output:

        if item.type == "function_call":
            args = json.loads(item.arguments)

            print("模型选择工具：", item.name)
            print("模型生成参数：", args)

            # 查询可以直接执行
            if item.name == "get_stock":
                result = get_stock(
                    args["material"],
                    args["unit"]
                )

                return (
                    f'{result["material"]}当前库存为 '
                    f'{result["current_stock"]}{result["unit"]}'
                )

            # 写操作不直接执行，先保存状态
            if item.name == "create_inventory_record":
                pending_action = args

                return (
                    f'确认{args["type"]}'
                    f'{args["quantity"]}{args["unit"]}'
                    f'{args["material"]}吗？'
                    f'请回复“确认”或“取消”。'
                )

    return response.output_text
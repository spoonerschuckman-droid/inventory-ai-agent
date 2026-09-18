import os
import json

from openai import OpenAI
from database import fetch_records_by_material


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
        "current_stock": current_stock
    }


client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)


tools = [
    {
        "type": "function",
        "name": "get_stock",
        "description": "查询指定物料和单位的当前库存",
        "parameters": {
            "type": "object",
            "properties": {
                "material": {
                    "type": "string",
                    "description": "物料名称"
                },
                "unit": {
                    "type": "string",
                    "description": "库存单位，例如斤、克、吨"
                }
            },
            "required": ["material", "unit"]
        }
    }
]


user_message = "金刚石微粉现在还有多少斤？"


response = client.responses.create(
    model="deepseek-flash",
    input=user_message,
    tools=tools
)


for item in response.output:
    if item.type == "function_call":

        print("模型决定调用：", item.name)
        print("模型生成参数：", item.arguments)

        args = json.loads(item.arguments)

        result = get_stock(
            args["material"],
            args["unit"]
        )

        print("真实数据库结果：", result)

        final_response = client.responses.create(
            model="deepseek-flash",
            input=[
                {
                    "role": "user",
                    "content": user_message
                },
                {
                    "type": "function_call",
                    "call_id": item.call_id,
                    "name": item.name,
                    "arguments": item.arguments
                },
                {
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps(
                        result,
                        ensure_ascii=False
                    )
                }
            ],
            tools=tools
        )

        print("AI最终回答：", final_response.output_text)
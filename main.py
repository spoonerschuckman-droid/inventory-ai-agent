from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Literal
from database import insert_record, fetch_records, fetch_records_by_material
from agent import ask_agent
from inventory_service import get_stock as get_stock_service

app = FastAPI()


class InventoryRecord(BaseModel):
    material: str = Field(min_length=1)
    type: Literal["入库", "出库"]
    quantity: float = Field(gt=0)
    unit: str = Field(min_length=1)

class AgentQuery(BaseModel):
    message: str = Field(min_length=1)


@app.get("/")
def home():
    return {"message": "inventory-ai-agent is running"}

def calculate_stock(records):
    stock = {}

    for item in records:
        key = f'{item["material"]}_{item["unit"]}'

        if key not in stock:
            stock[key] = 0

        if item["type"] == "入库":
            stock[key] += item["quantity"]
        elif item["type"] == "出库":
            stock[key] -= item["quantity"]

    return stock

@app.post("/inventory")
def create_inventory(record: InventoryRecord):

    records = fetch_records()
    stock = calculate_stock(records)

    key = f"{record.material}_{record.unit}"
    current_stock = stock.get(key, 0)

    if record.type == "出库" and record.quantity > current_stock:
        raise HTTPException(
            status_code=400,
            detail="库存不足，无法出库"
        )

    insert_record(
        record.material,
        record.type,
        record.quantity,
        record.unit
    )

    return {
        "message": "库存记录保存成功",
        "data": record
    }

@app.get("/inventory")
def get_inventory():

    records = fetch_records()
    stock = calculate_stock(records)

    return {
        "records": records,
        "current_stock": stock
    }

@app.get("/stock")
def get_stock_api(material: str, unit: str):
    return get_stock_service(material, unit)

@app.post("/agent/query")
def agent_query(query: AgentQuery):

    answer = ask_agent(query.message)

    return {
        "message": query.message,
        "answer": answer
    }
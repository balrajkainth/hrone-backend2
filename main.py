from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from pymongo import MongoClient
from bson import ObjectId

# MongoDB connection
client = MongoClient("mongodb+srv://<username>:<password>@cluster0.mongodb.net/hrone?retryWrites=true&w=majority")
db = client["hrone"]
product_collection = db["products"]
order_collection = db["orders"]

# App init
app = FastAPI()

# Allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helpers
def obj_id_str(doc):
    doc["id"] = str(doc["_id"])
    del doc["_id"]
    return doc

# Models
class SizeItem(BaseModel):
    size: str
    quantity: int

class Product(BaseModel):
    name: str
    price: float
    sizes: List[SizeItem]

class OrderItem(BaseModel):
    productId: str
    qty: int

class Order(BaseModel):
    userId: str
    items: List[OrderItem]

# 1. Create Product
@app.post("/products", status_code=201)
def create_product(product: Product):
    result = product_collection.insert_one(product.dict())
    return {"id": str(result.inserted_id)}

# 2. Get Products
@app.get("/products")
def list_products(
    name: Optional[str] = Query(None),
    size: Optional[str] = Query(None),
    limit: int = Query(10),
    offset: int = Query(0)
):
    query = {}
    if name:
        query["name"] = {"$regex": name, "$options": "i"}
    if size:
        query["sizes.size"] = size

    cursor = product_collection.find(query).skip(offset).limit(limit)
    products = [obj_id_str(p) for p in cursor]

    return {
        "data": products,
        "page": {
            "next": offset + limit,
            "limit": len(products),
            "previous": offset - limit
        }
    }

# 3. Create Order
@app.post("/orders", status_code=201)
def create_order(order: Order):
    result = order_collection.insert_one(order.dict())
    return {"id": str(result.inserted_id)}

# 4. Get Orders for a User
@app.get("/orders/{user_id}")
def get_orders(user_id: str, limit: int = 10, offset: int = 0):
    cursor = order_collection.find({"userId": user_id}).skip(offset).limit(limit)
    orders = []

    for order in cursor:
        total = 0
        enriched_items = []
        for item in order["items"]:
            prod = product_collection.find_one({"_id": ObjectId(item["productId"])})
            if prod:
                prod_info = {"id": str(prod["_id"]), "name": prod["name"]}
                total += item["qty"] * prod["price"]
                enriched_items.append({"productDetails": prod_info, "qty": item["qty"]})
        orders.append({
            "id": str(order["_id"]),
            "items": enriched_items,
            "total": total
        })

    return {
        "data": orders,
        "page": {
            "next": offset + limit,
            "limit": len(orders),
            "previous": offset - limit
        }
    }

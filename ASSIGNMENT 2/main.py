from fastapi import FastAPI, Query, Path, HTTPException
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional

app = FastAPI()

products = [
    {"id": 1, "name": "Wireless Mouse", "price": 799, "category": "Electronics", "in_stock": True},
    {"id": 2, "name": "Notebook", "price": 149, "category": "Stationery", "in_stock": True},
    {"id": 3, "name": "Gaming Chair", "price": 12000, "category": "Furniture", "in_stock": False},
    {"id": 4, "name": "Desk Lamp", "price": 899, "category": "Electronics", "in_stock": True},
    {"id": 5, "name": "Laptop Stand", "price": 1299, "category": "Electronics", "in_stock": True},
    {"id": 6, "name": "Mechanical Keyboard", "price": 2499, "category": "Electronics", "in_stock": True},
    {"id": 7, "name": "Webcam", "price": 1899, "category": "Electronics", "in_stock": False},
]

feedback_db = [] 
orders_db = {}   


@app.get("/")
def home():
    return {"message": "Welcome to the E-commerce API Day 1 Assignment"}

@app.get("/products")
def get_all_products():
    return {"products": products, "total": len(products)}

@app.get("/products/category/{category_name}")
def get_by_category(category_name: str):
    result = [p for p in products if p["category"].lower() == category_name.lower()]
    if not result:
        return {"error": f"No products found in category: {category_name}"}
    return {"category": category_name, "products": result, "total": len(result)}

@app.get("/products/instock")
def get_instock():
    available = [p for p in products if p["in_stock"]]
    return {"in_stock_products": available, "count": len(available)}

@app.get("/store/summary")
def store_summary():
    in_stock_count = len([p for p in products if p["in_stock"]])
    out_stock_count = len(products) - in_stock_count
    categories = list(set([p["category"] for p in products]))
    return {
        "store_name": "My E-commerce Store",
        "total_products": len(products),
        "in_stock": in_stock_count,
        "out_of_stock": out_stock_count,
        "categories": categories,
    }

@app.get("/products/search/{keyword}")
def search_products(keyword: str):
    results = [p for p in products if keyword.lower() in p["name"].lower()]
    if not results:
        return {"message": "No products matched your search"}
    return {"keyword": keyword, "results": results, "total_matches": len(results)}

@app.get("/products/deals")
def get_deals():
    if not products:
        return {"message": "No products available"}
    cheapest = min(products, key=lambda p: p["price"])
    expensive = max(products, key=lambda p: p["price"])
    return {"best_deal": cheapest, "premium_pick": expensive}


# --- DAY 2 TASKS ---

@app.get("/products/filter")
def filter_products(
    min_price: int = Query(0, ge=0), 
    max_price: Optional[int] = None, 
    category: Optional[str] = None
):
    filtered = products
    if category:
        filtered = [p for p in filtered if p["category"].lower() == category.lower()]
    
    filtered = [p for p in filtered if p["price"] >= min_price]
    
    if max_price:
        filtered = [p for p in filtered if p["price"] <= max_price]
        
    return filtered

@app.get("/products/{product_id}/price")
def get_product_price(product_id: int = Path(..., gt=0)):
    product = next((p for p in products if p["id"] == product_id), None)
    if not product:
        return {"error": "Product not found"}
    return {"name": product["name"], "price": product["price"]}

class CustomerFeedback(BaseModel):
    customer_name: str = Field(..., min_length=2)
    product_id: int = Field(..., gt=0)
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=300)

@app.post("/feedback")
def post_feedback(feedback: CustomerFeedback):
    feedback_db.append(feedback.dict())
    return {
        "message": "Feedback submitted successfully",
        "feedback": feedback,
        "total_feedback": len(feedback_db)
    }

@app.get("/products/summary")
def get_product_summary():
    in_stock = [p for p in products if p["in_stock"]]
    sorted_p = sorted(products, key=lambda x: x["price"])
    
    return {
        "total_products": len(products),
        "in_stock_count": len(in_stock),
        "out_of_stock_count": len(products) - len(in_stock),
        "most_expensive": {"name": sorted_p[-1]["name"], "price": sorted_p[-1]["price"]},
        "cheapest": {"name": sorted_p[0]["name"], "price": sorted_p[0]["price"]},
        "categories": list(set([p["category"] for p in products]))
    }

class OrderItem(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., ge=1, le=50)

class BulkOrder(BaseModel):
    company_name: str = Field(..., min_length=2)
    contact_email: str = Field(..., min_length=5)
    items: List[OrderItem] = Field(..., min_items=1)

@app.post("/orders/bulk")
def place_bulk_order(order: BulkOrder):
    confirmed, failed, grand_total = [], [], 0
    
    for item in order.items:
        product = next((p for p in products if p["id"] == item.product_id), None)
        if not product:
            failed.append({"product_id": item.product_id, "reason": "Product not found"})
        elif not product["in_stock"]:
            failed.append({"product_id": item.product_id, "reason": f"{product['name']} is out of stock"})
        else:
            subtotal = product["price"] * item.quantity
            grand_total += subtotal
            confirmed.append({"product": product["name"], "qty": item.quantity, "subtotal": subtotal})
            
    return {
        "company": order.company_name,
        "confirmed": confirmed,
        "failed": failed,
        "grand_total": grand_total
    }

@app.post("/orders")
def create_order(product_id: int):
    order_id = len(orders_db) + 1
    orders_db[order_id] = {"order_id": order_id, "product_id": product_id, "status": "pending"}
    return orders_db[order_id]

@app.get("/orders/{order_id}")
def get_order_status(order_id: int):
    order = orders_db.get(order_id)
    if not order:
        return {"error": "Order not found"}
    return order

@app.patch("/orders/{order_id}/confirm")
def confirm_order(order_id: int):
    if order_id not in orders_db:
        return {"error": "Order not found"}
    orders_db[order_id]["status"] = "confirmed"
    return {"message": "Order confirmed", "order": orders_db[order_id]}
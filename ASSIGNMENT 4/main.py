from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# Fake product database
products = {
    1: {"name": "Wireless Mouse", "price": 499, "in_stock": True},
    2: {"name": "Notebook", "price": 99, "in_stock": True},
    3: {"name": "USB Hub", "price": 799, "in_stock": False},
    4: {"name": "Pen Set", "price": 49, "in_stock": True},
    5: {"name": "Laptop", "price": 49999, "in_stock": True},
    6: {"name": "Bike", "price": 129000, "in_stock": False},
    7: {"name": "KeyBoard", "price": 1500, "in_stock": True}
}

# In-memory storage - Now using a Dictionary for O(1) lookups
cart = {}  # Format: {product_id: {item_details}}
orders = []
order_id_counter = 1

class CheckoutRequest(BaseModel):
    customer_name: str
    delivery_address: str

def calculate_total(product, quantity):
    return product["price"] * quantity

# --- Endpoints ---

@app.post("/cart/add")
def add_to_cart(product_id: int, quantity: int = 1):
    if product_id not in products:
        raise HTTPException(status_code=404, detail="Product not found")

    product = products[product_id]

    if not product["in_stock"]:
        raise HTTPException(status_code=400, detail=f"{product['name']} is out of stock")

    # Optimization: Use dictionary lookup instead of a loop
    if product_id in cart:
        cart[product_id]["quantity"] += quantity
        cart[product_id]["subtotal"] = calculate_total(product, cart[product_id]["quantity"])
        return {"message": "Cart updated", "cart_item": cart[product_id]}

    # Add new item if not exists
    subtotal = calculate_total(product, quantity)
    cart_item = {
        "product_id": product_id,
        "product_name": product["name"],
        "quantity": quantity,
        "unit_price": product["price"],
        "subtotal": subtotal
    }
    cart[product_id] = cart_item

    return {"message": "Added to cart", "cart_item": cart_item}

@app.get("/cart")
def get_cart():
    if not cart:
        return {"message": "Cart is empty", "items": [], "grand_total": 0}

    # Convert dictionary values to a list for the response
    items_list = list(cart.values())
    grand_total = sum(item["subtotal"] for item in items_list)

    return {
        "items": items_list,
        "item_count": len(items_list),
        "grand_total": grand_total
    }

@app.delete("/cart/{product_id}")
def remove_from_cart(product_id: int):
    # Dictionary 'pop' is faster and cleaner than searching a list
    if product_id in cart:
        cart.pop(product_id)
        return {"message": "Item removed from cart"}

    raise HTTPException(status_code=404, detail="Item not found in cart")

@app.post("/cart/checkout")
def checkout(data: CheckoutRequest):
    global order_id_counter

    if not cart:
        raise HTTPException(status_code=400, detail="Cart is empty — add items first")

    created_orders = []
    item_count = len(cart)

    # Iterate through dictionary items
    for item in cart.values():
        order = {
            "order_id": order_id_counter,
            "customer_name": data.customer_name,
            "delivery_address": data.delivery_address,
            "product": item["product_name"],
            "quantity": item["quantity"],
            "total_price": item["subtotal"]
        }
        orders.append(order)
        created_orders.append(order)
        order_id_counter += 1

    grand_total = sum(o["total_price"] for o in created_orders)
    
    # Clear dictionary
    cart.clear()

    return {
        "grand_total": grand_total,
        "cart_status": f"Cart with {item_count} item(s) is cleared",
        "orders_placed": created_orders,
        "message": "Checkout successful"
    }

@app.get("/orders")
def get_orders():
    return {
        "orders": orders,
        "total_orders": len(orders)
    }
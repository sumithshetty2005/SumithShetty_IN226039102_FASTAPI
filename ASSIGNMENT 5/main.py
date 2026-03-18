from fastapi import FastAPI, Query, Response, status
from pydantic import BaseModel, Field

app = FastAPI()

class OrderRequest(BaseModel):
    customer_name:    str = Field(..., min_length=2, max_length=100)
    product_id:       int = Field(..., gt=0)
    quantity:         int = Field(..., gt=0, le=100)
    delivery_address: str = Field(..., min_length=10)

class NewProduct(BaseModel):
    name:     str  = Field(..., min_length=2, max_length=100)
    price:    int  = Field(..., gt=0)
    category: str  = Field(..., min_length=2)
    in_stock: bool = True

class CheckoutRequest(BaseModel):
    customer_name:    str = Field(..., min_length=2)
    delivery_address: str = Field(..., min_length=10)

products = [
    {'id': 1, 'name': 'Wireless Mouse', 'price': 499, 'category': 'Electronics', 'in_stock': True},
    {'id': 2, 'name': 'Notebook',        'price':  99, 'category': 'Stationery',  'in_stock': True},
    {'id': 3, 'name': 'USB Hub',         'price': 799, 'category': 'Electronics', 'in_stock': False},
    {'id': 4, 'name': 'Pen Set',         'price':  49, 'category': 'Stationery',  'in_stock': True},
]

orders        = []
order_counter = 1
cart          = []

def find_product(product_id: int):
    for p in products:
        if p['id'] == product_id:
            return p
    return None

def calculate_total(product: dict, quantity: int) -> int:
    return product['price'] * quantity

@app.get('/')
def home():
    return {'message': 'Welcome to our E-commerce API'}

@app.get('/products')
def get_all_products():
    return {'products': products, 'total': len(products)}

# ══ ASSIGNMENT 6 ══════════════════════════════════════

@app.get('/products/search')
def search_products(keyword: str = Query(..., description='Word to search for')):
    results = [p for p in products if keyword.lower() in p['name'].lower()]
    if not results:
        return {'message': f'No products found for: {keyword}', 'results': []}
    return {'keyword': keyword, 'total_found': len(results), 'results': results}

@app.get('/products/sort')
def sort_products(
    sort_by: str = Query('price'),
    order:   str = Query('asc'),
):
    if sort_by not in ['price', 'name']:
        return {'error': "sort_by must be 'price' or 'name'"}
    if order not in ['asc', 'desc']:
        return {'error': "order must be 'asc' or 'desc'"}

    reverse = (order == 'desc')
    sorted_products = sorted(products, key=lambda p: p[sort_by], reverse=reverse)
    return {'sort_by': sort_by, 'order': order, 'products': sorted_products}

@app.get('/products/page')
def get_products_paged(
    page:  int = Query(1, ge=1),
    limit: int = Query(2, ge=1, le=20),
):
    start = (page - 1) * limit
    end   = start + limit
    paged = products[start:end]
    return {
        'page': page,
        'limit': limit,
        'total': len(products),
        'total_pages': -(-len(products) // limit),
        'products': paged,
    }

@app.get('/orders/search')
def search_orders(customer_name: str = Query(..., min_length=1)):
    results = [o for o in orders if customer_name.lower() in o['customer_name'].lower()]
    if not results:
        return {"message": f"No orders found for customer: {customer_name}"}
    return {"customer_name": customer_name, "total_found": len(results), "orders": results}

@app.get('/products/sort-by-category')
def sort_by_category():
    sorted_products = sorted(products, key=lambda p: (p['category'], p['price']))
    return {"sorted_products": sorted_products}

@app.get('/products/browse')
def browse_products(
    keyword: str = Query(None),
    sort_by: str = Query('price'),
    order:   str = Query('asc'),
    page:    int = Query(1, ge=1),
    limit:   int = Query(4, ge=1)
):
    filtered = products
    if keyword:
        filtered = [p for p in products if keyword.lower() in p['name'].lower()]
    
    rev = (order == 'desc')
    key_func = lambda p: p.get(sort_by, p['price'])
    sorted_list = sorted(filtered, key=key_func, reverse=rev)

    start = (page - 1) * limit
    end = start + limit
    paged_list = sorted_list[start:end]

    return {
        "filters": {"keyword": keyword},
        "sorting": {"sort_by": sort_by, "order": order},
        "pagination": {
            "page": page,
            "limit": limit,
            "total_found": len(sorted_list),
            "total_pages": -(-len(sorted_list) // limit)
        },
        "products": paged_list
    }

@app.get('/orders/page')
def get_orders_paged(page: int = Query(1, ge=1), limit: int = Query(3, ge=1)):
    start = (page - 1) * limit
    end = start + limit
    return {
        "page": page,
        "limit": limit,
        "total_orders": len(orders),
        "total_pages": -(-len(orders) // limit),
        "orders": orders[start:end]
    }

# ══ EXISTING ROUTES (CRUD & CART) ═════════════════════════════════

@app.get('/products/{product_id}')
def get_product(product_id: int):
    product = find_product(product_id)
    if not product:
        return {'error': 'Product not found'}
    return {'product': product}

@app.post('/products')
def add_product(new_product: NewProduct, response: Response):
    existing_names = [p['name'].lower() for p in products]
    if new_product.name.lower() in existing_names:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {'error': 'Product with this name already exists'}
    next_id = max(p['id'] for p in products) + 1
    product = {
        'id': next_id,
        'name': new_product.name,
        'price': new_product.price,
        'category': new_product.category,
        'in_stock': new_product.in_stock,
    }
    products.append(product)
    response.status_code = status.HTTP_201_CREATED
    return {'message': 'Product added', 'product': product}

@app.post('/orders')
def place_order(order_data: OrderRequest):
    global order_counter
    product = find_product(order_data.product_id)
    if not product: return {'error': 'Product not found'}
    if not product['in_stock']: return {'error': f"{product['name']} is out of stock"}
    order = {
        'order_id': order_counter,
        'customer_name': order_data.customer_name,
        'product': product['name'],
        'quantity': order_data.quantity,
        'delivery_address': order_data.delivery_address,
        'total_price': calculate_total(product, order_data.quantity),
        'status': 'confirmed',
    }
    orders.append(order)
    order_counter += 1
    return {'message': 'Order placed successfully', 'order': order}

@app.get('/orders')
def get_all_orders():
    return {'orders': orders, 'total_orders': len(orders)}
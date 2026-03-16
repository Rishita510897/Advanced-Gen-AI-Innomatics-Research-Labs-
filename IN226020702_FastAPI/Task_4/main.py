from pydantic import BaseModel, Field
from fastapi import FastAPI, Query, Response, status, HTTPException

app = FastAPI()
# PYDANTIC MODELS


class OrderRequest(BaseModel):
    customer_name: str = Field(..., min_length=2, max_length=100)
    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0, le=100)
    delivery_address: str = Field(..., min_length=10)


class CheckoutRequest(BaseModel):
    customer_name: str = Field(..., min_length=2)
    delivery_address: str = Field(..., min_length=10)


class NewProduct(BaseModel):
    name: str = Field(..., min_length=2)
    price: int = Field(..., gt=0)
    category: str = Field(..., min_length=2)
    in_stock: bool = True
  
# DATA STORAGE


products = [
    {"id": 1, "name": "Wireless Mouse", "price": 499, "category": "Electronics", "in_stock": True},
    {"id": 2, "name": "Notebook", "price": 99, "category": "Stationery", "in_stock": True},
    {"id": 3, "name": "USB Hub", "price": 799, "category": "Electronics", "in_stock": False},
    {"id": 4, "name": "Pen Set", "price": 49, "category": "Stationery", "in_stock": True},
]

orders = []
cart = []
order_counter = 1

# HELPER FUNCTION

def find_product(product_id: int):
    for p in products:
        if p["id"] == product_id:
            return p
    return None
  
# CART ENDPOINTS
# Add item to cart
@app.post("/cart/add")
def add_to_cart(
    product_id: int = Query(..., gt=0),
    quantity: int = Query(..., gt=0, le=100)
):

    product = find_product(product_id)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if not product["in_stock"]:
        raise HTTPException(
            status_code=400,
            detail=f"{product['name']} is out of stock"
        )

    # Check duplicate item
    for item in cart:
        if item["product_id"] == product_id:
            item["quantity"] += quantity
            item["subtotal"] = product["price"] * item["quantity"]

            return {
                "message": "Cart updated",
                "cart_item": item
            }

    subtotal = product["price"] * quantity

    cart_item = {
        "product_id": product["id"],
        "product_name": product["name"],
        "quantity": quantity,
        "unit_price": product["price"],
        "subtotal": subtotal
    }

    cart.append(cart_item)

    return {
        "message": "Added to cart",
        "cart_item": cart_item
    }


# View cart
@app.get("/cart")
def view_cart():

    if not cart:
        return {"message": "Cart is empty"}

    grand_total = sum(item["subtotal"] for item in cart)

    return {
        "items": cart,
        "item_count": len(cart),
        "grand_total": grand_total
    }


# Remove item
@app.delete("/cart/{product_id}")
def remove_from_cart(product_id: int):

    for item in cart:
        if item["product_id"] == product_id:
            cart.remove(item)
            return {"message": f"{item['product_name']} removed from cart"}

    raise HTTPException(status_code=404, detail="Item not found in cart")


# Checkout
@app.post("/cart/checkout")
def checkout(data: CheckoutRequest):

    global order_counter

    if not cart:
        return {"message": "Cart is empty"}

    orders_placed = []
    grand_total = 0

    for item in cart:

        order = {
            "order_id": order_counter,
            "customer_name": data.customer_name,
            "product": item["product_name"],
            "quantity": item["quantity"],
            "delivery_address": data.delivery_address,
            "total_price": item["subtotal"],
            "status": "confirmed"
        }

        orders.append(order)
        orders_placed.append(order)

        grand_total += item["subtotal"]
        order_counter += 1

    cart.clear()

    return {
        "message": "Checkout successful",
        "orders_placed": orders_placed,
        "grand_total": grand_total
    }

# BASIC ENDPOINTS

@app.get("/")
def home():
    return {"message": "Welcome to our E-commerce API"}


@app.get("/products")
def get_products():
    return {"products": products, "total": len(products)}


# PRODUCT FILTER

@app.get("/products/filter")
def filter_products(
    category: str = Query(None),
    min_price: int = Query(None),
    max_price: int = Query(None),
    in_stock: bool = Query(None)
):

    result = products

    if category:
        result = [p for p in result if p["category"] == category]

    if min_price is not None:
        result = [p for p in result if p["price"] >= min_price]

    if max_price is not None:
        result = [p for p in result if p["price"] <= max_price]

    if in_stock is not None:
        result = [p for p in result if p["in_stock"] == in_stock]

    return {"filtered_products": result, "count": len(result)}

# COMPARE PRODUCTS

@app.get("/products/compare")
def compare_products(
    product_id_1: int = Query(...),
    product_id_2: int = Query(...)
):

    p1 = find_product(product_id_1)
    p2 = find_product(product_id_2)

    if not p1 or not p2:
        raise HTTPException(status_code=404, detail="Product not found")

    cheaper = p1 if p1["price"] < p2["price"] else p2

    return {
        "product_1": p1,
        "product_2": p2,
        "better_value": cheaper["name"],
        "price_diff": abs(p1["price"] - p2["price"])
    }

# ADD PRODUCT
@app.post("/products")
def add_product(new_product: NewProduct, response: Response):

    if any(p["name"].lower() == new_product.name.lower() for p in products):
        raise HTTPException(status_code=400, detail="Product already exists")

    next_id = max(p["id"] for p in products) + 1

    product = {
        "id": next_id,
        "name": new_product.name,
        "price": new_product.price,
        "category": new_product.category,
        "in_stock": new_product.in_stock
    }

    products.append(product)

    response.status_code = status.HTTP_201_CREATED

    return {"message": "Product added", "product": product}

# UPDATE PRODUCT

@app.put("/products/{product_id}")
def update_product(
    product_id: int,
    in_stock: bool = Query(None),
    price: int = Query(None)
):

    product = find_product(product_id)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if in_stock is not None:
        product["in_stock"] = in_stock

    if price is not None:
        product["price"] = price

    return {"message": "Product updated", "product": product}

# DELETE PRODUCT
@app.delete("/products/{product_id}")
def delete_product(product_id: int):

    product = find_product(product_id)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    products.remove(product)

    return {"message": f"Product '{product['name']}' deleted"}

# GET SINGLE PRODUCT

@app.get("/products/{product_id}")
def get_product(product_id: int):

    product = find_product(product_id)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return {"product": product}


# ORDERS

@app.get("/orders")
def get_orders():
    return {"orders": orders, "total_orders": len(orders)}
   

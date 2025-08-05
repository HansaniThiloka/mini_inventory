from fastapi import FastAPI, HTTPException
from typing import List
from models import (
    Product, PurchaseRequest, InventoryResponse, 
    ProductResponse, PurchaseResponse, CategoryEnum
)
from utils import (
    load_data, save_data, get_inventory_status, 
    restock_if_needed, log_operation
)

app = FastAPI(title="Mini Inventory Management System", version="1.0.0")

@app.post("/products", response_model=ProductResponse)
def add_product(product: Product):
    """Add a new product to the inventory with automatic business rule application."""
    data = load_data()

    # Check if product already exists
    if product.product_id in data:
        log_operation("ADD_PRODUCT_FAILED", product.product_id, {"reason": "Product already exists"})
        raise HTTPException(status_code=400, detail="Product already exists")

    # Apply business rule: High priority products must have min_threshold >= 10
    if product.priority == "high" and product.min_threshold < 10:
        product.min_threshold = 10
        log_operation("BUSINESS_RULE_APPLIED", product.product_id, 
                     {"rule": "high_priority_min_threshold", "new_threshold": 10})

    # Apply business rule: Auto-assign category based on restock_quantity
    product.category = CategoryEnum.high_volume if product.restock_quantity > 50 else CategoryEnum.low_volume

    # Save product
    data[product.product_id] = product.dict()
    save_data(data)

    log_operation("ADD_PRODUCT", product.product_id, {
        "name": product.name,
        "stock_quantity": product.stock_quantity,
        "priority": product.priority,
        "category": product.category
    })

    return ProductResponse(message="Product added successfully", product=product)

@app.get("/inventory/{product_id}", response_model=InventoryResponse)
def inventory_status(product_id: str):
    """Get the current inventory status of a specific product."""
    data = load_data()
    
    if product_id not in data:
        log_operation("INVENTORY_CHECK_FAILED", product_id, {"reason": "Product not found"})
        raise HTTPException(status_code=404, detail="Product not found")

    product = data[product_id]
    status = get_inventory_status(product)
    
    log_operation("INVENTORY_CHECK", product_id, {
        "stock_quantity": product["stock_quantity"],
        "status": status
    })

    return InventoryResponse(
        product_id=product["product_id"],
        stock_quantity=product["stock_quantity"],
        status=status,
        priority=product["priority"]
    )

@app.get("/inventory", response_model=List[InventoryResponse])
def get_all_inventory():
    """Get inventory status for all products."""
    data = load_data()
    
    if not data:
        log_operation("GET_ALL_INVENTORY", "ALL", {"count": 0})
        return []

    results = []
    for product_id, product in data.items():
        status = get_inventory_status(product)
        results.append(InventoryResponse(
            product_id=product["product_id"],
            stock_quantity=product["stock_quantity"],
            status=status,
            priority=product["priority"]
        ))
    
    log_operation("GET_ALL_INVENTORY", "ALL", {"count": len(results)})
    return results

@app.post("/purchase/{product_id}", response_model=PurchaseResponse)
def purchase_product(product_id: str, purchase_request: PurchaseRequest):
    """Purchase a specified quantity of a product and trigger automatic restocking if needed."""
    data = load_data()
    
    if product_id not in data:
        log_operation("PURCHASE_FAILED", product_id, {"reason": "Product not found"})
        raise HTTPException(status_code=404, detail="Product not found")

    product = data[product_id]
    quantity = purchase_request.quantity

    # Check if sufficient stock is available
    if product["stock_quantity"] < quantity:
        log_operation("PURCHASE_FAILED", product_id, {
            "reason": "Insufficient stock",
            "requested": quantity,
            "available": product["stock_quantity"]
        })
        raise HTTPException(
            status_code=400, 
            detail=f"Insufficient stock. Available: {product['stock_quantity']}, Requested: {quantity}"
        )

    # Process the purchase
    old_stock = product["stock_quantity"]
    product["stock_quantity"] -= quantity
    
    # Check if restocking is needed
    restock_triggered = restock_if_needed(product)
    
    # Save updated data
    data[product_id] = product
    save_data(data)

    log_operation("PURCHASE", product_id, {
        "quantity_purchased": quantity,
        "stock_before": old_stock,
        "stock_after": product["stock_quantity"],
        "restock_triggered": restock_triggered
    })

    return PurchaseResponse(
        message="Purchase successful",
        remaining_stock=product["stock_quantity"],
        restock_triggered=restock_triggered
    )

@app.post("/restock/{product_id}")
def manual_restock(product_id: str):
    """Manually trigger restocking for a specific product."""
    data = load_data()
    
    if product_id not in data:
        log_operation("MANUAL_RESTOCK_FAILED", product_id, {"reason": "Product not found"})
        raise HTTPException(status_code=404, detail="Product not found")

    product = data[product_id]
    old_stock = product["stock_quantity"]
    
    # Force restock regardless of current stock level
    restock_qty = product["restock_quantity"]
    if product["priority"] == "high":
        actual_restock = int(restock_qty * 1.2)
    elif product["category"] == "high_volume":
        actual_restock = int(restock_qty * 1.1)
    else:
        actual_restock = restock_qty
    
    product["stock_quantity"] += actual_restock
    data[product_id] = product
    save_data(data)

    log_operation("MANUAL_RESTOCK", product_id, {
        "stock_before": old_stock,
        "stock_after": product["stock_quantity"],
        "restock_quantity": actual_restock
    })

    return {
        "message": "Manual restock completed",
        "product_id": product_id,
        "stock_before": old_stock,
        "stock_after": product["stock_quantity"],
        "restock_quantity": actual_restock
    }

@app.get("/")
def root():
    """Welcome endpoint with API information."""
    return {
        "message": "Mini Inventory Management System",
        "version": "1.0.0",
        "endpoints": {
            "POST /products": "Add new product",
            "GET /inventory/{product_id}": "Get product inventory status",
            "GET /inventory": "Get all products inventory status",
            "POST /purchase/{product_id}": "Purchase product",
            "POST /restock/{product_id}": "Manual restock product"
        }
    }
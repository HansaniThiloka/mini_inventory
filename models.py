from pydantic import BaseModel, validator
from typing import Optional
from enum import Enum

class PriorityEnum(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"

class CategoryEnum(str, Enum):
    high_volume = "high_volume"
    low_volume = "low_volume"

class StatusEnum(str, Enum):
    ok = "ok"
    below_threshold = "below_threshold"
    out_of_stock = "out_of_stock"

class Product(BaseModel):
    product_id: str
    name: str
    stock_quantity: int
    min_threshold: int
    restock_quantity: int
    priority: PriorityEnum
    category: Optional[CategoryEnum] = None

    @validator('stock_quantity', 'min_threshold', 'restock_quantity')
    def validate_positive_numbers(cls, v):
        if v < 0:
            raise ValueError('Values must be non-negative')
        return v

class PurchaseRequest(BaseModel):
    quantity: int

    @validator('quantity')
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be positive')
        return v

class InventoryResponse(BaseModel):
    product_id: str
    stock_quantity: int
    status: StatusEnum
    priority: PriorityEnum

class ProductResponse(BaseModel):
    message: str
    product: Product

class PurchaseResponse(BaseModel):
    message: str
    remaining_stock: int
    restock_triggered: bool = False
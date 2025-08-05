import json
import logging
from os.path import exists
from datetime import datetime
from typing import Dict, Any

# Configure logging for traceability
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('inventory.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

DATA_FILE = "inventory_store.json"

def load_data() -> Dict[str, Any]:
    """Load inventory data from JSON file with error handling and logging."""
    try:
        if not exists(DATA_FILE):
            logger.info(f"Data file {DATA_FILE} does not exist, returning empty dict")
            return {}
        
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            logger.info(f"Successfully loaded {len(data)} products from {DATA_FILE}")
            return data
    except Exception as e:
        logger.error(f"Error loading data from {DATA_FILE}: {str(e)}")
        return {}

def save_data(data: Dict[str, Any]) -> None:
    """Save inventory data to JSON file with error handling and logging."""
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)
            logger.info(f"Successfully saved {len(data)} products to {DATA_FILE}")
    except Exception as e:
        logger.error(f"Error saving data to {DATA_FILE}: {str(e)}")
        raise

def get_inventory_status(product: Dict[str, Any]) -> str:
    """Determine inventory status based on stock quantity and threshold."""
    stock = product["stock_quantity"]
    threshold = product["min_threshold"]
    
    if stock == 0:
        status = "out_of_stock"
    elif stock < threshold:
        status = "below_threshold"
    else:
        status = "ok"
    
    logger.debug(f"Product {product['product_id']}: stock={stock}, threshold={threshold}, status={status}")
    return status

def should_restock(product: Dict[str, Any]) -> bool:
    """
    Intelligent business rules for determining when to restock:
    1. Always restock if stock is 0 (out of stock)
    2. Restock if below threshold AND:
       - High priority products: restock when below threshold
       - Medium priority: restock when stock is <= 50% of threshold
       - Low priority: restock when stock is <= 25% of threshold
    """
    stock = product["stock_quantity"]
    threshold = product["min_threshold"]
    priority = product["priority"]
    
    if stock == 0:
        logger.info(f"Product {product['product_id']} is out of stock - triggering restock")
        return True
    
    if stock >= threshold:
        return False
    
    # Below threshold - apply priority-based logic
    if priority == "high":
        should_restock_flag = stock < threshold
    elif priority == "medium":
        should_restock_flag = stock <= (threshold * 0.5)
    else:  # low priority
        should_restock_flag = stock <= (threshold * 0.25)
    
    if should_restock_flag:
        logger.info(f"Product {product['product_id']} (priority: {priority}) qualifies for restock: stock={stock}, threshold={threshold}")
    
    return should_restock_flag

def restock_if_needed(product: Dict[str, Any]) -> bool:
    """
    Intelligently restock products based on business rules.
    Returns True if restocking was triggered, False otherwise.
    """
    if not should_restock(product):
        return False
    
    old_stock = product["stock_quantity"]
    restock_qty = product["restock_quantity"]
    
    # Enhanced restock logic based on priority and category
    if product["priority"] == "high":
        # High priority gets full restock + 20% buffer
        actual_restock = int(restock_qty * 1.2)
    elif product["category"] == "high_volume":
        # High volume gets full restock + 10% buffer
        actual_restock = int(restock_qty * 1.1)
    else:
        # Standard restock
        actual_restock = restock_qty
    
    product["stock_quantity"] += actual_restock
    
    logger.info(f"RESTOCK TRIGGERED - Product: {product['product_id']}, "
               f"Priority: {product['priority']}, Category: {product['category']}, "
               f"Stock: {old_stock} → {product['stock_quantity']} (+{actual_restock})")
    
    return True

def log_operation(operation: str, product_id: str, details: Dict[str, Any] = None) -> None:
    """Log operations for audit trail and debugging."""
    timestamp = datetime.now().isoformat()
    log_entry = {
        "timestamp": timestamp,
        "operation": operation,
        "product_id": product_id,
        "details": details or {}
    }
    logger.info(f"OPERATION: {json.dumps(log_entry)}")
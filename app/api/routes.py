from flask import Blueprint, request, jsonify
import os
import sys
import json
from utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)
# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from grocy.client import GrocyClient

# Initialize Blueprint
api_bp = Blueprint('api', __name__)

# Initialize Grocy client
grocy_client = GrocyClient(
    api_url=os.environ.get('GROCY_API_URL'),
    api_key=os.environ.get('GROCY_API_KEY')
)

# Load category mappings
with open('/config/category_mappings.json', 'r') as f:
    category_mappings = json.load(f)

@api_bp.route('/products/search', methods=['GET'])
def search_products():
    """
    Search for products in Grocy
    
    Query parameters:
    - query: Search query
    - barcode: Barcode to search for
    """
    query = request.args.get('query', '')
    barcode = request.args.get('barcode', '')
    standardized_barcode = grocy_client.normalize_receipt_barcode(barcode)

    if barcode:
        product = grocy_client.find_product_by_barcode(standardized_barcode)
        if product:
            return jsonify([product])
        return jsonify([])
    
    if query:
        products = grocy_client.search_products(query)
        return jsonify(products)
    
    return jsonify([])

@api_bp.route('/products', methods=['POST'])
def create_product():
    """
    Create a new product in Grocy
    
    Request body:
    - name: Product name
    - qu_id_purchase: Purchase Quantity Unit
    - qu_id_stock: Stock Quantity Unit
    - barcode: Product barcode (optional)
    - category: Product category (optional)
    - location: Product location (optional)
    - store: Store name (optional)
    """
    data = request.json
    
    if not data or 'name' not in data:
        return jsonify({'error': 'Product name is required'}), 400
    
    # Map store category to Grocy category if available
    store = data.get('store', '')
    category = data.get('category', '')
    logger.info(f"Store: {store} Category: {category}")

    # Create product in Grocy
    product_data = {
        'name': data['name'],
        'barcode': data.get('barcode', ''),
        'category': data.get('category', ''),
        'location_id': data.get('location', ''),
        # 'store': data.get('location', ''),
        'qu_id_purchase': data.get('qu_id_purchase'),
        'qu_id_stock': data.get('qu_id_stock'),
    }
    
    result = grocy_client.create_product(product_data)
    
    if 'error' in result:
        return jsonify(result), 400
    
    return jsonify(result)

@api_bp.route('/purchases', methods=['POST'])
def add_purchase():
    """
    Add a purchase in Grocy
    
    Request body:
    - product_id: Grocy product ID
    - amount: Purchase amount
    - price: Purchase price (optional)
    """
    data = request.json
    
    if not data or 'product_id' not in data or 'amount' not in data:
        return jsonify({'error': 'Product ID and amount are required'}), 400
    
    # Add purchase in Grocy
    purchase_data = {
        'product_id': data['product_id'],
        'amount': data['amount'],
        'price': data.get('price'),
        'days_out': data.get('days_out', 0),
        'shopping_location_id': data.get('shopping_location_id', '')
    }
    
    result = grocy_client.add_purchase(purchase_data)
    
    if 'error' in result:
        return jsonify(result), 400
    
    return jsonify(result)

@api_bp.route('/categories', methods=['GET'])
def get_categories():
    """
    Get all product categories from Grocy
    """
    categories = grocy_client.get_product_categories()
    return jsonify(categories)

@api_bp.route('/locations', methods=['GET'])
def get_locations():
    """
    Get all product locations from Grocy
    """
    locations = grocy_client.get_locations()
    return jsonify(locations)

@api_bp.route('/stores', methods=['GET'])
def get_stores():
    """
    Get all stores with category mappings
    """
    return jsonify(list(category_mappings.keys()))

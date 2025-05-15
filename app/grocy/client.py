import requests
import json
import os
import sys
from stdnum import ean
from datetime import date, timedelta

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

class GrocyClient:
    """
    Client for interacting with the Grocy API
    """
    
    def __init__(self, api_url=None, api_key=None):
        """
        Initialize the Grocy client
        
        Args:
            api_url: Grocy API URL
            api_key: Grocy API key
        """
        self.api_url = api_url or os.environ.get('GROCY_API_URL')
        self.api_key = api_key or os.environ.get('GROCY_API_KEY')
        
        if not self.api_url or not self.api_key:
            logger.error("Grocy API URL and API key must be provided")
            raise ValueError("Grocy API URL and API key must be provided")
        
        logger.info(f"Initializing Grocy client with API URL: {self.api_url}")
        
        self.headers = {
            'GROCY-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }
    
    def find_product_by_barcode(self, barcode):
        """
        Find a product by barcode
        
        Args:
            barcode: Product barcode
            
        Returns:
            Product data if found, None otherwise
        """

        logger.info(f"Finding product by barcode: {barcode}")
        url = f"{self.api_url}/stock/products/by-barcode/{barcode}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            product = response.json()
            if product:
                return product
            
            return None
        except Exception as e:
            print(f"Error finding product by barcode: {e}")
            return None
    
    def get_product_categories(self):
        """
        Get all product categories
        
        Returns:
            List of product categories
        """
        url = f"{self.api_url}/objects/product_groups"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            print(f"Error getting product categories: {e}")
            return []

    def get_locations(self):
        """
        Get all locations
        
        Returns:
            List of locations
        """
        url = f"{self.api_url}/objects/locations"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            print(f"Error getting product locations: {e}")
            return []

    def get_quantity_units(self):
        """
        Get all quantity_units
        
        Returns:
            List of quantity_units
        """
        url = f"{self.api_url}/objects/quantity_units"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            print(f"Error getting product quantity_units: {e}")
            return []

    def get_shopping_locations(self):
        """
        Get all quantity_units
        
        Returns:
            List of quantity_units
        """
        url = f"{self.api_url}/objects/shopping_locations"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            print(f"Error getting product quantity_units: {e}")
            return []

    def create_product(self, product_data):
        """
        Create a new product
        
        Args:
            product_data: Dictionary containing product data
            
        Returns:
            Created product data if successful, error message otherwise
        """
        url = f"{self.api_url}/objects/products"
        
        logger.info(f"Product Data: {product_data}")
        # Find category ID if category name is provided
        product_data['product_group_id'] = product_data['product_group_id']
        product_data['location_id'] = product_data['location_id']
        product_data['qu_id_stock'] = product_data['qu_id_stock']
        product_data['qu_id_purchase'] = product_data['qu_id_purchase']
        # del product_data['category']
        # del product_data['location']
        
        # Prepare product data for Grocy API
        grocy_product = {
            'name': product_data['name'],
            'description': product_data.get('description', ''),
            'product_group_id': product_data.get('product_group_id'),
            'location_id': product_data.get('location_id'),
            'qu_id_purchase': product_data.get('qu_id_purchase'),  # Default quantity unit
            'qu_id_stock': product_data.get('qu_id_stock'),     # Default quantity unit
            'treat_opened_as_out_of_stock': product_data.get('out_of_stock_default',False),
            # 'qu_factor_purchase_to_stock': 1
        }

        logger.info(f"Creating product: {grocy_product}")
        
        try:
            response = requests.post(
                url,
                headers=self.headers,
                data=json.dumps(grocy_product)
            )
            logger.info(f"Product response: {response.json()}")
            response.raise_for_status()

            if(response.status_code == 400):
                logger.error(f"Error creating product: {response.json()}")
                return {'error': response.json().get('error')}
            
            # Get the created product
            product_id = response.json().get('created_object_id')
            product = self.get_product(product_id)
        except Exception as e:
            print(f"Error getting product, trying by name: {e}")
            product = self.get_product_by_name(product_data['name'])
            logger.info(f"Product: {product}")
            
        if(product):
            # Add barcode to product
            barcode = product_data.get('barcode')
            product_id = product.get('id')
            logger.info(f"Product ID: {product_id}")
            logger.info(f"Product Barcode: {barcode}")
            if barcode:
                barcode_response = self.add_barcode_to_product(product_id, barcode, product_data)
                if 'error' in barcode_response:
                    return {'error': barcode_response['error']}

            return product
        
        return None

        
    def add_barcode_to_product(self, product_id, barcode, product_data):
        """
        Add barcode to a product

        Args:
            product_id: Product ID
            barcode: Barcode to add

        Returns:
            Barcode data if successful, error message otherwise
        """
        url = f"{self.api_url}/objects/product_barcodes"

        standardized_barcode = self.normalize_receipt_barcode(barcode)
        # Prepare barcode data for Grocy API
        grocy_barcode = {
            'note': product_data.get('name'),
            'barcode': standardized_barcode,
            'product_id': product_id,
            'amount': 1,  # Default quantity unit
        }

        try:
            response = requests.post(
                url,
                headers=self.headers,
                data=json.dumps(grocy_barcode)
            )
            response.raise_for_status()
            logger.info(f"Barcode response: {response.json()}")
            return response.json()
        
        except Exception as e:
            print(f"Error adding barcode to product: {e}")
            return {'error': str(e)}
    
    def get_product(self, product_id):
        """
        Get a product by ID
        
        Args:
            product_id: Product ID
            
        Returns:
            Product data if found, None otherwise
        """
        url = f"{self.api_url}/objects/products/{product_id}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            print(f"Error getting product: {e}")
            return None
    
    def get_product_details(self, product_id):
        """
        Get a product by ID
        
        Args:
            product_id: Product ID
            
        Returns:
            Product data if found, None otherwise
        """
        url = f"{self.api_url}/stock/products/{product_id}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            print(f"Error getting product: {e}")
            return None
        
    def get_all_products(self):
        """
        Get all products
        
        Args:
            products: Product ID
            
        Returns:
            Product data if found, None otherwise
        """
        url = f"{self.api_url}/objects/products"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            print(f"Error getting product: {e}")
            return None
        
    def get_product_by_name(self, product_name):
        """
        Get a product by name

        Args:
            product_name: Product name

        Returns:
            Product data if found, None otherwise
        """
        products = self.get_all_products()

        for product in products:
            if product.get('name') == product_name:
                return product

        return None
    
    def get_quantity_unit_conversions(self):
        """
        Get all quantity unit conversions

        Returns:
            List of quantity unit conversions
        """
        url = f"{self.api_url}/objects/quantity_unit_conversions"

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()

            return response.json()
        except Exception as e:
            print(f"Error getting quantity unit conversions: {e}")
            return []

    def add_purchase(self, purchase_data):
        """
        Add a purchase
        
        Args:
            purchase_data: Dictionary containing purchase data
            
        Returns:
            Purchase data if successful, error message otherwise
        """
        product_data = self.get_product_details(purchase_data['product_id'])
        logger.info(f"Adding purchase: {purchase_data}")
        logger.info(f"For product: {product_data}")

        url = f"{self.api_url}/stock/products/{purchase_data['product_id']}/add"
        
        today = date.today()  # or datetime.today() if you're using datetime
        days_out = purchase_data['days_out']
        shopping_location_id = purchase_data['shopping_location_id']

        logger.info(f"Days out: {days_out}")
        expiration_date_calc = (today + timedelta(days=days_out)).isoformat()

        calc_amount = purchase_data['amount'] * product_data['qu_conversion_factor_purchase_to_stock']
        calc_price = purchase_data.get('price') / product_data['qu_conversion_factor_purchase_to_stock']
        
        logger.info(f"Calculated amount: {calc_amount}")

        # Prepare purchase data for Grocy API
        grocy_purchase = {
            'amount': calc_amount,
            'transaction_type': 'purchase',
            'best_before_date': expiration_date_calc,
            'price': calc_price,
            'shopping_location_id': shopping_location_id,
        }
        logger.info(f"Request data: {grocy_purchase}")

        try:
            response = requests.post(
                url,
                headers=self.headers,
                data=json.dumps(grocy_purchase)
            )
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            print(f"Error adding purchase: {e}")
            return {'error': str(e)}
    
    def _get_category_id_by_name(self, category_name):
        """
        Get category ID by name
        
        Args:
            category_name: Category name
            
        Returns:
            Category ID if found, None otherwise
        """
        categories = self.get_product_categories()
        
        for category in categories:
            if category.get('name') == category_name:
                return category.get('id')
        
        return None

    def calculate_upc_check_digit(self, code11):
        """
        Given 11-digit UPC code, calculate the 12th check digit.
        """
        if len(code11) != 11 or not code11.isdigit():
            raise ValueError("Input must be an 11-digit string")
        
        total = 0
        for i, digit in enumerate(code11):
            num = int(digit)
            if i % 2 == 0:
                total += num * 3  # Odd positions (0-indexed)
            else:
                total += num * 1  # Even positions
        check_digit = (10 - (total % 10)) % 10
        return str(check_digit)

    def build_upc_from_receipt(self, receipt_code):
        """
        Normalize a 10-digit receipt code to a valid 12-digit UPC-A code.
        Pads with a leading 0, then calculates the correct check digit.
        """
        if len(receipt_code) != 10 or not receipt_code.isdigit():
            raise ValueError("Expected a 10-digit numeric receipt code")
        
        base_code = "0" + receipt_code  # pad to 11 digits
        check_digit = self.calculate_upc_check_digit(base_code)
        return base_code + check_digit

    def normalize_receipt_barcode(self, receipt_code):
        if len(receipt_code) == 10 and receipt_code.isdigit():
            return self.build_upc_from_receipt(receipt_code)
        else:
            return receipt_code
        
    def convert_purchase_quantities_to_stock(self, purchase_id, stock_id, amount):
        """
        Convert purchase quantities to stock

        Args:
            purchase_id: Purchase ID
            stock_id: Stock ID
            amount: Amount to convert

        Returns:
            Receipt code if successful, error message otherwise
        """
        conversions = self.get_quantity_unit_conversions()
        try:
            for conversion in conversions:
                if conversion['from_qu_id'] == purchase_id and conversion['to_qu_id'] == stock_id:
                    amount = amount * conversion['factor']

            return amount
        except Exception as e:
            print(f"Error converting purchase quantities to stock: {e}")
            return {'error': str(e)}
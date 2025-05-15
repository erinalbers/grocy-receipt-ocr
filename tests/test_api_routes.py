import unittest
import os
import sys
import json
from unittest.mock import patch, MagicMock
from flask import Flask

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.routes import api_bp


class TestAPIRoutes(unittest.TestCase):
    
    def setUp(self):
        # Create a Flask app for testing
        self.app = Flask(__name__)
        self.app.register_blueprint(api_bp, url_prefix='/api')
        self.app.config['TESTING'] = True
        
        # Create test client
        self.client = self.app.test_client()
    
    @patch('app.api.routes.grocy_client')
    def test_search_products_by_query(self, mock_grocy_client):
        """Test searching products by query"""
        # Setup mock
        mock_grocy_client.search_products.return_value = [
            {'id': 1, 'name': 'Apple'},
            {'id': 2, 'name': 'Applesauce'}
        ]
        
        # Search products
        response = self.client.get('/api/products/search?query=apple')
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['name'], 'Apple')
        mock_grocy_client.search_products.assert_called_once_with('apple')
    
    @patch('app.api.routes.grocy_client')
    def test_search_products_by_barcode(self, mock_grocy_client):
        """Test searching products by barcode"""
        # Setup mock
        mock_grocy_client.find_product_by_barcode.return_value = {'id': 1, 'name': 'Apple'}
        
        # Search product by barcode
        response = self.client.get('/api/products/search?barcode=1234567890123')
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'Apple')
        mock_grocy_client.find_product_by_barcode.assert_called_once_with('1234567890123')
    
    @patch('app.api.routes.grocy_client')
    def test_search_products_no_results(self, mock_grocy_client):
        """Test searching products with no results"""
        # Setup mock
        mock_grocy_client.find_product_by_barcode.return_value = None
        
        # Search product by barcode
        response = self.client.get('/api/products/search?barcode=nonexistent')
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 0)
    
    @patch('app.api.routes.grocy_client')
    def test_create_product(self, mock_grocy_client):
        """Test creating a product"""
        # Setup mock
        mock_grocy_client.create_product.return_value = {'id': 3, 'name': 'New Product'}
        
        # Create product
        response = self.client.post(
            '/api/products',
            data=json.dumps({
                'name': 'New Product',
                'barcode': '5555555555555',
                'category': 'PRODUCE',
                'store': 'Safeway'
            }),
            content_type='application/json'
        )
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['id'], 3)
        self.assertEqual(data['name'], 'New Product')
    
    @patch('app.api.routes.grocy_client')
    def test_create_product_missing_name(self, mock_grocy_client):
        """Test creating a product with missing name"""
        # Create product without name
        response = self.client.post(
            '/api/products',
            data=json.dumps({
                'barcode': '5555555555555'
            }),
            content_type='application/json'
        )
        
        # Assertions
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        mock_grocy_client.create_product.assert_not_called()
    
    @patch('app.api.routes.grocy_client')
    def test_create_product_error(self, mock_grocy_client):
        """Test error handling when creating a product"""
        # Setup mock
        mock_grocy_client.create_product.return_value = {'error': 'API Error'}
        
        # Create product
        response = self.client.post(
            '/api/products',
            data=json.dumps({
                'name': 'New Product'
            }),
            content_type='application/json'
        )
        
        # Assertions
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    @patch('app.api.routes.grocy_client')
    def test_add_purchase(self, mock_grocy_client):
        """Test adding a purchase"""
        # Setup mock
        mock_grocy_client.add_purchase.return_value = {'success': True}
        
        # Add purchase
        response = self.client.post(
            '/api/purchases',
            data=json.dumps({
                'product_id': 1,
                'amount': 2,
                'price': 3.99
            }),
            content_type='application/json'
        )
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['success'], True)
    
    @patch('app.api.routes.grocy_client')
    def test_add_purchase_missing_params(self, mock_grocy_client):
        """Test adding a purchase with missing parameters"""
        # Add purchase without required params
        response = self.client.post(
            '/api/purchases',
            data=json.dumps({
                'price': 3.99
            }),
            content_type='application/json'
        )
        
        # Assertions
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        mock_grocy_client.add_purchase.assert_not_called()
    
    @patch('app.api.routes.grocy_client')
    def test_add_purchase_error(self, mock_grocy_client):
        """Test error handling when adding a purchase"""
        # Setup mock
        mock_grocy_client.add_purchase.return_value = {'error': 'API Error'}
        
        # Add purchase
        response = self.client.post(
            '/api/purchases',
            data=json.dumps({
                'product_id': 1,
                'amount': 2
            }),
            content_type='application/json'
        )
        
        # Assertions
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    @patch('app.api.routes.grocy_client')
    def test_get_categories(self, mock_grocy_client):
        """Test getting product categories"""
        # Setup mock
        mock_grocy_client.get_product_categories.return_value = [
            {'id': 1, 'name': 'Produce'},
            {'id': 2, 'name': 'Dairy'}
        ]
        
        # Get categories
        response = self.client.get('/api/categories')
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['name'], 'Produce')
    
    @patch('app.api.routes.category_mappings')
    def test_get_stores(self, mock_category_mappings):
        """Test getting stores with category mappings"""
        # Setup mock
        mock_category_mappings.keys.return_value = ['Safeway', 'Kroger']
        
        # Get stores
        response = self.client.get('/api/stores')
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 2)
        self.assertIn('Safeway', data)
        self.assertIn('Kroger', data)


if __name__ == '__main__':
    unittest.main()

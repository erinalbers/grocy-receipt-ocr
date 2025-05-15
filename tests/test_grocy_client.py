import unittest
import os
import sys
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.grocy.client import GrocyClient


class TestGrocyClient(unittest.TestCase):
    
    def setUp(self):
        # Set environment variables for testing
        os.environ['GROCY_API_URL'] = 'https://test-grocy-instance/api'
        os.environ['GROCY_API_KEY'] = 'test-api-key'
        
        # Initialize client
        self.client = GrocyClient()
    
    def tearDown(self):
        # Clean up environment variables
        os.environ.pop('GROCY_API_URL', None)
        os.environ.pop('GROCY_API_KEY', None)
    
    def test_init(self):
        """Test client initialization"""
        # Test with environment variables
        client = GrocyClient()
        self.assertEqual(client.api_url, 'https://test-grocy-instance/api')
        self.assertEqual(client.api_key, 'test-api-key')
        self.assertEqual(client.headers['GROCY-API-KEY'], 'test-api-key')
        
        # Test with explicit parameters
        client = GrocyClient(api_url='https://custom-url/api', api_key='custom-key')
        self.assertEqual(client.api_url, 'https://custom-url/api')
        self.assertEqual(client.api_key, 'custom-key')
    
    def test_init_missing_params(self):
        """Test initialization with missing parameters"""
        # Remove environment variables
        os.environ.pop('GROCY_API_URL', None)
        os.environ.pop('GROCY_API_KEY', None)
        
        # Should raise ValueError
        with self.assertRaises(ValueError):
            GrocyClient()
    
    @patch('requests.get')
    def test_find_product_by_barcode(self, mock_get):
        """Test finding a product by barcode"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {'id': 1, 'name': 'Product 1', 'barcode': '1234567890123'},
            {'id': 2, 'name': 'Product 2', 'barcode': '9876543210987'}
        ]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        # Test finding existing product
        product = self.client.find_product_by_barcode('1234567890123')
        
        # Assertions
        mock_get.assert_called_once_with(
            'https://test-grocy-instance/api/objects/products',
            headers=self.client.headers
        )
        self.assertEqual(product['id'], 1)
        self.assertEqual(product['name'], 'Product 1')
        
        # Test finding non-existent product
        product = self.client.find_product_by_barcode('5555555555555')
        self.assertIsNone(product)
    
    @patch('requests.get')
    def test_find_product_by_barcode_error(self, mock_get):
        """Test error handling when finding a product"""
        # Setup mock to raise exception
        mock_get.side_effect = Exception('API Error')
        
        # Should return None on error
        product = self.client.find_product_by_barcode('1234567890123')
        self.assertIsNone(product)
    
    @patch('requests.get')
    def test_get_product_categories(self, mock_get):
        """Test getting product categories"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {'id': 1, 'name': 'Produce'},
            {'id': 2, 'name': 'Dairy'}
        ]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        # Get categories
        categories = self.client.get_product_categories()
        
        # Assertions
        mock_get.assert_called_once_with(
            'https://test-grocy-instance/api/objects/product_groups',
            headers=self.client.headers
        )
        self.assertEqual(len(categories), 2)
        self.assertEqual(categories[0]['name'], 'Produce')
    
    @patch('requests.get')
    def test_get_product_categories_error(self, mock_get):
        """Test error handling when getting categories"""
        # Setup mock to raise exception
        mock_get.side_effect = Exception('API Error')
        
        # Should return empty list on error
        categories = self.client.get_product_categories()
        self.assertEqual(categories, [])
    
    @patch('requests.post')
    def test_create_product(self, mock_post):
        """Test creating a product"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {'created_object_id': 3}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response
        
        # Setup mock for get_product
        self.client.get_product = MagicMock(return_value={'id': 3, 'name': 'New Product'})
        
        # Create product
        product_data = {
            'name': 'New Product',
            'barcode': '5555555555555'
        }
        result = self.client.create_product(product_data)
        
        # Assertions
        mock_post.assert_called_once()
        self.assertEqual(result['id'], 3)
        self.assertEqual(result['name'], 'New Product')
    
    @patch('requests.post')
    def test_create_product_error(self, mock_post):
        """Test error handling when creating a product"""
        # Setup mock to raise exception
        mock_post.side_effect = Exception('API Error')
        
        # Should return error dict on error
        result = self.client.create_product({'name': 'Test'})
        self.assertIn('error', result)
    
    @patch('requests.get')
    def test_get_product(self, mock_get):
        """Test getting a product by ID"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {'id': 1, 'name': 'Product 1'}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        # Get product
        product = self.client.get_product(1)
        
        # Assertions
        mock_get.assert_called_once_with(
            'https://test-grocy-instance/api/objects/products/1',
            headers=self.client.headers
        )
        self.assertEqual(product['id'], 1)
        self.assertEqual(product['name'], 'Product 1')
    
    @patch('requests.get')
    def test_get_product_error(self, mock_get):
        """Test error handling when getting a product"""
        # Setup mock to raise exception
        mock_get.side_effect = Exception('API Error')
        
        # Should return None on error
        product = self.client.get_product(1)
        self.assertIsNone(product)
    
    @patch('requests.post')
    def test_add_purchase(self, mock_post):
        """Test adding a purchase"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {'success': True}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response
        
        # Add purchase
        purchase_data = {
            'product_id': 1,
            'amount': 2,
            'price': 3.99
        }
        result = self.client.add_purchase(purchase_data)
        
        # Assertions
        mock_post.assert_called_once_with(
            'https://test-grocy-instance/api/stock/products/1/add',
            headers=self.client.headers,
            data='{"amount": 2, "transaction_type": "purchase", "price": 3.99}'
        )
        self.assertEqual(result['success'], True)
    
    @patch('requests.post')
    def test_add_purchase_error(self, mock_post):
        """Test error handling when adding a purchase"""
        # Setup mock to raise exception
        mock_post.side_effect = Exception('API Error')
        
        # Should return error dict on error
        result = self.client.add_purchase({'product_id': 1, 'amount': 2})
        self.assertIn('error', result)
    
    @patch('app.grocy.client.GrocyClient.get_product_categories')
    def test_get_category_id_by_name(self, mock_get_categories):
        """Test getting category ID by name"""
        # Setup mock response
        mock_get_categories.return_value = [
            {'id': 1, 'name': 'Produce'},
            {'id': 2, 'name': 'Dairy'}
        ]
        
        # Get category ID
        category_id = self.client._get_category_id_by_name('Produce')
        
        # Assertions
        self.assertEqual(category_id, 1)
        
        # Test non-existent category
        category_id = self.client._get_category_id_by_name('Non-existent')
        self.assertIsNone(category_id)


if __name__ == '__main__':
    unittest.main()

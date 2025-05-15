import unittest
import os
import sys
import json
import tempfile
from unittest.mock import patch, MagicMock
from io import BytesIO

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the Flask app
from app.web.app import app


class TestWebApp(unittest.TestCase):
    
    def setUp(self):
        # Configure Flask app for testing
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['DEBUG'] = False
        app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()
        
        # Create test client
        self.client = app.test_client()
        
        # Create a test image
        self.test_image = BytesIO(b'fake image data')
        self.test_image.name = 'test_receipt.jpg'
    
    def tearDown(self):
        # Clean up temporary directory
        if os.path.exists(app.config['UPLOAD_FOLDER']):
            import shutil
            shutil.rmtree(app.config['UPLOAD_FOLDER'])
    
    def test_index_route(self):
        """Test the index route"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Upload Receipt', response.data)
    
    @patch('app.web.app.queue')
    def test_upload_receipt_no_file(self, mock_queue):
        """Test upload route with no file"""
        response = self.client.post('/upload', data={})
        self.assertEqual(response.status_code, 302)  # Redirect
    
    @patch('app.web.app.queue')
    def test_upload_receipt_empty_filename(self, mock_queue):
        """Test upload route with empty filename"""
        response = self.client.post('/upload', data={'receipt': (BytesIO(b''), '')})
        self.assertEqual(response.status_code, 302)  # Redirect
    
    @patch('app.web.app.queue')
    def test_upload_receipt_success(self, mock_queue):
        """Test successful receipt upload"""
        # Setup mock
        mock_job = MagicMock()
        mock_job.id = 'test-job-id'
        mock_queue.enqueue.return_value = mock_job
        
        # Upload file
        response = self.client.post(
            '/upload',
            data={'receipt': (self.test_image, 'test_receipt.jpg')},
            content_type='multipart/form-data'
        )
        
        # Assertions
        self.assertEqual(response.status_code, 302)  # Redirect
        self.assertIn('/processing/test-job-id', response.location)
        mock_queue.enqueue.assert_called_once()
    
    @patch('app.web.app.queue')
    def test_processing_route_job_not_found(self, mock_queue):
        """Test processing route with non-existent job"""
        # Setup mock
        mock_queue.fetch_job.return_value = None
        
        # Access processing page
        response = self.client.get('/processing/non-existent-job')
        
        # Assertions
        self.assertEqual(response.status_code, 302)  # Redirect to index
    
    @patch('app.web.app.queue')
    def test_processing_route_job_in_progress(self, mock_queue):
        """Test processing route with job in progress"""
        # Setup mock
        mock_job = MagicMock()
        mock_job.is_finished = False
        mock_queue.fetch_job.return_value = mock_job
        
        # Access processing page
        response = self.client.get('/processing/test-job-id')
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Processing Receipt', response.data)
    
    @patch('app.web.app.queue')
    def test_processing_route_job_finished(self, mock_queue):
        """Test processing route with finished job"""
        # Setup mock
        mock_job = MagicMock()
        mock_job.is_finished = True
        mock_queue.fetch_job.return_value = mock_job
        
        # Access processing page
        response = self.client.get('/processing/test-job-id')
        
        # Assertions
        self.assertEqual(response.status_code, 302)  # Redirect to review
        self.assertIn('/review/test-job-id', response.location)
    
    @patch('app.web.app.queue')
    def test_job_status_route(self, mock_queue):
        """Test job status API endpoint"""
        # Setup mock for job in progress
        mock_job = MagicMock()
        mock_job.get_status.return_value = 'started'
        mock_job.is_finished = False
        mock_job.result = None
        mock_queue.fetch_job.return_value = mock_job
        
        # Check status
        response = self.client.get('/job-status/test-job-id')
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'started')
        self.assertIsNone(data['result'])
        
        # Setup mock for finished job
        mock_job.get_status.return_value = 'finished'
        mock_job.is_finished = True
        mock_job.result = [{'name': 'Test Product'}]
        
        # Check status again
        response = self.client.get('/job-status/test-job-id')
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'finished')
        self.assertEqual(data['result'], [{'name': 'Test Product'}])
    
    @patch('app.web.app.queue')
    def test_job_status_not_found(self, mock_queue):
        """Test job status API with non-existent job"""
        # Setup mock
        mock_queue.fetch_job.return_value = None
        
        # Check status
        response = self.client.get('/job-status/non-existent-job')
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
    
    @patch('app.web.app.queue')
    @patch('app.web.app.grocy_client')
    def test_review_route(self, mock_grocy_client, mock_queue):
        """Test review route"""
        # Setup mocks
        mock_job = MagicMock()
        mock_job.is_finished = True
        mock_job.result = [
            {'name': 'Product 1', 'barcode': '1234567890123'},
            {'name': 'Product 2', 'barcode': '9876543210987'}
        ]
        mock_queue.fetch_job.return_value = mock_job
        
        # Mock Grocy client responses
        def find_product_side_effect(barcode):
            if barcode == '1234567890123':
                return {'id': 1, 'name': 'Product 1'}
            return None
        
        mock_grocy_client.find_product_by_barcode.side_effect = find_product_side_effect
        
        # Access review page
        response = self.client.get('/review/test-job-id')
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Review Products', response.data)
        self.assertIn(b'Product 1', response.data)
        self.assertIn(b'Product 2', response.data)
        self.assertIn(b'In Grocy', response.data)  # Product 1 should be in Grocy
        self.assertIn(b'Not in Grocy', response.data)  # Product 2 should not be in Grocy
    
    @patch('app.web.app.grocy_client')
    def test_create_product(self, mock_grocy_client):
        """Test create product API endpoint"""
        # Setup mock
        mock_grocy_client.create_product.return_value = {'id': 3, 'name': 'New Product'}
        
        # Create product
        response = self.client.post(
            '/create-product',
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
    
    @patch('app.web.app.queue')
    def test_purchases_route(self, mock_queue):
        """Test purchases route"""
        # Setup mock
        mock_job = MagicMock()
        mock_job.is_finished = True
        mock_job.result = [
            {'name': 'Product 1', 'price': 2.99, 'in_grocy': True, 'grocy_id': 1},
            {'name': 'Product 2', 'price': 1.49, 'in_grocy': True, 'grocy_id': 2}
        ]
        mock_queue.fetch_job.return_value = mock_job
        
        # Access purchases page
        response = self.client.get('/purchases/test-job-id')
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Add Purchases to Grocy', response.data)
        self.assertIn(b'Product 1', response.data)
        self.assertIn(b'Product 2', response.data)
        self.assertIn(b'2.99', response.data)
        self.assertIn(b'1.49', response.data)
    
    @patch('app.web.app.grocy_client')
    def test_add_purchase(self, mock_grocy_client):
        """Test add purchase API endpoint"""
        # Setup mock
        mock_grocy_client.add_purchase.return_value = {'success': True}
        
        # Add purchase
        response = self.client.post(
            '/add-purchase',
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


if __name__ == '__main__':
    unittest.main()

import unittest
import os
import sys
import tempfile
from unittest.mock import patch, MagicMock
import numpy as np
import cv2
from PIL import Image

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ocr.processor import (
    process_receipt,
    extract_text,
    preprocess_image,
    parse_receipt,
    detect_store,
    parse_safeway_receipt,
    parse_generic_receipt
)


class TestOCRProcessor(unittest.TestCase):
    
    def setUp(self):
        # Create a temporary directory for test files
        self.test_dir = tempfile.TemporaryDirectory()
        
        # Create a simple test image
        self.test_image_path = os.path.join(self.test_dir.name, 'test_receipt.jpg')
        self._create_test_image(self.test_image_path)
        
        # Create a simple test PDF
        self.test_pdf_path = os.path.join(self.test_dir.name, 'test_receipt.pdf')
        
    def tearDown(self):
        # Clean up temporary directory
        self.test_dir.cleanup()
    
    def _create_test_image(self, path):
        """Create a simple test image with text"""
        # Create a white image
        img = np.ones((500, 300, 3), dtype=np.uint8) * 255
        
        # Add some text
        cv2.putText(img, 'SAFEWAY', (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        cv2.putText(img, 'PRODUCE', (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        cv2.putText(img, 'Apples $2.99', (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
        cv2.putText(img, 'Bananas $1.49', (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
        cv2.putText(img, '1234567890123', (50, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
        
        # Save the image
        cv2.imwrite(path, img)
    
    @patch('app.ocr.processor.extract_text')
    @patch('app.ocr.processor.parse_receipt')
    def test_process_receipt(self, mock_parse_receipt, mock_extract_text):
        """Test the process_receipt function"""
        # Setup mocks
        mock_extract_text.return_value = "Sample receipt text"
        mock_parse_receipt.return_value = [
            {'name': 'Apples', 'price': 2.99, 'barcode': '1234567890123', 'category': 'PRODUCE'}
        ]
        
        # Call the function
        result = process_receipt(self.test_image_path)
        
        # Assertions
        mock_extract_text.assert_called_once_with(self.test_image_path)
        mock_parse_receipt.assert_called_once_with("Sample receipt text")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['name'], 'Apples')
        self.assertEqual(result[0]['price'], 2.99)
    
    @patch('pytesseract.image_to_string')
    @patch('cv2.imread')
    @patch('cv2.cvtColor')
    @patch('app.ocr.processor.preprocess_image')
    def test_extract_text_from_image(self, mock_preprocess, mock_cvt_color, mock_imread, mock_image_to_string):
        """Test extracting text from an image"""
        # Setup mocks
        mock_image = MagicMock()
        mock_imread.return_value = mock_image
        mock_processed_image = MagicMock()
        mock_preprocess.return_value = mock_processed_image
        mock_image_to_string.return_value = "Sample receipt text"
        
        # Call the function
        result = extract_text(self.test_image_path)
        
        # Assertions
        mock_imread.assert_called_once_with(self.test_image_path)
        mock_preprocess.assert_called_once()
        mock_image_to_string.assert_called_once_with(mock_processed_image)
        self.assertEqual(result, "Sample receipt text")
    
    @patch('pdf2image.convert_from_path')
    @patch('cv2.cvtColor')
    @patch('app.ocr.processor.preprocess_image')
    @patch('pytesseract.image_to_string')
    def test_extract_text_from_pdf(self, mock_image_to_string, mock_preprocess, mock_cvt_color, mock_convert_from_path):
        """Test extracting text from a PDF"""
        # Setup mocks
        mock_image1 = MagicMock()
        mock_image2 = MagicMock()
        mock_convert_from_path.return_value = [mock_image1, mock_image2]
        mock_processed_image = MagicMock()
        mock_preprocess.return_value = mock_processed_image
        mock_image_to_string.return_value = "Page text"
        
        # Call the function
        result = extract_text(self.test_pdf_path)
        
        # Assertions
        mock_convert_from_path.assert_called_once_with(self.test_pdf_path)
        self.assertEqual(mock_preprocess.call_count, 2)
        self.assertEqual(mock_image_to_string.call_count, 2)
        self.assertEqual(result, "Page text\n\nPage text\n\n")
    
    def test_preprocess_image(self):
        """Test image preprocessing"""
        # Create a test image
        img = np.ones((100, 100, 3), dtype=np.uint8) * 200
        
        # Process the image
        result = preprocess_image(img)
        
        # Assertions
        self.assertIsNotNone(result)
        self.assertEqual(result.shape[:2], (100, 100))  # Check dimensions
    
    def test_detect_store(self):
        """Test store detection from receipt text"""
        # Test cases
        self.assertEqual(detect_store("Welcome to SAFEWAY"), "Safeway")
        self.assertEqual(detect_store("Thank you for shopping at Kroger"), "Kroger")
        self.assertEqual(detect_store("WALMART receipt"), "Walmart")
        self.assertEqual(detect_store("TARGET store"), "Target")
        self.assertEqual(detect_store("Some other store"), "Unknown")
    
    def test_parse_safeway_receipt(self):
        """Test parsing Safeway receipt format"""
        # Sample receipt text
        receipt_text = """
        SAFEWAY
        
        PRODUCE
        Apples $2.99
        Bananas $1.49
        
        DAIRY
        Milk $3.99
        
        1234567890123
        """
        
        # Parse the receipt
        result = parse_safeway_receipt(receipt_text)
        
        # Assertions
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]['name'], 'Apples')
        self.assertEqual(result[0]['price'], 2.99)
        self.assertEqual(result[0]['category'], 'PRODUCE')
        self.assertEqual(result[1]['name'], 'Bananas')
        self.assertEqual(result[1]['price'], 1.49)
        self.assertEqual(result[1]['category'], 'PRODUCE')
        self.assertEqual(result[2]['name'], 'Milk')
        self.assertEqual(result[2]['price'], 3.99)
        self.assertEqual(result[2]['category'], 'DAIRY')
    
    def test_parse_generic_receipt(self):
        """Test parsing generic receipt format"""
        # Sample receipt text
        receipt_text = """
        Store Receipt
        
        Apples $2.99
        Bananas $1.49
        Milk $3.99
        
        1234567890123
        """
        
        # Parse the receipt
        result = parse_generic_receipt(receipt_text)
        
        # Assertions
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]['name'], 'Apples')
        self.assertEqual(result[0]['price'], 2.99)
        self.assertEqual(result[1]['name'], 'Bananas')
        self.assertEqual(result[1]['price'], 1.49)
        self.assertEqual(result[2]['name'], 'Milk')
        self.assertEqual(result[2]['price'], 3.99)
    
    @patch('app.ocr.processor.detect_store')
    @patch('app.ocr.processor.parse_safeway_receipt')
    @patch('app.ocr.processor.parse_kroger_receipt')
    @patch('app.ocr.processor.parse_generic_receipt')
    def test_parse_receipt(self, mock_generic, mock_kroger, mock_safeway, mock_detect_store):
        """Test the parse_receipt function with different store types"""
        # Setup
        sample_products = [{'name': 'Test Product', 'price': 1.99}]
        
        # Test Safeway
        mock_detect_store.return_value = "Safeway"
        mock_safeway.return_value = sample_products
        
        result = parse_receipt("Sample text")
        
        mock_detect_store.assert_called_with("Sample text")
        mock_safeway.assert_called_with("Sample text")
        self.assertEqual(result[0]['store'], "Safeway")
        
        # Test Kroger
        mock_detect_store.return_value = "Kroger"
        mock_kroger.return_value = sample_products
        
        result = parse_receipt("Sample text")
        
        mock_kroger.assert_called_with("Sample text")
        self.assertEqual(result[0]['store'], "Kroger")
        
        # Test generic
        mock_detect_store.return_value = "Unknown"
        mock_generic.return_value = sample_products
        
        result = parse_receipt("Sample text")
        
        mock_generic.assert_called_with("Sample text")
        self.assertEqual(result[0]['store'], "Unknown")


if __name__ == '__main__':
    unittest.main()

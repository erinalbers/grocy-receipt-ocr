#!/usr/bin/env python3
"""
Run all tests for the Grocy Receipt OCR application
"""

import unittest
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import test modules
from tests.test_ocr_processor import TestOCRProcessor
from tests.test_grocy_client import TestGrocyClient
from tests.test_web_app import TestWebApp
from tests.test_api_routes import TestAPIRoutes

if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(TestOCRProcessor))
    test_suite.addTest(unittest.makeSuite(TestGrocyClient))
    test_suite.addTest(unittest.makeSuite(TestWebApp))
    test_suite.addTest(unittest.makeSuite(TestAPIRoutes))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Exit with appropriate code
    sys.exit(not result.wasSuccessful())

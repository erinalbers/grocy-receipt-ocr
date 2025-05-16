import os
import re
import pytesseract
from PIL import Image
import pdf2image
import cv2
import numpy as np
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import get_logger

# Initialize logger
logger = get_logger('ocr_process')

def process_receipt(filepath, output_txt_path=None):
    """
    Process a receipt image or PDF and save OCR text to a file.

    Args:
        filepath: Path to the receipt file.
        output_txt_path: Optional path to save OCR text.

    Returns:
        Path to saved OCR text file.
    """
    logger.info(f"Processing receipt image: {filepath}")

    if not os.path.exists(filepath):
        logger.error(f"File not found: {filepath}")
        return None

    if output_txt_path is None:
        output_txt_path = os.path.splitext(filepath)[0] + ".txt"
    logger.info(f"OCR text will be saved to: {output_txt_path}")
    # try:
    logger.info("Extracting text from receipt")
    text = extract_text(filepath)
    text = pre_filter_text(text)
    logger.info(f"Extracted text: {text}")
    Path(output_txt_path).write_text(text, encoding='utf-8')
    logger.info(f"OCR text saved to {output_txt_path}")
    return output_txt_path
    # except Exception as e:
    #     logger.error(f"Failed to extract OCR text: {e}")
    #     return None

def extract_products_from_ocr_file(txt_path):
    """
    Parse saved OCR text and extract product information.

    Args:
        txt_path: Path to OCR text file.

    Returns:
        List of product dictionaries.
    """
    logger.info(f"Parsing products from OCR file: {txt_path}")

    if not os.path.exists(txt_path):
        logger.error(f"OCR text file not found: {txt_path}")
        return []

    # try:
    text = Path(txt_path).read_text(encoding='utf-8')
    products = parse_receipt(text)

    logger.info(f"Parsed {len(products)} products")
    for product in products:
        logger.debug(f"Product: {product}")
    return products
    # except Exception as e:
    #     logger.error(f"Failed to parse products: {e}")
    #     return []

def extract_text(filepath):
    """
    Extract text from an image or PDF using OCR
    
    Args:
        filepath: Path to the image or PDF file
        
    Returns:
        Extracted text as string
    """
    file_ext = os.path.splitext(filepath)[1].lower()
    custom_words_path = "/config/ocr_dict.txt"  # one word per line
    custom_config = f'--psm 6 --user-words {custom_words_path}'
    
    if file_ext == '.pdf':
        # Convert PDF to images
        images = pdf2image.convert_from_path(filepath)
        text = ""
        # Process each page
        for img in images:
            # Convert PIL image to OpenCV format
            img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            
            # Preprocess image
            img_processed = preprocess_image(img_cv)
            
            # Extract text from processed image
            page_text = pytesseract.image_to_string(img_processed, config=custom_config)
            text += page_text + "\n\n"
    else:
        # Load image
        img = cv2.imread(filepath)
        
        # Preprocess image
        img_processed = preprocess_image(img)
        
        # Extract text
        text = pytesseract.image_to_string(img_processed, config=custom_config)
    
    return text

def preprocess_image(img):
    """
    Preprocess image for better OCR results
    
    Args:
        img: OpenCV image
        
    Returns:
        Processed image
    """
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Apply thresholding
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Noise removal
    kernel = np.ones((1, 1), np.uint8)
    opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
    
    return opening

def parse_receipt(self, text):
    """
    Parse receipt text to extract product information
    
    Args:
        text: Receipt text
        
    Returns:
        List of dictionaries containing product information
    """
    products = []
    
    # Detect receipt type/store
    store = self.detect_store(text)
    logger.info(f"Detected store: {store}")
    
    if store:    
        if store.get('has_categories',False) == True:
            
            products = self.generic_category_receipt()
            
    
    # Apply store-specific parsing
    if store == "Safeway":
        products = parse_safeway_receipt(text)
    elif store == "Albertsons":
        products = parse_albertsons_receipt(text)
    elif store == "Kroger":
        products = parse_kroger_receipt(text)
    elif store == "WinCo":
        products = parse_winco_receipt(text)
    elif store == "PetCo":
        products = parse_petco_receipt(text)
    else:
        # Generic parsing
        products = self.parse_generic_receipt(text)
    
    # Add store information to each product
    for product in products:
        product['store'] = store
    
    return products

def detect_store(text):
    """
    Detect the store from receipt text
    
    Args:
        text: Receipt text
        
    Returns:
        Store name or "Unknown"
    """
    text_lower = text.lower()
    
    if "safeway" in text_lower:
        return "Safeway"
    elif "kroger" in text_lower:
        return "Kroger"
    elif "walmart" in text_lower:
        return "Walmart"
    elif "target" in text_lower:
        return "Target"
    elif "winco" in text_lower:
        return "WinCo"
    elif "petco" in text_lower:
        return "PetCo"
    else:
        return "Unknown"

def get_category_mappings_for_store(store):
    with open('/config/category_mappings.json', 'r') as f:
        category_mappings = json.load(f)
    return category_mappings.get(store, {})

def parse_winco_receipt(text):
    pattern = r'^(?P<title>.*)\s+(?P<barcode>\d+)\s+(?P<price>\d*[\.\,]{1}\d{2})\s*[\S]{0,2}$'
    return generic_no_category_receipt(text, pattern)

def parse_petco_receipt(text):
    pattern = r'^(?P<barcode>\d+)\s+(?P<title>.*)\s+(?P<price>\d*[\.\,]{1}\d{2})\s*[\S]{0,2}$'
    return generic_no_category_receipt(text, pattern)

def parse_safeway_receipt(text):
    categories = get_category_mappings_for_store("Safeway")
    pattern = r'^(?P<barcode>\d+)\s*(?P<title>.*)\s+(?P<full_price>\d+[\.,]+\d{2})\s+(?P<price>\d+[\.,]+\d{2})\s*[5S$]*$'
    return generic_category_receipt(text, None, categories)

def parse_albertsons_receipt(text):
    categories = get_category_mappings_for_store("Albertsons")
    pattern = r'^(?P<barcode>\d+)\s*(?P<title>.*)\s+(?P<full_price>\d+[\.,]+\d{2})\s+(?P<price>\d+[\.,]+\d{2})\s*[5S$]*$'
    return generic_category_receipt(text, None, categories)

def generic_category_receipt(text, pattern, categories):
    """
    Parse generic receipt format
    
    Args:
        text: Receipt text
        
    Returns:
        List of dictionaries containing product information
    """
    products = []
    
    text = remove_header_footer(text, False, False)
    # Split text into lines
    lines = text.split('\n')
    logger.info(f"Processing {len(lines)} lines")

    current_category = ""

    logger.info(f"Categories: {categories}")
    
    for i, line in enumerate(lines):
        # Look for lines with price patterns
        line = clean_line(line)

        logger.info(f"Line {i}: {line}")

        if len(line) > 3:
            category_set = False
            if categories.get(line) is not None:
                current_category = categories.get(line)
                logger.info(f"Found category: {current_category}")
                category_set = True
            else:
                for key, value in categories.items():
                    # logger.info(f"Checking category: {key} {value} {line}")
                    if line.startswith(key) == True:
                        current_category = value
                        logger.info(f"Found category: {current_category}")
                        category_set = True
                        break
            if(category_set == True):
                continue

        product_match = re.search(pattern, line)
        if product_match:
            # Extract price
            price_str = product_match.group(4)
            try:
                price = float(price_str)
            except ValueError:
                logger.info(f"Invalid price: {price_str}")
                continue
            
            # Extract product name (text before the price)
            product_name = product_match.group(2)
            
            # Skip if product name is too short or empty
            if len(product_name) < 3:
                continue
            
            # Look for barcode in adjacent lines
            barcode = product_match.group(1)
            
            logger.info({
                'name': product_name,
                'price': price,
                'barcode': barcode,
                'category': current_category,
                'store': 'Safeway',
            })

            products.append({
                'name': product_name,
                'price': price,
                'barcode': barcode,
                'category': current_category,
                'store': 'Safeway',
            })
    
    return products

def generic_no_category_receipt(text, regexp):
    """
    Parse generic receipt format
    
    Args:
        text: Receipt text
        
    Returns:
        List of dictionaries containing product information
    """
    products = []
    lines = text.split('\n')
    logger.info(f"Processing {len(lines)} lines")
    for i, line in enumerate(lines):
        # Look for lines with price patterns
        line = clean_line(line)

        logger.info(f"Line {i}: {line}")

        if len(line) > 3:
                
            product_match = re.search(regexp, line)
            if product_match:
                # Extract price
                price_str = product_match.group('price')
                try:
                    price = float(price_str)
                except ValueError:
                    logger.info(f"Invalid price: {price_str}")
                    continue
                
                # Extract product name (text before the price)
                product_name = product_match.group('title')
                
                # Skip if product name is too short or empty
                if len(product_name) < 3:
                    continue
                
                # Look for barcode in adjacent lines
                barcode = product_match.group('barcode')
                
                logger.info({
                    'name': product_name,
                    'price': price,
                    'barcode': barcode,
                    'category': None,
                    'store': 'Safeway',
                })

                products.append({
                    'name': product_name,
                    'price': price,
                    'barcode': barcode,
                    'category': None,
                    'store': 'Safeway',
                })
    
    return products

def parse_kroger_receipt(text):
    """
    Parse Kroger receipt format
    
    Args:
        text: Receipt text
        
    Returns:
        List of dictionaries containing product information
    """
    # Similar implementation to Safeway but adjusted for Kroger format
    products = []
    current_category = None
    
    # Split text into lines
    lines = text.split('\n')
    
    for i, line in enumerate(lines):
        # Implementation specific to Kroger receipts
        # ...
        pass
    
    return products

def remove_header_footer(text, start_marker, end_marker):
    """
    Remove header and footer from receipt text

    Args:
        text: Receipt text
        start: Start of header/footer
        end: End of header/footer

    Returns:
        Receipt text with header/footer removed
    """
    # Remove header/footer
    logger.info(text)

    # Find the index after the start marker
    if(start_marker):
        start_index = text.find(start_marker)
        if start_index != -1:
            start_index += len(start_marker)
        else:
            start_index = 0
    else:
        start_index = 0

    if end_marker:
        # Find the index of the end marker
        end_index = text.find(end_marker, start_index)
        if end_index == -1:
            end_index = len(text)
    else: 
        # Find the index of the end marker
        end_index = len(text)

    # Extract the substring
    result = text[start_index:end_index].strip()

    logger.info("stripped product text: " + result)

    return result

def clean_line(line):
    original_line = line
    line = line.strip()
    line = line.replace("€", "e")
    line = line.replace("«", "")
    line = line.replace("~", "-")
    line = line.replace("(", "")
    line = line.replace(")", "")
    line = line.replace("¥", "Y")
    line = line.replace("Wenber Savings", "Member Savings")
    line = re.sub(r'\s§$', ' S', line)
    line = re.sub(r'\s8$', ' S', line)
    line = re.sub(r'\s\$$', r' S', line)
    line = re.sub(r'(\d\d)8$', r'\1 S', line)
    line = re.sub(r'(\d+)\,(\d{2})\s', r'\1.\2', line) # commas instead of decimals in prices
    line = re.sub(r'(\d\.\d{2})(\d)', r'\1 \2', line) # triple decimal points are usually numbers that were squished and need to be separated
    line = re.sub(r'\s5$', ' S', line) # the 5 at the end of the line is an S for sale (Safeway, Albertsons)
    line = re.sub(r'\S{4}er S\Svings -', 'Member Savings -', line) # the 5 at the end of the line is an S for sale (Safeway, Albertsons)
    line = re.sub(r'Coup\Sn', 'Coupon', line) # the 5 at the end of the line is an S for sale (Safeway, Albertsons)
    line = re.sub(r'Stor\S', 'Store', line) # the 5 at the end of the line is an S for sale (Safeway, Albertsons)

    if line != original_line:
        logger.info(f"Cleaned line: {original_line} : {line}")
    return line

def pre_filter_text(text):
    """
    Pre-filter text for better OCR results
    """
    logger.info("Pre-filtering text")
    logger.info(text)
    lines = text.split('\n')
    filtered_lines = []
    for line in lines:
        line = clean_line(line)
        filtered_lines.append(line)
    return '\n'.join(filtered_lines)
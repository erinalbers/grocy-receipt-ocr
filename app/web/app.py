import os
import json
from flask import Flask, request, render_template, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
import redis
from rq import Queue
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ocr.processor import process_receipt
from ocr.processor import extract_products_from_ocr_file
from grocy.client import GrocyClient
from utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key')
app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', '/uploads')
app.config['USE_QUEUE'] = os.environ.get('USE_QUEUE', "False") == "True"
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

logger.info(f"Upload folder set to: {app.config['UPLOAD_FOLDER']}")

# Setup Redis connection
redis_host = os.environ.get('REDIS_HOST', 'redis')
redis_port = int(os.environ.get('REDIS_PORT', 6379))
logger.info(f"Connecting to Redis at {redis_host}:{redis_port}")

try:
    redis_conn = redis.Redis(
        host=redis_host,
        port=redis_port
    )
    queue = Queue(connection=redis_conn)
    logger.info("Redis connection established")
except Exception as e:
    logger.error(f"Failed to connect to Redis: {e}")
    raise

# Initialize Grocy client
grocy_client = GrocyClient(
    api_url=os.environ.get('GROCY_API_URL'),
    api_key=os.environ.get('GROCY_API_KEY')
)

# Load category mappings
with open('/config/category_mappings.json', 'r') as f:
    category_mappings = json.load(f)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_receipt():
    if 'receipt' not in request.files:
        flash('No file part')
        logger.warning("Upload attempted with no file part")
        return redirect(request.url)
    
    file = request.files['receipt']
    if file.filename == '':
        flash('No selected file')
        logger.warning("Upload attempted with empty filename")
        return redirect(request.url)
    
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        logger.info(f"Saving uploaded file to {filepath}")
        try:
            # Ensure upload directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            file.save(filepath)
            logger.info(f"File saved successfully: {filepath}")
            
            # Check if file exists after saving
            if os.path.exists(filepath):
                logger.info(f"File exists at {filepath}, size: {os.path.getsize(filepath)} bytes")
            else:
                logger.error(f"File does not exist after saving: {filepath}")
            
            if app.config['USE_QUEUE'] == True:
                logger.info("Using queue")
                # Queue OCR processing job
                job = queue.enqueue(process_receipt, filepath)
                logger.info(f"OCR job queued with ID: {job.id}")
                logger.info(queue)
                return redirect(url_for('processing', job_id=job.id))
            else:
                logger.info("Not using queue")
                ocr_file = process_receipt(filepath)
                # products = extract_products_from_ocr_file(ocr_file)
                logger.info(f"OCR ocr_file: {ocr_file}")
                # print(products)

        except Exception as e:
            logger.error(f"Error saving file or queueing job: {e}")
            flash(f"Error processing file: {str(e)}")
            return redirect(request.url)

@app.route('/processing/<job_id>')
def processing(job_id):
    job = queue.fetch_job(job_id)
    
    if job is None:
        flash('Job not found')
        return redirect(url_for('index'))
    
    if job.is_finished:
        return redirect(url_for('ocr', job_id=job_id))
    
    return render_template('processing.html', job_id=job_id)

@app.route('/job-status/<job_id>')
def job_status(job_id):
    job = queue.fetch_job(job_id)
    
    if job is None:
        return jsonify({'status': 'error', 'message': 'Job not found'})
    
    status = {
        'status': job.get_status(),
        'result': job.result if job.is_finished else None
    }
    logger.info(f"Job status: {status}")
    return jsonify(status)

@app.route('/ocr/<job_id>', methods=['POST','GET'])
def ocr(job_id):
    job = queue.fetch_job(job_id)
    
    if job is None or not job.is_finished:
        flash('Job not found or still processing')
        return redirect(url_for('index'))
    
    path = job.result  # Assuming job.result contains the file path

    # Check if the file exists at the path
    if not os.path.exists(path):
        flash('OCR file not found.')
        return redirect(url_for('index'))

    if request.method == 'POST':
        ocr_data = request.form.get('ocr_data')
        if ocr_data:
            logger.info(f"OCR data received: {ocr_data[:500]}...")  # Log first 500 chars of OCR data for debugging
            try:
                with open(path, 'w', encoding='utf-8') as file:
                    file.write(ocr_data)
                return redirect(url_for('review', job_id=job_id))
            except Exception as e:
                logger.error(f"Error writing OCR data to file: {e}")
                flash('Error saving OCR data.')
                return redirect(url_for('index'))
    else: 
        try:
            # Open and read the OCR text file
            with open(path, 'r') as file:
                ocr_data = file.read()
            
            logger.info(f"OCR job result: {ocr_data[:500]}...")  # Log first 500 chars of OCR data for debugging

            return render_template('ocr.html', job_id=job_id, ocr_data=ocr_data)        
        except Exception as e:
            logger.error(f"Error reading OCR file: {e}")
            flash('Error reading OCR file.')
            return redirect(url_for('index'))
            

@app.route('/review/<job_id>')
def review(job_id):
    job = queue.fetch_job(job_id)
    
    if job is None or not job.is_finished:
        flash('Job not found or still processing')
        return redirect(url_for('index'))
    
    products = extract_products_from_ocr_file(job.result)
    logger.info(f"Products: {products}")
    categories = grocy_client.get_product_categories()
    locations = grocy_client.get_locations()
    quantity_units = grocy_client.get_quantity_units()

    # Check each product against Grocy database
    for product in products:
        if 'barcode' in product and product['barcode']:
            standardized_barcode = grocy_client.normalize_receipt_barcode(product['barcode'])
            product['barcode'] = standardized_barcode
            grocy_product = grocy_client.find_product_by_barcode(standardized_barcode)
            logger.info(f"Grocy product: {grocy_product}")
            product['in_grocy'] = grocy_product is not None
            if grocy_product is not None:
                logger.info(f"Grocy product id: {grocy_product.get('product',{}).get('id')}")
                product['grocy_id'] = grocy_product.get('product',{}).get('id')
        else:
            product['in_grocy'] = False
            product['grocy_id'] = None
    
    return render_template('review.html', products=products, job_id=job_id, categories=categories, locations=locations, quantity_units=quantity_units)

@app.route('/create-product', methods=['POST'])
def create_product():
    data = request.json
    
    # Map store category to Grocy category if available
    logger.info(f"Data: {data}")
    product_id = data.get('product_id',None)
    barcode = data.get('barcode', '')
    if product_id is not None and product_id != "":
        grocy_product = grocy_client.get_product(data['product_id'])
        if grocy_product:
            assignments = {
                "display_amount": data.get('display_amount',1),
                "qu_id": data.get('qu_id',None),
                "note": data.get('name', ''),
                'store': data.get('store', ''),
            }
            logger.info(f"Assignments: {assignments}")
            result = grocy_client.add_barcode_to_product(product_id, barcode, assignments)
    else:
        # Create product in Grocy
        product_data = {
            'name': data['name'],
            'barcode': data.get('barcode', ''),
            'product_group_id': data.get('category'),
            'location_id': data.get('location'),
            'qu_id_purchase': data.get('qu_id_purchase'),
            'qu_id_stock': data.get('qu_id_stock'),
            'store': data.get('store', ''),
        }
        logger.info(f"Creating product: {product_data}")
        result = grocy_client.create_product(product_data)
    
    return jsonify(result)

@app.route('/lookup-product', methods=['POST'])
def lookup_product():
    data = request.json
    
    barcode = data.get('barcode', '')
    logger.info(f"Data: {data}")

    logger.info(f"Looking up product: {barcode}")
    result = grocy_client.external_lookup(barcode)
    
    return jsonify(result)

@app.route('/products-for-group/<product_group_id>', methods=['POST'])
def products_for_group(product_group_id):
    data = request.json
    
    logger.info(f"Data: {data}")

    logger.info(f"Looking up product: {product_group_id}")
    result = grocy_client.products_for_group(product_group_id)
    
    return jsonify(result)

@app.route('/purchases/<job_id>')
def purchases(job_id):
    job = queue.fetch_job(job_id)

    logger.info(f"Job: {job}")
    
    if job is None or not job.is_finished:
        flash('Job not found or still processing')
        return redirect(url_for('index'))
    
    products = extract_products_from_ocr_file(job.result)
    grocy_products = []
    stores = grocy_client.get_shopping_locations()

    logger.info(f"Products: {stores}")

    for product in products:
        shopping_location_id = None
        for store in stores:
            if store['name'] == product['store']:
                shopping_location_id = store['id']
                break
        if 'barcode' in product and product['barcode']:
            standardized_barcode = grocy_client.normalize_receipt_barcode(product['barcode'])
            grocy_product = grocy_client.find_product_by_barcode(standardized_barcode)
            logger.info(f"Grocy product: {grocy_product}")

            if grocy_product is not None:
                grocy_product['barcode'] = standardized_barcode
                grocy_product['price'] = product['price']
                grocy_product['shopping_location_id'] = shopping_location_id
                grocy_product['url'] = os.environ.get('GROCY_API_URL').replace('/api','') + "/products/" + str(grocy_product.get('product',{}).get('id'))
                grocy_products.append(grocy_product)
        else:
            product['in_grocy'] = False


    # Filter only products that are in Grocy or have been created    
    return render_template('purchases.html', products=grocy_products)

@app.route('/add-purchase', methods=['POST'])
def add_purchase():
    data = request.json
    
    purchase_data = {
        'product_id': data['product_id'],
        'amount': data['amount'],
        'price': data['price'],
        'days_out': data['days_out'],
        'shopping_location_id': data['shopping_location_id'],
    }
    
    result = grocy_client.add_purchase(purchase_data)
    
    return jsonify(result)

if __name__ == '__main__':
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 8080))
    app.run(host=host, port=port, debug=True)

# Grocy Receipt OCR

A tool to automatically process grocery receipts, extract product information using OCR, and add items to your Grocy inventory system.

## Features

- **Receipt OCR**: Extract product information from receipt images or PDFs
- **Grocy Integration**: Check products against your Grocy database
- **Barcode Matching**: Identify products by barcode number
- **Smart Product Creation**: Generate links to create missing products in Grocy
- **Category Mapping**: Map store categories to Grocy product categories
- **Purchase Automation**: Pre-populate purchase entries with prices from receipts

## How It Works

1. Upload a receipt image or PDF
2. The system OCRs the receipt to extract product information
3. Products are checked against your Grocy database by barcode
4. For products not found in the database:
   - A link is provided to create the item
   - Store categories are mapped to Grocy categories when possible
5. After all products are added (or marked to skip), you'll be directed to a page with:
   - Links to the "purchase" APIs for each product
   - Pre-populated prices from the receipt

## Prerequisites

- Docker and Docker Compose
- Grocy instance with API access
- Receipt files (images or PDFs)

## Setup

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/grocy-receipt-ocr.git
   cd grocy-receipt-ocr
   ```

2. Configure your environment variables in a `.env` file:
   ```
   GROCY_API_URL=https://your-grocy-instance/api
   GROCY_API_KEY=your-api-key
   ```

3. Start the application:
   ```
   docker-compose up -d
   ```

4. Access the web interface at `http://localhost:8080`

## Configuration

### Category Mapping

You can configure store-specific category mappings in the `config/category_mappings.json` file:

```json
{
  "Safeway": {
    "REFRIG/FROZEN": "Refrigerated Foods",
    "PRODUCE": "Fruits & Vegetables",
    "MEAT": "Meat"
  }
}
```

## Usage

1. Upload a receipt through the web interface
2. Review the extracted products
3. For each product not found in Grocy:
   - Click "Create in Grocy" to add it to your database
   - Or click "Skip" to ignore this product
4. Once all products are processed, proceed to the purchase page
5. Review the pre-populated purchase entries
6. Click "Add Purchase" for each item you want to add to your inventory

## Development

### Project Structure

```
grocy-receipt-ocr/
├── app/                  # Application code
│   ├── api/              # API endpoints
│   ├── ocr/              # OCR processing logic
│   ├── grocy/            # Grocy API integration
│   └── web/              # Web interface
├── config/               # Configuration files
├── docker/               # Docker configuration
├── tests/                # Test suite
└── docker-compose.yml    # Docker Compose configuration
```

### Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Testing

### Running Tests

You can run the tests using the provided test runner:

```bash
# Run tests locally
python run_tests.py

# Or using Docker
docker-compose -f docker-compose.test.yml up
```

The test suite includes:

- Unit tests for OCR processing
- Unit tests for Grocy API integration
- Unit tests for web interface
- Unit tests for API endpoints

### Test Coverage

To generate a test coverage report:

```bash
pytest --cov=app tests/
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

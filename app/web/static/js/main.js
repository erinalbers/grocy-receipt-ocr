/**
 * Grocy Receipt OCR - Main JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    // File input validation
    const fileInput = document.getElementById('receipt');
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            validateFileInput(this);
        });
    }
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});

/**
 * Validate file input for receipt upload
 * @param {HTMLInputElement} input - The file input element
 */
function validateFileInput(input) {
    const maxSize = 10 * 1024 * 1024; // 10MB
    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'application/pdf'];
    const submitButton = document.querySelector('button[type="submit"]');
    
    if (input.files.length > 0) {
        const file = input.files[0];
        
        // Check file type
        if (!allowedTypes.includes(file.type)) {
            alert('Invalid file type. Please upload an image (JPEG, PNG, GIF) or PDF file.');
            input.value = '';
            return false;
        }
        
        // Check file size
        if (file.size > maxSize) {
            alert('File is too large. Maximum file size is 10MB.');
            input.value = '';
            return false;
        }
        
        // Enable submit button
        if (submitButton) {
            submitButton.disabled = false;
        }
        
        return true;
    }
    
    return false;
}

/**
 * Poll for job status
 * @param {string} jobId - The job ID to check
 * @param {function} onComplete - Callback function when job is complete
 */
function pollJobStatus(jobId, onComplete) {
    fetch(`/job-status/${jobId}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'finished') {
                onComplete(data.result);
            } else if (data.status === 'failed') {
                showError('Error processing receipt. Please try again.');
            } else {
                // Continue polling
                setTimeout(() => pollJobStatus(jobId, onComplete), 1000);
            }
        })
        .catch(error => {
            console.error('Error checking job status:', error);
            showError('Error checking status. Please refresh the page.');
        });
}

/**
 * Show error message
 * @param {string} message - Error message to display
 */
function showError(message) {
    const errorContainer = document.getElementById('error-container');
    if (errorContainer) {
        errorContainer.innerHTML = `<div class="alert alert-danger">${message}</div>`;
        errorContainer.style.display = 'block';
    } else {
        alert(message);
    }
}

/**
 * Create product in Grocy
 * @param {Object} productData - Product data to create
 * @param {function} onSuccess - Callback function on success
 * @param {function} onError - Callback function on error
 */
function createProduct(productData, onSuccess, onError) {
    fetch('/create-product', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(productData),
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            onError(data.error);
        } else {
            onSuccess(data);
        }
    })
    .catch(error => {
        console.error('Error creating product:', error);
        onError('Network error. Please try again.');
    });
}

/**
 * Add purchase in Grocy
 * @param {Object} purchaseData - Purchase data to add
 * @param {function} onSuccess - Callback function on success
 * @param {function} onError - Callback function on error
 */
function addPurchase(purchaseData, onSuccess, onError) {
    fetch('/add-purchase', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(purchaseData),
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            onError(data.error);
        } else {
            onSuccess(data);
        }
    })
    .catch(error => {
        console.error('Error adding purchase:', error);
        onError('Network error. Please try again.');
    });
}

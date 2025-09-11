// CSV Upload Drag & Drop functionality
class CSVUploadHandler {
    constructor() {
        this.dropZone = null;
        this.fileInput = null;
        this.initialize();
    }

    initialize() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setup());
        } else {
            this.setup();
        }
    }

    setup() {
        // Find the CSV upload element
        this.dropZone = document.getElementById('csv-upload');
        if (!this.dropZone) {
            console.log('CSV upload element not found, retrying...');
            setTimeout(() => this.setup(), 1000);
            return;
        }

        // Find the actual file input within the drop zone
        this.fileInput = this.dropZone.querySelector('input[type="file"]');
        if (!this.fileInput) {
            console.log('File input not found within CSV upload element');
            return;
        }

        this.setupDragAndDrop();
        console.log('CSV Upload Handler initialized');
    }

    setupDragAndDrop() {
        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            this.dropZone.addEventListener(eventName, this.preventDefaults, false);
            document.body.addEventListener(eventName, this.preventDefaults, false);
        });

        // Highlight drop zone when item is dragged over it
        ['dragenter', 'dragover'].forEach(eventName => {
            this.dropZone.addEventListener(eventName, this.highlight, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            this.dropZone.addEventListener(eventName, this.unhighlight, false);
        });

        // Handle dropped files
        this.dropZone.addEventListener('drop', this.handleDrop.bind(this), false);
    }

    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    highlight(e) {
        const dropZone = e.target.closest('#csv-upload');
        if (dropZone) {
            dropZone.style.borderColor = '#007bff';
            dropZone.style.backgroundColor = '#f8f9ff';
        }
    }

    unhighlight(e) {
        const dropZone = e.target.closest('#csv-upload');
        if (dropZone) {
            dropZone.style.borderColor = '#ddd';
            dropZone.style.backgroundColor = '';
        }
    }

    handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;

        this.handleFiles(files);
    }

    handleFiles(files) {
        const feedbackEl = this._ensureFeedbackElement();
        const emitFeedback = (msg, level = 'info') => {
            if (feedbackEl) {
                feedbackEl.textContent = msg;
                feedbackEl.dataset.level = level;
            }
            console[level === 'error' ? 'error' : 'log'](msg);
            const evt = new CustomEvent('csv-upload-feedback', { detail: { message: msg, level } });
            window.dispatchEvent(evt);
        };

        // Filter for CSV files only
        const csvFiles = Array.from(files).filter(file => {
            return file.type === 'text/csv' ||
                   file.type === 'application/vnd.ms-excel' ||
                   file.name.toLowerCase().endsWith('.csv');
        });

        if (csvFiles.length === 0) {
            emitFeedback('Please drop a CSV file (.csv)', 'error');
            return;
        }

        if (csvFiles.length > 1) {
            emitFeedback('Please drop only one CSV file at a time', 'error');
            return;
        }

        const file = csvFiles[0];

        // Determine max size from data attribute if present
        if (!this.dropZone.dataset.maxSize) {
            // default 500MB fallback
            this.dropZone.dataset.maxSize = String(500 * 1024 * 1024);
        }
        const maxSize = parseInt(this.dropZone.dataset.maxSize, 10);
        if (file.size > maxSize) {
            emitFeedback(`File size too large. Maximum size is ${(maxSize / (1024 * 1024)).toFixed(0)}MB.`, 'error');
            return;
        }

        // Create a DataTransfer object to set the file
        const dt = new DataTransfer();
        dt.items.add(file);
        this.fileInput.files = dt.files;

        // Trigger change event to notify Gradio
        const event = new Event('change', { bubbles: true });
        this.fileInput.dispatchEvent(event);

        emitFeedback(`CSV file selected: ${file.name}`, 'info');
    }

    _ensureFeedbackElement() {
        let el = document.getElementById('csv-upload-feedback');
        return el;
    }
}

// Initialize when page loads
window.addEventListener('load', function() {
    setTimeout(function() {
        window.csvUploadHandler = new CSVUploadHandler();
    }, 1000);
});

// Export for potential external use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CSVUploadHandler;
}
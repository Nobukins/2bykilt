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
        // Filter for CSV files only
        const csvFiles = Array.from(files).filter(file => {
            return file.type === 'text/csv' ||
                   file.type === 'application/vnd.ms-excel' ||
                   file.name.toLowerCase().endsWith('.csv');
        });

        if (csvFiles.length === 0) {
            alert('Please drop a CSV file (.csv)');
            return;
        }

        if (csvFiles.length > 1) {
            alert('Please drop only one CSV file at a time');
            return;
        }

        const file = csvFiles[0];

        // Validate file size (max 500MB as per BatchEngine config)
        const maxSize = 500 * 1024 * 1024; // 500MB
        if (file.size > maxSize) {
            alert('File size too large. Maximum size is 500MB.');
            return;
        }

        // Create a DataTransfer object to set the file
        const dt = new DataTransfer();
        dt.items.add(file);
        this.fileInput.files = dt.files;

        // Trigger change event to notify Gradio
        const event = new Event('change', { bubbles: true });
        this.fileInput.dispatchEvent(event);

        console.log('CSV file dropped:', file.name);
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
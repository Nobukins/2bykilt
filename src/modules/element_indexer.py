from playwright.sync_api import sync_playwright

def add_element_indices(page):
    """Add visual indices to elements, marking interactive vs non-interactive elements"""
    return page.evaluate("""() => {
        // Remove existing indices if any
        document.querySelectorAll('.element-index-overlay').forEach(el => el.remove());
        
        // Get all visible elements
        const elements = Array.from(document.querySelectorAll('*'));
        const visibleElements = elements.filter(el => {
            const style = window.getComputedStyle(el);
            const rect = el.getBoundingClientRect();
            return style.display !== 'none' && 
                   style.visibility !== 'hidden' && 
                   rect.width > 0 && rect.height > 0;
        });
        
        // Create element data store
        const elementData = [];
        
        // Add indices to elements
        visibleElements.forEach((el, i) => {
            // Determine if element is interactive
            const isInteractive = ['A', 'BUTTON', 'INPUT', 'SELECT', 'TEXTAREA'].includes(el.tagName) || 
                                el.getAttribute('role') === 'button' || 
                                parseInt(el.getAttribute('tabindex') || '-1') >= 0;
            
            // Create index prefix based on interactivity
            const prefix = isInteractive ? `${i}[:]` : `_[:]`;
            
            // Create overlay element with index
            const overlay = document.createElement('div');
            overlay.className = 'element-index-overlay';
            overlay.textContent = prefix + el.tagName.toLowerCase();
            overlay.style.cssText = `
                position: absolute;
                background-color: ${isInteractive ? 'rgba(0, 255, 0, 0.7)' : 'rgba(255, 0, 0, 0.7)'};
                color: white;
                padding: 2px 5px;
                border-radius: 3px;
                font-size: 12px;
                z-index: 10000;
                pointer-events: none;
            `;
            
            // Position the overlay
            const rect = el.getBoundingClientRect();
            overlay.style.top = `${window.scrollY + rect.top}px`;
            overlay.style.left = `${window.scrollX + rect.left}px`;
            
            // Add to document
            document.body.appendChild(overlay);
            
            // Store element data
            elementData.push({
                index: i,
                isInteractive: isInteractive,
                tagName: el.tagName.toLowerCase(),
                element: el  // Store reference to the actual element
            });
        });
        
        // Store element data globally
        window.__elementIndices = elementData;
        
        // Add a utility function to interact with elements by index
        window.interactWithIndexedElement = (index, action, value) => {
            if (!window.__elementIndices || index >= window.__elementIndices.length) return false;
            const elementData = window.__elementIndices[index];
            if (!elementData || !elementData.isInteractive) return false;
            
            const element = elementData.element;
            if (!element) return false;
            
            try {
                if (action === 'click') {
                    element.click();
                    return true;
                } else if (action === 'fill' && (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA')) {
                    element.value = value;
                    element.dispatchEvent(new Event('input', { bubbles: true }));
                    element.dispatchEvent(new Event('change', { bubbles: true }));
                    return true;
                }
            } catch (e) {
                console.error(`Error interacting with element: ${e}`);
                return false;
            }
            return false;
        };
        
        return elementData;
    }""")

def interact_with_indexed_element(page, index, action, value=None):
    """Interact with an element by its index"""
    value_js = f"'{value}'" if value is not None else "null"
    
    result = page.evaluate(f"""() => {{
        if (!window.interactWithIndexedElement) return {{ success: false, error: 'Element indexing not initialized' }};
        const success = window.interactWithIndexedElement({index}, '{action}', {value_js});
        
        if (!success) {{
            // Try to get error information
            if (!window.__elementIndices) return {{ success: false, error: 'No indexed elements found' }};
            if ({index} >= window.__elementIndices.length) return {{ success: false, error: 'Index out of bounds' }};
            const element = window.__elementIndices[{index}];
            if (!element) return {{ success: false, error: 'Element not found' }};
            if (!element.isInteractive) return {{ success: false, error: 'Element is not interactive' }};
            return {{ success: false, error: 'Unknown error occurred' }};
        }}
        
        return {{ success: true }};
    }}""")
    
    if not result.get('success', False):
        print(f"Cannot interact with element {index}: {result.get('error', 'Unknown error')}")
        return False
    
    return True

# Example usage
def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("https://example.com")
        
        # Add indices to all elements
        add_element_indices(page)
        
        # Wait for manual inspection
        page.wait_for_timeout(5000)
        
        # Example interaction with element by index
        interact_with_indexed_element(page, 0, "click")  # Click first interactive element
        
        browser.close()

if __name__ == "__main__":
    main()
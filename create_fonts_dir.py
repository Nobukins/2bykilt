import os
import shutil
import sys

def create_font_directories():
    """Create necessary font directories in the assets folder"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    fonts_dir = os.path.join(base_dir, "assets", "fonts")
    
    # Create main fonts directory
    os.makedirs(fonts_dir, exist_ok=True)
    
    # Create sub-directories for different font families
    font_families = ["ui-sans-serif", "system-ui"]
    for family in font_families:
        family_dir = os.path.join(fonts_dir, family)
        os.makedirs(family_dir, exist_ok=True)
        
    print(f"✅ Font directories created at {fonts_dir}")
    
    # Create a placeholder font file to avoid 404s
    # This is just a temporary solution - real fonts should be added later
    for family in font_families:
        for weight in ["Regular", "Bold"]:
            placeholder_path = os.path.join(fonts_dir, family, f"{family}-{weight}.woff2")
            
            # Create an empty file (or copy a default font if available)
            with open(placeholder_path, 'wb', encoding='utf-8') as f:
                f.write(b'')  # Empty file as placeholder
                
            print(f"Created placeholder font: {placeholder_path}")

if __name__ == "__main__":
    create_font_directories()
    print("Run this script to create the necessary font directories.")
    print("Then add actual font files to these directories.")

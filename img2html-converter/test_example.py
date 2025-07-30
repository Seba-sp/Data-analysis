#!/usr/bin/env python3
"""
Test script to demonstrate img2html functionality
"""

import pathlib
from img2html import encode_image, build_html

def test_encode_image():
    """Test the image encoding functionality"""
    print("Testing image encoding...")
    
    # Example usage - you would need an actual image file
    # image_path = pathlib.Path("test_image.jpg")
    # try:
    #     data_uri = encode_image(image_path)
    #     print(f"✅ Image encoded successfully")
    #     print(f"Data URI length: {len(data_uri)} characters")
    # except FileNotFoundError:
    #     print("❌ Test image not found - please add a test image file")
    # except ValueError as e:
    #     print(f"❌ Error: {e}")
    
    print("To test with an actual image:")
    print("1. Place a JPEG (.jpg/.jpeg) or PNG (.png) image file in this directory")
    print("2. Uncomment the test code in this script")
    print("3. Run: python test_example.py")

def test_build_html():
    """Test the HTML generation functionality"""
    print("\nTesting HTML generation...")
    
    # Create a dummy data URI for testing
    dummy_data_uri = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    
    # Test with default A4 size
    html_content = build_html(dummy_data_uri, 210, 297, "test_image")
    print("✅ HTML generated successfully")
    print(f"HTML content length: {len(html_content)} characters")
    
    # Save test HTML file
    test_output = pathlib.Path("test_output.html")
    test_output.write_text(html_content, encoding="utf-8")
    print(f"✅ Test HTML saved to: {test_output}")

if __name__ == "__main__":
    print("=== Image to HTML Converter Test ===\n")
    
    test_build_html()
    test_encode_image()
    
    print("\n=== Test Complete ===")
    print("You can now run the main script with:")
    print("python img2html.py <image_file> [width_mm] [height_mm]") 
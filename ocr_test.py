#!/usr/bin/env python3
"""
Simple OCR test app to evaluate pytesseract vs gosseract
"""

import os
import sys
from PIL import Image
import pytesseract
import argparse
from pathlib import Path

def test_tesseract_installation():
    """Test if tesseract is properly installed and accessible"""
    try:
        version = pytesseract.get_tesseract_version()
        print(f"✅ Tesseract version: {version}")
        return True
    except Exception as e:
        print(f"❌ Tesseract installation issue: {e}")
        return False

def test_basic_ocr():
    """Test basic OCR with a simple created image"""
    try:
        # Create a simple test image with text
        from PIL import Image, ImageDraw, ImageFont
        
        # Create a white image with black text
        img = Image.new('RGB', (400, 100), color='white')
        draw = ImageDraw.Draw(img)
        
        # Try to use a default font, fallback to basic if needed
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 24)
        except:
            font = ImageFont.load_default()
        
        draw.text((10, 30), "Hello World! Test 123", fill='black', font=font)
        
        # Save test image
        test_image_path = "test_ocr_image.png"
        img.save(test_image_path)
        print(f"📸 Created test image: {test_image_path}")
        
        # Perform OCR
        text = pytesseract.image_to_string(img)
        print(f"🔍 OCR Result: '{text.strip()}'")
        
        # Clean up
        os.remove(test_image_path)
        return True
        
    except Exception as e:
        print(f"❌ Basic OCR test failed: {e}")
        return False

def test_pdf_ocr(pdf_path):
    """Test OCR on a PDF file"""
    try:
        import pdf2image
        
        # Convert PDF to images
        pages = pdf2image.convert_from_path(pdf_path, first_page=1, last_page=1)
        
        if not pages:
            print("❌ No pages found in PDF")
            return False
            
        # OCR first page
        text = pytesseract.image_to_string(pages[0])
        print(f"📄 PDF OCR Result (first 200 chars): '{text[:200].strip()}...'")
        return True
        
    except ImportError:
        print("⚠️  pdf2image not installed - skipping PDF test")
        print("   Install with: pip install pdf2image")
        return True
    except Exception as e:
        print(f"❌ PDF OCR test failed: {e}")
        return False

def test_image_ocr(image_path):
    """Test OCR on an image file"""
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img)
        print(f"🖼️  Image OCR Result (first 200 chars): '{text[:200].strip()}...'")
        return True
    except Exception as e:
        print(f"❌ Image OCR test failed: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Test OCR functionality")
    parser.add_argument("--pdf", help="Test OCR on a PDF file")
    parser.add_argument("--image", help="Test OCR on an image file")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    
    args = parser.parse_args()
    
    print("🚀 Starting OCR Tests...")
    print("=" * 50)
    
    # Test 1: Installation
    print("\n1. Testing Tesseract Installation:")
    installation_ok = test_tesseract_installation()
    
    if not installation_ok:
        print("\n💀 Tesseract not properly installed. Exiting.")
        sys.exit(1)
    
    # Test 2: Basic OCR
    print("\n2. Testing Basic OCR:")
    basic_ok = test_basic_ocr()
    
    # Test 3: File-specific tests
    if args.pdf:
        print(f"\n3. Testing PDF OCR on: {args.pdf}")
        test_pdf_ocr(args.pdf)
    
    if args.image:
        print(f"\n3. Testing Image OCR on: {args.image}")
        test_image_ocr(args.image)
    
    print("\n" + "=" * 50)
    if installation_ok and basic_ok:
        print("✅ All basic tests passed! Python OCR setup looks good.")
    else:
        print("❌ Some tests failed. Check the output above.")
    
    print("\n📦 Dependencies used:")
    print("   - pytesseract")
    print("   - Pillow (PIL)")
    print("   - pdf2image (optional, for PDF support)")

if __name__ == "__main__":
    main()
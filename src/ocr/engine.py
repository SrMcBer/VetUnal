import io
import cv2
import fitz
import numpy as np
from PIL import Image, ImageEnhance
import pytesseract

def preprocess_image_for_ocr(image: np.ndarray) -> np.ndarray:
    """
    Preprocess image to improve OCR accuracy
    """
    
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (1, 1), 0)
    
    # Apply adaptive thresholding
    thresh = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    
    # Morphological operations to clean up
    kernel = np.ones((1, 1), np.uint8)
    cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    
    return cleaned

def gentle_preprocess_image(image: Image.Image) -> Image.Image:
    """
    Very gentle preprocessing - only basic enhancements
    """
    # Convert to grayscale if needed
    if image.mode != 'L':
        image = image.convert('L')
    
    # Very slight contrast enhancement only if needed
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(1.1)  # Just 10% increase
    
    return image



def ocr_pdf_page_with_tesseract_improved(pdf_path: str, page_number: int, 
                                        dpi: int = 300) -> str:
    """
    Improved OCR function with Spanish language support and better preprocessing
    """
    try:
        # Open PDF
        doc = fitz.open(pdf_path)
        
        if page_number < 1 or page_number > len(doc):
            raise ValueError(f"Page number {page_number} out of range")
        
        # Get the page (PyMuPDF uses 0-based indexing)
        page = doc.load_page(page_number - 1)
        
        # Render page to image with high DPI
        mat = fitz.Matrix(dpi/72, dpi/72)  # 72 is default DPI
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("ppm")
        
        # Convert to PIL Image
        pil_image = Image.open(io.BytesIO(img_data))
        # 'image': pil_image,
        # 'config': r'--oem 3 --psm 1 -l spa',

        text = pytesseract.image_to_string(pil_image, config=r'--oem 3 --psm 1 -l spa')
        
        doc.close()
        
        return clean_ocr_text(text)
        
    except Exception as e:
        raise RuntimeError(f"OCR failed for page {page_number}: {str(e)}")
        

def clean_ocr_text(text: str) -> str:
    """
    Clean and normalize OCR output
    """
    if not text:
        return ""
    
    # Remove excessive whitespace
    lines = text.split('\n')
    cleaned_lines = []
    prev_empty = False
    
    for line in lines:
        line = line.rstrip()  # Remove trailing whitespace

        if not line.strip():  # Empty line
            if not prev_empty:  # Only add one empty line
                cleaned_lines.append("")
                prev_empty = True
                
        else:
            cleaned_lines.append(line)
            prev_empty = False
    
    return '\n'.join(cleaned_lines)

def debug_ocr_output(pdf_path: str, page_number: int, save_processed_image: bool = False):
    """
    Debug function to help diagnose OCR issues using the new gentle approach
    """
    try:
        doc = fitz.open(pdf_path)
        page = doc.load_page(page_number - 1)
        
        print("=" * 150)
        print(f"Debugging OCR for page {page_number} in {pdf_path}")
        print("=" * 150)
        
        # High resolution render
        mat = fitz.Matrix(300/72, 300/72)
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("ppm")
        
        pil_image = Image.open(io.BytesIO(img_data))
        print(f"Original image size: {pil_image.size}")
        print(f"Original image mode: {pil_image.mode}")
        
        # Save original if requested
        if save_processed_image:
            pil_image.save(f"debug_original_page_{page_number}.png")
            print(f"Saved original image as: debug_original_page_{page_number}.png")
        
        # Create gently processed version
        processed_image = gentle_preprocess_image(pil_image.copy())
        
        if save_processed_image:
            processed_image.save(f"debug_processed_page_{page_number}.png")
            print(f"Saved processed image as: debug_processed_page_{page_number}.png")
        
        # Test the same approaches as the improved OCR function
        approaches = [
            {
                'image': pil_image,
                'config': r'--oem 3 --psm 6 -l spa',
                'name': 'Original + Spanish'
            },
            {
                'image': pil_image,
                'config': r'--oem 3 --psm 6 -l spa+eng',
                'name': 'Original + Spanish+English'
            },
            {
                'image': processed_image,
                'config': r'--oem 3 --psm 6 -l spa',
                'name': 'Gentle preprocessing + Spanish'
            },
            {
                'image': pil_image,
                'config': r'--oem 3 --psm 4 -l spa',
                'name': 'Original + PSM 4 + Spanish'
            },
            {
                'image': pil_image,
                'config': r'--oem 3 --psm 1 -l spa',
                'name': 'Original + PSM 1 + Spanish'  
            },
            {
                'image': pil_image,
                'config': r'--oem 3 --psm 6',
                'name': 'Original + Auto language'
            },
            {
                'image': pil_image,
                'config': r'--oem 3 --psm 6 -l eng',
                'name': 'Original + English only'
            }
        ]
        
        results = []
        
        for approach in approaches:
            try:
                # Get confidence data
                data = pytesseract.image_to_data(
                    approach['image'], 
                    config=approach['config'], 
                    output_type=pytesseract.Output.DICT
                )
                
                # Calculate confidence metrics
                all_confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                high_confidences = [int(conf) for conf in data['conf'] if int(conf) > 30]
                
                avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0
                high_conf_avg = sum(high_confidences) / len(high_confidences) if high_confidences else 0
                
                # Get the text
                text = pytesseract.image_to_string(approach['image'], config=approach['config'])
                
                result = {
                    'name': approach['name'],
                    'config': approach['config'],
                    'avg_confidence': avg_confidence,
                    'high_conf_avg': high_conf_avg,
                    'text_length': len(text.strip()),
                    'text': text,
                    'high_conf_count': len(high_confidences),
                    'total_detections': len(all_confidences)
                }
                results.append(result)
                
            except Exception as e:
                print(f"\n❌ {approach['name']} failed: {e}")
        
        # Sort results by high confidence average (our main metric)
        results.sort(key=lambda x: x['high_conf_avg'], reverse=True)
        
        print(f"\n🏆 RESULTS RANKED BY QUALITY (High confidence average):")
        print("=" * 150)
        
        for i, result in enumerate(results, 1):
            print(f"\n#{i} - {result['name']}")
            print(f"   Config: {result['config']}")
            print(f"   📊 High confidence avg: {result['high_conf_avg']:.1f} ({result['high_conf_count']}/{result['total_detections']} detections)")
            print(f"   📊 Overall confidence avg: {result['avg_confidence']:.1f}")
            print(f"   📝 Text length: {result['text_length']} characters")
            
            # Show text preview
            preview = result['text'][:400].replace('\n', ' ').replace('\r', ' ')
            print(f"   📖 Text preview: {preview}{'...' if len(result['text']) > 400 else ''}")
            print("-" * 100)
        
        # Show the best result in detail
        if results:
            best = results[0]
            print(f"\n🎯 BEST RESULT DETAILS ({best['name']}):")
            print("=" * 150)
            print(best['text'])
            print("=" * 150)
        
        doc.close()
        
    except Exception as e:
        print(f"Debug failed: {e}")
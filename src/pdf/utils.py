import os
import re
from PyPDF2 import PdfReader, PdfWriter
from typing import List
from typing import Optional
import logging


def get_page_count(pdf_path: str) -> int:
    try:
        reader = PdfReader(pdf_path)
        return len(reader.pages)
    except Exception as e:
        raise RuntimeError(f"Failed to get page count for {pdf_path}: {e}")
    

def extract_single_page(pdf_path: str, page_number: int, output_dir: str, desired_name: str) -> str:
    try:
        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        writer.add_page(reader.pages[page_number - 1])  # 1-indexed

        if not desired_name.endswith('.pdf'):
            desired_name += '.pdf'

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        output_path = os.path.join(output_dir, desired_name)

        with open(output_path, 'wb') as out_file:
            writer.write(out_file)

        return output_path
    except Exception as e:
        raise RuntimeError(f"Failed to extract page {page_number}: {e}")

def extract_multiple_pages(pdf_path: str, pages: List[int], output_dir: str, final_name: str) -> str:
    try:
        reader = PdfReader(pdf_path)
        writer = PdfWriter()

        for p in pages:
            writer.add_page(reader.pages[p - 1])  # 1-indexed

        if not final_name.endswith('.pdf'):
            final_name += '.pdf'

        os.makedirs(output_dir, exist_ok=True)

        final_path = os.path.join(output_dir, final_name)

        with open(final_path, 'wb') as out_file:
            writer.write(out_file)

        return final_path
    except Exception as e:
        raise RuntimeError(f"Failed to extract multiple pages {pages}: {e}")

def normalize_string(text: str) -> str:
    """
    Normalize text to handle OCR inconsistencies.
    
    Args:
        text: Input text to normalize
        
    Returns:
        Normalized text
    """
    if not text:
        return ""
    
    # Convert to lowercase and strip whitespace
    normalized = text.lower().strip()
    
    # Add any other normalization rules here
    # For example, replacing common OCR errors
    
    return normalized

def validate_microchip_id(microchip_id: str) -> bool:
    """
    Validate that a microchip ID is properly formatted.
    
    Args:
        microchip_id: The microchip ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not microchip_id:
        return False
    
    # Check if it's exactly 15 digits
    return len(microchip_id) == 15 and microchip_id.isdigit()

def clean_filename(filename: str) -> str:
    """
    Clean a filename by removing invalid characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Cleaned filename safe for filesystem use
    """
    if not filename:
        return "unnamed"
    
    # Remove or replace invalid characters
    invalid_chars = r'[<>:"/\\|?*]'
    cleaned = re.sub(invalid_chars, '_', filename)
    
    # Remove leading/trailing dots and spaces
    cleaned = cleaned.strip('. ')
    
    # Ensure it's not empty after cleaning
    return cleaned if cleaned else "unnamed"

def extract_microchip_id(text: str) -> str:
    """
    Extract microchip ID from text, handling OCR inconsistencies.
    
    Args:
        text: Text containing potential microchip ID
        
    Returns:
        Extracted microchip ID (15 digits)
        
    Raises:
        ValueError: If microchip ID not found or invalid
    """
    logger = logging.getLogger(__name__)
    
    if not text:
        raise ValueError("Empty text provided")
    
    # Normalize text to handle OCR inconsistencies
    normalized_text = normalize_string(text)
    
    # Replace common OCR errors for the marker string
    normalized_text = normalized_text.replace("microchip", "microchip")
    
    # Try to find microchip pattern with potential line breaks or spaces
    # This regex captures the word "microchip" followed by any amount of whitespace/punctuation,
    # then captures consecutive digit groups that might be separated by spaces
    pattern = r'microchip\s*(?:no?\s*)?(\d+(?:\s+\d+)*)'
    matches = re.search(pattern, normalized_text, re.IGNORECASE)
    
    if matches:
        # Extract all digits from the captured group, removing any spaces
        digit_string = matches.group(1)
        digit_string = re.sub(r'[\s\t\n]', '', digit_string)
        
        # Check if we have exactly 15 digits (expected microchip length)
        if len(digit_string) == 15 and digit_string.isdigit():
            return digit_string
        
        # If not exactly 15 digits, but we have digits, try to find a 15-digit sequence
        # This handles cases where there might be extra digits before or after
        fifteen_digit_match = re.search(r'\d{15}', digit_string)
        if fifteen_digit_match:
            return fifteen_digit_match.group(0)
        
        # If we found digits but not 15, return what we found with a warning
        if digit_string and digit_string.isdigit():
            logger.warning(
                f"Found microchip digits '{digit_string}' but length is {len(digit_string)}, expected 15"
            )
            return digit_string
    
    # Fallback: Look for any 15-digit sequence near "microchip" text
    # This is more aggressive and looks for 15 consecutive digits anywhere in the vicinity of "microchip"
    if "microchip" in normalized_text:
        # Find the position of "microchip" and search in a reasonable range around it
        microchip_pos = normalized_text.find("microchip")
        
        # Search in a window around the microchip keyword (500 characters before and after)
        start = max(0, microchip_pos - 500)
        end = min(len(normalized_text), microchip_pos + 500)
        
        search_window = normalized_text[start:end]
        
        # Look for 15 consecutive digits
        fifteen_digit_match = re.search(r'\d{15}', search_window)
        if fifteen_digit_match:
            return fifteen_digit_match.group(0)
        
        # Last resort: look for patterns like "941000031 499323" and concatenate
        split_digits_match = re.search(r'(\d{9})\s+(\d{6})', search_window)
        if split_digits_match:
            combined = split_digits_match.group(1) + split_digits_match.group(2)
            if len(combined) == 15:
                return combined

    raise ValueError("Microchip ID not found")

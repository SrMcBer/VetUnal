from typing import List, Optional
import logging
from pathlib import Path

from .patient_records import PatientRecord
from .utils import extract_single_page, extract_multiple_pages

class PatientRecordExtractor:
    """Handles extraction of patient record pages from PDFs"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def extract_patient_record(self, main_pdf_path: str, output_dir: str, 
                                record: PatientRecord) -> None:
        """
        Extract all pages for a single patient record.
        
        Args:
            main_pdf_path: Path to the main PDF file
            output_dir: Output directory for extracted pages
            record: PatientRecord containing page numbers to extract
            
        Raises:
            RuntimeError: If extraction fails for any page type
        """
        try:
            self.logger.info(f"Extracting patient record to {output_dir}")
            
            # Ensure output directory exists
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            # Extract HISTORIA CLINICA pages
            if record.historia_pages:
                self.logger.debug(f"Extracting {len(record.historia_pages)} HISTORIA pages")
                self._extract_pages_by_type(
                    main_pdf_path, 
                    output_dir, 
                    record.historia_pages, 
                    "0.1 HISTORIA CLINICA VETERINARIA"
                )
            
            # Extract CEDULA pages
            if record.cedula_pages:
                self.logger.debug(f"Extracting {len(record.cedula_pages)} CEDULA pages")
                self._extract_pages_by_type(
                    main_pdf_path, 
                    output_dir, 
                    record.cedula_pages, 
                    "0.2 CEDULA DE CIUDADANIA"
                )
            
            # Extract RECIBO pages
            if record.recibo_pages:
                self.logger.debug(f"Extracting {len(record.recibo_pages)} RECIBO pages")
                self._extract_pages_by_type(
                    main_pdf_path, 
                    output_dir, 
                    record.recibo_pages, 
                    "0.3 RECIBO PUBLICO"
                )
            
            # Extract UNKNOWN pages
            if record.unknown_pages:
                self.logger.warning(f"Extracting {len(record.unknown_pages)} UNKNOWN pages")
                self._extract_pages_by_type(
                    main_pdf_path, 
                    output_dir, 
                    record.unknown_pages, 
                    "0.9 UNKNOWN PAGES"
                )
            
            self.logger.info(f"Successfully extracted patient record with {len(record.all_pages)} total pages")
            
        except Exception as e:
            self.logger.error(f"Error extracting patient record: {e}")
            raise RuntimeError(f"Error extracting patient record: {e}")
    
    def _extract_pages_by_type(self, main_pdf_path: str, output_dir: str, 
                                page_numbers: List[int], type_name: str) -> None:
        """
        Extract pages of a specific type and save them with proper naming.
        
        Args:
            main_pdf_path: Path to the main PDF file
            output_dir: Output directory for extracted pages
            page_numbers: List of page numbers to extract
            type_name: Name/prefix for the extracted file(s)
            
        Raises:
            RuntimeError: If extraction fails
        """
        if not page_numbers:
            return
        
        try:
            if len(page_numbers) == 1:
                # Single page extraction
                self.logger.debug(f"Extracting single page {page_numbers[0]} as {type_name}")
                extract_single_page(main_pdf_path, page_numbers[0], output_dir, type_name)
            else:
                # Multiple pages extraction
                self.logger.debug(f"Extracting multiple pages {page_numbers} as {type_name}")
                extract_multiple_pages(main_pdf_path, page_numbers, output_dir, type_name)
                
        except Exception as e:
            error_msg = f"error extracting {type_name.lower()} pages: {e}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def get_extraction_summary(self, record: PatientRecord) -> dict:
        """
        Get a summary of what would be extracted from a patient record.
        
        Args:
            record: PatientRecord to analyze
            
        Returns:
            Dictionary with extraction summary
        """
        return {
            'total_pages': len(record.all_pages),
            'historia_pages': len(record.historia_pages),
            'cedula_pages': len(record.cedula_pages),
            'recibo_pages': len(record.recibo_pages),
            'unknown_pages': len(record.unknown_pages),
            'page_breakdown': {
                'historia': record.historia_pages,
                'cedula': record.cedula_pages,
                'recibo': record.recibo_pages,
                'unknown': record.unknown_pages
            },
            'is_complete': record.is_complete,
            'has_issues': record.has_issues,
            'issues': record.issues.copy()
        }
    
    def validate_extraction_feasibility(self, main_pdf_path: str, 
                                        record: PatientRecord) -> dict:
        """
        Validate if extraction is feasible for the given record.
        
        Args:
            main_pdf_path: Path to the main PDF file
            record: PatientRecord to validate
            
        Returns:
            Dictionary with validation results
        """
        from .utils import get_page_count
        
        try:
            total_pdf_pages = get_page_count(main_pdf_path)
            all_pages = record.all_pages
            
            # Check if all page numbers are within valid range
            invalid_pages = [p for p in all_pages if p < 1 or p > total_pdf_pages]
            
            return {
                'is_feasible': len(invalid_pages) == 0,
                'total_pdf_pages': total_pdf_pages,
                'record_pages': all_pages,
                'invalid_pages': invalid_pages,
                'extraction_summary': self.get_extraction_summary(record)
            }
            
        except Exception as e:
            return {
                'is_feasible': False,
                'error': str(e),
                'extraction_summary': self.get_extraction_summary(record)
            }

# Factory function for convenience
def create_patient_record_extractor() -> PatientRecordExtractor:
    """
    Factory function to create a PatientRecordExtractor instance.
    
    Returns:
        Configured PatientRecordExtractor instance
    """
    return PatientRecordExtractor()

# Convenience functions for direct use
def extract_patient_record(main_pdf_path: str, output_dir: str, 
                            record: PatientRecord) -> None:
    """
    Convenience function to extract a patient record.
    
    Args:
        main_pdf_path: Path to the main PDF file
        output_dir: Output directory for extracted pages
        record: PatientRecord containing page numbers to extract
        
    Raises:
        RuntimeError: If extraction fails
    """
    extractor = create_patient_record_extractor()
    extractor.extract_patient_record(main_pdf_path, output_dir, record)

def extract_pages_by_type(main_pdf_path: str, output_dir: str, 
                            page_numbers: List[int], type_name: str) -> None:
    """
    Convenience function to extract pages by type.
    
    Args:
        main_pdf_path: Path to the main PDF file
        output_dir: Output directory for extracted pages
        page_numbers: List of page numbers to extract
        type_name: Name/prefix for the extracted file(s)
        
    Raises:
        RuntimeError: If extraction fails
    """
    extractor = create_patient_record_extractor()
    extractor.extract_pages_by_type_only(main_pdf_path, output_dir, page_numbers, type_name)
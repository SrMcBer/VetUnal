from typing import List, Dict, Optional
import logging
from dataclasses import dataclass

from src.ocr.text_classifier import TextClassifier, PageInfo, PageType
from src.ocr.engine import ocr_pdf_page_with_tesseract_improved
from .utils import get_page_count
from src.ocr.pattern_rules import resolve_unknown_page_types

@dataclass
class ValidationResult:
    """Results from document validation"""
    total_pages: int
    type_counts: Dict[PageType, int]
    unknown_pages: List[int]
    suspicious_transitions: List[str]
    warnings: List[str]
    

class PDFProcessor:
    """Handles the processing of PDF documents"""
    
    def __init__(self, classifier: Optional[TextClassifier] = None):
        """
        Initialize PDF processor with a text classifier.
        Args:
            classifier: Optional TextClassifier instance. If None, creates a new one.
        """
        self.classifier = classifier or TextClassifier()
        self.logger = logging.getLogger(__name__)

    @property
    def text_classifier(self) -> TextClassifier:
        """Get the text classifier for external configuration"""
        return self.classifier

    def scan_all_pages(self, pdf_path: str, 
                        progress_callback: Optional[callable] = None,
                        include_full_text: bool = False) -> List[PageInfo]:
        """
        Scan all pages in the PDF and classify them with detailed criteria.
        
        Args:
            pdf_path: Path to the PDF file
            progress_callback: Optional callback function for progress updates
            include_full_text: Whether to include full text in the results
            
        Returns:
            List of PageInfo objects with classification results and matched criteria
            
        Raises:
            RuntimeError: If page count retrieval or OCR fails
        """
        try:
            page_count = get_page_count(pdf_path)
            self.logger.info(f"Scanning and classifying {page_count} pages...")
            
            pages: List[PageInfo] = []
            
            for page_num in range(1, page_count + 1):
                try:
                    # Perform OCR on the page
                    text = ocr_pdf_page_with_tesseract_improved(pdf_path, page_num)
                    
                    # Classify the page
                    classification_result = self.classifier.classify_page(text)

                    page_info = PageInfo(
                        page_number=page_num,
                        page_type=classification_result.page_type,
                        text=text if include_full_text else text[:200] + "..." if len(text) > 200 else text,
                        matched_indicators=classification_result.matched_indicators,
                        confidence_score=classification_result.confidence_score
                    )
                    pages.append(page_info)
                    
                    # Enhanced logging with criteria
                    indicators_str = ", ".join(classification_result.matched_indicators) if classification_result.matched_indicators else "None"
                    self.logger.info(
                        f"Page {page_num}: {classification_result.page_type} "
                        f"(confidence: {classification_result.confidence_score:.2f}, "
                        f"matched: {indicators_str})"
                    )
                    
                    # Call progress callback if provided
                    if progress_callback:
                        details = f"Page {page_num}: {classification_result.page_type}"
                            
                        progress_callback(
                            "splitting_main_pdf",  # step
                            page_num,              # current
                            page_count,            # total
                            details                # details
                        )

                except Exception as e:
                    self.logger.error(f"Error processing page {page_num}: {e}")
                    raise RuntimeError(f"Error performing OCR on page {page_num}: {e}")
            
            return pages
            
        except Exception as e:
            raise RuntimeError(f"Error getting page count for {pdf_path}: {e}")

    def process_document(self, pdf_path: str, 
                    resolve_unknowns: bool = True,
                    progress_callback: Optional[callable] = None) -> List[PageInfo]:
        """
        Complete document processing pipeline.
        
        Args:
            pdf_path: Path to the PDF file
            resolve_unknowns: Whether to apply unknown page resolution
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of processed PageInfo objects
        """
        # Scan and classify all pages
        pages = self.scan_all_pages(pdf_path, progress_callback, include_full_text=True)

        # Print detailed summary
        self.print_classification_summary(pages)

        # Resolve unknown pages if requested
        if resolve_unknowns:
            self.logger.info("Resolving unknown page types...")
            pages = resolve_unknown_page_types(pages)
            self.logger.info("Unknown page types resolved. Alleged classifications:")
            self.print_classification_summary(pages)
        
        return pages
    
    def print_classification_summary(self, pages: List[PageInfo]):
        """
        Print a detailed summary of all classifications
        """
        print(f"\n{'='*60}")
        print("CLASSIFICATION SUMMARY")
        print(f"{'='*60}")
        
        for page in pages:
            print(f"\nPage {page.page_number}:")
            print(f"  Type: {page.page_type}")
            print(f"  Confidence: {page.confidence_score:.2f}")
            print(f"  Matched Indicators: {', '.join(page.matched_indicators) if page.matched_indicators else 'None'}")
            
            # Show first few lines of text
            text_preview = page.text.replace('\n', ' ')[:150]
            print(f"  Text Preview: {text_preview}{'...' if len(page.text) > 150 else ''}")
            print(f"  {'-'*40}")
    
    def validate_document(self, pages: List[PageInfo]) -> ValidationResult:
        """
        Validate the document structure and return detailed results.
        
        Args:
            pages: List of PageInfo objects to validate
            
        Returns:
            ValidationResult with validation details
        """
        type_counts: Dict[PageType, int] = {}
        unknown_pages: List[int] = []
        suspicious_transitions: List[str] = []
        warnings: List[str] = []
        
        # Count types and collect unknowns
        for page in pages:
            type_counts[page.page_type] = type_counts.get(page.page_type, 0) + 1
            if page.page_type == PageType.UNKNOWN:
                unknown_pages.append(page.page_number)

        # Check for suspicious transitions
        for i in range(1, len(pages)):
            prev_page = pages[i - 1]
            curr_page = pages[i]
            prev_type = prev_page.page_type
            curr_type = curr_page.page_type
            
            # Flag problematic transitions
            if prev_type == PageType.RECIBO and curr_type == PageType.CEDULA:
                transition = f"Page {prev_page.page_number} RECIBO → Page {curr_page.page_number} CEDULA"
                suspicious_transitions.append(transition)
                warnings.append(f"Suspicious transition: {transition}")
            
            if prev_type == PageType.CEDULA and curr_type == PageType.CEDULA:
                double_cedula = f"Double CEDULA: Page {prev_page.page_number} and Page {curr_page.page_number}"
                suspicious_transitions.append(double_cedula)
                warnings.append(double_cedula)

        # Add unknown pages warning if any exist
        if unknown_pages:
            warnings.append(f"{len(unknown_pages)} pages remain UNKNOWN: {unknown_pages}")
        
        return ValidationResult(
            total_pages=len(pages),
            type_counts=type_counts,
            unknown_pages=unknown_pages,
            suspicious_transitions=suspicious_transitions,
            warnings=warnings
        )

    def print_validation_report(self, pages: List[PageInfo]) -> None:
        """
        Print a detailed validation report to console.
        
        Args:
            pages: List of PageInfo objects to validate
        """
        result = self.validate_document(pages)
        
        print("=== VALIDATION REPORT ===")
        print(f"Total pages: {result.total_pages}")
        
        # Print type counts
        for page_type in PageType:
            count = result.type_counts.get(page_type, 0)
            print(f"  {page_type.value}: {count}")
        
        # Print warnings
        if result.warnings:
            print("\nWarnings:")
            for warning in result.warnings:
                print(f"⚠️  {warning}")
        
        print("=== END OF VALIDATION ===")

    def get_pages_by_type(self, pages: List[PageInfo], 
                            page_type: PageType) -> List[PageInfo]:
        """
        Filter pages by type.
        
        Args:
            pages: List of PageInfo objects
            page_type: PageType to filter by
            
        Returns:
            List of pages matching the specified type
        """
        return [page for page in pages if page.page_type == page_type]

    def get_document_summary(self, pages: List[PageInfo]) -> Dict[str, any]:
        """
        Get a summary of the document structure.
        
        Args:
            pages: List of PageInfo objects
            
        Returns:
            Dictionary with document summary information
        """
        validation = self.validate_document(pages)
        
        return {
            'total_pages': validation.total_pages,
            'type_distribution': validation.type_counts,
            'unknown_pages_count': len(validation.unknown_pages),
            'warnings_count': len(validation.warnings),
            'has_issues': len(validation.warnings) > 0,
            'completion_rate': (validation.total_pages - len(validation.unknown_pages)) / validation.total_pages if validation.total_pages > 0 else 0
        }

# Factory function for convenience
def create_pdf_processor(classifier: Optional[TextClassifier] = None) -> PDFProcessor:
    """
    Factory function to create a PDF processor.
    
    Args:
        classifier: Optional TextClassifier instance
        
    Returns:
        Configured PDFProcessor instance
    """
    return PDFProcessor(classifier)
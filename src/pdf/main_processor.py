
import os
from pathlib import Path
from typing import List, Optional, Callable
import logging
from datetime import datetime

from .patient_records import PatientRecord
from .processor import PDFProcessor
from src.ocr.pattern_rules import resolve_unknown_page_types
from .patient_records import PatientRecordGrouper
from .extractor import PatientRecordExtractor
from .folder_manager import FolderManager
from .test_data import export_pages_for_testing

class MainPDFProcessor:
    """Main orchestrator for PDF processing workflow"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.pdf_processor = PDFProcessor()
        self.record_grouper = PatientRecordGrouper()
        self.record_extractor = PatientRecordExtractor()
        self.folder_manager = FolderManager()
        
    def split_main_pdf_into_folders(
        self, 
        main_pdf_path: str, 
        output_base_dir: str, 
        folder_names: List[str],
        progress_callback: Optional[Callable] = None,
        correction_callback: Optional[Callable] = None
    ) -> None:
        """
        Split the main PDF based on "HISTORIA CLINICA" markers into patient folders.
        
        Args:
            main_pdf_path: Path to the main PDF file
            output_base_dir: Base directory for output folders
            folder_names: List of folder names (from microchip IDs)
            progress_callback: Optional callback for progress updates
            
        Raises:
            RuntimeError: If processing fails at any step
        """
        try:
            self.logger.info(f"Starting PDF splitting process for {main_pdf_path}")
            
            # Create debug directory
            debug_dir = os.path.join(output_base_dir, "_DEBUG")
            os.makedirs(debug_dir, exist_ok=True)
        
            # Get PDF filename for debug files
            pdf_name = Path(main_pdf_path).stem
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # We'll track progress through 4 main steps, with substeps
            total_steps = 4
            
            # Step 1: Classify all pages
            self.logger.info("Step 1: Classifying all pages...")
            if progress_callback:
                progress_callback("splitting_main_pdf", 0, total_steps, "Classifying pages...")
            
            pages = self.pdf_processor.scan_all_pages(main_pdf_path, progress_callback)
            
            # Export original pages for testing
            export_pages_for_testing(pages, "original_pages")
            
            # Save initial classification results
            self._save_classification_debug(pages, debug_dir, f"{pdf_name}_{timestamp}_01_initial_classification.txt")
            
            # Apply classification rules to resolve unknown page types
            self.logger.info("Resolving unknown page types...")
            if progress_callback:
                progress_callback("splitting_main_pdf", 0.5, total_steps, "Resolving unknown page types...")
                
            pages = resolve_unknown_page_types(pages)
            
            # Save post-resolution classification results
            self._save_classification_debug(pages, debug_dir, f"{pdf_name}_{timestamp}_02_after_resolution.txt")
            
            if progress_callback:
                progress_callback("splitting_main_pdf", 1, total_steps, "Page classification completed")

            
            # Step 2: Group pages into patient records
            self.logger.info("Step 2: Grouping pages into patient records...")
            if progress_callback:
                progress_callback("splitting_main_pdf", 1, total_steps, "Grouping pages into patient records...")

            patient_records = self.record_grouper.group_pages_into_patient_records(pages)
            
            # Validate patient records
            self.logger.info("Validating patient records...")
            if progress_callback:
                progress_callback("splitting_main_pdf", 1.5, total_steps, "Validating patient records...")
                
            self.record_grouper.validate_patient_records(patient_records)
            
            # Save patient records after validation
            self._save_patient_records_debug(patient_records, debug_dir, f"{pdf_name}_{timestamp}_03_patient_records.txt")

            # --- NEW CORRECTION STEP ---
            if correction_callback and any(r.has_issues for r in patient_records):
                self.logger.info("Entering interactive correction mode...")
                try:
                    corrected_data = correction_callback(patient_records, pages, folder_names)
                    
                    # Update records based on what the callback returns
                    if corrected_data:
                        pages = corrected_data.get('pages', pages)
                        patient_records = self.record_grouper.group_pages_into_patient_records(pages)
                        self.record_grouper.validate_patient_records(patient_records)
                        
                        if not corrected_data.get('proceed', False):
                            self.logger.warning("User chose to abort processing after review. Halting.")
                            return
                except Exception as e:
                    self.logger.error(f"Error during correction callback: {e}")
                    raise RuntimeError(f"Failed during interactive correction: {e}")
            # --- END OF NEW STEP ---
            
            if progress_callback:
                progress_callback("splitting_main_pdf", 2, total_steps, f"Found {len(patient_records)} patient records")
            
            
            # Step 3: Validate we have the right number of records
            if progress_callback:
                progress_callback("splitting_main_pdf", 2, total_steps, "Validating record count...")
                
            # Step 3: Validate we have the right number of records
            self._validate_record_count(patient_records, folder_names)
            
            if progress_callback:
                progress_callback("splitting_main_pdf", 3, total_steps, "Record count validation passed")
            
            if progress_callback:
                progress_callback("extracting", 3, 4)
            
            
            # Step 4: Extract pages for each patient
            self.logger.info("Step 4: Extracting patient records...")
            if progress_callback:
                progress_callback("splitting_main_pdf", 3, total_steps, "Starting page extraction...")

            self._extract_patient_records(
                main_pdf_path, 
                output_base_dir, 
                patient_records, 
                folder_names,
                progress_callback  # Pass the callback down to extraction method
            )
            
            if progress_callback:
                progress_callback("splitting_main_pdf", total_steps, total_steps, "PDF splitting completed successfully")
            
            
            self.logger.info("PDF splitting process completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error in PDF splitting process: {e}")

            try:
                if 'pages' in locals():
                    error_debug_file = f"{pdf_name}_{timestamp}_ERROR_pages_at_failure.txt"
                    self._save_classification_debug(pages, debug_dir, error_debug_file)
                
                if 'patient_records' in locals():
                    error_debug_file = f"{pdf_name}_{timestamp}_ERROR_records_at_failure.txt"
                    self._save_patient_records_debug(patient_records, debug_dir, error_debug_file)
                    
            except Exception as debug_error:
                self.logger.error(f"Failed to save debug info: {debug_error}")
            
            raise RuntimeError(f"Error splitting PDF: {e}")
    
    def _validate_record_count(self, patient_records: List, folder_names: List[str]) -> None:
        """
        Validate that we have the right number of records vs folder names.
        
        Args:
            patient_records: List of patient records found
            folder_names: List of expected folder names
        """
        records_count = len(patient_records)
        folders_count = len(folder_names)
        
        if records_count != folders_count:
            self.logger.warning(
                f"Found {records_count} patient records but have {folders_count} microchip IDs"
            )
            
            min_count = min(records_count, folders_count)
            self.logger.warning(f"Processing first {min_count} records...")
    
    def _extract_patient_records(
        self, 
        main_pdf_path: str, 
        output_base_dir: str, 
        patient_records: List, 
        folder_names: List[str],
        progress_callback: Optional[Callable] = None
    ) -> None:
        """
        Extract patient records to their respective folders.
        
        Args:
            main_pdf_path: Path to the main PDF
            output_base_dir: Base output directory
            patient_records: List of patient records
            folder_names: List of folder names
        """
        total_records = len(patient_records)

        for i, record in enumerate(patient_records):
            if i >= len(folder_names):
                self.logger.warning(f"Skipping record {i+1} - no corresponding microchip ID")
                break
            
            folder_name = folder_names[i]
            original_dir = Path(output_base_dir) / folder_name
            
                        # Update progress at start of extraction
            if progress_callback:
                progress_callback(
                    "splitting_main_pdf", 
                    3 + (i / total_records),  # Progress within step 4
                    4, 
                    f"Extracting record {i+1} of {total_records}: {folder_name}"
                )
            
            # Check if this record needs review
            needs_review = record.has_issues
            
            try:
                # Extract the patient record
                self.record_extractor.extract_patient_record(
                    main_pdf_path, 
                    str(original_dir), 
                    record
                )
                
                # Rename folder if review is needed
                final_dir = original_dir
                if needs_review:
                    review_dir = Path(output_base_dir) / f"REVIEW - {folder_name}"
                    try:
                        original_dir.rename(review_dir)
                        final_dir = review_dir
                        self.logger.info(f"Renamed folder to REVIEW status: {review_dir}")
                    except OSError as e:
                        self.logger.warning(f"Could not rename folder to REVIEW status: {e}")
                        
                if needs_review:
                    self._save_issues_file(final_dir, record, folder_name)
                
                # Log completion status
                review_status = ""
                if needs_review:
                    issues_str = ", ".join(record.issues)
                    review_status = f" [REVIEW NEEDED: {issues_str}]"
                
                self.logger.info(f"✅ Extracted record {i+1} for microchip {folder_name}{review_status}")
                
                if progress_callback:
                    status_detail = f"Completed {folder_name}"
                    if needs_review:
                        status_detail += " (marked for review)"
                    progress_callback(
                        "splitting_main_pdf", 
                        3 + ((i + 1) / total_records),
                        4, 
                        status_detail
                    )
                
            except Exception as e:
                self.logger.error(f"Error extracting record for microchip {folder_name}: {e}")
                
                # Update progress even on error
                if progress_callback:
                    progress_callback(
                        "splitting_main_pdf", 
                        3 + ((i + 1) / total_records),
                        4, 
                        f"Error extracting {folder_name}"
                    )
                
                raise RuntimeError(f"Error extracting record for microchip {folder_name}: {e}")
    
    def _save_issues_file(self, output_dir: Path, record: PatientRecord, folder_name: str) -> None:
        """
        Save issues to a text file in the patient record directory.
        
        Args:
            output_dir: Directory where the issues file should be saved
            record: PatientRecord containing the issues
            folder_name: Name of the folder (microchip ID)
        """
        try:
            issues_file_path = output_dir / "ISSUES_REVIEW_REQUIRED.txt"
            with open(issues_file_path, 'w', encoding='utf-8') as f:
                f.write(f"REVIEW REQUIRED FOR PATIENT RECORD: {folder_name}\n")
                f.write("=" * 60 + "\n\n")
                
                f.write("This patient record has been flagged for manual review due to the following issues:\n\n")
                
                # Write validation issues
                if record.issues:
                    f.write("VALIDATION ISSUES:\n")
                    for i, issue in enumerate(record.issues, 1):
                        f.write(f"  {i}. {issue}\n")
                    f.write("\n")
                
                # Write information about unknown pages
                if record.unknown_pages:
                    f.write("UNKNOWN PAGES DETECTED:\n")
                    f.write(f"  Found {len(record.unknown_pages)} page(s) that could not be classified: ")
                    f.write(f"{', '.join(map(str, record.unknown_pages))}\n")
                    f.write("  These pages have been saved in the '0.9 UNKNOWN PAGES' folder.\n\n")
                
                # Write record summary
                f.write("RECORD SUMMARY:\n")
                f.write(f"  Total pages: {len(record.all_pages)}\n")
                f.write(f"  Historia Clínica pages: {len(record.historia_pages)}\n")
                f.write(f"  Cédula pages: {len(record.cedula_pages)}\n")
                f.write(f"  Recibo pages: {len(record.recibo_pages)}\n")
                f.write(f"  Unknown pages: {len(record.unknown_pages)}\n\n")
                
                # Write completion status
                f.write("COMPLETION STATUS:\n")
                if record.is_complete:
                    f.write("  ✓ Record contains all required document types\n")
                else:
                    f.write("  ✗ Record is missing required document types:\n")
                    if not record.historia_pages:
                        f.write("    - Missing Historia Clínica pages\n")
                    if not record.cedula_pages:
                        f.write("    - Missing Cédula pages\n")
                    if not record.recibo_pages:
                        f.write("    - Missing Recibo pages\n")
                
                f.write("\n" + "=" * 60 + "\n")
                f.write("Please review the extracted files and resolve the issues above before proceeding.\n")
            
            self.logger.info(f"Created issues file: {issues_file_path}")
            
        except Exception as e:
            self.logger.error(f"Error creating issues file for {folder_name}: {e}")

    def process_complete_workflow(
        self, 
        control_sheet_path: str, 
        main_pdf_path: str, 
        output_base_dir: str, 
        clinic_history: int,
        progress_callback: Optional[Callable] = None,
        correction_callback: Optional[Callable] = None
    ) -> List[str]:
        """
        Complete PDF processing workflow from control sheet to final folders.
        
        Args:
            control_sheet_path: Path to control sheet PDF
            main_pdf_path: Path to main PDF file
            output_base_dir: Base directory for output
            clinic_history: Starting clinic history number
            progress_callback: Optional progress callback
            correction_callback: Optional callback for correcting records
            
        Returns:
            List of created folder names
            
        Raises:
            RuntimeError: If any step in the workflow fails
        """
        try:
            self.logger.info("Starting complete PDF processing workflow")
            
            # Step 1: Extract microchip IDs and create folders
            folder_names = self.folder_manager.extract_microchip_ids_and_create_folders(
                control_sheet_path, 
                output_base_dir, 
                clinic_history,
                progress_callback
            )
            
            self.logger.info(f"Created {len(folder_names)} folders from control sheet")
            
            # Step 2: Split main PDF into the created folders
            self.split_main_pdf_into_folders(
                main_pdf_path, 
                output_base_dir, 
                folder_names,
                progress_callback,
                correction_callback
            )
            
            if progress_callback:
                progress_callback("workflow_completed", 1, 1, "All processing completed successfully!")
            
            self.logger.info("Complete workflow finished successfully")
            return folder_names
            
        except Exception as e:
            self.logger.error(f"Error in complete workflow: {e}")
            raise RuntimeError(f"Complete workflow failed: {e}")
    
    def get_processing_summary(
        self, 
        main_pdf_path: str, 
        folder_names: List[str]
    ) -> dict:
        """
        Get a summary of what would be processed without actually processing.
        
        Args:
            main_pdf_path: Path to main PDF
            folder_names: List of folder names
            
        Returns:
            Dictionary with processing summary
        """
        try:
            # Scan and classify pages
            pages = self.pdf_processor.scan_all_pages(main_pdf_path)
            pages = resolve_unknown_page_types(pages)
            
            # Group into records
            patient_records = self.record_grouper.group_pages_into_patient_records(pages)
            
            # Get document summary
            doc_summary = self.pdf_processor.get_document_summary(pages)
            
            return {
                'total_pages': len(pages),
                'patient_records_found': len(patient_records),
                'expected_folders': len(folder_names),
                'records_match_folders': len(patient_records) == len(folder_names),
                'document_summary': doc_summary,
                'records_needing_review': sum(1 for record in patient_records if record.has_issues)
            }
            
        except Exception as e:
            self.logger.error(f"Error generating processing summary: {e}")
            return {'error': str(e)}

    def _save_classification_debug(self, pages: List, debug_dir: str, filename: str) -> None:
        """
        Save page classification results to debug file
        """
        try:
            debug_path = os.path.join(debug_dir, filename)
            
            with open(debug_path, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write(f"PAGE CLASSIFICATION DEBUG - {datetime.now()}\n")
                f.write("=" * 80 + "\n")
                f.write(f"Total pages: {len(pages)}\n\n")
                
                # Summary by page type
                type_counts = {}
                for page in pages:
                    page_type = page.page_type.value if hasattr(page.page_type, 'value') else str(page.page_type)
                    type_counts[page_type] = type_counts.get(page_type, 0) + 1
                
                f.write("SUMMARY BY PAGE TYPE:\n")
                f.write("-" * 40 + "\n")
                for page_type, count in sorted(type_counts.items()):
                    f.write(f"{page_type}: {count} pages\n")
                
                f.write("\n" + "=" * 80 + "\n")
                f.write("DETAILED PAGE-BY-PAGE ANALYSIS:\n")
                f.write("=" * 80 + "\n\n")
                
                for page in pages:
                    page_type = page.page_type if hasattr(page.page_type, 'value') else str(page.page_type)
                    
                    f.write(f"Page {page.page_number}:\n")
                    f.write(f"  Type: {page_type}\n")
                    
                    # Add matched indicators if available
                    if hasattr(page, 'matched_indicators') and page.matched_indicators:
                        f.write(f"  Matched indicators: {', '.join(page.matched_indicators)}\n")
                    
                    # Add confidence if available
                    if hasattr(page, 'confidence_score'):
                        f.write(f"  Confidence: {page.confidence_score:.2f}\n")
                    
                    # Add text preview
                    if hasattr(page, 'text') and page.text:
                        # Clean and truncate text for preview
                        text_preview = page.text.replace('\n', ' ').replace('\r', ' ')[:200]
                        f.write(f"  Text preview: {text_preview}{'...' if len(page.text) > 200 else ''}\n")
                    
                    f.write("\n" + "-" * 60 + "\n\n")
            
            self.logger.info(f"Saved classification debug to: {debug_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save classification debug: {e}")

    def _save_patient_records_debug(self, patient_records: List, debug_dir: str, filename: str) -> None:
        """
        Save patient records to debug file
        """
        try:
            debug_path = os.path.join(debug_dir, filename)
            
            with open(debug_path, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write(f"PATIENT RECORDS DEBUG - {datetime.now()}\n")
                f.write("=" * 80 + "\n")
                f.write(f"Total patient records: {len(patient_records)}\n\n")
                
                for i, record in enumerate(patient_records, 1):
                    f.write(f"PATIENT RECORD {i}:\n")
                    f.write("-" * 50 + "\n")
                    
                    # Page breakdown by type (PatientRecord stores page numbers as integers)
                    if hasattr(record, 'historia_pages'):
                        page_nums = [str(p) for p in record.historia_pages]
                        f.write(f"Historia pages: {', '.join(page_nums)} ({len(record.historia_pages)} pages)\n")
                    
                    if hasattr(record, 'cedula_pages'):
                        page_nums = [str(p) for p in record.cedula_pages]
                        f.write(f"Cedula pages: {', '.join(page_nums)} ({len(record.cedula_pages)} pages)\n")
                    
                    if hasattr(record, 'recibo_pages'):
                        page_nums = [str(p) for p in record.recibo_pages]
                        f.write(f"Recibo pages: {', '.join(page_nums)} ({len(record.recibo_pages)} pages)\n")
                    
                    if hasattr(record, 'unknown_pages'):
                        page_nums = [str(p) for p in record.unknown_pages]
                        f.write(f"Unknown pages: {', '.join(page_nums)} ({len(record.unknown_pages)} pages)\n")
                    
                    # Calculate total pages
                    total_pages = 0
                    all_pages = []
                    if hasattr(record, 'historia_pages'):
                        total_pages += len(record.historia_pages)
                        all_pages.extend(record.historia_pages)
                    if hasattr(record, 'cedula_pages'):
                        total_pages += len(record.cedula_pages)
                        all_pages.extend(record.cedula_pages)
                    if hasattr(record, 'recibo_pages'):
                        total_pages += len(record.recibo_pages)
                        all_pages.extend(record.recibo_pages)
                    if hasattr(record, 'unknown_pages'):
                        total_pages += len(record.unknown_pages)
                        all_pages.extend(record.unknown_pages)
                    
                    # Sort all pages for display
                    all_pages.sort()
                    all_page_strs = [str(p) for p in all_pages]
                    f.write(f"All pages in record: {', '.join(all_page_strs)}\n")
                    f.write(f"Total pages in record: {total_pages}\n")
                    
                    # Issues
                    if hasattr(record, 'issues') and record.issues:
                        f.write(f"Issues: {', '.join(record.issues)}\n")
                    else:
                        f.write("Issues: None\n")
                    
                    # Has issues property
                    has_issues = bool(getattr(record, 'issues', []))
                    f.write(f"Has issues: {has_issues}\n")
                    
                    # Show record structure
                    f.write(f"\nRecord structure:\n")
                    for attr_name in ['historia_pages', 'cedula_pages', 'recibo_pages', 'unknown_pages', 'issues']:
                        if hasattr(record, attr_name):
                            attr_value = getattr(record, attr_name)
                            f.write(f"  {attr_name}: {attr_value}\n")
                    
                    # Show any additional attributes
                    f.write(f"\nOther attributes:\n")
                    for attr_name in dir(record):
                        if (not attr_name.startswith('_') and 
                            not callable(getattr(record, attr_name)) and
                            attr_name not in ['historia_pages', 'cedula_pages', 'recibo_pages', 'unknown_pages', 'issues', 'microchip_id']):
                            try:
                                attr_value = getattr(record, attr_name)
                                f.write(f"  {attr_name}: {attr_value}\n")
                            except Exception:
                                f.write(f"  {attr_name}: <unable to access>\n")
                    
                    f.write("\n" + "=" * 80 + "\n\n")
            
            self.logger.info(f"Saved patient records debug to: {debug_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save patient records debug: {e}")
            # Add more detailed error info for debugging
            import traceback
            self.logger.error(f"Debug save traceback: {traceback.format_exc()}")

# Factory function
def create_main_processor() -> MainPDFProcessor:
    """
    Factory function to create a MainPDFProcessor instance.
    
    Returns:
        Configured MainPDFProcessor instance
    """
    return MainPDFProcessor()

# Convenience function for the complete workflow
def process_pdfs(
    control_sheet_path: str, 
    main_pdf_path: str, 
    output_base_dir: str, 
    clinic_history: int,
    progress_callback: Optional[Callable] = None,
    correction_callback: Optional[Callable] = None
) -> List[str]:
    """
    Convenience function that orchestrates the complete PDF processing workflow.
    
    Args:
        control_sheet_path: Path to control sheet PDF
        main_pdf_path: Path to main PDF file
        output_base_dir: Base directory for output
        clinic_history: Starting clinic history number
        progress_callback: Optional progress callback
        correction_callback: Optional callback for correcting records
        
    Returns:
        List of created folder names
        
    Raises:
        RuntimeError: If processing fails
    """
    processor = create_main_processor()
    return processor.process_complete_workflow(
        control_sheet_path, 
        main_pdf_path, 
        output_base_dir, 
        clinic_history,
        progress_callback,
        correction_callback
    )

# Alternative convenience function using the class method
def process_pdfs_advanced(
    control_sheet_path: str, 
    main_pdf_path: str, 
    output_base_dir: str, 
    clinic_history: int,
    progress_callback: Optional[Callable] = None
) -> List[str]:
    """
    Advanced version using the class-based approach with more features.
    
    Args:
        control_sheet_path: Path to control sheet PDF
        main_pdf_path: Path to main PDF file
        output_base_dir: Base directory for output
        clinic_history: Starting clinic history number
        progress_callback: Optional progress callback
        
    Returns:
        List of created folder names
        
    Raises:
        RuntimeError: If processing fails
    """
    processor = create_main_processor()
    return processor.process_complete_workflow(
        control_sheet_path, 
        main_pdf_path, 
        output_base_dir, 
        clinic_history,
        progress_callback
    )

# Alternative convenience function using the class method
def process_pdfs_advanced(
    control_sheet_path: str, 
    main_pdf_path: str, 
    output_base_dir: str, 
    clinic_history: int,
    progress_callback: Optional[Callable] = None
) -> List[str]:
    """
    Advanced version using the class-based approach with more features.
    
    Args:
        control_sheet_path: Path to control sheet PDF
        main_pdf_path: Path to main PDF file
        output_base_dir: Base directory for output
        clinic_history: Starting clinic history number
        progress_callback: Optional progress callback
        
    Returns:
        List of created folder names
        
    Raises:
        RuntimeError: If processing fails
    """
    processor = create_main_processor()
    return processor.process_complete_workflow(
        control_sheet_path, 
        main_pdf_path, 
        output_base_dir, 
        clinic_history,
        progress_callback
    )
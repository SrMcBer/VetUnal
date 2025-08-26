import os
from pathlib import Path
from typing import List, Optional
import logging

from .utils import get_page_count
from src.ocr.engine import ocr_pdf_page_with_tesseract_improved
from .extractor import extract_single_page
from .utils import extract_microchip_id

class FolderManager:
    """Handles folder creation and microchip ID extraction from control sheets"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def extract_microchip_ids_and_create_folders(
        self, 
        control_sheet_path: str, 
        output_base_dir: str, 
        clinic_history: int,
        progress_callback: Optional[callable] = None
    ) -> List[str]:
        """
        Extract microchip IDs from control sheet and create corresponding folders.
        
        Args:
            control_sheet_path: Path to the control sheet PDF
            output_base_dir: Base directory for output folders
            clinic_history: Starting clinic history number
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of created folder names
            
        Raises:
            RuntimeError: If page count retrieval fails or no microchip IDs found
            OSError: If folder creation fails
        """
        
        try:
            page_count = get_page_count(control_sheet_path)
            self.logger.info(f"Processing {page_count} pages from control sheet...")
            
            folder_names: List[str] = []
            current_clinic_history = clinic_history
            
            for page_num in range(1, page_count + 1):
                try:
                    # Update progress with current page being processed
                    if progress_callback:
                        progress_callback(
                            "processing_control_sheet", 
                            page_num - 1,  # 0-based for current progress
                            page_count, 
                            f"Processing page {page_num} of {page_count}"
                        )

                    # Perform OCR on the page
                    text = ocr_pdf_page_with_tesseract_improved(control_sheet_path, page_num)
                    
                    try:
                        # Extract microchip ID
                        microchip_id = extract_microchip_id(text)
                        self.logger.info(f"Found Microchip ID: {microchip_id} on page {page_num}")
                        
                        # Create folder name and path
                        folder_name = f"HC_{current_clinic_history}_UN_{microchip_id}"
                        folder_names.append(folder_name)
                        
                        output_folder = Path(output_base_dir) / folder_name
                        
                        # Create the output folder
                        try:
                            output_folder.mkdir(parents=True, exist_ok=True)
                            self.logger.debug(f"Created folder: {output_folder}")
                        except OSError as e:
                            raise OSError(f"Error creating output folder {output_folder}: {e}")
                        
                        # Extract the control sheet page to the folder
                        try:
                            extract_single_page(
                                control_sheet_path, 
                                page_num, 
                                str(output_folder), 
                                "0.0 HOJA DE CONTROL"
                            )
                            self.logger.debug(f"Extracted control sheet page {page_num} to {output_folder}")
                        except Exception as e:
                            self.logger.warning(
                                f"Failed to extract control sheet page {page_num} for microchip {microchip_id}: {e}"
                            )
                        
                        # Increment clinic history after successful processing
                        current_clinic_history += 1
                        
                        # Call progress callback if provided
                        if progress_callback:
                            progress_callback(
                                "processing_control_sheet", 
                                page_num, 
                                page_count, 
                                f"Created folder for microchip {microchip_id} ({len(folder_names)} folders created)"
                            )
                    
                    except ValueError as e:
                        self.logger.warning(
                            f"Could not find microchip ID on page {page_num} of {control_sheet_path}. Skipping page."
                        )
                        
                        if progress_callback:
                            progress_callback(
                                "processing_control_sheet", 
                                page_num, 
                                page_count, 
                                f"Skipped page {page_num} (no microchip ID found)"
                            )
                        
                        continue

                except Exception as e:
                    self.logger.warning(
                        f"Could not perform OCR on page {page_num} of {control_sheet_path}: {e}. Skipping page."
                    )
                    
                    # Still update progress even for failed pages
                    if progress_callback:
                        progress_callback(
                            "processing_control_sheet", 
                            page_num, 
                            page_count, 
                            f"Skipped page {page_num} (OCR failed)"
                        )
                    continue

            if not folder_names:
                raise RuntimeError("No microchip IDs found in the control document")
            
            # Final progress update
            if progress_callback:
                progress_callback(
                    "processing_control_sheet", 
                    page_count, 
                    page_count, 
                    f"Completed: {len(folder_names)} folders created"
                )

            self.logger.info(f"Successfully created {len(folder_names)} folders")
            return folder_names
        
        except Exception as e:
            if isinstance(e, RuntimeError) and "No microchip IDs found" in str(e):
                raise
            raise RuntimeError(f"Could not get page count for control sheet: {e}")

    def create_folder_structure(self, base_dir: str, folder_names: List[str]) -> None:
        """
        Create folder structure for given folder names.
        
        Args:
            base_dir: Base directory path
            folder_names: List of folder names to create
            
        Raises:
            OSError: If folder creation fails
        """
        base_path = Path(base_dir)
        
        for folder_name in folder_names:
            folder_path = base_path / folder_name
            try:
                folder_path.mkdir(parents=True, exist_ok=True)
                self.logger.debug(f"Created folder: {folder_path}")
            except OSError as e:
                raise OSError(f"Failed to create folder {folder_path}: {e}")

    def validate_output_directory(self, output_dir: str) -> None:
        """
        Validate that output directory exists and is writable.
        
        Args:
            output_dir: Directory path to validate
            
        Raises:
            ValueError: If directory is invalid or not writable
        """
        path = Path(output_dir)
        
        if not path.exists():
            try:
                path.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                raise ValueError(f"Cannot create output directory {output_dir}: {e}")
        
        if not path.is_dir():
            raise ValueError(f"Output path {output_dir} is not a directory")
        
        # Test write permissions
        test_file = path / ".write_test"
        try:
            test_file.touch()
            test_file.unlink()
        except OSError:
            raise ValueError(f"Output directory {output_dir} is not writable")

    def get_existing_folders(self, base_dir: str) -> List[str]:
        """
        Get list of existing folders in base directory.
        
        Args:
            base_dir: Base directory to scan
            
        Returns:
            List of folder names (not full paths)
        """
        try:
            base_path = Path(base_dir)
            if not base_path.exists():
                return []
            
            return [item.name for item in base_path.iterdir() if item.is_dir()]
        except Exception as e:
            self.logger.error(f"Error scanning directory {base_dir}: {e}")
            return []

    def cleanup_empty_folders(self, base_dir: str) -> int:
        """
        Remove empty folders from base directory.
        
        Args:
            base_dir: Base directory to clean
            
        Returns:
            Number of folders removed
        """
        removed_count = 0
        base_path = Path(base_dir)
        
        if not base_path.exists():
            return 0
        
        try:
            for folder_path in base_path.iterdir():
                if folder_path.is_dir():
                    try:
                        # Check if folder is empty
                        if not any(folder_path.iterdir()):
                            folder_path.rmdir()
                            removed_count += 1
                            self.logger.debug(f"Removed empty folder: {folder_path}")
                    except OSError as e:
                        self.logger.warning(f"Could not remove folder {folder_path}: {e}")
        except Exception as e:
            self.logger.error(f"Error during cleanup of {base_dir}: {e}")
        
        return removed_count

# Factory function for convenience
def create_folder_manager() -> FolderManager:
    """
    Factory function to create a FolderManager instance.
    
    Returns:
        Configured FolderManager instance
    """
    return FolderManager()
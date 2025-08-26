from typing import List, Dict
from dataclasses import dataclass, field
import logging

from src.ocr.text_classifier import PageInfo, PageType

@dataclass
class PatientRecord:
    """Represents a complete patient record with all document types"""
    historia_pages: List[int] = field(default_factory=list)
    cedula_pages: List[int] = field(default_factory=list)
    recibo_pages: List[int] = field(default_factory=list)
    unknown_pages: List[int] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    
    @property
    def all_pages(self) -> List[int]:
        """Get all pages in this record sorted by page number"""
        all_pages = (self.historia_pages + self.cedula_pages + 
                    self.recibo_pages + self.unknown_pages)
        return sorted(all_pages)
    
    @property
    def is_complete(self) -> bool:
        """Check if record has all required document types"""
        return (len(self.historia_pages) > 0 and 
                len(self.cedula_pages) > 0 and 
                len(self.recibo_pages) > 0)
        
    @property
    def has_issues(self) -> bool:
        """Check if record has any validation issues"""
        return len(self.issues) > 0 or len(self.unknown_pages) > 0

class PatientRecordGrouper:
    """Handles grouping pages into patient records"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def group_pages_into_patient_records(self, pages: List[PageInfo]) -> List[PatientRecord]:
        """
        Group pages into complete patient records based on page types.
        
        Args:
            pages: List of classified PageInfo objects
            
        Returns:
            List of PatientRecord objects
        """
        if not pages:
            return []
        
        records: List[PatientRecord] = []
        current_record = PatientRecord()
        in_record = False
        
        for i, page in enumerate(pages):
            page_type = page.page_type
            
            if page_type == PageType.HISTORIA_CLINICA:
                if (in_record and len(current_record.historia_pages) >= 2):
                    records.append(current_record)
                    current_record = PatientRecord()
                
                elif (in_record and 
                    len(current_record.historia_pages) > 0 and
                    (len(current_record.cedula_pages) > 0 or len(current_record.recibo_pages) > 0)):
                        records.append(current_record)
                        current_record = PatientRecord()
                
                if not in_record:
                    in_record = True
                current_record.historia_pages.append(page.page_number)
            
            elif page_type == PageType.CEDULA:
                if not in_record:
                    in_record = True
                current_record.cedula_pages.append(page.page_number)
            
            elif page_type == PageType.RECIBO:
                if not in_record:
                    in_record = True
                current_record.recibo_pages.append(page.page_number)
            
            elif page_type == PageType.UNKNOWN:
                if not in_record:
                    in_record = True
                current_record.unknown_pages.append(page.page_number)
            
            # Check if we've reached the end
            if i == len(pages) - 1:
                # End of pages, save current record if it has content
                if (in_record and 
                    (len(current_record.historia_pages) > 0 or
                        len(current_record.cedula_pages) > 0 or
                        len(current_record.recibo_pages) > 0 or
                        len(current_record.unknown_pages) > 0)):
                    records.append(current_record)
        
        self.logger.info(f"Grouped {len(pages)} pages into {len(records)} patient records")
        return records
      
    def validate_patient_records(self, records: List[PatientRecord]) -> None:
        """
        Validate patient records and add issues to records that have problems.
        
        Args:
            records: List of PatientRecord objects to validate
        """
        for i, record in enumerate(records):
            record.issues.clear()  # Clear any existing issues
            
            # Check for missing required document types
            if not record.historia_pages:
                record.issues.append("Missing HISTORIA CLINICA pages")
            
            if not record.cedula_pages:
                record.issues.append("Missing CEDULA pages")
            
            if not record.recibo_pages:
                record.issues.append("Missing RECIBO pages")
            
            # Check for unknown pages
            if record.unknown_pages:
                record.issues.append(f"Contains {len(record.unknown_pages)} UNKNOWN pages")
            
            if len(record.historia_pages) > 2:
                record.issues.append("More than 2 HISTORIA CLINICA pages found")
            
            if len(record.cedula_pages) > 1:
                record.issues.append("More than 1 CEDULA page found")
                
            if len(record.recibo_pages) > 2:
                record.issues.append("More than 2 RECIBO pages found")

            if len(record.historia_pages) == 0 and len(record.cedula_pages) > 0:
                record.issues.append("Cedula page found without corresponding HISTORIA CLINICA")

            if len(record.historia_pages) == 0 and len(record.recibo_pages) > 0:
                record.issues.append("Recibo page found without corresponding HISTORIA CLINICA")

            if len(record.cedula_pages) == 0 and len(record.recibo_pages) > 0:
                record.issues.append("Recibo page found without corresponding CEDULA")
                
            # Log validation results
            if record.has_issues:
                issues_str = ", ".join(record.issues)
                self.logger.warning(f"Record {i+1} has issues: {issues_str}")
            else:
                self.logger.debug(f"Record {i+1} is complete and valid")
    
    def print_patient_records_summary(self, pages: List[PageInfo], folder_names: List[str]) -> None:
        """
        Print a summary of the grouped records for debugging.
        
        Args:
            pages: List of PageInfo objects
            folder_names: List of folder names for correlation
        """
        records = self.group_pages_into_patient_records(pages)
        
        print("=== PATIENT RECORDS SUMMARY ===")
        print(f"Total pages processed: {len(pages)}")
        print(f"Patient records found: {len(records)}")
        print(f"Expected folders: {len(folder_names)}")
        
        if len(records) != len(folder_names):
            print(f"⚠️  WARNING: Record count ({len(records)}) doesn't match folder count ({len(folder_names)})")
        
        for i, record in enumerate(records):
            folder_name = folder_names[i] if i < len(folder_names) else "NO FOLDER"
            
            print(f"\nRecord {i+1} -> {folder_name}")
            print(f"  HISTORIA pages: {record.historia_pages}")
            print(f"  CEDULA pages: {record.cedula_pages}")
            print(f"  RECIBO pages: {record.recibo_pages}")
            
            if record.unknown_pages:
                print(f"  UNKNOWN pages: {record.unknown_pages}")
            
            if record.has_issues:
                print(f"  ⚠️  Issues: {', '.join(record.issues)}")
            else:
                print("  ✅ Complete record")
        
        print("=== END OF SUMMARY ===")
    
    def get_records_statistics(self, records: List[PatientRecord]) -> Dict[str, any]:
        """
        Get statistical information about patient records.
        
        Args:
            records: List of PatientRecord objects
            
        Returns:
            Dictionary with statistics
        """
        if not records:
            return {
                'total_records': 0,
                'complete_records': 0,
                'records_with_issues': 0,
                'completion_rate': 0.0
            }
        
        complete_records = sum(1 for record in records if record.is_complete)
        records_with_issues = sum(1 for record in records if record.has_issues)
        
        return {
            'total_records': len(records),
            'complete_records': complete_records,
            'records_with_issues': records_with_issues,
            'completion_rate': complete_records / len(records) if records else 0.0,
            'average_pages_per_record': sum(len(record.all_pages) for record in records) / len(records),
            'total_unknown_pages': sum(len(record.unknown_pages) for record in records)
        }
    
    def filter_records_by_completeness(self, records: List[PatientRecord], 
                                      complete_only: bool = True) -> List[PatientRecord]:
        """
        Filter records based on completeness.
        
        Args:
            records: List of PatientRecord objects
            complete_only: If True, return only complete records; if False, return incomplete ones
            
        Returns:
            Filtered list of records
        """
        if complete_only:
            return [record for record in records if record.is_complete]
        else:
            return [record for record in records if not record.is_complete]

# Factory function for convenience
def create_patient_record_grouper() -> PatientRecordGrouper:
    """
    Factory function to create a PatientRecordGrouper instance.
    
    Returns:
        Configured PatientRecordGrouper instance
    """
    return PatientRecordGrouper()
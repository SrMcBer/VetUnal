import sys
import os
import pickle
import copy
from src.pdf.main_processor import create_main_processor, process_pdfs
from src.pdf.processor import create_pdf_processor
from src.ocr.engine import debug_ocr_output
from src.pdf.utils import extract_multiple_pages
from src.ocr.pattern_rules import resolve_unknown_page_types
from tkinter import Tk
from src.gui.app_ui import PDFApp

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

if __name__ == "__main__":
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='[%(levelname)s] %(asctime)s - %(name)s - %(message)s',
        handlers=[logging.StreamHandler()]  # Output to stdout
    )
    
    mainPath = "tests/fixtures/MasterJuly22.pdf"
    controlPath = "tests/fixtures/ControlJuly22.pdf"
    output_dir = "tests/output/July22"
    
    # ? GUI Application
    root = Tk()
    app = PDFApp(root)
    root.mainloop()

    # ? Testing ocr outputs
    # processor = create_pdf_processor()
    # processor.process_document(mainPath)
    # debug_ocr_output(mainPath, 1)
    # debug_ocr_output(mainPath, 31)
    # debug_ocr_output(mainPath, 41,)
    # debug_ocr_output(mainPath, 36,)
    # debug_ocr_output(mainPath, 5, save_processed_image=True)

    # # ? Main processing function 
    # def progress_handler(step, current, total):
    #     if step == "step1_start":
    #         print("Starting control sheet processing...")
    #     elif step == "step1_complete":
    #         print("Control sheet processing complete!")
    #     elif step == "step2_complete":
    #         print("PDF splitting complete!")

    # microchip_ids = process_pdfs(
    #     controlPath, mainPath, output_dir, 1425,
    #     progress_callback=progress_handler
    # )
    
    
    # ? Testing for unkown page types resolution
    # processor = create_main_processor()
    # debug_dir = os.path.join(output_dir, "_DEBUG")
    
    # with open("original_pages.pkl", "rb") as f:
    #     test_pages = pickle.load(f)
    
    # print(f"Loaded {len(test_pages)} pages from original_pages1.pkl")

    # test_copy = copy.deepcopy(test_pages)

    # processor._save_classification_debug(test_copy, debug_dir, "01_initial_classification.txt")

    # # Test your function
    # # result = resolve_unknown_page_types(test_copy)
    # result = new_resolve_unknown_page_types(test_copy)

    # print(f"Resolved {len(result)} pages with updated types.")
    
    # processor._save_classification_debug(result, debug_dir, "02_after_resolution.txt")

    # # Compare before/after
    # for i, (before, after) in enumerate(zip(test_pages, result)):
    #     # if before.page_type != after.page_type:
    #     print(f"Page {after.page_number}: {before.page_type} -> {after.page_type}")
    
    # patient_records = processor.record_grouper.group_pages_into_patient_records(result)

    # processor.record_grouper.validate_patient_records(patient_records)
    
    # processor._save_patient_records_debug(patient_records, debug_dir, "03_patient_records.txt")
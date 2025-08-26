import pickle
from typing import List
from dataclasses import asdict
from src.ocr.text_classifier import PageInfo

def export_pages_for_testing(pages: List[PageInfo], filename: str = "test_pages"):
    """Export pages data in multiple formats for testing"""
    # Export as pickle (preserves exact object structure)
    with open(f"{filename}.pkl", 'wb') as f:
        pickle.dump(pages, f)

    print(f"Exported pages data to {filename}.pkl")

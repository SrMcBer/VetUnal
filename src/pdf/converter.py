import fitz  # PyMuPDF
from PIL import Image

def pdf_page_to_image(pdf_path: str, page_number: int, zoom: float = 2.0) -> Image.Image:
    try:
        doc = fitz.open(pdf_path)

        if not (1 <= page_number <= len(doc)):
            raise ValueError(f"Page number {page_number} out of bounds (1 - {len(doc)})")

        page = doc.load_page(page_number - 1)  # 0-indexed
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        doc.close()
        return img
    except Exception as e:
        raise RuntimeError(f"Failed to render PDF page to image: {e}")
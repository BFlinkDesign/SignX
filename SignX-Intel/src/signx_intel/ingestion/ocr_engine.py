"""OCR engine for handling scanned or image-based PDFs."""
from pathlib import Path
from typing import Dict, Any

try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


class OCREngine:
    """OCR engine for extracting text from images and scanned PDFs."""
    
    def __init__(self):
        """Initialize OCR engine."""
        if not TESSERACT_AVAILABLE:
            print("Warning: Tesseract OCR not available. Install with: pip install pytesseract pillow")
            print("Also install Tesseract system package: https://github.com/tesseract-ocr/tesseract")
    
    def extract_text_from_image(self, image_path: Path) -> str:
        """
        Extract text from an image file using OCR.
        
        Args:
            image_path: Path to image file
        
        Returns:
            Extracted text
        """
        if not TESSERACT_AVAILABLE:
            raise RuntimeError("Tesseract OCR not available")
        
        try:
            img = Image.open(image_path)
            text = pytesseract.image_to_string(img)
            return text
        except Exception as e:
            print(f"Error extracting text from {image_path}: {e}")
            return ""
    
    def extract_data_from_image(self, image_path: Path) -> Dict[str, Any]:
        """
        Extract structured data from an image.
        
        Args:
            image_path: Path to image file
        
        Returns:
            Structured data dictionary
        """
        text = self.extract_text_from_image(image_path)
        
        # TODO: Add structured extraction logic similar to PDF parser
        return {
            "raw_text": text,
            "source_file": image_path.name
        }


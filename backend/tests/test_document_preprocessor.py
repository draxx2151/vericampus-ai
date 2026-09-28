import io
import unittest
from pathlib import Path
from PIL import Image, ImageDraw
import fitz  # PyMuPDF

from app.services.verification.document_preprocessor import (
    DocumentPreprocessor,
    PreprocessingResult,
    PreprocessedPage,
)


class TestDocumentPreprocessor(unittest.TestCase):
    """Unit tests for DocumentPreprocessor."""

    def setUp(self):
        self.preprocessor = DocumentPreprocessor(max_pages=5, target_dpi=150)

    def _create_synthetic_image_bytes(self, text: str = "Government of Maharashtra", fmt: str = "PNG") -> bytes:
        img = Image.new("RGB", (600, 200), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((30, 80), text, fill=(0, 0, 0))
        buf = io.BytesIO()
        img.save(buf, format=fmt)
        return buf.getvalue()

    def _create_synthetic_pdf_bytes(self, num_pages: int = 1) -> bytes:
        doc = fitz.open()
        for i in range(num_pages):
            page = doc.new_page(width=595, height=842)
            page.insert_text((50, 100), f"Page {i + 1} Content: Scholarship Application Document")
        pdf_bytes = doc.write()
        doc.close()
        return pdf_bytes

    def test_preprocess_valid_png_image(self):
        img_bytes = self._create_synthetic_image_bytes(text="Aadhaar 1234 5678 9012", fmt="PNG")
        result: PreprocessingResult = self.preprocessor.preprocess(img_bytes)

        self.assertTrue(result.success)
        self.assertFalse(result.is_pdf)
        self.assertEqual(result.original_page_count, 1)
        self.assertEqual(len(result.processed_pages), 1)

        page = result.processed_pages[0]
        self.assertEqual(page.page_number, 1)
        self.assertGreater(len(page.image_bytes), 0)
        self.assertGreater(page.width, 0)
        self.assertGreater(page.height, 0)

    def test_preprocess_valid_jpeg_image(self):
        img_bytes = self._create_synthetic_image_bytes(text="Marksheet Percentage 85.5%", fmt="JPEG")
        result: PreprocessingResult = self.preprocessor.preprocess(img_bytes)

        self.assertTrue(result.success)
        self.assertFalse(result.is_pdf)
        self.assertEqual(len(result.processed_pages), 1)

    def test_preprocess_single_page_pdf(self):
        pdf_bytes = self._create_synthetic_pdf_bytes(num_pages=1)
        result: PreprocessingResult = self.preprocessor.preprocess(pdf_bytes)

        self.assertTrue(result.success)
        self.assertTrue(result.is_pdf)
        self.assertEqual(result.original_page_count, 1)
        self.assertEqual(len(result.processed_pages), 1)
        self.assertEqual(result.processed_pages[0].page_number, 1)

    def test_preprocess_multipage_pdf_bounds_to_max_pages(self):
        # Create 7-page PDF; max_pages is 5
        pdf_bytes = self._create_synthetic_pdf_bytes(num_pages=7)
        result: PreprocessingResult = self.preprocessor.preprocess(pdf_bytes)

        self.assertTrue(result.success)
        self.assertTrue(result.is_pdf)
        self.assertEqual(result.original_page_count, 7)
        self.assertEqual(len(result.processed_pages), 5)
        # Verify warning about truncation
        self.assertTrue(any("truncated" in w.lower() for w in result.warnings))

    def test_preprocess_empty_bytes(self):
        result: PreprocessingResult = self.preprocessor.preprocess(b"")
        self.assertFalse(result.success)
        self.assertEqual(len(result.processed_pages), 0)
        self.assertTrue(any("empty" in w.lower() for w in result.warnings))

    def test_preprocess_corrupted_bytes(self):
        result: PreprocessingResult = self.preprocessor.preprocess(b"CORRUPTED_NOT_AN_IMAGE_OR_PDF")
        self.assertFalse(result.success)
        self.assertEqual(len(result.processed_pages), 0)
        self.assertTrue(len(result.warnings) > 0)

    def test_preprocess_from_file_path(self, tmp_path=None):
        import tempfile
        img_bytes = self._create_synthetic_image_bytes()
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(img_bytes)
            tmp_name = f.name

        try:
            result = self.preprocessor.preprocess(tmp_name)
            self.assertTrue(result.success)
            self.assertEqual(len(result.processed_pages), 1)
        finally:
            Path(tmp_name).unlink(missing_ok=True)

    def test_preprocess_nonexistent_file(self):
        result = self.preprocessor.preprocess("C:\\nonexistent\\path\\document.pdf")
        self.assertFalse(result.success)
        self.assertTrue(any("does not exist" in w for w in result.warnings))


if __name__ == "__main__":
    unittest.main()

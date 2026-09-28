import unittest
from app.services.verification.ocr.base_ocr import (
    BaseOCRProvider,
    OCRResult,
    OCRLine,
    OCRBoundingBox,
)
from app.services.verification.ocr.paddleocr_provider import PaddleOCRProvider


class TestOCRProvider(unittest.TestCase):
    """Unit tests for OCR Provider interface and PaddleOCRProvider."""

    def test_base_ocr_provider_is_abstract(self):
        with self.assertRaises(TypeError):
            BaseOCRProvider()

    def test_paddle_ocr_provider_with_mock_runner(self):
        # PaddleOCR returns: list of page results, where each page is list of [box, (text, score)]
        raw_paddle_output = [
            [
                [[[10, 20], [110, 20], [110, 50], [10, 50]], ("GOVERNMENT OF INDIA", 0.98)],
                [[[10, 60], [200, 60], [200, 90], [10, 90]], ("Aadhaar No: 1234 5678 9012", 0.95)],
                [[[10, 100], [150, 100], [150, 130], [10, 130]], ("Name: Aarav Patil", 0.92)],
            ]
        ]

        def mock_runner(img_np):
            return raw_paddle_output

        provider = PaddleOCRProvider(custom_runner=mock_runner)
        self.assertTrue(provider.is_available())

        # Process dummy image bytes (1x1 PNG or small bytes)
        import io
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGB", (100, 100)).save(buf, format="PNG")

        result: OCRResult = provider.extract_text(buf.getvalue())
        self.assertTrue(result.success)
        self.assertEqual(len(result.lines), 3)
        self.assertIn("GOVERNMENT OF INDIA", result.full_text)
        self.assertIn("1234 5678 9012", result.full_text)
        self.assertIn("Aarav Patil", result.full_text)
        self.assertAlmostEqual(result.average_confidence, 0.95, places=2)

        # Check line details
        first_line = result.lines[0]
        self.assertEqual(first_line.text, "GOVERNMENT OF INDIA")
        self.assertEqual(first_line.confidence, 0.98)
        self.assertIsNotNone(first_line.bounding_box)
        self.assertEqual(first_line.bounding_box.x_min, 10)
        self.assertEqual(first_line.bounding_box.y_min, 20)
        self.assertEqual(first_line.bounding_box.x_max, 110)
        self.assertEqual(first_line.bounding_box.y_max, 50)

    def test_paddle_ocr_provider_empty_input(self):
        provider = PaddleOCRProvider(custom_runner=lambda img: [])
        result = provider.extract_text(b"")
        self.assertFalse(result.success)
        self.assertTrue(any("Empty" in w for w in result.warnings))

    def test_paddle_ocr_provider_runner_exception_handling(self):
        import io
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGB", (10, 10)).save(buf, format="PNG")

        def failing_runner(img):
            raise RuntimeError("Engine execution failed")

        provider = PaddleOCRProvider(custom_runner=failing_runner)
        result = provider.extract_text(buf.getvalue())
        self.assertFalse(result.success)
        self.assertTrue(any("failed" in w.lower() for w in result.warnings))

    def test_paddle_ocr_provider_fallback_when_unavailable(self):
        # Explicitly pass is_available returning False
        provider = PaddleOCRProvider()
        # Force simulate paddleocr not installed
        provider._is_available = False
        self.assertFalse(provider.is_available())

        result = provider.extract_text(b"dummy_bytes")
        self.assertFalse(result.success)
        self.assertTrue(any("unavailable" in w.lower() or "not installed" in w.lower() for w in result.warnings))


if __name__ == "__main__":
    unittest.main()

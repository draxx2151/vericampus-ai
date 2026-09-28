import re
from typing import Optional, Tuple, List
from app.services.verification.base import MarksheetExtraction
from app.services.verification.ocr.base_ocr import OCRResult


class MarksheetExtractor:
    """
    Extracts candidate marksheet fields (Candidate name, roll number, exam, passing year,
    total marks, percentage, result classification) from raw OCR text.
    """

    @classmethod
    def extract(cls, ocr_result: OCRResult) -> Tuple[MarksheetExtraction, List[str]]:
        warnings: List[str] = []
        text = ocr_result.full_text
        lines = [line.text.strip() for line in ocr_result.lines if line.text.strip()]

        candidate_name = cls._extract_candidate_name(lines, text)
        roll_number = cls._extract_roll_number(text)
        exam_name = cls._extract_exam_name(text)
        passing_year = cls._extract_passing_year(text)
        total_marks, max_marks = cls._extract_marks(text)
        percentage = cls._extract_percentage(text, total_marks, max_marks)
        result_status = cls._extract_result_status(text)

        if not candidate_name:
            warnings.append("Could not locate candidate name on academic marksheet.")
        if not roll_number:
            warnings.append("Could not locate examination roll/seat number.")
        if percentage is None:
            warnings.append("Could not extract or calculate marks percentage.")

        extraction = MarksheetExtraction(
            candidate_name=candidate_name,
            roll_number=roll_number,
            exam_name=exam_name,
            passing_year=passing_year,
            total_marks=total_marks,
            max_marks=max_marks,
            percentage=percentage,
            result_status=result_status,
        )
        return extraction, warnings

    @staticmethod
    def _extract_candidate_name(lines: List[str], text: str) -> Optional[str]:
        for line in lines:
            m = re.search(r'(?:Candidate(?:\'s)?\s*Name|Student(?:\'s)?\s*Name|Name\s*of\s*Candidate)\s*[:\-]\s*(.+)', line, re.IGNORECASE)
            if m:
                cand = m.group(1).strip()
                if len(cand) > 2 and not any(ch.isdigit() for ch in cand):
                    return cand

        # Fallback: look for "Name:"
        for line in lines:
            m2 = re.search(r'\bName\s*[:\-]\s*([A-Za-z\s.]+)', line, re.IGNORECASE)
            if m2:
                cand = m2.group(1).strip()
                if len(cand) > 3 and not any(h in cand.upper() for h in ["BOARD", "EXAMINATION", "SCHOOL", "COLLEGE", "CENTRE"]):
                    return cand
        return None

    @staticmethod
    def _extract_roll_number(text: str) -> Optional[str]:
        m = re.search(r'(?:Roll\s*(?:No|Number)?|Seat\s*(?:No|Number)?)\s*[:\-]?\s*([A-Z0-9\-]+)', text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        return None

    @staticmethod
    def _extract_exam_name(text: str) -> Optional[str]:
        upper = text.upper()
        if "H.S.C" in upper or "HIGHER SECONDARY" in upper or "HSC" in upper:
            return "Higher Secondary Certificate (HSC)"
        elif "S.S.C" in upper or "SECONDARY SCHOOL" in upper or "SSC" in upper:
            return "Secondary School Certificate (SSC)"
        elif "CLASS XII" in upper or "CLASS 12" in upper or "CBSE XII" in upper:
            return "Class 12th Senior Secondary Examination"
        elif "CLASS X" in upper or "CLASS 10" in upper:
            return "Class 10th Secondary Examination"
        return "Board Examination"

    @staticmethod
    def _extract_passing_year(text: str) -> Optional[int]:
        m = re.search(r'(?:Passing\s*Year|Month\s*&\s*Year|Year\s*of\s*Exam|Exam\s*Year|Year)\s*[:\-]?\s*(?:[A-Za-z]+\s*)?(\b20\d{2}\b|\b19\d{2}\b)', text, re.IGNORECASE)
        if m:
            return int(m.group(1))

        # Look for 4-digit years in the 2000-2030 range
        years = [int(y) for y in re.findall(r'\b(20[0-2]\d)\b', text)]
        if years:
            return max(years)
        return None

    @staticmethod
    def _extract_marks(text: str) -> Tuple[Optional[float], Optional[float]]:
        # Match pattern like "Total Marks: 540 / 600" or "Total: 540/600"
        m = re.search(r'(?:Total\s*Marks|Grand\s*Total|Total)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:/\s*(\d+(?:\.\d+)?))?', text, re.IGNORECASE)
        if m:
            total = float(m.group(1))
            max_m = float(m.group(2)) if m.group(2) else None
            return total, max_m
        return None, None

    @staticmethod
    def _extract_percentage(text: str, total: Optional[float], max_m: Optional[float]) -> Optional[float]:
        m = re.search(r'(?:Percentage|Aggregate|Percent|%)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*%?', text, re.IGNORECASE)
        if m:
            val = float(m.group(1))
            if 0.0 <= val <= 100.0:
                return round(val, 2)

        # Calculate if total and max available
        if total is not None and max_m is not None and max_m > 0:
            calc = (total / max_m) * 100.0
            if 0.0 <= calc <= 100.0:
                return round(calc, 2)

        return None

    @staticmethod
    def _extract_result_status(text: str) -> Optional[str]:
        upper = text.upper()
        if "FIRST CLASS WITH DISTINCTION" in upper:
            return "FIRST CLASS WITH DISTINCTION"
        elif "FIRST CLASS" in upper:
            return "FIRST CLASS"
        elif "SECOND CLASS" in upper:
            return "SECOND CLASS"
        elif re.search(r'\bPASS(?:ED)?\b', upper):
            return "PASS"
        elif re.search(r'\bFAIL(?:ED)?\b', upper):
            return "FAIL"
        elif "ATKT" in upper:
            return "ATKT"
        return "PASS"

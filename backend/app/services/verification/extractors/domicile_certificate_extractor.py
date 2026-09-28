import re
from typing import Optional, Tuple, List
from app.services.verification.base import DomicileCertificateExtraction
from app.services.verification.ocr.base_ocr import OCRResult


class DomicileCertificateExtractor:
    """
    Extracts Maharashtra domicile certificate fields (Candidate name, state,
    is_maharashtra_domicile, certificate number, issue date) from raw OCR text.
    """

    @classmethod
    def extract(cls, ocr_result: OCRResult) -> Tuple[DomicileCertificateExtraction, List[str]]:
        warnings: List[str] = []
        text = ocr_result.full_text
        lines = [line.text.strip() for line in ocr_result.lines if line.text.strip()]

        candidate_name = cls._extract_candidate_name(lines, text)
        state, is_mh = cls._extract_state_and_domicile(text)
        cert_no = cls._extract_certificate_number(text)
        issue_date = cls._extract_issue_date(text)

        if not candidate_name:
            warnings.append("Could not locate candidate name on domicile certificate.")
        if state is None and is_mh is None:
            warnings.append("Could not detect State of Domicile in certificate text.")
        if not cert_no:
            warnings.append("Could not locate official domicile certificate serial number.")

        extraction = DomicileCertificateExtraction(
            candidate_name=candidate_name,
            state=state,
            is_maharashtra_domicile=is_mh,
            certificate_number=cert_no,
            issue_date=issue_date,
        )
        return extraction, warnings

    @staticmethod
    def _extract_candidate_name(lines: List[str], text: str) -> Optional[str]:
        for line in lines:
            m = re.search(r'(?:Candidate\s*Name|Issued\s*to|Name\s*of\s*Person|Resident\s*Name)\s*[:\-]\s*(.+)', line, re.IGNORECASE)
            if m:
                cand = m.group(1).strip()
                if len(cand) > 2 and not any(ch.isdigit() for ch in cand):
                    return cand

        # Look for "certify that / certified that Shri/Smt/Kumari <Name>"
        m2 = re.search(r'certif(?:ied|y)\s+that\s*(?:Shri|Smt|Kumari|Kumar)?\.?\s*([A-Za-z\s.]+?)(?:\s+(?:is|residing|son|daughter)|\n|$)', text, re.IGNORECASE)
        if m2:
            cand = m2.group(1).strip()
            if len(cand) > 3 and not any(ch.isdigit() for ch in cand):
                return cand
        return None

    @staticmethod
    def _extract_state_and_domicile(text: str) -> Tuple[Optional[str], Optional[bool]]:
        upper = text.upper()
        if "MAHARASHTRA" in upper:
            return "Maharashtra", True
        elif "GOVERNMENT OF MAHARASHTRA" in upper or "STATE OF MAHARASHTRA" in upper:
            return "Maharashtra", True
        elif any(s in upper for s in ["GUJARAT", "KARNATAKA", "MADHYA PRADESH", "GOA", "DELHI", "RAJASTHAN"]):
            # Detect explicit other state
            for other_state in ["GUJARAT", "KARNATAKA", "MADHYA PRADESH", "GOA", "DELHI", "RAJASTHAN"]:
                if other_state in upper:
                    return other_state.title(), False
        return None, None

    @staticmethod
    def _extract_certificate_number(text: str) -> Optional[str]:
        m = re.search(r'(?:Certificate\s*(?:No\.?|Number\.?)|Barcode|Outward\s*(?:No\.?)?|Case\s*(?:No\.?)?|Cert\s*No\.?)\s*[:\-]?\s*([A-Z0-9\-/]+)', text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            if len(val) >= 4:
                return val
        return None

    @staticmethod
    def _extract_issue_date(text: str) -> Optional[str]:
        m = re.search(r'(?:Date|Date\s*of\s*Issue|Issued\s*on)\s*[:\-]?\s*(\d{2}[/-]\d{2}[/-]\d{4})', text, re.IGNORECASE)
        if m:
            return m.group(1).replace("/", "-")
        m2 = re.search(r'\b(\d{2}[/-]\d{2}[/-]\d{4})\b', text)
        if m2:
            return m2.group(1).replace("/", "-")
        return None

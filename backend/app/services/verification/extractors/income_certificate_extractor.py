import re
from typing import Optional, Tuple, List
from app.services.verification.base import IncomeCertificateExtraction
from app.services.verification.ocr.base_ocr import OCRResult


class IncomeCertificateExtractor:
    """
    Extracts family income certificate fields (Applicant name, father/guardian name,
    annual income in INR, certificate number, issuing authority, issue date, financial year)
    from raw OCR text.
    """

    @classmethod
    def extract(cls, ocr_result: OCRResult) -> Tuple[IncomeCertificateExtraction, List[str]]:
        warnings: List[str] = []
        text = ocr_result.full_text
        lines = [line.text.strip() for line in ocr_result.lines if line.text.strip()]

        applicant_name = cls._extract_applicant_name(lines, text)
        father_name = cls._extract_father_name(lines, text)
        income_inr = cls._extract_annual_income(text)
        cert_no = cls._extract_certificate_number(text)
        authority = cls._extract_issuing_authority(text)
        issue_date = cls._extract_issue_date(text)
        financial_year = cls._extract_financial_year(text)

        if not applicant_name:
            warnings.append("Could not locate applicant/beneficiary name on income certificate.")
        if income_inr is None:
            warnings.append("Could not extract annual family income figure from certificate text.")
        if not cert_no:
            warnings.append("Could not locate official certificate/outward number.")

        extraction = IncomeCertificateExtraction(
            applicant_name=applicant_name,
            father_guardian_name=father_name,
            annual_income_inr=income_inr,
            certificate_number=cert_no,
            issuing_authority=authority,
            issue_date=issue_date,
            financial_year=financial_year,
        )
        return extraction, warnings

    @staticmethod
    def _extract_applicant_name(lines: List[str], text: str) -> Optional[str]:
        for line in lines:
            m = re.search(r'(?:Applicant\s*Name|Issued\s*to|Name\s*of\s*Person|Candidate\s*Name)\s*[:\-]\s*(.+)', line, re.IGNORECASE)
            if m:
                cand = m.group(1).strip()
                if len(cand) > 2 and not any(ch.isdigit() for ch in cand):
                    return cand

        # Look for "Shri / Smt / Kum" pattern
        m_shri = re.search(r'\b(?:Shri|Smt|Kumari|Kumar)\.?\s+([A-Za-z\s.]+)', text)
        if m_shri:
            cand = m_shri.group(1).split("\n")[0].strip()
            if len(cand) > 3 and not any(ch.isdigit() for ch in cand):
                return cand
        return None

    @staticmethod
    def _extract_father_name(lines: List[str], text: str) -> Optional[str]:
        for line in lines:
            m = re.search(r'(?:Father(?:\'s)?\s*Name|Guardian(?:\'s)?\s*Name|Husband(?:\'s)?\s*Name|S/o|D/o|W/o)\s*[:\-]?\s*(.+)', line, re.IGNORECASE)
            if m:
                cand = m.group(1).strip()
                if len(cand) > 2 and not any(ch.isdigit() for ch in cand):
                    return cand
        return None

    @staticmethod
    def _extract_annual_income(text: str) -> Optional[float]:
        # 1. Match "Annual Income: Rs. 2,50,000" or "Total Family Income: ₹ 250000"
        m = re.search(r'(?:Annual\s*Income|Total\s*(?:Family)?\s*Income|Income\s*Amount)\s*[:\-]?\s*(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d+)?)', text, re.IGNORECASE)
        if m:
            clean_str = m.group(1).replace(",", "").strip()
            try:
                return float(clean_str)
            except ValueError:
                pass

        # 2. Match currency symbols with numbers e.g. "₹ 2,50,000" or "Rs. 2,50,000"
        m2 = re.search(r'(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d+)?)', text)
        if m2:
            clean_str = m2.group(1).replace(",", "").strip()
            try:
                val = float(clean_str)
                if val >= 1000.0:  # Reasonable income threshold
                    return val
            except ValueError:
                pass

        return None

    @staticmethod
    def _extract_certificate_number(text: str) -> Optional[str]:
        m = re.search(r'(?:Certificate\s*(?:No\.?|Number\.?)|Bar\s*Code\s*(?:No\.?)?|Outward\s*(?:No\.?)?|Application\s*(?:No\.?)?|Cert\s*No\.?)\s*[:\-]?\s*([A-Z0-9\-/]+)', text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            if len(val) >= 4:
                return val
        return None

    @staticmethod
    def _extract_issuing_authority(text: str) -> Optional[str]:
        upper = text.upper()
        if "TAHSILDAR" in upper or "TEHSILDAR" in upper:
            return "Tahsildar Revenue Office"
        elif "SUB-DIVISIONAL OFFICER" in upper or "SDO" in upper:
            return "Sub-Divisional Officer (Revenue)"
        elif "EXECUTIVE MAGISTRATE" in upper:
            return "Executive Magistrate"
        elif "DISTRICT MAGISTRATE" in upper or "COLLECTOR" in upper:
            return "Collector Office"
        return "Competent Revenue Authority"

    @staticmethod
    def _extract_issue_date(text: str) -> Optional[str]:
        m = re.search(r'(?:Date|Date\s*of\s*Issue|Issued\s*on)\s*[:\-]?\s*(\d{2}[/-]\d{2}[/-]\d{4})', text, re.IGNORECASE)
        if m:
            return m.group(1).replace("/", "-")
        m2 = re.search(r'\b(\d{2}[/-]\d{2}[/-]\d{4})\b', text)
        if m2:
            return m2.group(1).replace("/", "-")
        return None

    @staticmethod
    def _extract_financial_year(text: str) -> Optional[str]:
        m = re.search(r'(?:Financial\s*Year|Year)\s*[:\-]?\s*(\b20\d{2}\s*[-/]\s*20\d{2}\b|\b20\d{2}\s*[-/]\s*\d{2}\b)', text, re.IGNORECASE)
        if m:
            return m.group(1).replace(" ", "")
        return None

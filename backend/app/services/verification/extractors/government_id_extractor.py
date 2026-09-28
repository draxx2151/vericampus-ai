import re
from typing import Optional, Tuple, List
from app.services.verification.base import GovernmentIdExtraction
from app.services.verification.ocr.base_ocr import OCRResult


class GovernmentIdExtractor:
    """
    Extracts structured Government ID fields (Aadhaar, PAN, Voter ID, Driving License)
    from raw OCR text.
    """

    @classmethod
    def extract(cls, ocr_result: OCRResult) -> Tuple[GovernmentIdExtraction, List[str]]:
        warnings: List[str] = []
        text = ocr_result.full_text
        lines = [line.text.strip() for line in ocr_result.lines if line.text.strip()]

        id_type = cls._detect_id_type(text)
        id_number = cls._extract_id_number(text, id_type)
        full_name = cls._extract_full_name(lines, text, id_type)
        dob = cls._extract_dob(text)
        gender = cls._extract_gender(text)
        address = cls._extract_address(lines, text)

        if not id_number:
            warnings.append("Could not confidently extract Government ID number from document text.")
        if not full_name:
            warnings.append("Could not confidently locate cardholder full name in document text.")
        if not dob:
            warnings.append("Could not locate date of birth in Government ID.")

        extraction = GovernmentIdExtraction(
            id_type=id_type,
            id_number=id_number,
            full_name=full_name,
            date_of_birth=dob,
            gender=gender,
            address=address,
        )
        return extraction, warnings

    @staticmethod
    def _detect_id_type(text: str) -> str:
        upper = text.upper()
        if any(w in upper for w in ["AADHAAR", "UIDAI", "ENROLMENT", "UNIQUE IDENTIFICATION", "MERA AADHAAR"]):
            return "AADHAAR"
        elif any(w in upper for w in ["INCOME TAX DEPARTMENT", "PERMANENT ACCOUNT NUMBER", "PAN CARD"]):
            return "PAN"
        elif any(w in upper for w in ["ELECTION COMMISSION", "ELECTOR", "VOTER"]):
            return "VOTER_ID"
        elif any(w in upper for w in ["DRIVING LICENCE", "DRIVING LICENSE", "MOTOR VEHICLES", "UNION OF INDIA DRIVING"]):
            return "DRIVING_LICENSE"
        return "GOVERNMENT_ID"

    @staticmethod
    def _extract_id_number(text: str, id_type: str) -> Optional[str]:
        # 1. Aadhaar: 12 digits, often formatted as 4-4-4
        aadhaar_match = re.search(r'\b(\d{4}\s+\d{4}\s+\d{4})\b', text)
        if aadhaar_match:
            return aadhaar_match.group(1).strip()
        aadhaar_digits = re.search(r'\b([2-9]\d{11})\b', text)
        if aadhaar_digits and id_type == "AADHAAR":
            val = aadhaar_digits.group(1)
            return f"{val[:4]} {val[4:8]} {val[8:]}"

        # 2. PAN: 5 letters, 4 digits, 1 letter
        pan_match = re.search(r'\b([A-Z]{5}\d{4}[A-Z])\b', text, re.IGNORECASE)
        if pan_match:
            return pan_match.group(1).upper()

        # 3. Voter ID: 3 letters, 7 digits
        voter_match = re.search(r'\b([A-Z]{3}\d{7})\b', text, re.IGNORECASE)
        if voter_match:
            return voter_match.group(1).upper()

        # 4. Driving License: 2 letters, 13-14 digits/chars
        dl_match = re.search(r'\b([A-Z]{2}[-\s]?\d{13,14})\b', text, re.IGNORECASE)
        if dl_match:
            return dl_match.group(1).upper()

        return None

    @staticmethod
    def _extract_full_name(lines: List[str], full_text: str, id_type: str) -> Optional[str]:
        # Pattern 1: Explicit "Name:" or "Name :"
        for i, line in enumerate(lines):
            m = re.search(r'(?:Name|Full\s*Name)\s*[:\-]\s*(.+)', line, re.IGNORECASE)
            if m:
                cand = m.group(1).strip()
                if len(cand) > 2 and not any(ch.isdigit() for ch in cand):
                    return cand

        # Pattern 2: Line above DOB or Gender (common in Aadhaar)
        for i, line in enumerate(lines):
            if re.search(r'(?:DOB|Date\s*of\s*Birth|Year\s*of\s*Birth|Male|Female)', line, re.IGNORECASE):
                if i > 0:
                    cand = lines[i - 1].strip()
                    # Filter out government headers
                    if not any(h in cand.upper() for h in ["GOVERNMENT", "INDIA", "UIDAI", "ENROLMENT", "AUTHORITY"]):
                        if len(cand) > 2 and not any(ch.isdigit() for ch in cand):
                            return cand

        return None

    @staticmethod
    def _extract_dob(text: str) -> Optional[str]:
        # Look for DOB label or raw date
        m = re.search(r'(?:DOB|Date\s*of\s*Birth|Year\s*of\s*Birth|Birth|D\.O\.B\.)\s*[:\-]?\s*(\d{2}[/-]\d{2}[/-]\d{4})', text, re.IGNORECASE)
        raw_date = None
        if m:
            raw_date = m.group(1).replace("/", "-")
        else:
            m2 = re.search(r'\b(\d{2}[/-]\d{2}[/-]\d{4})\b', text)
            if m2:
                raw_date = m2.group(1).replace("/", "-")

        if raw_date:
            parts = raw_date.split("-")
            # If DD-MM-YYYY, convert to YYYY-MM-DD
            if len(parts) == 3 and len(parts[0]) == 2 and len(parts[2]) == 4:
                return f"{parts[2]}-{parts[1]}-{parts[0]}"
            return raw_date

        m_year = re.search(r'(?:Year\s*of\s*Birth|YOB)\s*[:\-]?\s*(\d{4})', text, re.IGNORECASE)
        if m_year:
            return f"{m_year.group(1)}-01-01"

        return None

    @staticmethod
    def _extract_gender(text: str) -> Optional[str]:
        upper = text.upper()
        if re.search(r'\bFEMALE\b', upper):
            return "FEMALE"
        elif re.search(r'\bMALE\b', upper):
            return "MALE"
        elif re.search(r'\bTRANSGENDER\b', upper):
            return "TRANSGENDER"
        return None

    @staticmethod
    def _extract_address(lines: List[str], text: str) -> Optional[str]:
        addr_lines = []
        found_start = False
        for line in lines:
            if found_start:
                addr_lines.append(line)
                if re.search(r'\b\d{6}\b', line):  # PIN code found
                    break
            elif re.search(r'(?:Address|Address\s*:|To:)', line, re.IGNORECASE):
                found_start = True
                cleaned = re.sub(r'^(?:Address|To)\s*[:\-]?\s*', '', line, flags=re.IGNORECASE).strip()
                if cleaned:
                    addr_lines.append(cleaned)

        if addr_lines:
            return ", ".join(addr_lines)

        # Fallback: look for line containing PIN code and preceding text
        pin_match = re.search(r'([A-Za-z0-9,\s\-]+(?:\bMaharashtra\b)?\s*\b\d{6}\b)', text, re.IGNORECASE)
        if pin_match:
            return pin_match.group(1).strip()

        return None

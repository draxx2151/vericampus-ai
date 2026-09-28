"""
VeriCampus AI — Stage 3 Government ID Field Extractor
Layout-aware extractor supporting Aadhaar, PAN, Voter ID, and Driving License.
CONSTRAINT: Checksum validation is strictly optional/advisory and never independently fails extraction.
Sensitive values are masked in debug representations.
"""
import re
from typing import Optional, Dict, Any, List, Tuple
from ..base import BaseFieldExtractor
from ..schemas import (
    FieldExtractionResult,
    ExtractionStatus,
    DocumentFieldExtractionResult,
    DocumentExtractionStatus,
)
from ..normalizers import (
    normalize_name,
    normalize_date,
    normalize_id_number,
    mask_sensitive_id,
    normalize_whitespace,
)
from ..scorer import (
    calculate_field_confidence,
    calculate_overall_confidence,
    calculate_completeness,
)
from ..aliases import FIELD_ALIASES


def _verhoeff_checksum_advisory(number_str: str) -> bool:
    """
    Advisory Verhoeff checksum calculation for 12-digit Indian Aadhaar numbers.
    NOTE: Advisory only. Extraction will NOT fail if this returns False.
    """
    clean_digits = re.sub(r'\D', '', number_str)
    if len(clean_digits) != 12:
        return False

    d_table = (
        (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
        (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
        (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
        (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
        (4, 0, 1, 2, 3, 9, 5, 6, 7, 8),
        (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
        (6, 5, 9, 8, 7, 1, 0, 4, 3, 2),
        (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
        (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
        (9, 8, 7, 6, 5, 4, 3, 2, 1, 0)
    )
    p_table = (
        (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
        (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
        (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
        (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
        (9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
        (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
        (2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
        (7, 0, 4, 6, 9, 1, 3, 2, 5, 8)
    )

    c = 0
    reversed_digits = [int(ch) for ch in reversed(clean_digits)]
    for i, digit in enumerate(reversed_digits):
        c = d_table[c][p_table[i % 8][digit]]
    return c == 0


class GovernmentIdFieldExtractor(BaseFieldExtractor):
    """Layout-aware generic Government ID field extractor."""

    def extract(
        self,
        ocr_result: Any,
        expected_type: Optional[str] = "GOVERNMENT_ID",
        **kwargs: Any
    ) -> DocumentFieldExtractionResult:
        lines = getattr(ocr_result, "lines", [])
        full_text = getattr(ocr_result, "full_text", "")
        warnings: List[str] = []
        errors: List[str] = []
        fields: Dict[str, FieldExtractionResult] = {}

        # 1. Detect ID Category (Aadhaar, PAN, Voter ID, Driving License)
        id_type_raw, id_type_norm, id_type_conf, id_type_bbox, id_type_line = self._detect_id_type(lines, full_text)
        fields["id_type"] = FieldExtractionResult(
            field_name="id_type",
            raw_value=id_type_raw,
            normalized_value=id_type_norm,
            confidence=id_type_conf,
            extraction_status=ExtractionStatus.EXTRACTED if id_type_norm else ExtractionStatus.NOT_FOUND,
            bounding_box=id_type_bbox,
            source_text=id_type_line,
        )

        # 2. Extract Government ID Number (Generic regex patterns)
        id_num_res, id_warnings = self._extract_id_number(lines, full_text, id_type_norm)
        fields["id_number"] = id_num_res
        warnings.extend(id_warnings)

        # 3. Extract Full Name
        name_res, name_warnings = self._extract_full_name(lines, full_text, id_type_norm)
        fields["full_name"] = name_res
        warnings.extend(name_warnings)

        # 4. Extract Date of Birth
        dob_res, dob_warnings = self._extract_dob(lines, full_text)
        fields["date_of_birth"] = dob_res
        warnings.extend(dob_warnings)

        # Completeness & Overall Confidence
        completeness_ratio, doc_status = calculate_completeness("GOVERNMENT_ID", fields)
        overall_conf = calculate_overall_confidence(fields)

        return DocumentFieldExtractionResult(
            document_type="GOVERNMENT_ID",
            extraction_status=doc_status,
            overall_confidence=overall_conf,
            completeness_score=completeness_ratio,
            fields=fields,
            warnings=warnings,
            errors=errors,
            source_pages=getattr(ocr_result, "page_count", 1),
            ocr_summary={
                "average_confidence": getattr(ocr_result, "average_confidence", 0.0),
                "lines_count": len(lines),
            },
            model_metadata={"id_subtype": id_type_norm, "is_generic": True},
        )

    def _detect_id_type(self, lines: List[Any], text: str) -> Tuple[Optional[str], Optional[str], float, Optional[Dict[str, float]], Optional[str]]:
        if not text or not text.strip():
            return None, None, 0.0, None, None
        upper = text.upper()
        if any(w in upper for w in ["AADHAAR", "UIDAI", "ENROLMENT", "UNIQUE IDENTIFICATION"]):
            return "Aadhaar Card", "AADHAAR", 0.95, None, "Aadhaar"
        if any(w in upper for w in ["INCOME TAX DEPARTMENT", "PERMANENT ACCOUNT NUMBER", "PAN CARD"]):
            return "PAN Card", "PAN", 0.95, None, "PAN"
        if any(w in upper for w in ["ELECTION COMMISSION", "ELECTOR", "VOTER"]):
            return "Voter ID", "VOTER_ID", 0.95, None, "Voter ID"
        if any(w in upper for w in ["DRIVING LICENCE", "DRIVING LICENSE", "MOTOR VEHICLES"]):
            return "Driving License", "DRIVING_LICENSE", 0.95, None, "Driving License"
        return "Government Identification", "GOVERNMENT_ID", 0.50, None, "Government ID"

    def _extract_id_number(
        self,
        lines: List[Any],
        text: str,
        id_type: str
    ) -> Tuple[FieldExtractionResult, List[str]]:
        warnings = []
        raw_val = None
        norm_val = None
        conf = 0.0
        bbox_dict = None
        source_line = None

        # Aadhaar: 12 digits (often 4-4-4)
        aadhaar_match = re.search(r'\b(\d{4}\s+\d{4}\s+\d{4})\b', text)
        if not aadhaar_match:
            aadhaar_match = re.search(r'\b([2-9]\d{11})\b', text)

        # PAN: 5 letters, 4 digits, 1 letter
        pan_match = re.search(r'\b([A-Z]{5}\d{4}[A-Z])\b', text, re.IGNORECASE)

        # Voter ID: 3 letters, 7 digits
        voter_match = re.search(r'\b([A-Z]{3}\d{7})\b', text, re.IGNORECASE)

        # Driving License: 2 letters, 13-14 chars
        dl_match = re.search(r'\b([A-Z]{2}[-\s]?\d{13,14})\b', text, re.IGNORECASE)

        matched_line_obj = None

        is_valid_advisory = True

        if id_type == "AADHAAR" and aadhaar_match:
            raw_val = aadhaar_match.group(1).strip()
            _, norm_val = normalize_id_number(raw_val)
            conf = 0.95
        elif id_type == "PAN" and pan_match:
            raw_val = pan_match.group(1).strip()
            _, norm_val = normalize_id_number(raw_val)
            conf = 0.95
        elif id_type == "VOTER_ID" and voter_match:
            raw_val = voter_match.group(1).strip()
            _, norm_val = normalize_id_number(raw_val)
            conf = 0.94
        elif id_type == "DRIVING_LICENSE" and dl_match:
            raw_val = dl_match.group(1).strip()
            _, norm_val = normalize_id_number(raw_val)
            conf = 0.92
        else:
            # Fallback across all candidate patterns
            for cand, score in [(aadhaar_match, 0.90), (pan_match, 0.90), (voter_match, 0.88), (dl_match, 0.85)]:
                if cand:
                    raw_val = cand.group(1).strip()
                    _, norm_val = normalize_id_number(raw_val)
                    conf = score
                    break

        # Check Verhoeff checksum advisory for 12-digit Aadhaar numbers
        if norm_val and len(norm_val) == 12 and norm_val.isdigit():
            is_valid_advisory = _verhoeff_checksum_advisory(norm_val)
            if not is_valid_advisory:
                conf = max(0.80, conf - 0.07)
                warnings.append("Advisory: Aadhaar Verhoeff checksum validation did not pass (extraction preserved).")

        # Locate line object for spatial metadata
        if raw_val:
            for l in lines:
                if raw_val in getattr(l, "text", ""):
                    matched_line_obj = l
                    source_line = getattr(l, "text", "")
                    raw_bbox = getattr(l, "bounding_box", None)
                    if raw_bbox:
                        bbox_dict = raw_bbox.model_dump() if hasattr(raw_bbox, "model_dump") else dict(raw_bbox)
                    break

        if not norm_val:
            warnings.append("Government ID number could not be located in document text.")
            return FieldExtractionResult(
                field_name="id_number",
                raw_value=None,
                normalized_value=None,
                confidence=0.0,
                extraction_status=ExtractionStatus.NOT_FOUND,
                reason="ID pattern not matched in OCR text",
            ), warnings

        # Mask sensitive ID number in result reason/diagnostics
        masked = mask_sensitive_id(norm_val)

        reason_str = f"Extracted valid ID number ending in {norm_val[-4:] if len(norm_val)>=4 else ''}"
        if not is_valid_advisory:
            reason_str += " (Advisory: Checksum validation not passed)"

        return FieldExtractionResult(
            field_name="id_number",
            raw_value=raw_val,
            normalized_value=norm_val,
            display_value=masked,
            confidence=conf,
            extraction_status=ExtractionStatus.EXTRACTED,
            bounding_box=bbox_dict,
            source_text=source_line,
            reason=reason_str,
        ), warnings

    def _extract_full_name(
        self,
        lines: List[Any],
        text: str,
        id_type: str
    ) -> Tuple[FieldExtractionResult, List[str]]:
        warnings = []
        raw_val = None
        norm_val = None
        conf = 0.0
        bbox_dict = None
        source_line = None

        # 1. Label-based search: "Name:"
        for l in lines:
            line_txt = getattr(l, "text", "")
            m = re.search(r'(?:Name|Full\s*Name|Cardholder\s*Name)\s*[:\-]\s*(.+)', line_txt, re.IGNORECASE)
            if m:
                cand = m.group(1).strip()
                if len(cand) >= 3 and not any(ch.isdigit() for ch in cand):
                    raw_val, norm_val = normalize_name(cand)
                    conf = calculate_field_confidence(getattr(l, "confidence", 0.90), 0.95, 0.10)
                    raw_bbox = getattr(l, "bounding_box", None)
                    bbox_dict = raw_bbox.model_dump() if hasattr(raw_bbox, "model_dump") else (dict(raw_bbox) if raw_bbox else None)
                    source_line = line_txt
                    break

        # 2. Positional heuristic (line preceding DOB or Gender in Aadhaar/Voter ID)
        if not norm_val:
            for i, l in enumerate(lines):
                line_txt = getattr(l, "text", "")
                if re.search(r'(?:DOB|Date\s*of\s*Birth|Year\s*of\s*Birth|Gender|Male|Female)', line_txt, re.IGNORECASE):
                    if i > 0:
                        prev_l = lines[i - 1]
                        prev_txt = getattr(prev_l, "text", "").strip()
                        if not any(h in prev_txt.upper() for h in ["GOVERNMENT", "INDIA", "UIDAI", "ENROLMENT", "AUTHORITY", "INCOME TAX"]):
                            if len(prev_txt) >= 3 and not any(ch.isdigit() for ch in prev_txt):
                                raw_val, norm_val = normalize_name(prev_txt)
                                conf = calculate_field_confidence(getattr(prev_l, "confidence", 0.85), 0.85, 0.0)
                                raw_bbox = getattr(prev_l, "bounding_box", None)
                                bbox_dict = raw_bbox.model_dump() if hasattr(raw_bbox, "model_dump") else (dict(raw_bbox) if raw_bbox else None)
                                source_line = prev_txt
                                break

        if not norm_val:
            warnings.append("Could not locate cardholder full name in Government ID.")
            return FieldExtractionResult(
                field_name="full_name",
                raw_value=None,
                normalized_value=None,
                confidence=0.0,
                extraction_status=ExtractionStatus.NOT_FOUND,
                reason="Full name pattern not matched",
            ), warnings

        return FieldExtractionResult(
            field_name="full_name",
            raw_value=raw_val,
            normalized_value=norm_val,
            confidence=conf,
            extraction_status=ExtractionStatus.EXTRACTED,
            bounding_box=bbox_dict,
            source_text=source_line,
        ), warnings

    def _extract_dob(
        self,
        lines: List[Any],
        text: str
    ) -> Tuple[FieldExtractionResult, List[str]]:
        warnings = []
        raw_val = None
        norm_val = None
        conf = 0.0
        bbox_dict = None
        source_line = None

        # 1. Label match e.g. "DOB: 15/01/2004"
        for l in lines:
            line_txt = getattr(l, "text", "")
            m = re.search(r'(?:DOB|Date\s*of\s*Birth|Birth\s*Date|Year\s*of\s*Birth|Born)\s*[:\-]?\s*([0-9A-Za-z\/\-\.\s]+)', line_txt, re.IGNORECASE)
            if m:
                cand = m.group(1).strip()
                raw_cand, norm_cand = normalize_date(cand)
                if norm_cand:
                    raw_val, norm_val = raw_cand, norm_cand
                    conf = calculate_field_confidence(getattr(l, "confidence", 0.90), 0.95, 0.10)
                    raw_bbox = getattr(l, "bounding_box", None)
                    bbox_dict = raw_bbox.model_dump() if hasattr(raw_bbox, "model_dump") else (dict(raw_bbox) if raw_bbox else None)
                    source_line = line_txt
                    break

        # 2. Standalone date regex across lines
        if not norm_val:
            for l in lines:
                line_txt = getattr(l, "text", "")
                raw_cand, norm_cand = normalize_date(line_txt)
                if norm_cand:
                    raw_val, norm_val = raw_cand, norm_cand
                    conf = calculate_field_confidence(getattr(l, "confidence", 0.85), 0.80, 0.0)
                    raw_bbox = getattr(l, "bounding_box", None)
                    bbox_dict = raw_bbox.model_dump() if hasattr(raw_bbox, "model_dump") else (dict(raw_bbox) if raw_bbox else None)
                    source_line = line_txt
                    break

        if not norm_val:
            warnings.append("Date of birth could not be located in Government ID.")
            return FieldExtractionResult(
                field_name="date_of_birth",
                raw_value=None,
                normalized_value=None,
                confidence=0.0,
                extraction_status=ExtractionStatus.NOT_FOUND,
                reason="Date of birth not detected",
            ), warnings

        return FieldExtractionResult(
            field_name="date_of_birth",
            raw_value=raw_val,
            normalized_value=norm_val,
            confidence=conf,
            extraction_status=ExtractionStatus.EXTRACTED,
            bounding_box=bbox_dict,
            source_text=source_line,
        ), warnings

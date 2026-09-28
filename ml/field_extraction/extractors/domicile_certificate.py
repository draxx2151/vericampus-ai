"""
VeriCampus AI — Stage 3 Domicile Certificate Field Extractor
Extracts applicant name, date of birth, domicile state, district, certificate number,
issue date, and issuing authority.
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
    normalize_whitespace,
)
from ..scorer import (
    calculate_field_confidence,
    calculate_overall_confidence,
    calculate_completeness,
)


class DomicileCertificateFieldExtractor(BaseFieldExtractor):
    """Layout-aware Domicile & Nationality Certificate extractor."""

    def extract(
        self,
        ocr_result: Any,
        expected_type: Optional[str] = "DOMICILE_CERTIFICATE",
        **kwargs: Any
    ) -> DocumentFieldExtractionResult:
        lines = getattr(ocr_result, "lines", [])
        full_text = getattr(ocr_result, "full_text", "")
        warnings: List[str] = []
        errors: List[str] = []
        fields: Dict[str, FieldExtractionResult] = {}

        # 1. Applicant Name
        fields["applicant_name"] = self._extract_applicant_name(lines, full_text, warnings)

        # 2. Date of Birth
        fields["date_of_birth"] = self._extract_dob(lines, full_text, warnings)

        # 3. Domicile State
        fields["domicile_state"] = self._extract_state(lines, full_text, warnings)

        # 4. Domicile District
        fields["domicile_district"] = self._extract_district(lines, full_text, warnings)

        # 5. Certificate Outward / Serial Number
        fields["certificate_number"] = self._extract_cert_number(lines, full_text, warnings)

        # 6. Issue Date
        fields["issue_date"] = self._extract_issue_date(lines, full_text, warnings)

        # 7. Issuing Authority
        fields["issuing_authority"] = self._extract_authority(lines, full_text, warnings)

        completeness_ratio, doc_status = calculate_completeness("DOMICILE_CERTIFICATE", fields)
        overall_conf = calculate_overall_confidence(fields)

        return DocumentFieldExtractionResult(
            document_type="DOMICILE_CERTIFICATE",
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
            model_metadata={"is_maharashtra": fields["domicile_state"].normalized_value == "maharashtra"},
        )

    def _extract_applicant_name(self, lines: List[Any], text: str, warnings: List[str]) -> FieldExtractionResult:
        # Pattern 1: Label match
        for l in lines:
            line_txt = getattr(l, "text", "")
            m = re.search(r'(?:Applicant(?:\'s)?\s*Name|Candidate(?:\'s)?\s*Name|Issued\s*to|Resident\s*Name)\s*[:\-]\s*(.+)', line_txt, re.IGNORECASE)
            if m:
                cand = m.group(1).strip()
                if len(cand) >= 3 and not any(ch.isdigit() for ch in cand):
                    raw, norm = normalize_name(cand)
                    raw_bbox = getattr(l, "bounding_box", None)
                    bbox_dict = raw_bbox.model_dump() if hasattr(raw_bbox, "model_dump") else (dict(raw_bbox) if raw_bbox else None)
                    return FieldExtractionResult(
                        field_name="applicant_name",
                        raw_value=raw,
                        normalized_value=norm,
                        confidence=calculate_field_confidence(getattr(l, "confidence", 0.90), 0.95),
                        extraction_status=ExtractionStatus.EXTRACTED,
                        bounding_box=bbox_dict,
                        source_text=line_txt,
                    )

        # Pattern 2: "Certified that Shri / Smt / Kumari <Name>"
        m2 = re.search(r'certif(?:ied|y)\s+that\s*(?:Shri|Smt|Kumari|Kumar)?\.?\s*([A-Za-z\s.]+?)(?:\s+(?:is|residing|son|daughter)|\n|$)', text, re.IGNORECASE)
        if m2:
            cand = m2.group(1).strip()
            if len(cand) >= 3 and not any(ch.isdigit() for ch in cand):
                raw, norm = normalize_name(cand)
                return FieldExtractionResult(
                    field_name="applicant_name",
                    raw_value=raw,
                    normalized_value=norm,
                    confidence=0.85,
                    extraction_status=ExtractionStatus.EXTRACTED,
                )

        warnings.append("Could not locate candidate name on domicile certificate.")
        return FieldExtractionResult(
            field_name="applicant_name",
            raw_value=None,
            normalized_value=None,
            confidence=0.0,
            extraction_status=ExtractionStatus.NOT_FOUND,
            reason="Candidate name not identified",
        )

    def _extract_dob(self, lines: List[Any], text: str, warnings: List[str]) -> FieldExtractionResult:
        for l in lines:
            line_txt = getattr(l, "text", "")
            m = re.search(r'(?:DOB|Date\s*of\s*Birth|Born\s*on)\s*[:\-]?\s*([0-9A-Za-z\/\-\.\s]+)', line_txt, re.IGNORECASE)
            if m:
                raw, norm = normalize_date(m.group(1))
                if norm:
                    raw_bbox = getattr(l, "bounding_box", None)
                    bbox_dict = raw_bbox.model_dump() if hasattr(raw_bbox, "model_dump") else (dict(raw_bbox) if raw_bbox else None)
                    return FieldExtractionResult(
                        field_name="date_of_birth",
                        raw_value=raw,
                        normalized_value=norm,
                        confidence=calculate_field_confidence(getattr(l, "confidence", 0.90), 0.95),
                        extraction_status=ExtractionStatus.EXTRACTED,
                        bounding_box=bbox_dict,
                        source_text=line_txt,
                    )
        return FieldExtractionResult(
            field_name="date_of_birth",
            raw_value=None,
            normalized_value=None,
            confidence=0.0,
            extraction_status=ExtractionStatus.NOT_FOUND,
            reason="Date of birth not present",
        )

    def _extract_state(self, lines: List[Any], text: str, warnings: List[str]) -> FieldExtractionResult:
        upper = text.upper()
        if "MAHARASHTRA" in upper:
            return FieldExtractionResult(
                field_name="domicile_state",
                raw_value="Maharashtra",
                normalized_value="maharashtra",
                confidence=0.96,
                extraction_status=ExtractionStatus.EXTRACTED,
            )

        for other_state in ["GUJARAT", "KARNATAKA", "MADHYA PRADESH", "GOA", "DELHI", "RAJASTHAN"]:
            if other_state in upper:
                return FieldExtractionResult(
                    field_name="domicile_state",
                    raw_value=other_state.title(),
                    normalized_value=other_state.lower(),
                    confidence=0.92,
                    extraction_status=ExtractionStatus.EXTRACTED,
                )

        warnings.append("Could not detect State of Domicile in certificate text.")
        return FieldExtractionResult(
            field_name="domicile_state",
            raw_value=None,
            normalized_value=None,
            confidence=0.0,
            extraction_status=ExtractionStatus.NOT_FOUND,
            reason="Domicile state not identified",
        )

    def _extract_district(self, lines: List[Any], text: str, warnings: List[str]) -> FieldExtractionResult:
        for l in lines:
            line_txt = getattr(l, "text", "")
            m = re.search(r'(?:District|Dist\.?|Zila)\s*[:\-]\s*([A-Za-z\s]+)', line_txt, re.IGNORECASE)
            if m:
                cand = m.group(1).strip()
                if len(cand) >= 3:
                    raw_bbox = getattr(l, "bounding_box", None)
                    bbox_dict = raw_bbox.model_dump() if hasattr(raw_bbox, "model_dump") else (dict(raw_bbox) if raw_bbox else None)
                    return FieldExtractionResult(
                        field_name="domicile_district",
                        raw_value=cand,
                        normalized_value=cand.lower(),
                        confidence=0.88,
                        extraction_status=ExtractionStatus.EXTRACTED,
                        bounding_box=bbox_dict,
                        source_text=line_txt,
                    )
        return FieldExtractionResult(
            field_name="domicile_district",
            raw_value=None,
            normalized_value=None,
            confidence=0.0,
            extraction_status=ExtractionStatus.NOT_FOUND,
            reason="District not specified",
        )

    def _extract_cert_number(self, lines: List[Any], text: str, warnings: List[str]) -> FieldExtractionResult:
        for l in lines:
            line_txt = getattr(l, "text", "")
            m = re.search(r'(?:Certificate\s*(?:No\.?|Number)|Barcode|Outward\s*(?:No\.?)?|Case\s*(?:No\.?)?|Cert\s*No\.?)\s*[:\-]?\s*([A-Z0-9\-/]+)', line_txt, re.IGNORECASE)
            if m:
                val = m.group(1).strip()
                if len(val) >= 4:
                    raw_bbox = getattr(l, "bounding_box", None)
                    bbox_dict = raw_bbox.model_dump() if hasattr(raw_bbox, "model_dump") else (dict(raw_bbox) if raw_bbox else None)
                    return FieldExtractionResult(
                        field_name="certificate_number",
                        raw_value=val,
                        normalized_value=val.upper(),
                        confidence=calculate_field_confidence(getattr(l, "confidence", 0.90), 0.95),
                        extraction_status=ExtractionStatus.EXTRACTED,
                        bounding_box=bbox_dict,
                        source_text=line_txt,
                    )

        warnings.append("Could not locate official domicile certificate serial number.")
        return FieldExtractionResult(
            field_name="certificate_number",
            raw_value=None,
            normalized_value=None,
            confidence=0.0,
            extraction_status=ExtractionStatus.NOT_FOUND,
            reason="Certificate number not detected",
        )

    def _extract_issue_date(self, lines: List[Any], text: str, warnings: List[str]) -> FieldExtractionResult:
        for l in lines:
            line_txt = getattr(l, "text", "")
            m = re.search(r'(?:Date|Date\s*of\s*Issue|Issued\s*on)\s*[:\-]?\s*([0-9A-Za-z\/\-\.\s]+)', line_txt, re.IGNORECASE)
            if m:
                raw, norm = normalize_date(m.group(1))
                if norm:
                    raw_bbox = getattr(l, "bounding_box", None)
                    bbox_dict = raw_bbox.model_dump() if hasattr(raw_bbox, "model_dump") else (dict(raw_bbox) if raw_bbox else None)
                    return FieldExtractionResult(
                        field_name="issue_date",
                        raw_value=raw,
                        normalized_value=norm,
                        confidence=calculate_field_confidence(getattr(l, "confidence", 0.90), 0.95),
                        extraction_status=ExtractionStatus.EXTRACTED,
                        bounding_box=bbox_dict,
                        source_text=line_txt,
                    )

        m_date = re.search(r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{4})\b', text)
        if m_date:
            raw, norm = normalize_date(m_date.group(1))
            if norm:
                return FieldExtractionResult(
                    field_name="issue_date",
                    raw_value=raw,
                    normalized_value=norm,
                    confidence=0.80,
                    extraction_status=ExtractionStatus.EXTRACTED,
                )

        warnings.append("Could not locate certificate issuance date.")
        return FieldExtractionResult(
            field_name="issue_date",
            raw_value=None,
            normalized_value=None,
            confidence=0.0,
            extraction_status=ExtractionStatus.NOT_FOUND,
            reason="Issue date not detected",
        )

    def _extract_authority(self, lines: List[Any], text: str, warnings: List[str]) -> FieldExtractionResult:
        upper = text.upper()
        if "TEHSILDAR" in upper or "TAHSILDAR" in upper:
            auth = "Office of the Tehsildar"
        elif "SUB DIVISIONAL OFFICER" in upper or "SDO" in upper:
            auth = "Sub-Divisional Officer (Revenue)"
        elif "EXECUTIVE MAGISTRATE" in upper:
            auth = "Executive Magistrate"
        elif "DISTRICT MAGISTRATE" in upper:
            auth = "District Magistrate / Collector"
        else:
            auth = None

        if auth:
            return FieldExtractionResult(
                field_name="issuing_authority",
                raw_value=auth,
                normalized_value=auth.lower(),
                confidence=0.90,
                extraction_status=ExtractionStatus.EXTRACTED,
            )

        return FieldExtractionResult(
            field_name="issuing_authority",
            raw_value=None,
            normalized_value=None,
            confidence=0.0,
            extraction_status=ExtractionStatus.NOT_FOUND,
            reason="Issuing authority not identified",
        )

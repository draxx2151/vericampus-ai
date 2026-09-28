"""
VeriCampus AI — Stage 3 Income Certificate Field Extractor
Extracts applicant name, father/guardian name, annual income amount (normalized to numeric float),
financial year, certificate number, issue date, issuing authority, and optional location fields.
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
    normalize_currency,
    normalize_whitespace,
)
from ..scorer import (
    calculate_field_confidence,
    calculate_overall_confidence,
    calculate_completeness,
)


class IncomeCertificateFieldExtractor(BaseFieldExtractor):
    """Layout-aware Income Certificate extractor."""

    def extract(
        self,
        ocr_result: Any,
        expected_type: Optional[str] = "INCOME_CERTIFICATE",
        **kwargs: Any
    ) -> DocumentFieldExtractionResult:
        lines = getattr(ocr_result, "lines", [])
        full_text = getattr(ocr_result, "full_text", "")
        warnings: List[str] = []
        errors: List[str] = []
        fields: Dict[str, FieldExtractionResult] = {}

        # 1. Applicant Name
        fields["applicant_name"] = self._extract_applicant_name(lines, full_text, warnings)

        # 2. Father / Guardian Name
        fields["father_guardian_name"] = self._extract_father_name(lines, full_text, warnings)

        # 3. Income Amount (Normalized numeric float e.g. 150000)
        fields["income_amount"] = self._extract_income_amount(lines, full_text, warnings)

        # 4. Financial Year
        fields["financial_year"] = self._extract_financial_year(lines, full_text, warnings)

        # 5. Certificate Outward / Serial Number
        fields["certificate_number"] = self._extract_cert_number(lines, full_text, warnings)

        # 6. Issue Date
        fields["issue_date"] = self._extract_issue_date(lines, full_text, warnings)

        # 7. Issuing Authority
        fields["issuing_authority"] = self._extract_authority(lines, full_text, warnings)

        # 8–10. Optional Location fields (District, Taluka, Village)
        fields["district"] = self._extract_location(lines, full_text, "district")
        fields["taluka"] = self._extract_location(lines, full_text, "taluka")
        fields["village"] = self._extract_location(lines, full_text, "village")

        completeness_ratio, doc_status = calculate_completeness("INCOME_CERTIFICATE", fields)
        overall_conf = calculate_overall_confidence(fields)

        return DocumentFieldExtractionResult(
            document_type="INCOME_CERTIFICATE",
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
            model_metadata={"has_numeric_income": fields["income_amount"].normalized_value is not None},
        )

    def _extract_applicant_name(self, lines: List[Any], text: str, warnings: List[str]) -> FieldExtractionResult:
        for l in lines:
            line_txt = getattr(l, "text", "")
            m = re.search(r'(?:Applicant(?:\'s)?\s*Name|Issued\s*to|Name\s*of\s*Person|Candidate\s*Name)\s*[:\-]\s*(.+)', line_txt, re.IGNORECASE)
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

        m_shri = re.search(r'\b(?:Shri|Smt|Kumari|Kumar)\.?\s+([A-Za-z\s.]+)', text)
        if m_shri:
            cand = m_shri.group(1).split("\n")[0].strip()
            if len(cand) >= 3 and not any(ch.isdigit() for ch in cand):
                raw, norm = normalize_name(cand)
                return FieldExtractionResult(
                    field_name="applicant_name",
                    raw_value=raw,
                    normalized_value=norm,
                    confidence=0.82,
                    extraction_status=ExtractionStatus.EXTRACTED,
                )

        warnings.append("Could not locate applicant name on income certificate.")
        return FieldExtractionResult(
            field_name="applicant_name",
            raw_value=None,
            normalized_value=None,
            confidence=0.0,
            extraction_status=ExtractionStatus.NOT_FOUND,
            reason="Applicant name not identified",
        )

    def _extract_father_name(self, lines: List[Any], text: str, warnings: List[str]) -> FieldExtractionResult:
        for l in lines:
            line_txt = getattr(l, "text", "")
            m = re.search(r'(?:Father(?:\'s)?\s*Name|Guardian(?:\'s)?\s*Name|Husband(?:\'s)?\s*Name|Son\s*of|Daughter\s*of|Ward\s*of|S/o|D/o|W/o)\s*[:\-]?\s*(.+)', line_txt, re.IGNORECASE)
            if m:
                cand = m.group(1).strip()
                if len(cand) >= 3 and not any(ch.isdigit() for ch in cand):
                    raw, norm = normalize_name(cand)
                    raw_bbox = getattr(l, "bounding_box", None)
                    bbox_dict = raw_bbox.model_dump() if hasattr(raw_bbox, "model_dump") else (dict(raw_bbox) if raw_bbox else None)
                    return FieldExtractionResult(
                        field_name="father_guardian_name",
                        raw_value=raw,
                        normalized_value=norm,
                        confidence=calculate_field_confidence(getattr(l, "confidence", 0.88), 0.90),
                        extraction_status=ExtractionStatus.EXTRACTED,
                        bounding_box=bbox_dict,
                        source_text=line_txt,
                    )
        return FieldExtractionResult(
            field_name="father_guardian_name",
            raw_value=None,
            normalized_value=None,
            confidence=0.0,
            extraction_status=ExtractionStatus.NOT_FOUND,
            reason="Father/guardian name not present",
        )

    def _extract_income_amount(self, lines: List[Any], text: str, warnings: List[str]) -> FieldExtractionResult:
        # Pattern 1: Explicit Label "Annual Income: Rs. 1,50,000"
        for l in lines:
            line_txt = getattr(l, "text", "")
            m = re.search(r'(?:Annual\s*Income|Total\s*(?:Family)?\s*Income|Income\s*Amount|Income)\s*[:\-]?\s*(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d+)?|\d+\s*(?:Lakh|Crore)?)', line_txt, re.IGNORECASE)
            if m:
                raw, num_val = normalize_currency(m.group(1))
                if num_val is not None:
                    raw_bbox = getattr(l, "bounding_box", None)
                    bbox_dict = raw_bbox.model_dump() if hasattr(raw_bbox, "model_dump") else (dict(raw_bbox) if raw_bbox else None)
                    return FieldExtractionResult(
                        field_name="income_amount",
                        raw_value=line_txt.strip(),
                        normalized_value=num_val,
                        confidence=calculate_field_confidence(getattr(l, "confidence", 0.90), 0.95),
                        extraction_status=ExtractionStatus.EXTRACTED,
                        bounding_box=bbox_dict,
                        source_text=line_txt,
                    )

        # Pattern 2: Currency sign anywhere with numbers
        m2 = re.search(r'(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d+)?)', text)
        if m2:
            raw, num_val = normalize_currency(m2.group(1))
            if num_val is not None and num_val >= 1000.0:
                return FieldExtractionResult(
                    field_name="income_amount",
                    raw_value=m2.group(0),
                    normalized_value=num_val,
                    confidence=0.82,
                    extraction_status=ExtractionStatus.EXTRACTED,
                )

        warnings.append("Could not extract annual family income figure from certificate text.")
        return FieldExtractionResult(
            field_name="income_amount",
            raw_value=None,
            normalized_value=None,
            confidence=0.0,
            extraction_status=ExtractionStatus.NOT_FOUND,
            reason="Income amount figure not detected",
        )

    def _extract_financial_year(self, lines: List[Any], text: str, warnings: List[str]) -> FieldExtractionResult:
        m = re.search(r'(?:Financial\s*Year|Fin\s*Year|Year)\s*[:\-]?\s*(\b20\d{2}\s*[-–]\s*(?:20)?\d{2}\b)', text, re.IGNORECASE)
        if m:
            val = re.sub(r'\s+', '', m.group(1)).replace('–', '-')
            return FieldExtractionResult(
                field_name="financial_year",
                raw_value=m.group(1),
                normalized_value=val,
                confidence=0.92,
                extraction_status=ExtractionStatus.EXTRACTED,
            )

        # Generic year span search
        m2 = re.search(r'\b(20\d{2}\s*[-–]\s*(?:20)?\d{2})\b', text)
        if m2:
            val = re.sub(r'\s+', '', m2.group(1)).replace('–', '-')
            return FieldExtractionResult(
                field_name="financial_year",
                raw_value=m2.group(1),
                normalized_value=val,
                confidence=0.82,
                extraction_status=ExtractionStatus.EXTRACTED,
            )

        warnings.append("Could not locate financial year on income certificate.")
        return FieldExtractionResult(
            field_name="financial_year",
            raw_value=None,
            normalized_value=None,
            confidence=0.0,
            extraction_status=ExtractionStatus.NOT_FOUND,
            reason="Financial year pattern not detected",
        )

    def _extract_cert_number(self, lines: List[Any], text: str, warnings: List[str]) -> FieldExtractionResult:
        for l in lines:
            line_txt = getattr(l, "text", "")
            m = re.search(r'(?:Certificate\s*(?:No\.?|Number)|Bar\s*Code\s*(?:No\.?)?|Outward\s*(?:No\.?)?|Cert\s*No\.?)\s*[:\-]?\s*([A-Z0-9\-/]+)', line_txt, re.IGNORECASE)
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

        warnings.append("Could not locate official certificate number.")
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
        elif "REVENUE OFFICER" in upper:
            auth = "Revenue Officer"
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

    def _extract_location(self, lines: List[Any], text: str, loc_type: str) -> FieldExtractionResult:
        for l in lines:
            line_txt = getattr(l, "text", "")
            m = re.search(rf'(?:{loc_type}|zila)\s*[:\-]\s*([A-Za-z\s]+)', line_txt, re.IGNORECASE)
            if m:
                cand = m.group(1).strip()
                if len(cand) >= 3:
                    raw_bbox = getattr(l, "bounding_box", None)
                    bbox_dict = raw_bbox.model_dump() if hasattr(raw_bbox, "model_dump") else (dict(raw_bbox) if raw_bbox else None)
                    return FieldExtractionResult(
                        field_name=loc_type,
                        raw_value=cand,
                        normalized_value=cand.lower(),
                        confidence=0.85,
                        extraction_status=ExtractionStatus.EXTRACTED,
                        bounding_box=bbox_dict,
                        source_text=line_txt,
                    )
        return FieldExtractionResult(
            field_name=loc_type,
            raw_value=None,
            normalized_value=None,
            confidence=0.0,
            extraction_status=ExtractionStatus.NOT_FOUND,
            reason=f"{loc_type.title()} not specified",
        )

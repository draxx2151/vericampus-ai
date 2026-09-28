"""
VeriCampus AI — Stage 3 Marksheet Field Extractor
Extracts student name, roll number, examination details, academic subjects table,
total marks, percentage, CGPA, and result status.
CONSTRAINT: If a field (like CGPA) is absent, sets status = NOT_FOUND without inventing values.
"""
import re
from typing import Optional, Dict, Any, List, Tuple
from ..base import BaseFieldExtractor
from ..schemas import (
    FieldExtractionResult,
    ExtractionStatus,
    DocumentFieldExtractionResult,
    DocumentExtractionStatus,
    SubjectScore,
)
from ..normalizers import (
    normalize_name,
    normalize_percentage,
    normalize_whitespace,
)
from ..scorer import (
    calculate_field_confidence,
    calculate_overall_confidence,
    calculate_completeness,
)


class MarksheetFieldExtractor(BaseFieldExtractor):
    """Layout-aware Marksheet and Academic Transcript extractor."""

    def extract(
        self,
        ocr_result: Any,
        expected_type: Optional[str] = "MARKSHEET",
        **kwargs: Any
    ) -> DocumentFieldExtractionResult:
        lines = getattr(ocr_result, "lines", [])
        full_text = getattr(ocr_result, "full_text", "")
        warnings: List[str] = []
        errors: List[str] = []
        fields: Dict[str, FieldExtractionResult] = {}

        # 1. Student / Candidate Name
        fields["student_name"] = self._extract_student_name(lines, full_text, warnings)

        # 2. Roll / Seat Number
        fields["roll_number"] = self._extract_roll_number(lines, full_text, warnings)

        # 3. Board or Educational Institution
        fields["board_or_institution"] = self._extract_board(lines, full_text, warnings)

        # 4. Examination Name
        fields["examination_name"] = self._extract_exam_name(lines, full_text, warnings)

        # 5. Examination Year
        fields["examination_year"] = self._extract_exam_year(lines, full_text, warnings)

        # 6. Academic Subjects Table (Structured rows)
        subjects_list, subj_conf = self._extract_subjects_table(lines, full_text)
        fields["subjects"] = FieldExtractionResult(
            field_name="subjects",
            raw_value=f"{len(subjects_list)} subjects extracted" if subjects_list else None,
            normalized_value=[s.model_dump() for s in subjects_list] if subjects_list else None,
            confidence=subj_conf,
            extraction_status=ExtractionStatus.EXTRACTED if subjects_list else ExtractionStatus.NOT_FOUND,
            reason=None if subjects_list else "No tabular subject rows detected",
        )

        # 7. Total Marks & Max Marks
        fields["total_marks"] = self._extract_total_marks(lines, full_text, warnings)

        # 8. Percentage
        fields["percentage"] = self._extract_percentage(lines, full_text, warnings)

        # 9. CGPA (Crucial: Do NOT invent if absent!)
        fields["cgpa"] = self._extract_cgpa(lines, full_text, warnings)

        # 10. Result Status
        fields["result_status"] = self._extract_result_status(lines, full_text, warnings)

        completeness_ratio, doc_status = calculate_completeness("MARKSHEET", fields)
        overall_conf = calculate_overall_confidence(fields)

        return DocumentFieldExtractionResult(
            document_type="MARKSHEET",
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
            model_metadata={"subjects_count": len(subjects_list)},
        )

    def _extract_student_name(self, lines: List[Any], text: str, warnings: List[str]) -> FieldExtractionResult:
        # Pattern 1: Explicit candidate label
        for l in lines:
            line_txt = getattr(l, "text", "")
            m = re.search(r'(?:Candidate(?:\'s)?\s*Name|Student(?:\'s)?\s*Name|Name\s*of\s*Candidate)\s*[:\-]\s*(.+)', line_txt, re.IGNORECASE)
            if m:
                cand = m.group(1).strip()
                if len(cand) >= 3 and not any(ch.isdigit() for ch in cand):
                    raw, norm = normalize_name(cand)
                    raw_bbox = getattr(l, "bounding_box", None)
                    bbox_dict = raw_bbox.model_dump() if hasattr(raw_bbox, "model_dump") else (dict(raw_bbox) if raw_bbox else None)
                    return FieldExtractionResult(
                        field_name="student_name",
                        raw_value=raw,
                        normalized_value=norm,
                        confidence=calculate_field_confidence(getattr(l, "confidence", 0.90), 0.95),
                        extraction_status=ExtractionStatus.EXTRACTED,
                        bounding_box=bbox_dict,
                        source_text=line_txt,
                    )

        # Pattern 2: Generic "Name:"
        for l in lines:
            line_txt = getattr(l, "text", "")
            m2 = re.search(r'\bName\s*[:\-]\s*([A-Za-z\s.]+)', line_txt, re.IGNORECASE)
            if m2:
                cand = m2.group(1).strip()
                if len(cand) >= 3 and not any(h in cand.upper() for h in ["BOARD", "EXAMINATION", "SCHOOL", "COLLEGE", "CENTRE"]):
                    raw, norm = normalize_name(cand)
                    raw_bbox = getattr(l, "bounding_box", None)
                    bbox_dict = raw_bbox.model_dump() if hasattr(raw_bbox, "model_dump") else (dict(raw_bbox) if raw_bbox else None)
                    return FieldExtractionResult(
                        field_name="student_name",
                        raw_value=raw,
                        normalized_value=norm,
                        confidence=calculate_field_confidence(getattr(l, "confidence", 0.85), 0.85),
                        extraction_status=ExtractionStatus.EXTRACTED,
                        bounding_box=bbox_dict,
                        source_text=line_txt,
                    )

        warnings.append("Could not locate candidate name on academic marksheet.")
        return FieldExtractionResult(
            field_name="student_name",
            raw_value=None,
            normalized_value=None,
            confidence=0.0,
            extraction_status=ExtractionStatus.NOT_FOUND,
            reason="Candidate name pattern not matched",
        )

    def _extract_roll_number(self, lines: List[Any], text: str, warnings: List[str]) -> FieldExtractionResult:
        for l in lines:
            line_txt = getattr(l, "text", "")
            m = re.search(r'(?:Roll\s*(?:No\.?|Number)?|Seat\s*(?:No\.?|Number)?|Registration\s*No\.?)\s*[:\-]?\s*([A-Z0-9\-]+)', line_txt, re.IGNORECASE)
            if m:
                val = m.group(1).strip()
                raw_bbox = getattr(l, "bounding_box", None)
                bbox_dict = raw_bbox.model_dump() if hasattr(raw_bbox, "model_dump") else (dict(raw_bbox) if raw_bbox else None)
                return FieldExtractionResult(
                    field_name="roll_number",
                    raw_value=val,
                    normalized_value=val.upper(),
                    confidence=calculate_field_confidence(getattr(l, "confidence", 0.90), 0.95),
                    extraction_status=ExtractionStatus.EXTRACTED,
                    bounding_box=bbox_dict,
                    source_text=line_txt,
                )

        warnings.append("Could not locate examination roll or seat number.")
        return FieldExtractionResult(
            field_name="roll_number",
            raw_value=None,
            normalized_value=None,
            confidence=0.0,
            extraction_status=ExtractionStatus.NOT_FOUND,
            reason="Roll/seat number not detected",
        )

    def _extract_board(self, lines: List[Any], text: str, warnings: List[str]) -> FieldExtractionResult:
        upper = text.upper()
        if "MAHARASHTRA STATE BOARD" in upper:
            board_name = "Maharashtra State Board of Secondary and Higher Secondary Education"
        elif "CBSE" in upper or "CENTRAL BOARD" in upper:
            board_name = "Central Board of Secondary Education"
        elif "ICSE" in upper or "COUNCIL FOR THE INDIAN" in upper:
            board_name = "Council for the Indian School Certificate Examinations"
        elif "PUNE BOARD" in upper or "MUMBAI BOARD" in upper:
            board_name = "Maharashtra Divisional Board"
        elif "UNIVERSITY" in upper:
            board_name = "State University Examination Division"
        else:
            board_name = None

        if board_name:
            return FieldExtractionResult(
                field_name="board_or_institution",
                raw_value=board_name,
                normalized_value=board_name.lower(),
                confidence=0.92,
                extraction_status=ExtractionStatus.EXTRACTED,
            )

        return FieldExtractionResult(
            field_name="board_or_institution",
            raw_value=None,
            normalized_value=None,
            confidence=0.0,
            extraction_status=ExtractionStatus.NOT_FOUND,
            reason="Educational board header not identified",
        )

    def _extract_exam_name(self, lines: List[Any], text: str, warnings: List[str]) -> FieldExtractionResult:
        for l in lines:
            line_txt = getattr(l, "text", "")
            m = re.search(r'(?:Examination|Exam(?:\s*Name)?)\s*[:\-]\s*(.+)', line_txt, re.IGNORECASE)
            if m:
                val = m.group(1).strip()
                raw_bbox = getattr(l, "bounding_box", None)
                bbox_dict = raw_bbox.model_dump() if hasattr(raw_bbox, "model_dump") else (dict(raw_bbox) if raw_bbox else None)
                return FieldExtractionResult(
                    field_name="examination_name",
                    raw_value=val,
                    normalized_value=val.lower(),
                    confidence=calculate_field_confidence(getattr(l, "confidence", 0.90), 0.90),
                    extraction_status=ExtractionStatus.EXTRACTED,
                    bounding_box=bbox_dict,
                    source_text=line_txt,
                )

        upper = text.upper()
        if "HSC" in upper or "HIGHER SECONDARY" in upper or "CLASS 12" in upper:
            name = "Higher Secondary Certificate Examination"
        elif "SSC" in upper or "SECONDARY SCHOOL" in upper or "CLASS 10" in upper:
            name = "Secondary School Certificate Examination"
        else:
            name = None

        if name:
            return FieldExtractionResult(
                field_name="examination_name",
                raw_value=name,
                normalized_value=name.lower(),
                confidence=0.85,
                extraction_status=ExtractionStatus.EXTRACTED,
            )

        return FieldExtractionResult(
            field_name="examination_name",
            raw_value=None,
            normalized_value=None,
            confidence=0.0,
            extraction_status=ExtractionStatus.NOT_FOUND,
            reason="Examination name not detected",
        )

    def _extract_exam_year(self, lines: List[Any], text: str, warnings: List[str]) -> FieldExtractionResult:
        # 1. Label match
        for l in lines:
            line_txt = getattr(l, "text", "")
            m = re.search(r'(?:Passing\s*Year|Exam\s*Year|Year\s*of\s*Exam|Year)\s*[:\-]?\s*(?:[A-Za-z]+\s*)?(\b20\d{2}\b|\b19\d{2}\b)', line_txt, re.IGNORECASE)
            if m:
                val_int = int(m.group(1))
                raw_bbox = getattr(l, "bounding_box", None)
                bbox_dict = raw_bbox.model_dump() if hasattr(raw_bbox, "model_dump") else (dict(raw_bbox) if raw_bbox else None)
                return FieldExtractionResult(
                    field_name="examination_year",
                    raw_value=str(val_int),
                    normalized_value=val_int,
                    confidence=calculate_field_confidence(getattr(l, "confidence", 0.90), 0.95),
                    extraction_status=ExtractionStatus.EXTRACTED,
                    bounding_box=bbox_dict,
                    source_text=line_txt,
                )

        # 2. Year regex scanning in range 2000-2030
        years = [int(y) for y in re.findall(r'\b(20[0-2]\d)\b', text)]
        if years:
            val_int = max(years)
            return FieldExtractionResult(
                field_name="examination_year",
                raw_value=str(val_int),
                normalized_value=val_int,
                confidence=0.80,
                extraction_status=ExtractionStatus.EXTRACTED,
            )

        warnings.append("Could not locate examination passing year.")
        return FieldExtractionResult(
            field_name="examination_year",
            raw_value=None,
            normalized_value=None,
            confidence=0.0,
            extraction_status=ExtractionStatus.NOT_FOUND,
            reason="Examination year not detected",
        )

    def _extract_subjects_table(self, lines: List[Any], text: str) -> Tuple[List[SubjectScore], float]:
        """Parses academic subjects and marks rows."""
        subjects: List[SubjectScore] = []
        common_subjects = [
            "ENGLISH", "MARATHI", "HINDI", "PHYSICS", "CHEMISTRY", "MATHEMATICS",
            "BIOLOGY", "COMPUTER SCIENCE", "HISTORY", "GEOGRAPHY", "ECONOMICS",
            "ACCOUNTANCY", "SCIENCE", "SOCIAL SCIENCE"
        ]

        for l in lines:
            line_txt = getattr(l, "text", "").strip()
            upper_line = line_txt.upper()
            matched_subj = None
            for s in common_subjects:
                if s in upper_line:
                    matched_subj = s
                    break

            if matched_subj:
                # Find marks numbers on the line e.g. "PHYSICS 85 100 A" or "PHYSICS: 85/100"
                nums = re.findall(r'\b(\d+(?:\.\d+)?)\b', line_txt)
                marks_obt = float(nums[0]) if len(nums) >= 1 else None
                max_marks = float(nums[1]) if len(nums) >= 2 else (100.0 if marks_obt is not None else None)
                grade_match = re.search(r'\b([A-D][+]?|PASS|FAIL)\b', upper_line)
                grade = grade_match.group(1) if grade_match else None

                subjects.append(SubjectScore(
                    subject_name=matched_subj.title(),
                    marks_obtained=marks_obt,
                    maximum_marks=max_marks,
                    grade=grade,
                    confidence=getattr(l, "confidence", 0.88),
                ))

        avg_conf = (sum(s.confidence for s in subjects) / len(subjects)) if subjects else 0.0
        return subjects, round(avg_conf, 3)

    def _extract_total_marks(self, lines: List[Any], text: str, warnings: List[str]) -> FieldExtractionResult:
        for l in lines:
            line_txt = getattr(l, "text", "")
            m = re.search(r'(?:Total\s*Marks|Grand\s*Total|Total)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:/\s*(\d+(?:\.\d+)?))?', line_txt, re.IGNORECASE)
            if m:
                raw_val = m.group(1)
                try:
                    val = float(raw_val)
                    raw_bbox = getattr(l, "bounding_box", None)
                    bbox_dict = raw_bbox.model_dump() if hasattr(raw_bbox, "model_dump") else (dict(raw_bbox) if raw_bbox else None)
                    return FieldExtractionResult(
                        field_name="total_marks",
                        raw_value=raw_val,
                        normalized_value=val,
                        confidence=calculate_field_confidence(getattr(l, "confidence", 0.90), 0.95),
                        extraction_status=ExtractionStatus.EXTRACTED,
                        bounding_box=bbox_dict,
                        source_text=line_txt,
                    )
                except ValueError:
                    pass

        warnings.append("Total secured marks figure could not be extracted.")
        return FieldExtractionResult(
            field_name="total_marks",
            raw_value=None,
            normalized_value=None,
            confidence=0.0,
            extraction_status=ExtractionStatus.NOT_FOUND,
            reason="Total marks figure not detected",
        )

    def _extract_percentage(self, lines: List[Any], text: str, warnings: List[str]) -> FieldExtractionResult:
        for l in lines:
            line_txt = getattr(l, "text", "")
            m = re.search(r'(?:Percentage|Percent|Aggregate\s*%)\s*[:\-]?\s*(\d{1,3}(?:\.\d{1,3})?)\s*%?', line_txt, re.IGNORECASE)
            if m:
                raw, norm = normalize_percentage(m.group(1))
                if norm is not None:
                    raw_bbox = getattr(l, "bounding_box", None)
                    bbox_dict = raw_bbox.model_dump() if hasattr(raw_bbox, "model_dump") else (dict(raw_bbox) if raw_bbox else None)
                    return FieldExtractionResult(
                        field_name="percentage",
                        raw_value=raw,
                        normalized_value=norm,
                        confidence=calculate_field_confidence(getattr(l, "confidence", 0.90), 0.95),
                        extraction_status=ExtractionStatus.EXTRACTED,
                        bounding_box=bbox_dict,
                        source_text=line_txt,
                    )

        # Fallback regex for "%" symbol with preceding number
        m2 = re.search(r'\b(\d{2}(?:\.\d{1,2})?)\s*%', text)
        if m2:
            raw, norm = normalize_percentage(m2.group(1))
            if norm is not None:
                return FieldExtractionResult(
                    field_name="percentage",
                    raw_value=raw,
                    normalized_value=norm,
                    confidence=0.80,
                    extraction_status=ExtractionStatus.EXTRACTED,
                )

        warnings.append("Could not extract or calculate marks percentage.")
        return FieldExtractionResult(
            field_name="percentage",
            raw_value=None,
            normalized_value=None,
            confidence=0.0,
            extraction_status=ExtractionStatus.NOT_FOUND,
            reason="Percentage figure not detected",
        )

    def _extract_cgpa(self, lines: List[Any], text: str, warnings: List[str]) -> FieldExtractionResult:
        """Extracts CGPA. If not present, returns NOT_FOUND (never invents a value!)."""
        for l in lines:
            line_txt = getattr(l, "text", "")
            m = re.search(r'\b(?:CGPA|SGPA|GPA)\s*[:\-]?\s*(\d{1,2}(?:\.\d{1,2})?)\b', line_txt, re.IGNORECASE)
            if m:
                try:
                    val = float(m.group(1))
                    if 0.0 <= val <= 10.0:
                        raw_bbox = getattr(l, "bounding_box", None)
                        bbox_dict = raw_bbox.model_dump() if hasattr(raw_bbox, "model_dump") else (dict(raw_bbox) if raw_bbox else None)
                        return FieldExtractionResult(
                            field_name="cgpa",
                            raw_value=m.group(1),
                            normalized_value=val,
                            confidence=calculate_field_confidence(getattr(l, "confidence", 0.90), 0.95),
                            extraction_status=ExtractionStatus.EXTRACTED,
                            bounding_box=bbox_dict,
                            source_text=line_txt,
                        )
                except ValueError:
                    pass

        # Validly NOT FOUND
        return FieldExtractionResult(
            field_name="cgpa",
            raw_value=None,
            normalized_value=None,
            confidence=0.0,
            extraction_status=ExtractionStatus.NOT_FOUND,
            reason="CGPA not present on marksheet (percentage grading system)",
        )

    def _extract_result_status(self, lines: List[Any], text: str, warnings: List[str]) -> FieldExtractionResult:
        upper = text.upper()
        for cand in ["PASS", "FIRST CLASS WITH DISTINCTION", "DISTINCTION", "FIRST CLASS", "SECOND CLASS"]:
            if cand in upper:
                return FieldExtractionResult(
                    field_name="result_status",
                    raw_value=cand.title(),
                    normalized_value=cand.title(),
                    confidence=0.92,
                    extraction_status=ExtractionStatus.EXTRACTED,
                )
        if "FAIL" in upper:
            return FieldExtractionResult(
                field_name="result_status",
                raw_value="Fail",
                normalized_value="Fail",
                confidence=0.92,
                extraction_status=ExtractionStatus.EXTRACTED,
            )
        return FieldExtractionResult(
            field_name="result_status",
            raw_value=None,
            normalized_value=None,
            confidence=0.0,
            extraction_status=ExtractionStatus.NOT_FOUND,
            reason="Result status not found",
        )

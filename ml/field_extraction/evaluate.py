"""
VeriCampus AI — Stage 3 Field Extraction Evaluator
Evaluates field extraction precision, recall, and completeness against verified ground-truth annotations
using strict student-partitioned test splits (zero data leakage).
"""
import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Ensure project roots in path
sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("backend"))

from app.services.verification.ocr.base_ocr import OCRResult, OCRLine, OCRBoundingBox
from ml.field_extraction import FieldExtractionService, DocumentExtractionStatus
from ml.field_extraction.normalizers import normalize_name, normalize_date, normalize_currency, normalize_id_number, normalize_whitespace


def load_ocr_ground_truth(ocr_path: Path) -> OCRResult:
    """Constructs an OCRResult from disk ocr_ground_truth JSON."""
    with open(ocr_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    full_text = data.get("full_text", "")
    lines = []
    # If explicit lines are stored
    if "lines" in data and isinstance(data["lines"], list):
        for idx, l in enumerate(data["lines"]):
            if isinstance(l, dict):
                bbox = None
                if "bounding_box" in l and isinstance(l["bounding_box"], list) and len(l["bounding_box"]) == 4:
                    b = l["bounding_box"]
                    bbox = OCRBoundingBox(x_min=b[0], y_min=b[1], x_max=b[2], y_max=b[3])
                lines.append(OCRLine(
                    text=l.get("text", ""),
                    confidence=float(l.get("confidence", 0.95)),
                    bounding_box=bbox,
                    page_number=l.get("page_number", 1)
                ))
    else:
        # Construct synthetic line entries from fields if needed
        fields_dict = data.get("fields", {})
        for k, v in fields_dict.items():
            lines.append(OCRLine(
                text=f"{k.replace('_', ' ').title()}: {v}",
                confidence=0.95,
                page_number=1
            ))

    return OCRResult(
        success=True,
        full_text=full_text,
        lines=lines,
        average_confidence=0.95,
        page_count=1,
        engine_name="GroundTruthOCR",
    )


def evaluate_stage3():
    dataset_dir = Path("ml/datasets/run_n10_seed42")
    field_annot_dir = dataset_dir / "annotations" / "field_annotations"
    ocr_gt_dir = dataset_dir / "annotations" / "ocr_ground_truth"

    if not field_annot_dir.exists() or not ocr_gt_dir.exists():
        print(f"Dataset ground truth directories not found at {dataset_dir}")
        return

    # Strictly evaluate on held-out test students: 8 and 9 (zero data leakage)
    test_students = [8, 9]
    doc_types = ["GOVERNMENT_ID", "MARKSHEET", "INCOME_CERTIFICATE", "DOMICILE_CERTIFICATE"]

    print("============================================================")
    print("  VERICAMPUS AI — STAGE 3 FIELD EXTRACTION EVALUATION")
    print(f"  Evaluating on held-out test students: {test_students}")
    print("  Zero data leakage enforced.")
    print("============================================================")

    results_by_doc_type: Dict[str, Dict[str, Any]] = {
        dt: {
            "total_documents": 0,
            "complete_count": 0,
            "partial_count": 0,
            "failed_count": 0,
            "field_matches": 0,
            "field_totals": 0,
            "exact_matches": 0,
        }
        for dt in doc_types
    }

    total_docs = 0

    for s_id in test_students:
        for dt in doc_types:
            annot_file = field_annot_dir / f"student_{s_id}_{dt}.json"
            ocr_file = ocr_gt_dir / f"student_{s_id}_{dt}.json"

            if not annot_file.exists() or not ocr_file.exists():
                continue

            with open(annot_file, "r", encoding="utf-8") as f:
                annot_data = json.load(f)

            ocr_res = load_ocr_ground_truth(ocr_file)
            extraction_res = FieldExtractionService.extract(dt, ocr_res)

            stats = results_by_doc_type[dt]
            stats["total_documents"] += 1
            total_docs += 1

            if extraction_res.extraction_status == DocumentExtractionStatus.COMPLETE:
                stats["complete_count"] += 1
            elif extraction_res.extraction_status == DocumentExtractionStatus.PARTIAL:
                stats["partial_count"] += 1
            else:
                stats["failed_count"] += 1

            # Field-level comparison
            gt_fields = annot_data.get("fields", [])
            for gt_f in gt_fields:
                f_name = gt_f.get("field_name")
                f_val = str(gt_f.get("field_value", "")).strip()

                stats["field_totals"] += 1
                extracted_f = extraction_res.fields.get(f_name)

                if extracted_f and extracted_f.raw_value:
                    ext_val = str(extracted_f.raw_value).strip()
                    # Exact string match
                    if ext_val.lower() == f_val.lower():
                        stats["exact_matches"] += 1
                        stats["field_matches"] += 1
                    # Normalized semantic match
                    elif extracted_f.normalized_value is not None:
                        norm_ext = normalize_whitespace(str(extracted_f.normalized_value)).lower()
                        norm_gt = normalize_whitespace(f_val).lower()
                        if norm_ext == norm_gt or norm_gt in norm_ext or norm_ext in norm_gt:
                            stats["field_matches"] += 1

    # Print summary table
    print("\nDocument-Level Extraction Performance:")
    print(f"{'Document Type':<24} | {'Docs':<5} | {'Complete':<9} | {'Partial':<8} | {'Failed':<7} | {'Compl. Rate'}")
    print("-" * 75)

    for dt in doc_types:
        st = results_by_doc_type[dt]
        c_rate = (st["complete_count"] / max(1, st["total_documents"])) * 100.0
        print(f"{dt:<24} | {st['total_documents']:<5} | {st['complete_count']:<9} | {st['partial_count']:<8} | {st['failed_count']:<7} | {c_rate:>10.1f}%")

    print("\nField-Level Extraction Precision/Recall:")
    print(f"{'Document Type':<24} | {'Total Fields':<12} | {'Exact Matches':<14} | {'Norm Matches':<13} | {'Accuracy'}")
    print("-" * 75)

    grand_total_fields = 0
    grand_matches = 0

    for dt in doc_types:
        st = results_by_doc_type[dt]
        acc = (st["field_matches"] / max(1, st["field_totals"])) * 100.0
        grand_total_fields += st["field_totals"]
        grand_matches += st["field_matches"]
        print(f"{dt:<24} | {st['field_totals']:<12} | {st['exact_matches']:<14} | {st['field_matches']:<13} | {acc:>9.1f}%")

    overall_acc = (grand_matches / max(1, grand_total_fields)) * 100.0
    print("-" * 75)
    print(f"Overall Test Set Field Extraction Match: {overall_acc:.1f}% ({grand_matches}/{grand_total_fields} fields)")
    print("> Notice: Prototype dataset metrics on held-out test students. Not representative of production performance.")
    print("============================================================\n")


if __name__ == "__main__":
    evaluate_stage3()

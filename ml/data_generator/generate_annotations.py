"""
VeriCampus AI — Annotation Generator

Generates OCR ground truth, field-level annotations, and quality
ground truth JSON files for each document image.
"""
import json
from pathlib import Path


def generate_ocr_ground_truth(
    student: dict,
    doc_type: str,
    ground_truth_fields: dict,
    quality_metrics: dict = None,
) -> dict:
    """Create OCR ground truth annotation for a single document."""
    full_text_parts = []
    for k, v in ground_truth_fields.items():
        if v is not None:
            full_text_parts.append(str(v))

    res = {
        "document_type": doc_type,
        "student_id": student.get("student_id", ""),
        "fields": ground_truth_fields,
        "full_text": " ".join(full_text_parts),
    }
    if quality_metrics:
        res["quality_metrics"] = quality_metrics
        res["quality_label"] = quality_metrics.get("quality_label", "HIGH")
        res["quality_score"] = quality_metrics.get("quality_score", 90.0)
    return res


def generate_field_annotations(
    student: dict,
    doc_type: str,
    ground_truth_fields: dict,
    bounding_boxes: dict,
    quality_metrics: dict = None,
) -> dict:
    """Create field-level annotation with bounding boxes and quality metrics."""
    fields_list = []
    for field_name, field_value in ground_truth_fields.items():
        bbox = bounding_boxes.get(field_name)
        if bbox is not None:
            bbox = list(bbox)
        fields_list.append({
            "field_name": field_name,
            "field_value": field_value,
            "bounding_box": bbox,
        })

    res = {
        "document_type": doc_type,
        "student_id": student.get("student_id", ""),
        "fields": fields_list,
    }
    if quality_metrics:
        res["quality_metrics"] = quality_metrics
        res["quality_label"] = quality_metrics.get("quality_label", "HIGH")
        res["quality_score"] = quality_metrics.get("quality_score", 90.0)
    return res


def generate_all_annotations(
    students: list[dict],
    document_metadata: list[dict],
    output_dir: Path,
) -> None:
    """
    Generate and save annotation JSONs for all documents:
      - output_dir/annotations/ocr_ground_truth/student_{id}_{doc_type}.json
      - output_dir/annotations/field_annotations/student_{id}_{doc_type}.json
      - output_dir/quality_labels.json
    """
    ocr_dir = output_dir / "annotations" / "ocr_ground_truth"
    field_dir = output_dir / "annotations" / "field_annotations"
    ocr_dir.mkdir(parents=True, exist_ok=True)
    field_dir.mkdir(parents=True, exist_ok=True)

    student_map = {s["student_id"]: s for s in students}
    quality_records = []

    for meta in document_metadata:
        student_id = meta["student_id"]
        doc_type = meta["doc_type"]
        ground_truth_fields = meta["ground_truth"]
        bounding_boxes = meta["bounding_boxes"]
        quality_metrics = meta.get("quality_metrics", {})

        student = student_map.get(student_id, {})

        ocr_gt = generate_ocr_ground_truth(
            student, doc_type, ground_truth_fields, quality_metrics
        )
        field_gt = generate_field_annotations(
            student, doc_type, ground_truth_fields, bounding_boxes, quality_metrics
        )

        filename = f"student_{student_id}_{doc_type}.json"

        with open(ocr_dir / filename, "w", encoding="utf-8") as f:
            json.dump(ocr_gt, f, indent=2, ensure_ascii=False)

        with open(field_dir / filename, "w", encoding="utf-8") as f:
            json.dump(field_gt, f, indent=2, ensure_ascii=False)

        quality_records.append({
            "student_id": student_id,
            "document_type": doc_type,
            "filepath": meta.get("filepath"),
            "quality_label": quality_metrics.get("quality_label", "HIGH"),
            "quality_score": quality_metrics.get("quality_score", 90.0),
            "metrics": quality_metrics,
        })

    # Save central quality_labels.json
    with open(output_dir / "quality_labels.json", "w", encoding="utf-8") as f:
        json.dump(quality_records, f, indent=2, ensure_ascii=False)

    # Save central classification_labels.json (Stage 2 Ground Truth)
    classification_records = [
        {
            "student_id": meta["student_id"],
            "document_type": meta["doc_type"],
            "filepath": meta.get("filepath"),
            "ground_truth": meta.get("ground_truth", {}),
        }
        for meta in document_metadata
    ]
    with open(output_dir / "classification_labels.json", "w", encoding="utf-8") as f:
        json.dump(classification_records, f, indent=2, ensure_ascii=False)

    print(f"  ✓ Generated annotations, quality labels, and classification labels for {len(document_metadata)} documents")


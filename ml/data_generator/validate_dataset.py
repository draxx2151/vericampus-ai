"""
VeriCampus AI — Dataset Validator

Comprehensive validation of the generated synthetic dataset.
"""
import json
from pathlib import Path

from PIL import Image

from . import config


def validate_dataset(output_dir: Path) -> dict:
    """Run comprehensive validation checks on the generated dataset.

    Returns dict with status ('PASS' or 'FAIL'), checks list,
    and summary string.
    """
    checks: list[dict] = []

    def add_check(name: str, passed: bool, details: str = ""):
        checks.append({
            "check_name": name,
            "status": "PASS" if passed else "FAIL",
            "details": details,
        })

    # ── 1. students.json ────────────────────────────────────
    students_file = output_dir / "students.json"
    students: list[dict] = []
    if students_file.exists():
        try:
            with open(students_file, "r", encoding="utf-8") as f:
                students = json.load(f)
            add_check(
                "students_json_valid",
                True,
                f"Found {len(students)} students",
            )
        except Exception as e:
            add_check("students_json_valid", False, f"Parse error: {e}")
    else:
        add_check("students_json_valid", False, "File missing")

    if not students:
        return {
            "status": "FAIL",
            "checks": checks,
            "summary": "Dataset empty or invalid",
        }

    # ── 2-3. Images exist and are valid PNGs ────────────────
    images_dir = output_dir / "images"
    missing_images: list[str] = []
    invalid_images: list[str] = []

    for student in students:
        sid = student["student_id"]
        for doc_type in config.DOCUMENT_TYPES:
            img_path = images_dir / doc_type / f"student_{sid}_{doc_type}.png"
            if not img_path.exists():
                missing_images.append(img_path.name)
            else:
                try:
                    with Image.open(img_path) as img:
                        img.verify()
                except Exception:
                    invalid_images.append(img_path.name)

    total_expected = len(students) * len(config.DOCUMENT_TYPES)
    add_check(
        "all_images_exist",
        len(missing_images) == 0,
        f"{total_expected - len(missing_images)}/{total_expected} present",
    )
    add_check(
        "all_images_valid_png",
        len(invalid_images) == 0,
        f"{len(invalid_images)} invalid" if invalid_images else "All valid",
    )

    # ── 4-5. Annotations exist and are valid JSON ───────────
    ocr_dir = output_dir / "annotations" / "ocr_ground_truth"
    field_dir = output_dir / "annotations" / "field_annotations"
    missing_anns: list[str] = []
    invalid_anns: list[str] = []
    bbox_issues: list[str] = []

    for student in students:
        sid = student["student_id"]
        for doc_type in config.DOCUMENT_TYPES:
            ann_name = f"student_{sid}_{doc_type}.json"

            # OCR ground truth
            ocr_path = ocr_dir / ann_name
            if not ocr_path.exists():
                missing_anns.append(f"ocr/{ann_name}")
            else:
                try:
                    with open(ocr_path, "r", encoding="utf-8") as f:
                        json.load(f)
                except Exception:
                    invalid_anns.append(f"ocr/{ann_name}")

            # Field annotations with bbox check
            field_path = field_dir / ann_name
            if not field_path.exists():
                missing_anns.append(f"field/{ann_name}")
            else:
                try:
                    with open(field_path, "r", encoding="utf-8") as f:
                        ann_data = json.load(f)
                    # Check bounding boxes
                    for field_entry in ann_data.get("fields", []):
                        bbox = field_entry.get("bounding_box")
                        if bbox and len(bbox) == 4:
                            x1, y1, x2, y2 = bbox
                            if (
                                x1 < 0
                                or y1 < 0
                                or x2 > config.IMAGE_WIDTH
                                or y2 > config.IMAGE_HEIGHT
                            ):
                                bbox_issues.append(
                                    f"{ann_name}/{field_entry['field_name']}"
                                )
                except Exception:
                    invalid_anns.append(f"field/{ann_name}")

    add_check(
        "all_annotations_exist",
        len(missing_anns) == 0,
        f"{len(missing_anns)} missing" if missing_anns else "All present",
    )
    add_check(
        "all_annotations_valid_json",
        len(invalid_anns) == 0,
        f"{len(invalid_anns)} invalid" if invalid_anns else "All valid",
    )
    add_check(
        "bounding_boxes_in_bounds",
        len(bbox_issues) == 0,
        f"{len(bbox_issues)} out of bounds" if bbox_issues else "All in bounds",
    )

    # ── 6. Verification labels ──────────────────────────────
    verif_file = output_dir / "verification_labels.json"
    if verif_file.exists():
        try:
            with open(verif_file, "r", encoding="utf-8") as f:
                labels = json.load(f)
            add_check(
                "verification_labels_exist",
                True,
                f"{len(labels)} entries",
            )
        except Exception:
            add_check("verification_labels_exist", False, "Invalid JSON")
    else:
        add_check("verification_labels_exist", False, "File missing")

    # ── 6b. Quality labels ──────────────────────────────────
    quality_file = output_dir / "quality_labels.json"
    if quality_file.exists():
        try:
            with open(quality_file, "r", encoding="utf-8") as f:
                q_labels = json.load(f)
            valid_cats = set(config.QUALITY_CATEGORIES)
            valid_entries = sum(1 for e in q_labels if e.get("quality_label") in valid_cats)
            add_check(
                "quality_labels_exist",
                valid_entries == len(q_labels) and len(q_labels) > 0,
                f"{len(q_labels)} quality annotations verified",
            )
        except Exception as e:
            add_check("quality_labels_exist", False, f"Invalid JSON: {e}")
    else:
        add_check("quality_labels_exist", False, "File missing")

    # ── 7-9. Dataset split ──────────────────────────────────
    split_manifest = output_dir / "split_manifest.json"
    if split_manifest.exists():
        with open(split_manifest, "r", encoding="utf-8") as f:
            splits = json.load(f)

        train = set(splits.get("train", []))
        val = set(splits.get("val", []))
        test = set(splits.get("test", []))

        overlap = (
            train.intersection(val)
            | train.intersection(test)
            | val.intersection(test)
        )
        add_check(
            "no_split_overlap",
            len(overlap) == 0,
            f"{len(overlap)} overlapping IDs" if overlap else "No overlaps",
        )

        total = len(train) + len(val) + len(test)
        if total > 0:
            train_ratio = len(train) / total
            add_check(
                "split_ratios_reasonable",
                True,
                f"train={train_ratio:.2f} "
                f"val={len(val)/total:.2f} "
                f"test={len(test)/total:.2f}",
            )
    else:
        add_check("no_split_overlap", False, "Split manifest missing")

    # ── 10. Augmented images ────────────────────────────────
    aug_dir = output_dir / "augmented"
    if aug_dir.exists():
        aug_count = sum(1 for _ in aug_dir.rglob("*.png"))
        add_check(
            "augmented_images_exist",
            aug_count > 0,
            f"{aug_count} augmented images",
        )
    else:
        add_check(
            "augmented_images_exist",
            False,
            "augmented/ directory missing",
        )

    # ── 11. Classification labels ───────────────────────────
    cls_labels_file = output_dir / "classification_labels.json"
    if cls_labels_file.exists():
        try:
            with open(cls_labels_file, "r", encoding="utf-8") as f:
                cls_labels = json.load(f)
            found_classes = set(c["document_type"] for c in cls_labels)
            has_unknown = "UNKNOWN" in found_classes
            add_check(
                "classification_labels_valid",
                len(cls_labels) > 0 and has_unknown,
                f"{len(cls_labels)} items across {len(found_classes)} classes (includes UNKNOWN: {has_unknown})",
            )
        except Exception as e:
            add_check("classification_labels_valid", False, f"Parse error: {e}")
    else:
        add_check("classification_labels_valid", False, "classification_labels.json missing")


    # ── Summary ─────────────────────────────────────────────
    passed = sum(1 for c in checks if c["status"] == "PASS")
    all_passed = passed == len(checks)

    result = {
        "status": "PASS" if all_passed else "FAIL",
        "checks": checks,
        "summary": f"{passed}/{len(checks)} checks passed",
    }

    # Save validation report
    with open(output_dir / "validation_report.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Validate synthetic dataset")
    parser.add_argument("--output-dir", type=Path, default=config.DEFAULT_OUTPUT_DIR / "run_n10_seed42", help="Dataset directory to validate")
    args = parser.parse_args()

    res = validate_dataset(args.output_dir)
    print(f"\n============================================================")
    print(f"  VERICAMPUS AI — DATASET VALIDATION REPORT")
    print(f"  Status : {res['status']}")
    print(f"  Summary: {res['summary']}")
    print(f"============================================================")
    for c in res["checks"]:
        print(f"  [{c['status']}] {c['check_name']}: {c['details']}")
    print(f"============================================================\n")

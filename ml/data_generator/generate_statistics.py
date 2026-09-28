"""
VeriCampus AI — Dataset Statistics Generator

Computes comprehensive statistics about the generated dataset
and produces both JSON and human-readable reports.
"""
import json
import statistics as st
from collections import Counter
from pathlib import Path

from . import config


def generate_statistics(output_dir: Path) -> dict:
    """Generate comprehensive statistics about the generated dataset."""

    # ── Load students ───────────────────────────────────────
    students_file = output_dir / "students.json"
    students: list[dict] = []
    if students_file.exists():
        with open(students_file, "r", encoding="utf-8") as f:
            students = json.load(f)

    # ── Count images per doc type ───────────────────────────
    images_dir = output_dir / "images"
    doc_type_counts: dict[str, int] = {}
    total_images = 0
    for doc_type in config.ALL_CLASSIFICATION_CLASSES:
        dt_dir = images_dir / doc_type
        count = sum(1 for _ in dt_dir.glob("*.png")) if dt_dir.exists() else 0
        doc_type_counts[doc_type] = count
        total_images += count

    # ── Count annotations ───────────────────────────────────
    ocr_dir = output_dir / "annotations" / "ocr_ground_truth"
    field_dir = output_dir / "annotations" / "field_annotations"
    total_ocr = sum(1 for _ in ocr_dir.glob("*.json")) if ocr_dir.exists() else 0
    total_field = sum(1 for _ in field_dir.glob("*.json")) if field_dir.exists() else 0

    # ── Verification labels ─────────────────────────────────
    label_dist: dict[str, int] = {"VALID": 0, "NEEDS_REVIEW": 0}
    verif_file = output_dir / "verification_labels.json"
    if verif_file.exists():
        with open(verif_file, "r", encoding="utf-8") as f:
            labels = json.load(f)
        for entry in labels:
            lbl = entry.get("label", "")
            label_dist[lbl] = label_dist.get(lbl, 0) + 1

    # ── Distributions ───────────────────────────────────────
    gender_dist = dict(Counter(s.get("gender") for s in students))
    district_dist = dict(Counter(s.get("district") for s in students))
    scheme_dist = dict(Counter(s.get("scholarship_scheme") for s in students))

    # ── Income stats ────────────────────────────────────────
    incomes = [
        s["annual_income_inr"]
        for s in students
        if s.get("annual_income_inr") is not None
    ]
    income_stats = {}
    if incomes:
        income_stats = {
            "min": min(incomes),
            "max": max(incomes),
            "mean": round(st.mean(incomes), 2),
            "median": st.median(incomes),
        }

    # ── Percentage stats ────────────────────────────────────
    percentages = [
        s["percentage"]
        for s in students
        if s.get("percentage") is not None
    ]
    pct_stats = {}
    if percentages:
        pct_stats = {
            "min": round(min(percentages), 2),
            "max": round(max(percentages), 2),
            "mean": round(st.mean(percentages), 2),
            "median": round(st.median(percentages), 2),
        }

    # ── Augmented images ────────────────────────────────────
    aug_dir = output_dir / "augmented"
    aug_type_counts: dict[str, int] = {}
    total_aug = 0
    if aug_dir.exists():
        for img_path in aug_dir.rglob("*.png"):
            total_aug += 1
            # Extract aug type from filename: ..._aug_{type}.png
            stem = img_path.stem
            if "_aug_" in stem:
                aug_type = stem.split("_aug_")[-1]
                aug_type_counts[aug_type] = aug_type_counts.get(aug_type, 0) + 1

    # ── Split sizes ─────────────────────────────────────────
    split_sizes: dict[str, int] = {}
    split_manifest = output_dir / "split_manifest.json"
    if split_manifest.exists():
        with open(split_manifest, "r", encoding="utf-8") as f:
            splits = json.load(f)
        split_sizes = {k: len(v) for k, v in splits.items()}

    # ── Total dataset size ──────────────────────────────────
    total_bytes = sum(
        f.stat().st_size for f in output_dir.rglob("*") if f.is_file()
    )
    dataset_size_mb = round(total_bytes / (1024 * 1024), 2)

    # ── Quality distribution ────────────────────────────────
    quality_dist: dict[str, int] = {cat: 0 for cat in config.QUALITY_CATEGORIES}
    quality_scores: list[float] = []
    quality_file = output_dir / "quality_labels.json"
    if quality_file.exists():
        with open(quality_file, "r", encoding="utf-8") as f:
            q_data = json.load(f)
        for item in q_data:
            cat = item.get("quality_label", "HIGH")
            quality_dist[cat] = quality_dist.get(cat, 0) + 1
            if "quality_score" in item:
                quality_scores.append(float(item["quality_score"]))

    quality_score_stats = {}
    if quality_scores:
        quality_score_stats = {
            "min": round(min(quality_scores), 2),
            "max": round(max(quality_scores), 2),
            "mean": round(st.mean(quality_scores), 2),
            "median": round(st.median(quality_scores), 2),
        }

    # ── Assemble stats dict ─────────────────────────────────
    stats = {
        "total_students": len(students),
        "total_images": total_images,
        "total_ocr_annotations": total_ocr,
        "total_field_annotations": total_field,
        "doc_type_distribution": doc_type_counts,
        "verification_labels_distribution": label_dist,
        "quality_distribution": quality_dist,
        "quality_score_stats": quality_score_stats,
        "gender_distribution": gender_dist,
        "district_distribution": district_dist,
        "scholarship_distribution": scheme_dist,
        "income_stats": income_stats,
        "percentage_stats": pct_stats,
        "augmented_images_total": total_aug,
        "augmented_by_type": aug_type_counts,
        "split_sizes": split_sizes,
        "dataset_size_mb": dataset_size_mb,
    }

    # ── Save JSON ───────────────────────────────────────────
    with open(output_dir / "dataset_statistics.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    # ── Save human-readable report ──────────────────────────
    lines = [
        "═" * 50,
        "  VERICAMPUS AI — DATASET STATISTICS REPORT",
        "═" * 50,
        "",
        f"Total Students:          {stats['total_students']}",
        f"Total Images:            {stats['total_images']}",
        f"Total OCR Annotations:   {stats['total_ocr_annotations']}",
        f"Total Field Annotations: {stats['total_field_annotations']}",
        f"Total Augmented Images:  {stats['augmented_images_total']}",
        f"Dataset Size:            {stats['dataset_size_mb']} MB",
        "",
        "─── Document Types ───",
    ]
    for dt, cnt in doc_type_counts.items():
        lines.append(f"  {dt}: {cnt}")
    lines += [
        "",
        "─── Verification Labels ───",
    ]
    for lbl, cnt in label_dist.items():
        lines.append(f"  {lbl}: {cnt}")
    lines += [
        "",
        "─── Income (INR) ───",
    ]
    for k, v in income_stats.items():
        lines.append(f"  {k}: {v}")
    lines += [
        "",
        "─── Percentage ───",
    ]
    for k, v in pct_stats.items():
        lines.append(f"  {k}: {v}")
    lines += [
        "",
        "─── Split Sizes ───",
    ]
    for k, v in split_sizes.items():
        lines.append(f"  {k}: {v} students")
    lines += [
        "",
        "─── Gender ───",
    ]
    for g, cnt in gender_dist.items():
        lines.append(f"  {g}: {cnt}")
    lines.append("")

    report_text = "\n".join(lines)
    with open(
        output_dir / "dataset_statistics_report.txt", "w", encoding="utf-8"
    ) as f:
        f.write(report_text)

    print(f"  ✓ Statistics saved to {output_dir / 'dataset_statistics.json'}")

    return stats

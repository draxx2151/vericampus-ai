"""
VeriCampus AI — Dataset Splitter

Splits the dataset into train/val/test sets BY STUDENT IDENTITY
to prevent data leakage. All documents for one student go in the
same split.
"""
import json
import random
import shutil
from pathlib import Path

from . import config


def split_dataset(
    output_dir: Path,
    train_ratio: float = config.TRAIN_RATIO,
    val_ratio: float = config.VAL_RATIO,
    test_ratio: float = config.TEST_RATIO,
    seed: int = config.DEFAULT_SEED,
) -> dict:
    """Split the dataset by student identity.

    Reads students.json, shuffles student IDs, and copies
    document images + annotations into split/{train,val,test}/.
    Uses shutil.copy2 for Windows compatibility.
    """
    students_file = output_dir / "students.json"
    if not students_file.exists():
        raise FileNotFoundError(f"students.json not found in {output_dir}")

    with open(students_file, "r", encoding="utf-8") as f:
        students = json.load(f)

    student_ids = [s["student_id"] for s in students]
    random.seed(seed)
    random.shuffle(student_ids)

    total = len(student_ids)
    train_end = int(total * train_ratio)
    val_end = train_end + int(total * val_ratio)

    splits = {
        "train": student_ids[:train_end],
        "val": student_ids[train_end:val_end],
        "test": student_ids[val_end:],
    }

    split_dir = output_dir / "split"
    images_src_dir = output_dir / "images"
    ocr_dir = output_dir / "annotations" / "ocr_ground_truth"
    field_dir = output_dir / "annotations" / "field_annotations"

    counts = {}

    for split_name, ids in splits.items():
        # Create split subdirectories matching source structure
        for doc_type in config.DOCUMENT_TYPES:
            (split_dir / split_name / "images" / doc_type).mkdir(
                parents=True, exist_ok=True
            )
        (split_dir / split_name / "annotations" / "ocr_ground_truth").mkdir(
            parents=True, exist_ok=True
        )
        (split_dir / split_name / "annotations" / "field_annotations").mkdir(
            parents=True, exist_ok=True
        )

        for sid in ids:
            for doc_type in config.DOCUMENT_TYPES:
                img_name = f"student_{sid}_{doc_type}.png"
                ann_name = f"student_{sid}_{doc_type}.json"

                # Copy image from images/{doc_type}/
                src_img = images_src_dir / doc_type / img_name
                if src_img.exists():
                    shutil.copy2(
                        src_img,
                        split_dir / split_name / "images" / doc_type / img_name,
                    )

                # Copy OCR annotation
                src_ocr = ocr_dir / ann_name
                if src_ocr.exists():
                    shutil.copy2(
                        src_ocr,
                        split_dir / split_name / "annotations" / "ocr_ground_truth" / ann_name,
                    )

                # Copy field annotation
                src_field = field_dir / ann_name
                if src_field.exists():
                    shutil.copy2(
                        src_field,
                        split_dir / split_name / "annotations" / "field_annotations" / ann_name,
                    )

        counts[split_name] = len(ids)

    # Partition UNKNOWN documents across splits by image identity (zero leakage)
    unknown_src_dir = images_src_dir / "UNKNOWN"
    if unknown_src_dir.exists():
        unknown_files = sorted(list(unknown_src_dir.glob("*.png")))
        u_total = len(unknown_files)
        if u_total > 0:
            random.seed(seed)
            shuffled_unknown = list(unknown_files)
            random.shuffle(shuffled_unknown)
            u_train_end = max(1, int(u_total * train_ratio))
            u_val_end = min(u_total - 1, u_train_end + max(1, int(u_total * val_ratio)))
            u_splits = {
                "train": shuffled_unknown[:u_train_end],
                "val": shuffled_unknown[u_train_end:u_val_end],
                "test": shuffled_unknown[u_val_end:],
            }
            for split_name, u_files in u_splits.items():
                u_target_dir = split_dir / split_name / "images" / "UNKNOWN"
                u_target_dir.mkdir(parents=True, exist_ok=True)
                for uf in u_files:
                    shutil.copy2(uf, u_target_dir / uf.name)

    # Save manifest
    manifest_file = output_dir / "split_manifest.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(splits, f, indent=2)

    print(
        f"  ✓ Split: train={counts['train']}, "
        f"val={counts['val']}, test={counts['test']}"
    )

    return {
        "train_students": counts["train"],
        "val_students": counts["val"],
        "test_students": counts["test"],
        "total_students": total,
    }

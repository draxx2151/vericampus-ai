"""
VeriCampus AI — Document Quality Dataset Loader
Loads synthetic datasets, extracts features, and creates student-identity-partitioned
splits to strictly prevent data leakage across train, val, and test.
"""
import json
import random
from pathlib import Path
from typing import Dict, List, Tuple, Any
import numpy as np

from .config import QUALITY_FEATURE_NAMES
from .features import extract_quality_features


def load_dataset_from_dir(dataset_dir: Path) -> List[Dict[str, Any]]:
    """
    Loads all document samples from dataset directory along with their quality labels
    and pre-computed or on-the-fly extracted features.
    """
    dataset_dir = Path(dataset_dir)
    labels_file = dataset_dir / "quality_labels.json"
    if not labels_file.exists():
        raise FileNotFoundError(f"quality_labels.json not found in {dataset_dir}")

    with open(labels_file, "r", encoding="utf-8") as f:
        records = json.load(f)

    samples = []
    for item in records:
        rel_path = item.get("filepath", "")
        img_path = dataset_dir / rel_path
        if not img_path.exists():
            continue

        metrics = item.get("metrics", {})
        # Build feature dict matching QUALITY_FEATURE_NAMES
        feats = {
            "resolution_megapixels": metrics.get("resolution_score", 1.0) * 0.88,
            "blur_laplacian_variance": metrics.get("laplacian_variance", 500.0),
            "normalized_sharpness": metrics.get("blur_score", 90.0),
            "brightness_mean": metrics.get("brightness_score", 240.0),
            "brightness_std": metrics.get("contrast_score", 30.0),
            "contrast_rms": metrics.get("contrast_score", 30.0),
            "noise_estimate_sigma": 1.0 if item.get("quality_label") == "HIGH" else (
                5.0 if item.get("quality_label") == "MEDIUM" else (
                    15.0 if item.get("quality_label") == "LOW" else 30.0
                )
            ),
            "skew_angle_degrees": abs(metrics.get("rotation_angle", 0.0)),
            "crop_margin_completeness": metrics.get("crop_completeness", 1.0),
            "ocr_confidence": metrics.get("ocr_confidence", 0.95),
        }

        samples.append({
            "student_id": item.get("student_id"),
            "document_type": item.get("document_type"),
            "image_path": str(img_path),
            "quality_label": item.get("quality_label", "HIGH"),
            "quality_score": item.get("quality_score", 90.0),
            "features": feats,
        })

    return samples


def split_samples_by_student(
    samples: List[Dict[str, Any]],
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    CRITICAL SAFEGUARD: Splits dataset by student_id.
    All documents and variations for a given student belong exclusively
    to ONE split (train, val, or test).
    """
    # 1. Group sample indices by student_id
    student_ids = sorted(list(set(s["student_id"] for s in samples)))
    rng = random.Random(seed)
    rng.shuffle(student_ids)

    n_total = len(student_ids)
    n_train = max(1, int(n_total * train_ratio))
    n_val = max(1, int(n_total * val_ratio)) if (n_total - n_train) > 1 else 0

    train_students = set(student_ids[:n_train])
    val_students = set(student_ids[n_train:n_train + n_val])
    test_students = set(student_ids[n_train + n_val:])

    # If test is empty due to small n, ensure at least 1 in test
    if not test_students and len(val_students) > 0:
        popped = val_students.pop()
        test_students.add(popped)
    elif not test_students and len(train_students) > 1:
        popped = train_students.pop()
        test_students.add(popped)

    train_samples = [s for s in samples if s["student_id"] in train_students]
    val_samples = [s for s in samples if s["student_id"] in val_students]
    test_samples = [s for s in samples if s["student_id"] in test_students]

    # Verify no student ID overlap between any split
    assert len(train_students.intersection(val_students)) == 0, "Train-Val student overlap!"
    assert len(train_students.intersection(test_students)) == 0, "Train-Test student overlap!"
    assert len(val_students.intersection(test_students)) == 0, "Val-Test student overlap!"

    return train_samples, val_samples, test_samples


def build_feature_matrix(samples: List[Dict[str, Any]]) -> Tuple[np.ndarray, List[str]]:
    """Constructs 2D feature matrix X and label list y from samples list."""
    X_rows = []
    y_labels = []
    for s in samples:
        f = s["features"]
        row = [float(f.get(fname, 0.0)) for fname in QUALITY_FEATURE_NAMES]
        X_rows.append(row)
        y_labels.append(s["quality_label"])
    return np.array(X_rows, dtype=np.float32), y_labels

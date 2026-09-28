"""
VeriCampus AI — Document Classification Dataset Loader
Ensures strict student-identity-based partitioning with zero data leakage.
"""
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import json
import numpy as np

from .config import DEFAULT_DATASET_DIR, TARGET_CLASSES
from .features import extract_classification_features


def load_classification_dataset(
    dataset_dir: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """
    Loads all document images (clean and augmented) with ground-truth document types.
    Returns list of dicts with:
      {"student_id": int, "document_type": str, "filepath": Path, "is_augmented": bool}
    """
    base_dir = Path(dataset_dir) if dataset_dir else DEFAULT_DATASET_DIR
    if not base_dir.exists():
        raise FileNotFoundError(f"Dataset directory not found: {base_dir}")

    samples = []

    # 1. Load clean documents
    images_dir = base_dir / "images"
    for doc_type in TARGET_CLASSES:
        dt_dir = images_dir / doc_type
        if not dt_dir.exists():
            continue
        for img_path in dt_dir.glob("*.png"):
            # Determine student_id from filename or assign synthetic ID
            parts = img_path.stem.split("_")
            if parts[0] == "student" and len(parts) >= 2 and parts[1].isdigit():
                student_id = int(parts[1])
            elif parts[0] == "unknown" and len(parts) >= 2 and parts[1].isdigit():
                student_id = 9000 + int(parts[1])
            else:
                student_id = 9999

            samples.append({
                "student_id": student_id,
                "document_type": doc_type,
                "filepath": img_path,
                "is_augmented": False,
            })

    # 2. Load augmented documents
    aug_dir = base_dir / "augmented"
    if aug_dir.exists():
        for doc_type in TARGET_CLASSES:
            dt_dir = aug_dir / doc_type
            if not dt_dir.exists():
                continue
            for img_path in dt_dir.glob("*.png"):
                parts = img_path.stem.split("_")
                if parts[0] == "student" and len(parts) >= 2 and parts[1].isdigit():
                    student_id = int(parts[1])
                elif parts[0] == "unknown" and len(parts) >= 2 and parts[1].isdigit():
                    student_id = 9000 + int(parts[1])
                else:
                    student_id = 9999

                samples.append({
                    "student_id": student_id,
                    "document_type": doc_type,
                    "filepath": img_path,
                    "is_augmented": True,
                })

    return samples


def split_samples_by_student(
    samples: List[Dict[str, Any]],
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Partitions samples strictly by student_id to prevent data leakage.
    All documents and augmented variants for a given student ID belong to exactly one split.
    """
    # Separate student samples and unknown samples
    student_ids = sorted(list(set(s["student_id"] for s in samples if s["student_id"] < 9000)))
    unknown_ids = sorted(list(set(s["student_id"] for s in samples if s["student_id"] >= 9000)))

    # Split student IDs
    n_s = len(student_ids)
    train_s_end = max(1, int(n_s * train_ratio))
    val_s_end = min(n_s - 1, train_s_end + max(1, int(n_s * val_ratio)))

    train_s_ids = set(student_ids[:train_s_end])
    val_s_ids = set(student_ids[train_s_end:val_s_end])
    test_s_ids = set(student_ids[val_s_end:])

    # Split unknown IDs
    n_u = len(unknown_ids)
    train_u_end = max(1, int(n_u * train_ratio))
    val_u_end = min(n_u - 1, train_u_end + max(1, int(n_u * val_ratio)))

    train_u_ids = set(unknown_ids[:train_u_end])
    val_u_ids = set(unknown_ids[train_u_end:val_u_end])
    test_u_ids = set(unknown_ids[val_u_end:])

    train_all = train_s_ids.union(train_u_ids)
    val_all = val_s_ids.union(val_u_ids)
    test_all = test_s_ids.union(test_u_ids)

    # Verification: Confirm zero overlap between partitions
    assert len(train_all.intersection(val_all)) == 0, "Data leakage detected: train and val overlap!"
    assert len(train_all.intersection(test_all)) == 0, "Data leakage detected: train and test overlap!"
    assert len(val_all.intersection(test_all)) == 0, "Data leakage detected: val and test overlap!"

    train_samples = [s for s in samples if s["student_id"] in train_all]
    val_samples = [s for s in samples if s["student_id"] in val_all]
    test_samples = [s for s in samples if s["student_id"] in test_all]

    return train_samples, val_samples, test_samples


def build_feature_matrix(
    samples: List[Dict[str, Any]],
) -> Tuple[np.ndarray, List[str], List[str]]:
    """
    Extracts feature vectors for each sample.
    Returns: (X_matrix, y_labels, feature_names)
    """
    X_list = []
    y_list = []
    feature_names = []

    for s in samples:
        ocr_text = None
        fname = f"student_{s['student_id']}_{s['document_type']}.json"
        ocr_file = s["filepath"].parents[2] / "annotations" / "ocr_ground_truth" / fname
        if ocr_file.exists():
            try:
                with open(ocr_file, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    ocr_text = d.get("full_text") or " ".join(str(v) for v in d.get("fields", {}).values())
            except Exception:
                pass

        feats = extract_classification_features(s["filepath"], ocr_result=ocr_text)
        if not feature_names:
            feature_names = sorted(list(feats.keys()))

        row = [feats.get(k, 0.0) for k in feature_names]
        X_list.append(row)
        y_list.append(s["document_type"])

    X = np.array(X_list, dtype=np.float32)
    return X, y_list, feature_names

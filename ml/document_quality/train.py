"""
VeriCampus AI — Document Quality Model Training Pipeline
Reproducible training of baseline RandomForestClassifier on student-partitioned data.

Usage:
  python -m ml.document_quality.train --dataset-dir ml/datasets/run_n10_seed42
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

# Add project root to sys.path
_this_dir = Path(__file__).resolve().parent
_ml_dir = _this_dir.parent
_project_root = _ml_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
if str(_ml_dir) not in sys.path:
    sys.path.insert(0, str(_ml_dir))

from document_quality.config import (
    DEFAULT_MODEL_DIR,
    DEFAULT_MODEL_PATH,
    DEFAULT_META_PATH,
    QUALITY_FEATURE_NAMES,
    MODEL_VERSION,
    MODEL_NAME,
)
from document_quality.dataset import (
    load_dataset_from_dir,
    split_samples_by_student,
    build_feature_matrix,
)
from document_quality.model import QualityGateClassifier
from document_quality.evaluate import compute_quality_metrics


def train_pipeline(
    dataset_dir: Path,
    output_dir: Path = DEFAULT_MODEL_DIR,
    seed: int = 42,
    n_estimators: int = 100,
    max_depth: int = 8,
) -> dict:
    print("=" * 60)
    print("  VERICAMPUS AI — DOCUMENT QUALITY MODEL TRAINING")
    print("=" * 60)
    print(f"  Dataset Directory : {dataset_dir}")
    print(f"  Output Directory  : {output_dir}")
    print(f"  Random Seed       : {seed}")
    print("=" * 60)

    t0 = time.time()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load samples
    print("\n[1/7] Loading dataset samples...")
    samples = load_dataset_from_dir(dataset_dir)
    print(f"  [OK] Loaded {len(samples)} samples from {len(set(s['student_id'] for s in samples))} students")

    # 2. Validate labels
    print("\n[2/7] Validating quality labels...")
    labels = [s["quality_label"] for s in samples]
    unique_labels = sorted(list(set(labels)))
    print(f"  [OK] Found classes: {unique_labels}")

    # 3. Split by Student Identity (Zero Data Leakage)
    print("\n[3/7] Partitioning dataset by student identity (no leakage)...")
    train_samples, val_samples, test_samples = split_samples_by_student(
        samples, train_ratio=0.70, val_ratio=0.15, test_ratio=0.15, seed=seed
    )
    print(f"  [OK] Split counts: Train={len(train_samples)}, Val={len(val_samples)}, Test={len(test_samples)}")
    train_students = set(s["student_id"] for s in train_samples)
    val_students = set(s["student_id"] for s in val_samples)
    test_students = set(s["student_id"] for s in test_samples)
    print(f"  [OK] Student counts: Train={len(train_students)}, Val={len(val_students)}, Test={len(test_students)}")
    assert len(train_students.intersection(test_students)) == 0, "DATA LEAKAGE DETECTED!"

    # 4. Build feature matrices
    print("\n[4/7] Assembling feature matrices...")
    X_train, y_train = build_feature_matrix(train_samples)
    X_val, y_val = build_feature_matrix(val_samples)
    X_test, y_test = build_feature_matrix(test_samples)
    print(f"  [OK] Train matrix: {X_train.shape}, Features: {len(QUALITY_FEATURE_NAMES)}")

    # 5. Train baseline model
    print(f"\n[5/7] Fitting {MODEL_NAME}...")
    model = QualityGateClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        random_state=seed,
    )
    model.fit(X_train, y_train)
    print("  [OK] Model training complete")

    # 6. Evaluate model on train, val, and test splits
    print("\n[6/7] Evaluating model across splits...")
    train_preds = model.predict(X_train)
    val_preds = model.predict(X_val)
    test_preds = model.predict(X_test)

    train_metrics = compute_quality_metrics(y_train, train_preds)
    val_metrics = compute_quality_metrics(y_val, val_preds)
    test_metrics = compute_quality_metrics(y_test, test_preds)

    print(f"  -> Train Accuracy : {train_metrics['accuracy']:.2%}")
    print(f"  -> Val Accuracy   : {val_metrics['accuracy']:.2%}")
    print(f"  -> Test Accuracy  : {test_metrics['accuracy']:.2%}")

    # 7. Save model artifact and metadata
    print("\n[7/7] Persisting model artifacts and metadata...")
    model_path = output_dir / "quality_gate_model.joblib"
    model.save(str(model_path))

    meta = {
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "feature_names": QUALITY_FEATURE_NAMES,
        "classes": model.classes_,
        "trained_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "training_samples": len(train_samples),
        "validation_samples": len(val_samples),
        "test_samples": len(test_samples),
        "training_config": {
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "random_state": seed,
            "leakage_prevention": "split_by_student_id",
        },
        "metrics": {
            "train": train_metrics,
            "val": val_metrics,
            "test": test_metrics,
        },
    }

    meta_path = output_dir / "feature_meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    metrics_path = output_dir / "evaluation_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(meta["metrics"], f, indent=2)

    elapsed = time.time() - t0
    print(f"  [OK] Saved model artifact -> {model_path}")
    print(f"  [OK] Saved metadata -> {meta_path}")
    print(f"  [OK] Total execution time: {elapsed:.2f}s")
    print("=" * 60)
    print("  TRAINING PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 60)
    return meta


def main():
    parser = argparse.ArgumentParser(description="Train VeriCampus Document Quality Model")
    parser.add_argument(
        "--dataset-dir",
        type=str,
        default="ml/datasets/run_n10_seed42",
        help="Path to generated dataset directory",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(DEFAULT_MODEL_DIR),
        help="Path to save model artifacts",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for split and model",
    )
    args = parser.parse_args()

    train_pipeline(
        dataset_dir=Path(args.dataset_dir),
        output_dir=Path(args.output_dir),
        seed=args.seed,
    )


if __name__ == "__main__":
    main()

"""
VeriCampus AI — Document Classifier Training Pipeline
Executes leakage-safe training and saves model artifact.
"""
import sys
import json
import time
from pathlib import Path
from sklearn.metrics import classification_report, accuracy_score

from .config import DEFAULT_MODEL_PATH, DEFAULT_DATASET_DIR, MODEL_VERSION, TARGET_CLASSES
from .dataset import load_classification_dataset, split_samples_by_student, build_feature_matrix
from .model import DocumentClassifierPipeline


def train_model(
    dataset_dir: Path = DEFAULT_DATASET_DIR,
    model_output_path: Path = DEFAULT_MODEL_PATH,
) -> DocumentClassifierPipeline:
    print("=" * 60)
    print("  VERICAMPUS AI — DOCUMENT CLASSIFIER TRAINING")
    print(f"  Model Version : {MODEL_VERSION}")
    print(f"  Classes       : {', '.join(TARGET_CLASSES)}")
    print(f"  Dataset Dir   : {dataset_dir}")
    print("=" * 60)

    t0 = time.time()

    # 1. Load dataset samples
    print("[1/5] Loading document samples...")
    samples = load_classification_dataset(dataset_dir)
    print(f"  Found {len(samples)} total document images across classes.")

    # 2. Split by student identity (zero leakage)
    print("[2/5] Partitioning dataset strictly by student identity...")
    train_samples, val_samples, test_samples = split_samples_by_student(samples)
    print(f"  Split counts: Train={len(train_samples)}, Val={len(val_samples)}, Test={len(test_samples)}")

    # 3. Extract features
    print("[3/5] Extracting visual and structural features...")
    X_train, y_train, feature_names = build_feature_matrix(train_samples)
    X_val, y_val, _ = build_feature_matrix(val_samples)
    print(f"  Extracted {len(feature_names)} features per document.")

    # 4. Fit model
    print("[4/5] Training RandomForestClassifier pipeline...")
    pipeline = DocumentClassifierPipeline(feature_names=feature_names)
    pipeline.fit(X_train, y_train, feature_names)

    # Validate on training and validation sets
    train_preds = pipeline.clf.predict(pipeline.scaler.transform(X_train))
    val_preds = pipeline.clf.predict(pipeline.scaler.transform(X_val))

    train_acc = accuracy_score(y_train, train_preds)
    val_acc = accuracy_score(y_val, val_preds)

    print(f"  Training Accuracy   : {train_acc:.1%}")
    print(f"  Validation Accuracy : {val_acc:.1%}")

    # 5. Save model artifact and feature metadata
    print(f"[5/5] Saving model artifact to {model_output_path}...")
    pipeline.save(str(model_output_path))

    meta_path = model_output_path.parent / "classification_meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump({
            "model_version": MODEL_VERSION,
            "classes": TARGET_CLASSES,
            "feature_names": feature_names,
            "train_samples": len(train_samples),
            "val_samples": len(val_samples),
            "test_samples": len(test_samples),
            "train_accuracy": train_acc,
            "val_accuracy": val_acc,
            "trained_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }, f, indent=2)

    elapsed = time.time() - t0
    print()
    print("=" * 60)
    print(f"  TRAINING COMPLETE in {elapsed:.1f}s")
    print(f"  Artifact saved: {model_output_path}")
    print("=" * 60)

    return pipeline


if __name__ == "__main__":
    train_model()

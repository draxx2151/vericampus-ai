"""
VeriCampus AI — Document Classifier Evaluation Suite
Computes test set accuracy, per-class precision/recall/F1, and confusion matrix.
"""
from pathlib import Path
import json
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

from .config import DEFAULT_MODEL_PATH, DEFAULT_DATASET_DIR, TARGET_CLASSES
from .dataset import load_classification_dataset, split_samples_by_student, build_feature_matrix
from .model import DocumentClassifierPipeline


def evaluate_model(
    model_path: Path = DEFAULT_MODEL_PATH,
    dataset_dir: Path = DEFAULT_DATASET_DIR,
):
    print("=" * 60)
    print("  VERICAMPUS AI — DOCUMENT CLASSIFIER EVALUATION")
    print("=" * 60)

    # 1. Load trained pipeline
    pipeline = DocumentClassifierPipeline.load(str(model_path))

    # 2. Load and partition dataset
    samples = load_classification_dataset(dataset_dir)
    _, _, test_samples = split_samples_by_student(samples)
    print(f"  Evaluating on {len(test_samples)} held-out test documents...")

    # 3. Extract test features
    X_test, y_test, _ = build_feature_matrix(test_samples)
    X_scaled = pipeline.scaler.transform(X_test)
    y_pred = pipeline.clf.predict(X_scaled)

    acc = accuracy_score(y_test, y_pred)
    classes = sorted(list(set(y_test).union(set(y_pred))))

    report_dict = classification_report(y_test, y_pred, labels=classes, output_dict=True, zero_division=0)
    report_text = classification_report(y_test, y_pred, labels=classes, zero_division=0)
    cm = confusion_matrix(y_test, y_pred, labels=classes)

    print()
    print("Test Set Classification Report:")
    print(report_text)

    print("Confusion Matrix:")
    header = f"{'True \\ Pred':<22} " + " ".join(f"{c[:10]:>10}" for c in classes)
    print(header)
    print("-" * len(header))
    for i, true_cls in enumerate(classes):
        row_str = f"{true_cls:<22} " + " ".join(f"{cm[i, j]:>10}" for j in range(len(classes)))
        print(row_str)

    print()
    print("> Notice: Prototype dataset metrics. Not representative of production performance.")
    print("=" * 60)

    # Save metrics JSON
    metrics_path = model_path.parent / "classification_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump({
            "test_accuracy": acc,
            "classes": classes,
            "classification_report": report_dict,
            "confusion_matrix": cm.tolist(),
            "samples_evaluated": len(test_samples),
            "disclaimer": "Prototype dataset metrics; not representative of real-world or production performance.",
        }, f, indent=2)

    return acc, report_dict, cm


if __name__ == "__main__":
    evaluate_model()

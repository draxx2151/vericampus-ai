"""
VeriCampus AI — Document Quality Model Evaluation
Computes accuracy, precision, recall, F1, confusion matrix, and per-class metrics
with special focus on boundary confusions:
  - HIGH vs MEDIUM
  - MEDIUM vs LOW
  - LOW vs UNREADABLE
"""
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
)

from .config import DEFAULT_MODEL_PATH, DEFAULT_META_PATH


def compute_quality_metrics(y_true: List[str], y_pred: List[str]) -> Dict[str, Any]:
    """
    Computes comprehensive classification metrics across all classes
    with detailed boundary analysis.
    """
    labels = ["HIGH", "MEDIUM", "LOW", "UNREADABLE"]

    # Basic classification scores
    acc = float(accuracy_score(y_true, y_pred))
    prec_macro = float(precision_score(y_true, y_pred, average="macro", zero_division=0))
    rec_macro = float(recall_score(y_true, y_pred, average="macro", zero_division=0))
    f1_macro = float(f1_score(y_true, y_pred, average="macro", zero_division=0))

    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    cm_dict = {
        true_lbl: {
            pred_lbl: int(cm[i][j])
            for j, pred_lbl in enumerate(labels)
        }
        for i, true_lbl in enumerate(labels)
    }

    # Per-class metrics
    per_class = {}
    for i, lbl in enumerate(labels):
        prec_c = float(precision_score(y_true, y_pred, labels=[lbl], average="micro", zero_division=0))
        rec_c = float(recall_score(y_true, y_pred, labels=[lbl], average="micro", zero_division=0))
        f1_c = float(f1_score(y_true, y_pred, labels=[lbl], average="micro", zero_division=0))
        support = sum(1 for y in y_true if y == lbl)
        per_class[lbl] = {
            "precision": round(prec_c, 3),
            "recall": round(rec_c, 3),
            "f1": round(f1_c, 3),
            "support": support,
        }

    # Boundary confusion analysis (Critical for Document Quality Gate)
    boundary_confusions = {
        "HIGH_vs_MEDIUM": {
            "HIGH_predicted_as_MEDIUM": cm_dict.get("HIGH", {}).get("MEDIUM", 0),
            "MEDIUM_predicted_as_HIGH": cm_dict.get("MEDIUM", {}).get("HIGH", 0),
        },
        "MEDIUM_vs_LOW": {
            "MEDIUM_predicted_as_LOW": cm_dict.get("MEDIUM", {}).get("LOW", 0),
            "LOW_predicted_as_MEDIUM": cm_dict.get("LOW", {}).get("MEDIUM", 0),
        },
        "LOW_vs_UNREADABLE": {
            "LOW_predicted_as_UNREADABLE": cm_dict.get("LOW", {}).get("UNREADABLE", 0),
            "UNREADABLE_predicted_as_LOW": cm_dict.get("UNREADABLE", {}).get("LOW", 0),
        },
    }

    return {
        "accuracy": round(acc, 4),
        "macro_precision": round(prec_macro, 4),
        "macro_recall": round(rec_macro, 4),
        "macro_f1": round(f1_macro, 4),
        "per_class": per_class,
        "confusion_matrix": cm_dict,
        "boundary_confusions": boundary_confusions,
        "critical_classes": {
            "LOW_recall": per_class["LOW"]["recall"],
            "UNREADABLE_recall": per_class["UNREADABLE"]["recall"],
        },
    }


def format_evaluation_report(metrics: Dict[str, Any]) -> str:
    """Formats human-readable evaluation summary."""
    lines = [
        "═" * 60,
        "  VERICAMPUS AI — DOCUMENT QUALITY MODEL EVALUATION",
        "═" * 60,
        f"  Overall Accuracy : {metrics['accuracy']:.2%}",
        f"  Macro Precision  : {metrics['macro_precision']:.2%}",
        f"  Macro Recall     : {metrics['macro_recall']:.2%}",
        f"  Macro F1-Score   : {metrics['macro_f1']:.2%}",
        "",
        "─── Per-Class Performance ───",
    ]
    for cls_name, vals in metrics["per_class"].items():
        lines.append(
            f"  {cls_name:<11} | Prec: {vals['precision']:.2f} | "
            f"Rec: {vals['recall']:.2f} | F1: {vals['f1']:.2f} | Support: {vals['support']}"
        )

    lines.extend([
        "",
        "─── Boundary Confusion Matrix ───",
        f"  HIGH vs MEDIUM     : HIGH->MED={metrics['boundary_confusions']['HIGH_vs_MEDIUM']['HIGH_predicted_as_MEDIUM']}, "
        f"MED->HIGH={metrics['boundary_confusions']['HIGH_vs_MEDIUM']['MEDIUM_predicted_as_HIGH']}",
        f"  MEDIUM vs LOW      : MED->LOW={metrics['boundary_confusions']['MEDIUM_vs_LOW']['MEDIUM_predicted_as_LOW']}, "
        f"LOW->MED={metrics['boundary_confusions']['MEDIUM_vs_LOW']['LOW_predicted_as_MEDIUM']}",
        f"  LOW vs UNREADABLE  : LOW->UNREAD={metrics['boundary_confusions']['LOW_vs_UNREADABLE']['LOW_predicted_as_UNREADABLE']}, "
        f"UNREAD->LOW={metrics['boundary_confusions']['LOW_vs_UNREADABLE']['UNREADABLE_predicted_as_LOW']}",
        "═" * 60,
    ])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Evaluate Document Quality Model")
    parser.add_argument(
        "--metrics-file",
        type=str,
        default="ml/models/evaluation_metrics.json",
        help="Path to evaluation metrics JSON",
    )
    args = parser.parse_args()

    m_path = Path(args.metrics_file)
    if not m_path.exists():
        print(f"Metrics file not found: {m_path}. Run training first.")
        return

    with open(m_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    test_metrics = data.get("test", data)
    report = format_evaluation_report(test_metrics)
    print(report)


if __name__ == "__main__":
    main()

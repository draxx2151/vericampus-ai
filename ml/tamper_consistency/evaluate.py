"""
VeriCampus AI — Stage 4: Tamper & Consistency Evaluation Suite
Evaluates Stage 4 detection accuracy, precision, recall, and F1 across benchmark test cases.
NOTE: Thresholds and evaluation metrics reflect prototype operational datasets,
not claimed as scientifically validated population constants.
"""
from typing import Dict, Any, List, Tuple
from .service import TamperConsistencyService
from .schemas import CheckStatus


def generate_benchmark_test_cases() -> List[Dict[str, Any]]:
    """Generates synthetic benchmark test scenarios spanning valid and conflicting documents."""
    return [
        {
            "case_id": "TC_001_CLEAN_ALL_PASS",
            "expected_status": CheckStatus.PASS,
            "extractions": {
                "GOVERNMENT_ID": {
                    "fields": {
                        "student_name": {"normalized_value": "rahul patil", "confidence": 0.95},
                        "date_of_birth": {"normalized_value": "2002-05-15", "confidence": 0.95},
                        "id_number": {"normalized_value": "987654321098", "confidence": 0.95},
                    }
                },
                "MARKSHEET": {
                    "fields": {
                        "student_name": {"normalized_value": "rahul patil", "confidence": 0.92},
                        "date_of_birth": {"normalized_value": "2002-05-15", "confidence": 0.90},
                        "total_marks": {"normalized_value": 450.0, "source_text": "450 / 600", "confidence": 0.95},
                        "percentage": {"normalized_value": 75.0, "confidence": 0.95},
                        "passing_year": {"normalized_value": 2020, "confidence": 0.95},
                    }
                },
                "DOMICILE_CERTIFICATE": {
                    "fields": {
                        "applicant_name": {"normalized_value": "rahul patil", "confidence": 0.90},
                        "issue_date": {"normalized_value": "2023-01-10", "confidence": 0.95},
                    }
                },
            },
        },
        {
            "case_id": "TC_002_MINOR_NAME_VARIATION",
            "expected_status": CheckStatus.PASS,
            "extractions": {
                "GOVERNMENT_ID": {
                    "fields": {
                        "student_name": {"normalized_value": "rahul k patil", "confidence": 0.95},
                        "date_of_birth": {"normalized_value": "2002-05-15", "confidence": 0.95},
                        "id_number": {"normalized_value": "987654321098", "confidence": 0.95},
                    }
                },
                "MARKSHEET": {
                    "fields": {
                        "student_name": {"normalized_value": "rahul kumar patil", "confidence": 0.92},
                        "date_of_birth": {"normalized_value": "2002-05-15", "confidence": 0.90},
                        "total_marks": {"normalized_value": 400.0, "source_text": "400 / 500", "confidence": 0.95},
                        "percentage": {"normalized_value": 80.0, "confidence": 0.95},
                        "passing_year": {"normalized_value": 2020, "confidence": 0.95},
                    }
                },
            },
        },
        {
            "case_id": "TC_003_DOB_MISMATCH_CRITICAL",
            "expected_status": CheckStatus.NEEDS_REVIEW,
            "extractions": {
                "GOVERNMENT_ID": {
                    "fields": {
                        "student_name": {"normalized_value": "priya sharma", "confidence": 0.95},
                        "date_of_birth": {"normalized_value": "2001-08-20", "confidence": 0.95},
                        "id_number": {"normalized_value": "112233445566", "confidence": 0.95},
                    }
                },
                "MARKSHEET": {
                    "fields": {
                        "student_name": {"normalized_value": "priya sharma", "confidence": 0.90},
                        "date_of_birth": {"normalized_value": "2004-03-12", "confidence": 0.90},
                        "total_marks": {"normalized_value": 420.0, "source_text": "420 / 500", "confidence": 0.95},
                        "percentage": {"normalized_value": 84.0, "confidence": 0.95},
                        "passing_year": {"normalized_value": 2020, "confidence": 0.95},
                    }
                },
            },
        },
        {
            "case_id": "TC_004_ID_MISMATCH_CRITICAL",
            "expected_status": CheckStatus.NEEDS_REVIEW,
            "extractions": {
                "GOVERNMENT_ID": {
                    "fields": {
                        "student_name": {"normalized_value": "anita deshmukh", "confidence": 0.95},
                        "id_number": {"normalized_value": "999988887777", "confidence": 0.95},
                    }
                },
                "DOMICILE_CERTIFICATE": {
                    "fields": {
                        "applicant_name": {"normalized_value": "anita deshmukh", "confidence": 0.90},
                        "id_number": {"normalized_value": "123456789012", "confidence": 0.90},
                    }
                },
            },
        },
        {
            "case_id": "TC_005_MARKS_ARITHMETIC_CONTRADICTION",
            "expected_status": CheckStatus.NEEDS_REVIEW,
            "extractions": {
                "MARKSHEET": {
                    "fields": {
                        "student_name": {"normalized_value": "vijay verma", "confidence": 0.95},
                        "total_marks": {"normalized_value": 520.0, "source_text": "520 / 500", "confidence": 0.95},
                        "percentage": {"normalized_value": 60.0, "confidence": 0.95},
                    }
                }
            },
        },
    ]


def run_stage4_evaluation() -> Dict[str, Any]:
    """Runs Stage 4 evaluation over the synthetic benchmark dataset."""
    cases = generate_benchmark_test_cases()
    service = TamperConsistencyService()

    tp = 0  # correctly flagged NEEDS_REVIEW
    tn = 0  # correctly flagged PASS / WARNING
    fp = 0
    fn = 0

    results = []
    for c in cases:
        eval_res = service.evaluate(extractions=c["extractions"])
        predicted = eval_res.overall_status
        expected = c["expected_status"]

        is_review_expected = (expected == CheckStatus.NEEDS_REVIEW)
        is_review_pred = (predicted == CheckStatus.NEEDS_REVIEW)

        if is_review_expected and is_review_pred:
            tp += 1
        elif not is_review_expected and not is_review_pred:
            tn += 1
        elif not is_review_expected and is_review_pred:
            fp += 1
        else:
            fn += 1

        results.append({
            "case_id": c["case_id"],
            "expected": expected.value,
            "predicted": predicted.value,
            "score": eval_res.overall_score,
            "review_required": eval_res.review_required,
        })

    total = len(cases)
    accuracy = (tp + tn) / max(total, 1)
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * (precision * recall) / max(precision + recall, 1e-6)

    return {
        "disclaimer": "Thresholds and evaluation metrics reflect prototype operational datasets, not claimed as scientifically validated population constants.",
        "total_test_cases": total,
        "accuracy": round(accuracy, 3),
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1_score": round(f1, 3),
        "confusion_matrix": {
            "true_positives": tp,
            "true_negatives": tn,
            "false_positives": fp,
            "false_negatives": fn,
        },
        "cases": results,
    }


if __name__ == "__main__":
    report = run_stage4_evaluation()
    print("Stage 4 Evaluation Report:")
    for k, v in report.items():
        print(f"  {k}: {v}")

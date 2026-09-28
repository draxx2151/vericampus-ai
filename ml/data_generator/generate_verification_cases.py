import json
import random
from pathlib import Path
import copy
from . import config

def introduce_inconsistency(student: dict, doc_type: str) -> tuple[dict, list[str]]:
    """Introduce controlled inconsistencies into a student's document data.
    Returns (modified_student_for_this_doc, list_of_inconsistency_descriptions).
    
    Possible inconsistencies:
    - Name mismatch between documents (slight spelling change)
    - Date of birth mismatch
    - Income above threshold for selected scheme
    - Percentage below minimum for selected scheme
    - Missing fields (set some fields to None)
    - Wrong state in domicile (not Maharashtra)
    """
    modified_student = copy.deepcopy(student)
    inconsistencies = []
    
    inconsistency_types = [
        "name_mismatch",
        "dob_mismatch",
        "income_above",
        "percentage_below",
        "missing_fields",
        "wrong_state"
    ]
    
    num_issues = random.randint(1, 2)
    chosen_issues = random.sample(inconsistency_types, num_issues)
    
    for issue in chosen_issues:
        if issue == "name_mismatch":
            if modified_student.get("first_name"):
                modified_student["first_name"] = modified_student["first_name"] + "x"
                modified_student["full_name"] = f"{modified_student['first_name']} {modified_student.get('last_name', '')}"
                inconsistencies.append("Name mismatch between documents")
        elif issue == "dob_mismatch":
            if modified_student.get("date_of_birth"):
                modified_student["date_of_birth"] = "1999-01-01"
                inconsistencies.append("Date of birth mismatch")
        elif issue == "income_above":
            scheme = modified_student.get("scholarship_scheme")
            rules = getattr(config, "DEFAULT_SCHOLARSHIP_RULES", {}).get(scheme, {})
            limit = rules.get("income_limit", 150000)
            modified_student["annual_income_inr"] = limit + 50000
            inconsistencies.append("Income above threshold for selected scheme")
        elif issue == "percentage_below":
            scheme = modified_student.get("scholarship_scheme")
            rules = getattr(config, "DEFAULT_SCHOLARSHIP_RULES", {}).get(scheme, {})
            min_pct = rules.get("minimum_percentage", 60.0)
            modified_student["percentage"] = max(0.0, min_pct - 10.0)
            inconsistencies.append("Percentage below minimum for selected scheme")
        elif issue == "missing_fields":
            modified_student["address"] = None
            inconsistencies.append("Missing fields")
        elif issue == "wrong_state":
            modified_student["state"] = "Karnataka"
            modified_student["is_maharashtra_domicile"] = False
            inconsistencies.append("Wrong state in domicile")

    return modified_student, inconsistencies


def generate_verification_cases(
    students: list[dict],
    output_dir: Path,
    needs_review_fraction: float = config.NEEDS_REVIEW_FRACTION,
    seed: int = config.DEFAULT_SEED,
) -> list[dict]:
    """Assign VALID or NEEDS_REVIEW labels to each student's document set.
    For NEEDS_REVIEW cases, introduce controlled inconsistencies.
    Saves verification_labels.json to output_dir/.
    Returns list of dicts with: student_id, label, inconsistencies (list), document_types_affected.
    """
    random.seed(seed)
    
    num_students = len(students)
    num_needs_review = int(num_students * needs_review_fraction)
    
    shuffled_students = students.copy()
    random.shuffle(shuffled_students)
    
    needs_review_students = set(s["student_id"] for s in shuffled_students[:num_needs_review])
    
    verification_cases = []
    
    for student in students:
        student_id = student["student_id"]
        if student_id in needs_review_students:
            label = "NEEDS_REVIEW"
            affected_doc = random.choice(config.DOCUMENT_TYPES)
            _, inconvs = introduce_inconsistency(student, affected_doc)
            
            verification_cases.append({
                "student_id": student_id,
                "label": label,
                "inconsistencies": inconvs,
                "document_types_affected": [affected_doc]
            })
        else:
            verification_cases.append({
                "student_id": student_id,
                "label": "VALID",
                "inconsistencies": [],
                "document_types_affected": []
            })
            
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / "verification_labels.json", "w", encoding="utf-8") as f:
        json.dump(verification_cases, f, indent=4)
        
    return verification_cases

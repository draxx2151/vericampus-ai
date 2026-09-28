"""
VeriCampus AI — Synthetic Student Data Generator

Generates realistic-but-fictional Indian student profiles
using Faker with the en_IN locale. All names, addresses,
and IDs are synthetic. Maharashtra-focused.
"""
import json
import random
import string
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from faker import Faker

from . import config

# Indian locale
fake = Faker("en_IN")


def _generate_aadhaar() -> str:
    """Synthetic 12-digit Aadhaar-style number (starts with 2-9)."""
    first = random.choice("23456789")
    rest = "".join(random.choices(string.digits, k=11))
    return first + rest


def _generate_pan() -> str:
    """Synthetic PAN-style alphanumeric (AAAAA0000A)."""
    letters = "".join(random.choices(string.ascii_uppercase, k=5))
    digits = "".join(random.choices(string.digits, k=4))
    last = random.choice(string.ascii_uppercase)
    return letters + digits + last


def _generate_voter_id() -> str:
    """Synthetic Voter ID style (AAA0000000)."""
    prefix = "".join(random.choices(string.ascii_uppercase, k=3))
    num = "".join(random.choices(string.digits, k=7))
    return prefix + num


def _generate_certificate_number(prefix: str = "CERT") -> str:
    """Generate a synthetic certificate number."""
    year = random.randint(2020, 2025)
    seq = "".join(random.choices(string.digits, k=6))
    return f"{prefix}/{year}/{seq}"


# ─── Common Indian first names (male/female) ────────────────
MALE_FIRST_NAMES = [
    "Aarav", "Aditya", "Arjun", "Dhruv", "Ishaan",
    "Karan", "Mihir", "Nikhil", "Om", "Pranav",
    "Rahul", "Rohit", "Sahil", "Tanmay", "Varun",
    "Vikram", "Yash", "Akash", "Siddharth", "Kunal",
    "Amit", "Raj", "Saurabh", "Vishal", "Ganesh",
    "Suresh", "Mahesh", "Rajesh", "Dinesh", "Prashant",
]

FEMALE_FIRST_NAMES = [
    "Ananya", "Diya", "Ishita", "Kavya", "Meera",
    "Nisha", "Pooja", "Riya", "Sakshi", "Tara",
    "Vidya", "Shreya", "Priya", "Aditi", "Neha",
    "Sonal", "Kajal", "Manasi", "Sneha", "Pallavi",
    "Swati", "Jyoti", "Sunita", "Rekha", "Seema",
]

LAST_NAMES = [
    "Patil", "Deshmukh", "Jadhav", "More", "Pawar",
    "Kulkarni", "Joshi", "Deshpande", "Bhosle", "Chavan",
    "Shinde", "Gaikwad", "Kadam", "Salunkhe", "Kale",
    "Wagh", "Borse", "Mane", "Naik", "Rane",
    "Sawant", "Thakur", "Gokhale", "Tambe", "Khare",
    "Deshpande", "Mahajan", "Phadke", "Gadkari", "Kokate",
]

FATHER_NAME_PREFIXES_M = [
    "Rajesh", "Suresh", "Mahesh", "Dinesh", "Ramesh",
    "Prakash", "Vijay", "Sanjay", "Anil", "Mohan",
    "Ashok", "Pradeep", "Manoj", "Satish", "Devendra",
]

FATHER_NAME_PREFIXES_F = FATHER_NAME_PREFIXES_M  # Same pool for father names


def generate_student(
    student_id: int,
    seed: Optional[int] = None,
) -> dict:
    """
    Generate one synthetic student profile.

    Returns a dict with fields aligned to the backend extraction schemas:
    - full_name, date_of_birth, gender, address (GovernmentIdExtraction)
    - candidate_name, percentage, passing_year (MarksheetExtraction)
    - applicant_name, father_guardian_name, annual_income_inr (IncomeCertificateExtraction)
    - candidate_name, state, is_maharashtra_domicile (DomicileCertificateExtraction)
    """
    if seed is not None:
        random.seed(seed + student_id)
        fake.seed_instance(seed + student_id)

    gender = random.choice(["Male", "Female"])
    if gender == "Male":
        first_name = random.choice(MALE_FIRST_NAMES)
    else:
        first_name = random.choice(FEMALE_FIRST_NAMES)

    last_name = random.choice(LAST_NAMES)
    full_name = f"{first_name} {last_name}"

    father_first = random.choice(FATHER_NAME_PREFIXES_M)
    father_name = f"{father_first} {last_name}"

    district = random.choice(config.MAHARASHTRA_DISTRICTS)

    # Date of birth: students aged 17-25
    today = date.today()
    age = random.randint(17, 25)
    dob = today - timedelta(days=age * 365 + random.randint(0, 364))

    # Address
    house_no = random.randint(1, 500)
    locality = fake.street_name()
    address = f"{house_no}, {locality}, {district}, Maharashtra {random.randint(400001, 445999)}"

    # Government ID
    id_type = random.choice(config.GOVT_ID_TYPES)
    if id_type == "Aadhaar Card":
        id_number = _generate_aadhaar()
    elif id_type == "PAN Card":
        id_number = _generate_pan()
    else:
        id_number = _generate_voter_id()

    # Academic
    passing_year = random.randint(2020, 2025)
    total_marks = random.randint(200, 600)
    max_marks = random.choice([500, 600, 700, 750, 1000])
    if total_marks > max_marks:
        total_marks = int(max_marks * random.uniform(0.35, 0.95))
    percentage = round((total_marks / max_marks) * 100, 2)
    result_status = "PASS" if percentage >= 35.0 else "FAIL"
    roll_number = f"MH{passing_year % 100}{random.randint(100000, 999999)}"
    exam_name = random.choice(config.EXAM_NAMES)

    # Income
    annual_income = random.choice([
        random.randint(50000, 100000),
        random.randint(100001, 250000),
        random.randint(250001, 500000),
        random.randint(500001, 800000),
        random.randint(800001, 1200000),
    ])

    # Certificates
    income_cert_number = _generate_certificate_number("INC")
    domicile_cert_number = _generate_certificate_number("DOM")
    issuing_authority = random.choice(config.ISSUING_AUTHORITIES)

    issue_date = dob + timedelta(days=random.randint(6000, 8000))
    financial_year_start = random.randint(2022, 2025)
    financial_year = f"{financial_year_start}-{financial_year_start + 1}"

    # Scholarship scheme
    scheme = random.choice(config.MAHADBT_SCHEMES)

    return {
        "student_id": student_id,
        "full_name": full_name,
        "first_name": first_name,
        "last_name": last_name,
        "gender": gender,
        "date_of_birth": dob.isoformat(),
        "address": address,
        "district": district,
        "state": "Maharashtra",
        "father_guardian_name": father_name,
        "id_type": id_type,
        "id_number": id_number,
        "exam_name": exam_name,
        "roll_number": roll_number,
        "passing_year": passing_year,
        "total_marks": total_marks,
        "max_marks": max_marks,
        "percentage": percentage,
        "result_status": result_status,
        "annual_income_inr": annual_income,
        "income_certificate_number": income_cert_number,
        "domicile_certificate_number": domicile_cert_number,
        "issuing_authority": issuing_authority,
        "issue_date": issue_date.isoformat(),
        "financial_year": financial_year,
        "is_maharashtra_domicile": True,
        "scholarship_scheme": scheme,
    }


def generate_students(
    count: int,
    seed: int = config.DEFAULT_SEED,
    output_dir: Optional[Path] = None,
) -> list[dict]:
    """
    Generate *count* synthetic student profiles.

    If output_dir is provided, saves students.json there.
    Returns the list of student dicts.
    """
    random.seed(seed)
    fake.seed_instance(seed)

    students = [generate_student(i, seed=seed) for i in range(count)]

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / "students.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(students, f, indent=2, ensure_ascii=False)
        print(f"  ✓ Generated {len(students)} student profiles → {out_path}")

    return students

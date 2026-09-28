"""
VeriCampus AI — Stage 3 Field Aliases & OCR Noise Variants
Centralized registry of label synonyms, multilingual headers, and common OCR misrecognitions.
"""
from typing import Dict, List

FIELD_ALIASES: Dict[str, Dict[str, List[str]]] = {
    "GOVERNMENT_ID": {
        "id_number": [
            "id number", "id no", "uid", "uidai", "aadhaar no", "aadhaar number", "aadhar no",
            "pan", "pan no", "permanent account number", "epic", "voter id", "voter no",
            "card no", "license no", "dl no", "licence no", "identification no"
        ],
        "full_name": [
            "name", "full name", "cardholder name", "applicant name", "name of person"
        ],
        "date_of_birth": [
            "date of birth", "dob", "birth date", "born on", "year of birth", "yob", "d.o.b"
        ],
        "id_type": [
            "identity type", "card type", "document type"
        ],
    },
    "MARKSHEET": {
        "student_name": [
            "candidate name", "student name", "candidate's name", "student's name",
            "name of candidate", "name", "examinee name"
        ],
        "roll_number": [
            "roll no", "roll number", "seat no", "seat number", "registration no",
            "reg no", "hall ticket no", "candidate no"
        ],
        "board_or_institution": [
            "board", "university", "council", "institution", "school", "college",
            "maharashtra state board", "cbse", "icse", "pune board"
        ],
        "examination_name": [
            "examination", "exam name", "exam", "course", "standard", "class",
            "higher secondary certificate", "secondary school certificate", "hsc", "ssc"
        ],
        "examination_year": [
            "passing year", "month & year", "exam year", "year of exam", "session",
            "examination held in", "year"
        ],
        "total_marks": [
            "total marks", "grand total", "total", "aggregate marks", "marks secured", "marks obtained"
        ],
        "percentage": [
            "percentage", "percent", "pct", "% of marks", "aggregate %"
        ],
        "cgpa": [
            "cgpa", "sgpa", "gpa", "cumulative grade", "grade point"
        ],
        "result_status": [
            "result", "result status", "grade", "division", "class"
        ],
    },
    "INCOME_CERTIFICATE": {
        "applicant_name": [
            "applicant name", "issued to", "name of person", "candidate name",
            "beneficiary name", "name", "person name"
        ],
        "father_guardian_name": [
            "father name", "father's name", "guardian name", "husband name", "s/o", "d/o", "w/o"
        ],
        "income_amount": [
            "annual income", "total income", "family income", "income amount",
            "annual family income", "gross income", "income"
        ],
        "financial_year": [
            "financial year", "fin year", "assessment year", "for the year", "period"
        ],
        "certificate_number": [
            "certificate no", "certificate number", "cert no", "outward no", "barcode no",
            "application no", "case no", "sr no", "serial no"
        ],
        "issue_date": [
            "issue date", "date of issue", "issued on", "date", "dated"
        ],
        "issuing_authority": [
            "issuing authority", "issued by", "designation", "tehsildar", "tahsildar",
            "sub divisional officer", "sdo", "revenue officer", "executive magistrate"
        ],
        "district": [
            "district", "zila", "dist"
        ],
        "taluka": [
            "taluka", "tahsil", "tehsil"
        ],
        "village": [
            "village", "gram", "mouza", "city"
        ],
    },
    "DOMICILE_CERTIFICATE": {
        "applicant_name": [
            "applicant name", "candidate name", "issued to", "resident name",
            "name of person", "certified that", "name"
        ],
        "date_of_birth": [
            "date of birth", "dob", "birth date", "born on"
        ],
        "domicile_state": [
            "state", "state of domicile", "domicile state", "state of residence",
            "permanent resident of", "resident of state"
        ],
        "domicile_district": [
            "district", "zila", "district of residence"
        ],
        "certificate_number": [
            "certificate no", "certificate number", "cert no", "outward no",
            "application no", "case no", "barcode"
        ],
        "issue_date": [
            "issue date", "date of issue", "issued on", "date", "dated"
        ],
        "issuing_authority": [
            "issuing authority", "issued by", "designation", "tehsildar", "tahsildar",
            "sub divisional officer", "sdo", "competent authority", "executive magistrate"
        ],
    }
}

"""
VeriCampus AI — Stage 4: Cross-Document Consistency Package
Exports consistency checkers for Name, DOB, Masked ID, Dates, and Marksheet arithmetic.
"""
from .name_consistency import NameConsistencyChecker
from .dob_consistency import DOBConsistencyChecker
from .id_consistency import IDConsistencyChecker
from .date_consistency import DateConsistencyChecker
from .marks_consistency import MarksConsistencyChecker

__all__ = [
    "NameConsistencyChecker",
    "DOBConsistencyChecker",
    "IDConsistencyChecker",
    "DateConsistencyChecker",
    "MarksConsistencyChecker",
]

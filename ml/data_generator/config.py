"""
VeriCampus AI — Synthetic ML Dataset Generator Configuration

Central configuration for all dataset generation parameters.
All field names align with the real backend extraction schemas:
  GovernmentIdExtraction, MarksheetExtraction,
  IncomeCertificateExtraction, DomicileCertificateExtraction
"""
import os
from pathlib import Path

# ─── Paths ───────────────────────────────────────────────────
ML_ROOT = Path(__file__).resolve().parent.parent          # ml/
DATA_GEN_ROOT = Path(__file__).resolve().parent           # ml/data_generator/
DEFAULT_OUTPUT_DIR = ML_ROOT / "datasets"

# ─── Document types (must match backend DocumentType enum) ───
DOCUMENT_TYPES = [
    "GOVERNMENT_ID",
    "MARKSHEET",
    "INCOME_CERTIFICATE",
    "DOMICILE_CERTIFICATE",
]

# Classification target classes (Includes UNKNOWN / OTHER)
ALL_CLASSIFICATION_CLASSES = DOCUMENT_TYPES + ["UNKNOWN"]

# Sub-categories for generating synthetic UNKNOWN / OTHER class images
UNKNOWN_DOCUMENT_TYPES = [
    "blank_paper",
    "generic_letter",
    "unrelated_receipt",
    "generic_form",
]


# ─── MahaDBT scholarship schemes (from backend schemas) ─────
MAHADBT_SCHEMES = [
    "Post Matric Scholarship to VJNT Students",
    "Post Matric Scholarship to OBC Students",
    "Post Matric Scholarship to SBC Students",
    "Post Matric Scholarship to the Girls Belonging to Other Backward Classes taking admission in Professional Courses",
    "Rajarshi Chhatrapati Shahu Maharaj Shikshan Shulkh Shishyavrutti Yojna (EBC)",
    "Dr. Panjabrao Deshmukh Vasatigruh Nirvah Bhatta Yojna (DTE)",
    "State Minority Scholarship Part II (DHE)",
    "Scholarship for students of minority communities pursuing Higher and Professional courses (DTE)",
]

# ─── Scholarship eligibility rules (from backend rules_engine) ──
DEFAULT_SCHOLARSHIP_RULES = {
    "Rajarshi Chhatrapati Shahu Maharaj Shikshan Shulkh Shishyavrutti Yojna (EBC)": {
        "minimum_percentage": 50.0,
        "income_limit": 800000.0,
        "requires_maharashtra_domicile": True,
    },
    "Dr. Panjabrao Deshmukh Vasatigruh Nirvah Bhatta Yojna (DTE)": {
        "minimum_percentage": 50.0,
        "income_limit": 800000.0,
        "requires_maharashtra_domicile": True,
    },
    "Post Matric Scholarship to OBC Students": {
        "minimum_percentage": None,
        "income_limit": 150000.0,
        "requires_maharashtra_domicile": True,
    },
    "Post Matric Scholarship to VJNT Students": {
        "minimum_percentage": None,
        "income_limit": 150000.0,
        "requires_maharashtra_domicile": True,
    },
    "Post Matric Scholarship to SBC Students": {
        "minimum_percentage": None,
        "income_limit": 150000.0,
        "requires_maharashtra_domicile": True,
    },
    "Post Matric Scholarship to the Girls Belonging to Other Backward Classes taking admission in Professional Courses": {
        "minimum_percentage": None,
        "income_limit": 800000.0,
        "requires_maharashtra_domicile": True,
    },
    "State Minority Scholarship Part II (DHE)": {
        "minimum_percentage": 50.0,
        "income_limit": 800000.0,
        "requires_maharashtra_domicile": True,
    },
    "Scholarship for students of minority communities pursuing Higher and Professional courses (DTE)": {
        "minimum_percentage": 50.0,
        "income_limit": 800000.0,
        "requires_maharashtra_domicile": True,
    },
}

# ─── Image generation defaults ──────────────────────────────
IMAGE_WIDTH = 800
IMAGE_HEIGHT = 1100
IMAGE_DPI = 150
FONT_SIZE_TITLE = 28
FONT_SIZE_HEADING = 20
FONT_SIZE_BODY = 16
FONT_SIZE_SMALL = 12
BG_COLOR = (255, 255, 255)
TEXT_COLOR = (20, 20, 20)
BORDER_COLOR = (0, 51, 102)
ACCENT_COLOR = (0, 102, 153)
WATERMARK_TEXT = "SYNTHETIC DEMO DOCUMENT — NOT REAL"

# ─── Maharashtra districts for domicile/addresses ───────────
MAHARASHTRA_DISTRICTS = [
    "Mumbai", "Pune", "Nagpur", "Thane", "Nashik",
    "Aurangabad", "Solapur", "Kolhapur", "Sangli", "Satara",
    "Ratnagiri", "Sindhudurg", "Jalgaon", "Dhule", "Nandurbar",
    "Ahmednagar", "Beed", "Latur", "Osmanabad", "Nanded",
    "Parbhani", "Hingoli", "Jalna", "Buldhana", "Akola",
    "Washim", "Amravati", "Yavatmal", "Wardha", "Chandrapur",
    "Gadchiroli", "Gondia", "Bhandara", "Palghar", "Raigad",
]

# ─── Government ID types ────────────────────────────────────
GOVT_ID_TYPES = ["Aadhaar Card", "PAN Card", "Voter ID"]

# ─── Examination names for marksheets ───────────────────────
EXAM_NAMES = [
    "SSC (Class 10) Board Examination",
    "HSC (Class 12) Board Examination",
    "First Year B.E. Examination",
    "Second Year B.E. Examination",
    "Third Year B.E. Examination",
    "Final Year B.E. Examination",
    "First Year B.Sc. Examination",
    "First Year B.A. Examination",
    "First Year B.Com. Examination",
]

# ─── Visual augmentation defaults ───────────────────────────
AUGMENTATION_TYPES = [
    "blur",
    "rotation",
    "brightness_up",
    "brightness_down",
    "noise",
    "jpeg_compression",
    "perspective_distortion",
]

# How many augmented variants to create per clean image
AUGMENTATIONS_PER_IMAGE = 3

# ─── Dataset split ratios ───────────────────────────────────
TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15

# ─── Verification dataset labels ────────────────────────────
VERIFICATION_LABELS = ["VALID", "NEEDS_REVIEW"]

# Fraction of samples to assign controlled inconsistencies
NEEDS_REVIEW_FRACTION = 0.30

# ─── Issuing authorities ────────────────────────────────────
ISSUING_AUTHORITIES = [
    "Office of the Tehsildar",
    "Office of the Sub-Divisional Magistrate",
    "Office of the District Collector",
    "Talathi Office",
    "Office of the Naib Tehsildar",
]

# ─── Random seed ────────────────────────────────────────────
DEFAULT_SEED = 42

# ─── Document Quality Gate Settings ─────────────────────────
QUALITY_CATEGORIES = ["HIGH", "MEDIUM", "LOW", "UNREADABLE"]

# Central Thresholds (Single source of truth)
QUALITY_THRESHOLD_HIGH = 85.0
QUALITY_THRESHOLD_ACCEPTABLE = 70.0
QUALITY_THRESHOLD_LOW = 0.0

# Target proportions in synthetic dataset generation
QUALITY_DISTRIBUTION_TARGETS = {
    "HIGH": 0.35,
    "MEDIUM": 0.35,
    "LOW": 0.18,
    "UNREADABLE": 0.12,
}

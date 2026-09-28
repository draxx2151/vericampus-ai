"""
VeriCampus AI — Stage 3 Field Normalizers & Sanitizers
Type-safe normalization for names, dates, currencies, numbers, and PII masking.
Complies strictly with non-destructive name normalization and sensitive ID protections.
"""
import re
import unicodedata
from datetime import datetime
from typing import Optional, Union, Tuple, Any

from .config import MASK_CHARACTER, VISIBLE_TRAILING_DIGITS


def normalize_whitespace(text: Optional[str]) -> str:
    """Collapses consecutive spaces, tabs, and line breaks into single space, stripping edges."""
    if not text:
        return ""
    # Normalize unicode characters (e.g. non-breaking spaces NFKD)
    normalized = unicodedata.normalize("NFKD", str(text))
    return " ".join(normalized.split()).strip()


def normalize_name(raw_name: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Normalizes candidate / applicant names.
    CONSTRAINT: Does NOT force title-case.
    Returns:
        (raw_value, normalized_lowercase_value)
    """
    if not raw_name:
        return None, None
    raw_str = normalize_whitespace(raw_name)
    if not raw_str:
        return None, None

    # Strip common salutations/honorifics if leading
    honorific_pattern = r'^(?:Shri|Smt|Kumari|Kumar|Kum|Dr|Prof|Mr|Mrs|Ms|Master)\.?\s+'
    cleaned_lower = re.sub(honorific_pattern, '', raw_str, flags=re.IGNORECASE)

    # Clean non-alphanumeric noise (preserving spaces and basic hyphens)
    cleaned_lower = re.sub(r'[^a-zA-Z\s\-]', ' ', cleaned_lower)
    normalized_value = normalize_whitespace(cleaned_lower).lower()

    if not normalized_value or len(normalized_value) < 2:
        return raw_str, None

    return raw_str, normalized_value


def normalize_date(raw_date: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Normalizes date representations to ISO format (YYYY-MM-DD) where unambiguous.
    Returns:
        (raw_value, normalized_iso_value)
    """
    if not raw_date:
        return None, None
    raw_str = normalize_whitespace(raw_date)
    if not raw_str:
        return None, None

    # Clean out non-date characters like "Date:", "DOB:"
    clean_str = re.sub(r'^(?:Date\s*of\s*Birth|DOB|Date|Dated|Issued\s*on)\s*[:\-]?\s*', '', raw_str, flags=re.IGNORECASE)
    clean_str = clean_str.replace(',', ' ').strip()
    clean_str = normalize_whitespace(clean_str)

    date_formats = [
        "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%Y/%m/%d",
        "%d.%m.%Y", "%Y.%m.%d",
        "%d %b %Y", "%d %B %Y", "%b %d %Y", "%B %d %Y",
        "%d-%b-%Y", "%d-%B-%Y"
    ]

    for fmt in date_formats:
        try:
            dt = datetime.strptime(clean_str, fmt)
            # Sanity check year bounds
            if 1940 <= dt.year <= 2035:
                return raw_str, dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Regex heuristic for standard Indian formats DD/MM/YYYY or DD-MM-YYYY
    match_dmy = re.search(r'\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\b', clean_str)
    if match_dmy:
        d, m, y = int(match_dmy.group(1)), int(match_dmy.group(2)), int(match_dmy.group(3))
        if 1 <= m <= 12 and 1 <= d <= 31 and 1940 <= y <= 2035:
            try:
                dt = datetime(y, m, d)
                return raw_str, dt.strftime("%Y-%m-%d")
            except ValueError:
                pass

    # Regex for YYYY-MM-DD
    match_ymd = re.search(r'\b(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})\b', clean_str)
    if match_ymd:
        y, m, d = int(match_ymd.group(1)), int(match_ymd.group(2)), int(match_ymd.group(3))
        if 1 <= m <= 12 and 1 <= d <= 31 and 1940 <= y <= 2035:
            try:
                dt = datetime(y, m, d)
                return raw_str, dt.strftime("%Y-%m-%d")
            except ValueError:
                pass

    return raw_str, None


def normalize_currency(raw_currency: Optional[Union[str, float, int]]) -> Tuple[Optional[str], Optional[float]]:
    """
    Normalizes Indian Rupee currency strings (e.g. 'Rs. 1,50,000/-', '₹ 150000', '1.5 Lakh')
    to an integer/float amount in INR.
    Returns:
        (raw_value, normalized_float_inr)
    """
    if raw_currency is None:
        return None, None
    if isinstance(raw_currency, (int, float)):
        return str(raw_currency), float(raw_currency)

    raw_str = normalize_whitespace(str(raw_currency))
    if not raw_str:
        return None, None

    # Handle Lakh / Crore expressions
    lakh_match = re.search(r'([\d.]+)\s*(?:lakh|lac|lacs|lakhs)', raw_str, re.IGNORECASE)
    if lakh_match:
        try:
            return raw_str, float(lakh_match.group(1)) * 100000.0
        except ValueError:
            pass

    crore_match = re.search(r'([\d.]+)\s*(?:crore|cr|crores)', raw_str, re.IGNORECASE)
    if crore_match:
        try:
            return raw_str, float(crore_match.group(1)) * 10000000.0
        except ValueError:
            pass

    # Clean out currency symbols and suffixes
    cleaned = re.sub(r'^(?:Rs\.?|INR|₹|\$)\s*', '', raw_str, flags=re.IGNORECASE)
    cleaned = re.sub(r'/\-.*$', '', cleaned)  # remove trailing "/-"
    cleaned = cleaned.replace(',', '').replace(' ', '').strip()

    num_match = re.search(r'\b(\d+(?:\.\d+)?)\b', cleaned)
    if num_match:
        try:
            val = float(num_match.group(1))
            return raw_str, val
        except ValueError:
            pass

    return raw_str, None


def normalize_percentage(raw_percentage: Optional[Union[str, float, int]]) -> Tuple[Optional[str], Optional[float]]:
    """
    Normalizes academic percentage score e.g. '82.4%', '82.40' -> float (82.4)
    """
    if raw_percentage is None:
        return None, None
    if isinstance(raw_percentage, (int, float)):
        return str(raw_percentage), float(raw_percentage)

    raw_str = normalize_whitespace(str(raw_percentage))
    clean = raw_str.replace('%', '').replace(',', '').strip()
    match = re.search(r'\b(\d{1,3}(?:\.\d{1,3})?)\b', clean)
    if match:
        try:
            val = float(match.group(1))
            if 0.0 <= val <= 100.0:
                return raw_str, round(val, 2)
        except ValueError:
            pass
    return raw_str, None


def normalize_id_number(raw_id: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Normalizes Government Identification number (stripping inner spaces/hyphens).
    """
    if not raw_id:
        return None, None
    raw_str = normalize_whitespace(raw_id)
    if not raw_str:
        return None, None

    # Remove dashes, dots, spaces
    normalized = re.sub(r'[\s\-\.]', '', raw_str).upper()
    return raw_str, normalized


def mask_sensitive_id(id_number: Optional[str], id_type: Optional[str] = None) -> str:
    """
    Returns a masked version of sensitive ID strings (e.g. Aadhaar: '********9012').
    Never exposes full number in logs or diagnostics.
    """
    if not id_number:
        return ""
    clean = normalize_whitespace(str(id_number))
    clean_unspaced = clean.replace(" ", "").replace("-", "")
    if len(clean_unspaced) > VISIBLE_TRAILING_DIGITS:
        unmasked_tail = clean_unspaced[-VISIBLE_TRAILING_DIGITS:]
        masked_head = MASK_CHARACTER * (len(clean_unspaced) - VISIBLE_TRAILING_DIGITS)
        return f"{masked_head}{unmasked_tail}"

    return clean

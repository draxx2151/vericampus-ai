"""
VeriCampus AI — Stage 3 Document Field Extractors
"""
from .government_id import GovernmentIdFieldExtractor
from .marksheet import MarksheetFieldExtractor
from .income_certificate import IncomeCertificateFieldExtractor
from .domicile_certificate import DomicileCertificateFieldExtractor

__all__ = [
    "GovernmentIdFieldExtractor",
    "MarksheetFieldExtractor",
    "IncomeCertificateFieldExtractor",
    "DomicileCertificateFieldExtractor",
]

"""
VeriCampus AI — Stage 4: Metadata Tamper Feature Extraction
Inspects non-sensitive EXIF, image properties, and PDF metadata:
1. Producer, Creator, and Software strings (Photoshop, Canva, GIMP, etc.).
2. DPI / resolution consistency.
3. Image format properties.
IMPORTANT: Software metadata is an advisory signal only (SignalSeverity.INFO or LOW,
EvidenceStrength.WEAK), NEVER proof of fraud. Many legitimate student documents are
scanned, resized, or saved using image processing tools.
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
from PIL import Image

from ..schemas import TamperSignal, SignalCategory, SignalSeverity, CheckStatus, EvidenceStrength
from ..config import SUSPICIOUS_SOFTWARE_KEYWORDS


def extract_metadata_signals(
    image_or_path: Any,
    doc_type: str,
    metadata: Optional[Dict[str, Any]] = None
) -> List[TamperSignal]:
    """
    Extracts advisory metadata signals from image file headers or provided metadata dict.
    Never exposes PII or private metadata tags.
    """
    signals: List[TamperSignal] = []
    meta = dict(metadata or {})

    # Extract EXIF/info if a file path or PIL image is available
    software_found: Optional[str] = None
    file_format: Optional[str] = None
    dpi: Optional[float] = None

    try:
        if isinstance(image_or_path, (str, Path)):
            p = Path(image_or_path)
            if p.exists() and not p.is_dir():
                with Image.open(p) as img:
                    file_format = img.format
                    dpi_info = img.info.get("dpi")
                    if dpi_info and isinstance(dpi_info, (tuple, list)) and len(dpi_info) > 0:
                        dpi = float(dpi_info[0])

                    # Inspect software tags in info
                    for k in ["Software", "software", "creator", "Producer", "Creator"]:
                        if k in img.info:
                            val = str(img.info[k]).lower()
                            for kw in SUSPICIOUS_SOFTWARE_KEYWORDS:
                                if kw in val:
                                    software_found = str(img.info[k])
                                    break
        elif isinstance(image_or_path, Image.Image):
            file_format = image_or_path.format
            for k in ["Software", "software", "creator", "Producer", "Creator"]:
                if k in image_or_path.info:
                    val = str(image_or_path.info[k]).lower()
                    for kw in SUSPICIOUS_SOFTWARE_KEYWORDS:
                        if kw in val:
                            software_found = str(image_or_path.info[k])
                            break
    except Exception:
        pass

    # Also check explicitly passed metadata dictionary
    if not software_found:
        for k in ["software", "creator", "producer", "software_used"]:
            if k in meta:
                val = str(meta[k]).lower()
                for kw in SUSPICIOUS_SOFTWARE_KEYWORDS:
                    if kw in val:
                        software_found = str(meta[k])
                        break

    # 1. Advisory Software Metadata Signal
    if software_found:
        signals.append(
            TamperSignal(
                signal_name="editing_software_metadata",
                category=SignalCategory.METADATA,
                severity=SignalSeverity.LOW,
                score=78.0,
                confidence=0.70,
                status=CheckStatus.WARNING,
                explanation=(
                    f"Metadata indicates file was generated or edited with '{software_found}'. "
                    f"Advisory signal only: legitimate applicants frequently use image tools to resize or convert scans."
                ),
                affected_document=doc_type,
                evidence_strength=EvidenceStrength.WEAK,
            )
        )
    else:
        signals.append(
            TamperSignal(
                signal_name="editing_software_metadata",
                category=SignalCategory.METADATA,
                severity=SignalSeverity.INFO,
                score=100.0,
                confidence=0.85,
                status=CheckStatus.PASS,
                explanation="No image manipulation software signatures detected in document metadata.",
                affected_document=doc_type,
                evidence_strength=EvidenceStrength.WEAK,
            )
        )

    # 2. DPI / Resolution Sanity Signal
    if dpi and dpi < 100.0:
        signals.append(
            TamperSignal(
                signal_name="dpi_resolution_sanity",
                category=SignalCategory.METADATA,
                severity=SignalSeverity.INFO,
                score=80.0,
                confidence=0.80,
                status=CheckStatus.PASS,
                explanation=f"Reported metadata DPI ({dpi:.0f}) is low; document quality gate handles resolution adequacy.",
                affected_document=doc_type,
                evidence_strength=EvidenceStrength.WEAK,
            )
        )

    return signals

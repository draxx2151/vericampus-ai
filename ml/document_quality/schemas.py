"""
VeriCampus AI — Document Quality Schemas
Pydantic contracts for quality assessments, statuses, and feature payloads.
"""
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class QualityLevel(str, Enum):
    HIGH = "HIGH"
    ACCEPTABLE = "ACCEPTABLE"
    LOW = "LOW"
    UNREADABLE = "UNREADABLE"


class QualityGateStatus(str, Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    REUPLOAD_REQUIRED = "REUPLOAD_REQUIRED"


class QualityFeatures(BaseModel):
    resolution_megapixels: float = Field(..., description="Megapixels of image (w*h/1M)")
    blur_laplacian_variance: float = Field(..., description="Laplacian variance sharpness")
    normalized_sharpness: float = Field(..., description="Normalized sharpness score (0-100)")
    brightness_mean: float = Field(..., description="Mean luminance (0-255)")
    brightness_std: float = Field(..., description="Luminance standard deviation")
    contrast_rms: float = Field(..., description="RMS contrast")
    noise_estimate_sigma: float = Field(..., description="Estimated noise sigma")
    skew_angle_degrees: float = Field(..., description="Estimated skew angle in degrees")
    crop_margin_completeness: float = Field(..., description="Estimated border completeness ratio")
    ocr_confidence: float = Field(..., description="OCR average confidence (0.0 to 1.0)")
    
    # Optional raw diagnostic details
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    ocr_word_count: Optional[int] = None
    ocr_text_length: Optional[int] = None


class QualityAssessment(BaseModel):
    quality_score: float = Field(..., ge=0.0, le=100.0, description="Overall quality score 0-100")
    quality_level: QualityLevel = Field(..., description="Assessed quality tier")
    quality_gate_status: QualityGateStatus = Field(..., description="Gate decision: PASS, WARNING, REUPLOAD_REQUIRED")
    reasons: List[str] = Field(default_factory=list, description="Actionable, machine-readable explanation strings")
    features: Dict[str, Any] = Field(default_factory=dict, description="Extracted numerical quality features")
    model_version: str = Field("1.0.0", description="Version of model or analyzer producing this assessment")
    is_fallback: bool = Field(False, description="Whether rule-based fallback was used in place of ML model")

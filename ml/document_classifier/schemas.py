"""
VeriCampus AI — Document Classification Schemas
Pydantic contracts for classification results, status enums, and confidence alternatives.
"""
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from .config import MODEL_VERSION


class ClassificationStatus(str, Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    UNKNOWN = "UNKNOWN"
    DOCUMENT_TYPE_MISMATCH = "DOCUMENT_TYPE_MISMATCH"


class ClassificationAlternative(BaseModel):
    document_type: str
    confidence: float = Field(ge=0.0, le=1.0)


class DocumentClassificationResult(BaseModel):
    """
    Standardized payload for Stage 2 Document Classification.
    """
    predicted_type: str = Field(description="Predicted document class (GOVERNMENT_ID, MARKSHEET, etc.)")
    confidence: float = Field(ge=0.0, le=1.0, description="Model prediction probability for predicted_type")
    classification_status: ClassificationStatus = Field(description="Operational classification outcome")
    alternatives: List[ClassificationAlternative] = Field(default_factory=list, description="Top ranked class alternatives with probabilities")
    expected_type: Optional[str] = Field(default=None, description="Expected document type required by application slot")
    type_match: Optional[bool] = Field(default=None, description="Whether predicted_type matches expected_type")
    model_version: str = Field(default=MODEL_VERSION, description="Model version tag")
    reasons: List[str] = Field(default_factory=list, description="Actionable human/admin readable explanation strings")
    features_summary: Dict[str, Any] = Field(default_factory=dict, description="Summary of salient visual/structural cues")
    is_fallback: bool = Field(default=False, description="True if heuristic fallback was used instead of ML artifact")

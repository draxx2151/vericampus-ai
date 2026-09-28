from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class RiskLevel(str, Enum):
    """
    Standardized review risk levels for administrative assistance only.
    NOT an automated approval/rejection or fraud detection verdict.
    """
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RiskFeatures(BaseModel):
    """
    Numerical and categorical features built strictly from non-PII verification signals.
    Contains zero student PII (no Aadhaar numbers, names, phone numbers, addresses, emails, or raw text).
    """
    identity_pass_rate: float = Field(..., ge=0.0, le=1.0, description="Proportion of identity checks passed (0.0 to 1.0)")
    name_mismatch_count: int = Field(default=0, ge=0, description="Count of name discrepancies across documents")
    dob_mismatch_count: int = Field(default=0, ge=0, description="DOB mismatch indicator (0 or 1)")
    government_id_mismatch_count: int = Field(default=0, ge=0, description="Government ID mismatch indicator (0 or 1)")
    domicile_issue: int = Field(default=0, ge=0, le=1, description="Domicile verification failure indicator (0 or 1)")
    income_issue: int = Field(default=0, ge=0, le=1, description="Income criteria failure indicator (0 or 1)")
    marksheet_issue: int = Field(default=0, ge=0, le=1, description="Academic performance failure indicator (0 or 1)")
    missing_field_count: int = Field(default=0, ge=0, description="Count of missing expected fields across documents")
    warning_count: int = Field(default=0, ge=0, description="Total non-critical warnings emitted during verification")
    critical_failure_count: int = Field(default=0, ge=0, description="Total critical failures detected")
    cross_document_mismatch_count: int = Field(default=0, ge=0, description="Count of cross-document inconsistencies")
    ocr_quality_score: float = Field(..., ge=0.0, le=1.0, description="Aggregated OCR readability quality (0.0 to 1.0)")
    overall_rule_score: float = Field(..., ge=0.0, le=100.0, description="Overall score produced by the rules engine (0.0 to 100.0)")

    model_config = ConfigDict(extra="forbid")


class RiskPrediction(BaseModel):
    """
    Output of a RiskModel prediction for administrative verification review assistance.
    """
    risk_score: float = Field(..., ge=0.0, le=100.0, description="Bounded review risk score from 0.0 (lowest risk) to 100.0 (highest review risk)")
    risk_level: RiskLevel = Field(..., description="Review risk level: LOW, MEDIUM, or HIGH")
    model_name: str = Field(..., description="Identifier of the risk model that produced this assessment")
    model_version: str = Field(..., description="Version of the risk model")
    explanation: List[str] = Field(default_factory=list, description="Human-readable review assistance justifications")

    model_config = ConfigDict(extra="ignore")


class RiskAnalysisResult(BaseModel):
    """
    Encapsulates both the model prediction and the extracted feature vector.
    """
    prediction: RiskPrediction
    features: RiskFeatures

from typing import List
from app.services.risk_analysis.base import BaseRiskModel
from app.services.risk_analysis.schemas import RiskFeatures, RiskPrediction, RiskLevel


# Review Risk Level Thresholds (for administrative verification assistance only)
# These are prototype heuristics and NOT official government or automated fraud thresholds.
RISK_THRESHOLD_LOW_UPPER = 30.0     # [0.0, 30.0) -> LOW
RISK_THRESHOLD_MEDIUM_UPPER = 60.0  # [30.0, 60.0) -> MEDIUM
                                    # [60.0, 100.0] -> HIGH


class PrototypeRuleBasedRiskModel(BaseRiskModel):
    """
    Deterministic, prototype review-risk model implementing BaseRiskModel.
    Synthesizes non-PII verification features into a bounded review risk score (0.0–100.0)
    and an explainable risk level (LOW, MEDIUM, HIGH) to assist administrators during review.

    CRITICAL SAFEGUARDS:
    - Does NOT make automated scholarship approval or rejection decisions.
    - Does NOT label applicants as fraudulent or make fraud determinations.
    - Communicates review risk (need for manual administrative inspection).
    - Can be cleanly replaced by a trained scikit-learn or statistical model in the future.
    """

    model_name: str = "PrototypeRuleBasedRiskModel"
    model_version: str = "1.0"

    def predict(self, features: RiskFeatures) -> RiskPrediction:
        """
        Evaluate non-PII risk features and compute review risk score and explanations.
        """
        explanations: List[str] = []

        # 1. Base Review Risk derived from inverse of rules engine score (0.0 to 35.0 pts)
        # If overall_rule_score is 100, base_risk = 0. If 50, base_risk = 17.5. If 0, base_risk = 35.
        base_risk = (100.0 - features.overall_rule_score) * 0.35

        # 2. Risk Penalties from Specific Inconsistencies & Failures
        penalties = 0.0

        # Identity & Credential Discrepancies
        if features.government_id_mismatch_count > 0:
            penalties += 35.0
            explanations.append("Government ID number mismatch requires administrative verification.")

        if features.dob_mismatch_count > 0:
            penalties += 30.0
            explanations.append("Date of birth discrepancy detected between student profile and identity document.")

        if features.name_mismatch_count > 0:
            if features.name_mismatch_count > 1:
                penalties += 25.0
                explanations.append("Multiple name discrepancies detected across submitted documents.")
            else:
                penalties += 15.0
                explanations.append("Name variation detected across documents; administrative review recommended.")

        # Scheme Eligibility Issues
        if features.income_issue > 0:
            penalties += 25.0
            explanations.append("Income certificate details indicate household income may exceed scheme eligibility ceiling.")

        if features.domicile_issue > 0:
            penalties += 25.0
            explanations.append("Domicile certificate does not confirm Maharashtra state residence required for this scheme.")

        if features.marksheet_issue > 0:
            penalties += 20.0
            explanations.append("Academic marksheet percentage falls below minimum scheme eligibility requirement.")

        # Cross-Document Consistency & Warnings
        if features.cross_document_mismatch_count > 0:
            penalties += min(20.0, features.cross_document_mismatch_count * 10.0)
            if not any("name" in e.lower() for e in explanations):
                explanations.append("Inconsistencies detected across multiple submitted documents.")

        if features.warning_count > 0:
            penalties += min(15.0, features.warning_count * 5.0)
            if features.warning_count >= 2 and not any("warning" in e.lower() for e in explanations):
                explanations.append("Multiple non-critical warnings detected; manual officer review suggested.")

        # Low OCR Quality & Missing Fields
        if features.ocr_quality_score < 0.50:
            quality_penalty = (0.50 - features.ocr_quality_score) * 40.0
            penalties += quality_penalty
            explanations.append("OCR quality was low for one or more documents, increasing extraction review risk.")

        if features.missing_field_count > 0:
            penalties += min(15.0, features.missing_field_count * 3.0)
            explanations.append("One or more expected fields could not be extracted from the uploaded documents.")

        # Critical Failure Multiplier
        if features.critical_failure_count > 0:
            penalties += min(30.0, features.critical_failure_count * 15.0)
            if not any("critical" in e.lower() for e in explanations):
                explanations.append("Critical validation failures detected; elevated manual review required before scholarship decision.")

        # 3. Aggregate and Clamp Risk Score (0.0 to 100.0)
        raw_score = base_risk + penalties
        clamped_score = max(0.0, min(100.0, raw_score))
        risk_score = round(clamped_score, 1)

        # 4. Determine Risk Level
        if risk_score < RISK_THRESHOLD_LOW_UPPER:
            risk_level = RiskLevel.LOW
        elif risk_score < RISK_THRESHOLD_MEDIUM_UPPER:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.HIGH

        # 5. Default Positive Explanation for Clean Applications
        if not explanations:
            explanations.append("All required documents passed basic consistency and eligibility checks.")

        return RiskPrediction(
            risk_score=risk_score,
            risk_level=risk_level,
            model_name=self.model_name,
            model_version=self.model_version,
            explanation=explanations,
        )

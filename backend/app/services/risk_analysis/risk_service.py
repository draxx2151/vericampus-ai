from typing import Optional, Dict, Any, Union
from app.db.models.enums import DocumentType
from app.services.verification.base import DocumentExtractionResult
from app.services.verification.rules_engine import VerificationEvaluation
from app.services.risk_analysis.base import BaseRiskModel
from app.services.risk_analysis.schemas import (
    RiskFeatures,
    RiskPrediction,
    RiskAnalysisResult,
)
from app.services.risk_analysis.feature_builder import FeatureBuilder
from app.services.risk_analysis.risk_model import PrototypeRuleBasedRiskModel


class RiskService:
    """
    Orchestrates the ML/AI Risk Analysis Layer.
    Consumes rules-engine evaluation results and document extraction metadata,
    extracts non-PII features via FeatureBuilder, executes the pluggable BaseRiskModel,
    and returns an explainable RiskAnalysisResult.
    """

    def __init__(
        self,
        risk_model: Optional[BaseRiskModel] = None,
        feature_builder: Optional[FeatureBuilder] = None,
    ):
        self.risk_model = risk_model if risk_model is not None else PrototypeRuleBasedRiskModel()
        self.feature_builder = feature_builder if feature_builder is not None else FeatureBuilder()

    def analyze_risk(
        self,
        evaluation: VerificationEvaluation,
        extractions: Optional[Dict[Union[DocumentType, str], DocumentExtractionResult]] = None,
    ) -> RiskAnalysisResult:
        """
        Execute risk feature building and prediction.

        :param evaluation: VerificationEvaluation from RulesEngine.
        :param extractions: Mapping of DocumentType to DocumentExtractionResult.
        :return: RiskAnalysisResult with prediction and features.
        """
        features: RiskFeatures = self.feature_builder.build_features(
            evaluation=evaluation,
            extractions=extractions,
        )
        prediction: RiskPrediction = self.risk_model.predict(features)

        return RiskAnalysisResult(
            prediction=prediction,
            features=features,
        )

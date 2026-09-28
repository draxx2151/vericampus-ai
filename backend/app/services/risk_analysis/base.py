from abc import ABC, abstractmethod
from app.services.risk_analysis.schemas import RiskFeatures, RiskPrediction


class BaseRiskModel(ABC):
    """
    Abstract interface for verification review risk models.
    Can be backed by heuristic rules, scikit-learn models, or other statistical classifiers.
    The model provides administrative verification review assistance only and does NOT
    perform automated scholarship approvals, rejections, or fraud determinations.
    """

    model_name: str = "BaseRiskModel"
    model_version: str = "1.0"

    @abstractmethod
    def predict(self, features: RiskFeatures) -> RiskPrediction:
        """
        Evaluate non-PII risk features and return a bounded RiskPrediction.

        :param features: Numerical/categorical features from FeatureBuilder.
        :return: RiskPrediction with risk_score (0-100), risk_level, and explanations.
        """
        pass

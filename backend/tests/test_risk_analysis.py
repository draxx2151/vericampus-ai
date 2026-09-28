import unittest
import uuid
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.db.models.college import College
from app.db.models.student import Student
from app.db.models.admin_officer import AdminOfficer
from app.db.models.scholarship_application import ScholarshipApplication
from app.db.models.document import Document
from app.db.models.verification_result import VerificationResult
from app.db.models.enums import UserRole, ApplicationStatus, DocumentType, UploadStatus, VerificationStatus
from app.core.security import create_access_token, get_password_hash

from app.services.verification.base import (
    DocumentExtractionResult,
    ReadabilityScore,
    GovernmentIdExtraction,
    MarksheetExtraction,
    IncomeCertificateExtraction,
    DomicileCertificateExtraction,
)
from app.services.verification.rules_engine import (
    RulesEngine,
    CheckStatus,
    FieldCheckResult,
    CrossDocumentMatch,
    VerificationEvaluation,
)
from app.services.verification.mock_verifier import MockAIVerifier, MockScenario
from app.services.verification.verification_service import VerificationService
from app.services.risk_analysis import (
    RiskLevel,
    RiskFeatures,
    RiskPrediction,
    RiskAnalysisResult,
    BaseRiskModel,
    FeatureBuilder,
    PrototypeRuleBasedRiskModel,
    RiskService,
)

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


class TestRiskAnalysisLayer(unittest.TestCase):
    """
    Comprehensive unit & integration tests for Phase 6 Module 5:
    ML/AI Risk Analysis Layer.
    """

    @classmethod
    def setUpClass(cls):
        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

    def setUp(self):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        self.db = TestingSessionLocal()
        self._seed_data()
        self.risk_model = PrototypeRuleBasedRiskModel()
        self.risk_service = RiskService()

    def tearDown(self):
        self.db.close()

    def _seed_data(self):
        # 1. Colleges
        self.college1_id = uuid.uuid4()
        self.college2_id = uuid.uuid4()
        colleges = [
            College(id=self.college1_id, college_name="COEP Pune", college_code="COEP01", email="coep@demo.edu"),
            College(id=self.college2_id, college_name="VJTI Mumbai", college_code="VJTI02", email="vjti@demo.edu"),
        ]
        self.db.add_all(colleges)
        self.db.commit()

        # 2. Students
        self.student1_id = uuid.uuid4()
        self.student2_id = uuid.uuid4()
        students = [
            Student(
                id=self.student1_id,
                college_id=self.college1_id,
                full_name="Test Student",
                email="aarav@coep.edu",
                password_hash=get_password_hash("StudentPass123!"),
                date_of_birth=date(2004, 1, 15),
                government_id_number="TEST-1234-5678-9012",
                is_active=True,
            ),
            Student(
                id=self.student2_id,
                college_id=self.college2_id,
                full_name="Priya Ramesh Deshmukh",
                email="priya@vjti.edu",
                password_hash=get_password_hash("StudentPass123!"),
                date_of_birth=date(2004, 5, 20),
                government_id_number="9876 5432 1098",
                is_active=True,
            ),
        ]
        self.db.add_all(students)
        self.db.commit()

        # 3. Admin Officers
        self.admin1_id = uuid.uuid4()
        admins = [
            AdminOfficer(
                id=self.admin1_id,
                college_id=self.college1_id,
                full_name="Admin COEP",
                email="admin@coep.edu",
                password_hash=get_password_hash("AdminPass123!"),
                is_active=True,
            ),
        ]
        self.db.add_all(admins)
        self.db.commit()

        # 4. Applications
        self.app1_id = uuid.uuid4()
        applications = [
            ScholarshipApplication(
                id=self.app1_id,
                application_number="APP-COEP-2026-001",
                student_id=self.student1_id,
                scholarship_name="Rajarshi Chhatrapati Shahu Maharaj Shikshan Shulkh Shishyavrutti Yojna (EBC)",
                status=ApplicationStatus.SUBMITTED,
            ),
        ]
        self.db.add_all(applications)
        self.db.commit()

        # 5. Core 4 Documents for Application 1
        docs = [
            Document(
                id=uuid.uuid4(),
                application_id=self.app1_id,
                document_type=DocumentType.GOVERNMENT_ID,
                original_filename="aadhaar.pdf",
                storage_path=f"{self.app1_id}/government_id/aadhaar.pdf",
                upload_status=UploadStatus.UPLOADED,
            ),
            Document(
                id=uuid.uuid4(),
                application_id=self.app1_id,
                document_type=DocumentType.MARKSHEET,
                original_filename="hsc_marksheet.pdf",
                storage_path=f"{self.app1_id}/marksheet/hsc_marksheet.pdf",
                upload_status=UploadStatus.UPLOADED,
            ),
            Document(
                id=uuid.uuid4(),
                application_id=self.app1_id,
                document_type=DocumentType.INCOME_CERTIFICATE,
                original_filename="income_cert.pdf",
                storage_path=f"{self.app1_id}/income_certificate/income_cert.pdf",
                upload_status=UploadStatus.UPLOADED,
            ),
            Document(
                id=uuid.uuid4(),
                application_id=self.app1_id,
                document_type=DocumentType.DOMICILE_CERTIFICATE,
                original_filename="domicile_cert.pdf",
                storage_path=f"{self.app1_id}/domicile_certificate/domicile_cert.pdf",
                upload_status=UploadStatus.UPLOADED,
            ),
        ]
        self.db.add_all(docs)
        self.db.commit()

        # Generate auth tokens
        self.student1_token = create_access_token(
            subject=str(self.student1_id),
            role="STUDENT",
            college_id=str(self.college1_id),
        )
        self.admin1_token = create_access_token(
            subject=str(self.admin1_id),
            role="ADMIN",
            college_id=str(self.college1_id),
        )

    def _create_clean_evaluation(self) -> VerificationEvaluation:
        return VerificationEvaluation(
            overall_status=CheckStatus.PASS,
            overall_score=100.0,
            field_checks={
                "student_name_match": FieldCheckResult(
                    check_name="Student Name Match",
                    status=CheckStatus.PASS,
                    score=100.0,
                    details="Exact match",
                ),
                "date_of_birth_match": FieldCheckResult(
                    check_name="Date of Birth Match",
                    status=CheckStatus.PASS,
                    score=100.0,
                    details="Match",
                ),
                "government_id_match": FieldCheckResult(
                    check_name="Government ID Match",
                    status=CheckStatus.PASS,
                    score=100.0,
                    details="Match",
                ),
                "income_eligibility": FieldCheckResult(
                    check_name="Income Eligibility",
                    status=CheckStatus.PASS,
                    score=100.0,
                    details="Eligible",
                ),
                "domicile_eligibility": FieldCheckResult(
                    check_name="Domicile Eligibility",
                    status=CheckStatus.PASS,
                    score=100.0,
                    details="Maharashtra resident",
                ),
                "marksheet_performance": FieldCheckResult(
                    check_name="Marksheet Performance",
                    status=CheckStatus.PASS,
                    score=100.0,
                    details="Passed",
                ),
            },
            cross_document_matches=[
                CrossDocumentMatch(
                    check_name="Cross Document Name Check",
                    source_document="GOVERNMENT_ID",
                    target_document="MARKSHEET",
                    status=CheckStatus.PASS,
                    score=100.0,
                    details="Names match",
                )
            ],
            issues=[],
            critical_flags=[],
            recommended_status="VERIFIED",
        )

    # 1. Clean Successful Application -> Low Risk
    def test_01_clean_application_low_risk(self):
        evaluation = self._create_clean_evaluation()
        result = self.risk_service.analyze_risk(evaluation)

        self.assertIsInstance(result, RiskAnalysisResult)
        self.assertEqual(result.prediction.risk_level, RiskLevel.LOW)
        self.assertLess(result.prediction.risk_score, 30.0)
        self.assertGreaterEqual(result.prediction.risk_score, 0.0)
        self.assertTrue(any("passed basic consistency" in exp.lower() for exp in result.prediction.explanation))

    # 2. Single Non-Critical Warning -> Appropriately Increased Risk
    def test_02_single_warning_increased_risk(self):
        evaluation = self._create_clean_evaluation()
        evaluation.overall_score = 88.0
        evaluation.overall_status = CheckStatus.WARNING
        evaluation.field_checks["student_name_match"] = FieldCheckResult(
            check_name="Student Name Match",
            status=CheckStatus.WARNING,
            score=85.0,
            details="Minor initial variation detected",
            flag_code="NAME_VARIATION",
        )

        clean_eval = self._create_clean_evaluation()
        clean_res = self.risk_service.analyze_risk(clean_eval)
        warn_res = self.risk_service.analyze_risk(evaluation)

        self.assertGreater(warn_res.prediction.risk_score, clean_res.prediction.risk_score)
        self.assertIn(warn_res.prediction.risk_level, [RiskLevel.LOW, RiskLevel.MEDIUM])
        self.assertTrue(any("name variation" in exp.lower() for exp in warn_res.prediction.explanation))

    # 3. Multiple Warnings -> Medium Risk
    def test_03_multiple_warnings_medium_risk(self):
        evaluation = self._create_clean_evaluation()
        evaluation.overall_score = 72.0
        evaluation.overall_status = CheckStatus.WARNING
        evaluation.field_checks["student_name_match"] = FieldCheckResult(
            check_name="Student Name Match",
            status=CheckStatus.WARNING,
            score=80.0,
            details="Partial name variation",
            flag_code="NAME_VARIATION",
        )
        evaluation.field_checks["income_eligibility"] = FieldCheckResult(
            check_name="Income Eligibility",
            status=CheckStatus.WARNING,
            score=70.0,
            details="Income close to threshold",
        )
        evaluation.cross_document_matches = [
            CrossDocumentMatch(
                check_name="Cross Document Name Check",
                source_document="GOVERNMENT_ID",
                target_document="MARKSHEET",
                status=CheckStatus.WARNING,
                score=75.0,
                details="Minor name spelling difference",
            )
        ]

        res = self.risk_service.analyze_risk(evaluation)
        self.assertEqual(res.prediction.risk_level, RiskLevel.MEDIUM)
        self.assertGreaterEqual(res.prediction.risk_score, 30.0)
        self.assertLess(res.prediction.risk_score, 60.0)

    # 4. Critical Mismatch -> High Risk
    def test_04_critical_mismatch_high_risk(self):
        evaluation = self._create_clean_evaluation()
        evaluation.overall_score = 45.0
        evaluation.overall_status = CheckStatus.FAIL
        evaluation.critical_flags = ["GOVERNMENT_ID_MISMATCH", "NAME_MISMATCH"]
        evaluation.field_checks["government_id_match"] = FieldCheckResult(
            check_name="Government ID Match",
            status=CheckStatus.FAIL,
            score=0.0,
            details="ID mismatch",
            is_critical=True,
            flag_code="GOVERNMENT_ID_MISMATCH",
        )
        evaluation.field_checks["student_name_match"] = FieldCheckResult(
            check_name="Student Name Match",
            status=CheckStatus.FAIL,
            score=10.0,
            details="Significant name mismatch",
            is_critical=True,
            flag_code="NAME_MISMATCH",
        )

        res = self.risk_service.analyze_risk(evaluation)
        self.assertEqual(res.prediction.risk_level, RiskLevel.HIGH)
        self.assertGreaterEqual(res.prediction.risk_score, 60.0)
        self.assertTrue(any("government id" in exp.lower() for exp in res.prediction.explanation))
        self.assertTrue(any("name" in exp.lower() for exp in res.prediction.explanation))

    # 5. Missing Extraction Fields -> Increased Risk
    def test_05_missing_fields_increased_risk(self):
        evaluation = self._create_clean_evaluation()
        evaluation.overall_score = 80.0
        evaluation.field_checks["marksheet_performance"] = FieldCheckResult(
            check_name="Academic Marksheet Check",
            status=CheckStatus.NOT_AVAILABLE,
            score=0.0,
            details="Academic performance fields not available",
        )

        clean_eval = self._create_clean_evaluation()
        clean_res = self.risk_service.analyze_risk(clean_eval)
        missing_res = self.risk_service.analyze_risk(evaluation)

        self.assertGreater(missing_res.prediction.risk_score, clean_res.prediction.risk_score)
        self.assertGreater(missing_res.features.missing_field_count, 0)
        self.assertTrue(any("expected fields" in exp.lower() for exp in missing_res.prediction.explanation))

    # 6. Low OCR Quality -> Increased Risk
    def test_06_low_ocr_quality_increased_risk(self):
        evaluation = self._create_clean_evaluation()

        # Extractions with heavily degraded OCR
        degraded_extractions = {
            DocumentType.GOVERNMENT_ID: DocumentExtractionResult(
                document_type=DocumentType.GOVERNMENT_ID,
                extraction_success=True,
                readability=ReadabilityScore.LOW,
                extracted_fields=GovernmentIdExtraction(full_name="Aarav Patil"),
            ),
            DocumentType.MARKSHEET: DocumentExtractionResult(
                document_type=DocumentType.MARKSHEET,
                extraction_success=True,
                readability=ReadabilityScore.UNREADABLE,
                extracted_fields=None,
            ),
        }

        res = self.risk_service.analyze_risk(evaluation, extractions=degraded_extractions)
        self.assertLess(res.features.ocr_quality_score, 0.50)
        self.assertTrue(any("ocr quality" in exp.lower() for exp in res.prediction.explanation))

    # 7. Risk Score Always Clamped to 0.0 - 100.0
    def test_07_risk_score_clamping_0_to_100(self):
        # Scenario A: Maximum failures
        worst_features = RiskFeatures(
            identity_pass_rate=0.0,
            name_mismatch_count=10,
            dob_mismatch_count=1,
            government_id_mismatch_count=1,
            domicile_issue=1,
            income_issue=1,
            marksheet_issue=1,
            missing_field_count=10,
            warning_count=15,
            critical_failure_count=10,
            cross_document_mismatch_count=10,
            ocr_quality_score=0.0,
            overall_rule_score=0.0,
        )
        worst_pred = self.risk_model.predict(worst_features)
        self.assertEqual(worst_pred.risk_score, 100.0)
        self.assertEqual(worst_pred.risk_level, RiskLevel.HIGH)

        # Scenario B: Ideal features
        best_features = RiskFeatures(
            identity_pass_rate=1.0,
            name_mismatch_count=0,
            dob_mismatch_count=0,
            government_id_mismatch_count=0,
            domicile_issue=0,
            income_issue=0,
            marksheet_issue=0,
            missing_field_count=0,
            warning_count=0,
            critical_failure_count=0,
            cross_document_mismatch_count=0,
            ocr_quality_score=1.0,
            overall_rule_score=100.0,
        )
        best_pred = self.risk_model.predict(best_features)
        self.assertGreaterEqual(best_pred.risk_score, 0.0)
        self.assertLessEqual(best_pred.risk_score, 10.0)
        self.assertEqual(best_pred.risk_level, RiskLevel.LOW)

    # 8. Risk Level Always One of LOW, MEDIUM, HIGH
    def test_08_risk_level_always_valid_enum(self):
        for score in [0.0, 15.5, 29.9, 30.0, 45.0, 59.9, 60.0, 85.0, 100.0]:
            features = RiskFeatures(
                identity_pass_rate=1.0,
                name_mismatch_count=0,
                dob_mismatch_count=0,
                government_id_mismatch_count=0,
                domicile_issue=0,
                income_issue=0,
                marksheet_issue=0,
                missing_field_count=0,
                warning_count=0,
                critical_failure_count=0,
                cross_document_mismatch_count=0,
                ocr_quality_score=1.0,
                overall_rule_score=score,
            )
            pred = self.risk_model.predict(features)
            self.assertIn(pred.risk_level, [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH])

    # 9. No PII is Included in Generated Features
    def test_09_no_pii_in_features(self):
        evaluation = self._create_clean_evaluation()
        features = FeatureBuilder.build_features(evaluation)
        feature_dict = features.model_dump()

        # Verify no string fields containing names, IDs, phones, emails, or raw text
        prohibited_pii_keys = [
            "full_name", "student_name", "name", "email", "phone", "mobile",
            "aadhaar", "government_id_number", "id_number", "address", "raw_text", "text"
        ]
        for key in feature_dict.keys():
            self.assertNotIn(key.lower(), prohibited_pii_keys)

        # All values must be numerical floats or ints
        for val in feature_dict.values():
            self.assertIsInstance(val, (int, float))

    # 10. Deterministic Output: Same Input -> Same Result
    def test_10_deterministic_output(self):
        evaluation = self._create_clean_evaluation()
        res1 = self.risk_service.analyze_risk(evaluation)
        res2 = self.risk_service.analyze_risk(evaluation)

        self.assertEqual(res1.prediction.risk_score, res2.prediction.risk_score)
        self.assertEqual(res1.prediction.risk_level, res2.prediction.risk_level)
        self.assertEqual(res1.prediction.explanation, res2.prediction.explanation)
        self.assertEqual(res1.features.model_dump(), res2.features.model_dump())

    # 11. Existing Rules-Engine Decision is NOT Overridden by Risk Model
    def test_11_risk_model_does_not_override_rules_decision(self):
        # Even with a custom risk model returning maximum risk score 100.0,
        # the VerificationService must preserve the rules-engine's status VERIFIED.
        class HighRiskAdvisoryModel(BaseRiskModel):
            def predict(self, features: RiskFeatures) -> RiskPrediction:
                return RiskPrediction(
                    risk_score=99.0,
                    risk_level=RiskLevel.HIGH,
                    model_name="HighRiskAdvisoryModel",
                    model_version="1.0",
                    explanation=["Manual inspection requested by test advisory model."],
                )

        custom_risk_service = RiskService(risk_model=HighRiskAdvisoryModel())
        res = VerificationService.verify_application(
            db=self.db,
            app_id_str=self.app1_id,
            user_id_str=self.student1_id,
            role=UserRole.STUDENT,
            user_college_id_str=self.college1_id,
            risk_service=custom_risk_service,
        )

        # The rules engine passed, so status must remain VERIFIED
        self.assertEqual(res["status"], "VERIFIED")
        self.assertEqual(res["verification_status"], "VERIFIED")
        self.assertEqual(res["overall_score"], 100.0)

        # But the risk analysis output is present in the response
        self.assertIsNotNone(res.get("risk_analysis"))
        self.assertEqual(res["risk_analysis"]["risk_level"], "HIGH")
        self.assertEqual(res["risk_analysis"]["risk_score"], 99.0)

    # 12. Re-Verification Remains Deterministic & Preserves Risk Analysis
    def test_12_reverification_deterministic(self):
        res1 = VerificationService.verify_application(
            db=self.db,
            app_id_str=self.app1_id,
            user_id_str=self.student1_id,
            role=UserRole.STUDENT,
            user_college_id_str=self.college1_id,
        )
        res2 = VerificationService.verify_application(
            db=self.db,
            app_id_str=self.app1_id,
            user_id_str=self.student1_id,
            role=UserRole.STUDENT,
            user_college_id_str=self.college1_id,
        )

        self.assertEqual(res1["risk_analysis"]["risk_score"], res2["risk_analysis"]["risk_score"])
        self.assertEqual(res1["risk_analysis"]["risk_level"], res2["risk_analysis"]["risk_level"])
        self.assertEqual(res1["status"], res2["status"])

    # 13. Tenant Isolation Remains Enforced
    def test_13_tenant_isolation_preserved(self):
        # Cross-college admin cannot trigger verification or access verification result
        headers = {"Authorization": f"Bearer {self.admin1_token}"}
        # Attempt to access an application belonging to college 2
        app_other = ScholarshipApplication(
            id=uuid.uuid4(),
            application_number="APP-VJTI-2026-999",
            student_id=self.student2_id,  # college 2 student
            scholarship_name="Post Matric Scholarship to OBC Students",
            status=ApplicationStatus.SUBMITTED,
        )
        self.db.add(app_other)
        self.db.commit()

        # Admin of college 1 cannot verify application of college 2
        response = self.client.post(
            f"/api/v1/applications/{app_other.id}/verify",
            headers=headers,
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Cross-college", response.json()["detail"])

    # 14. Existing API Authentication Preserved
    def test_14_existing_auth_preserved(self):
        # Unauthenticated call rejected
        response = self.client.post(f"/api/v1/applications/{self.app1_id}/verify")
        self.assertEqual(response.status_code, 401)

        # Authenticated student call succeeds and includes risk_analysis
        headers = {"Authorization": f"Bearer {self.student1_token}"}
        response = self.client.post(f"/api/v1/applications/{self.app1_id}/verify", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("risk_analysis", data)
        self.assertEqual(data["risk_analysis"]["risk_level"], "LOW")
        self.assertIn("risk_score", data["risk_analysis"])

    # 15. Risk Analysis Persisted in VerificationResult in Database
    def test_15_risk_analysis_persistence_in_verification_result(self):
        VerificationService.verify_application(
            db=self.db,
            app_id_str=self.app1_id,
            user_id_str=self.student1_id,
            role=UserRole.STUDENT,
            user_college_id_str=self.college1_id,
        )

        db_result = self.db.query(VerificationResult).filter(
            VerificationResult.application_id == self.app1_id,
            VerificationResult.document_id.is_(None),
        ).first()

        self.assertIsNotNone(db_result)
        self.assertIsInstance(db_result.extracted_data, dict)
        self.assertIn("risk_analysis", db_result.extracted_data)
        saved_risk = db_result.extracted_data["risk_analysis"]
        self.assertEqual(saved_risk["risk_level"], "LOW")
        self.assertEqual(saved_risk["model_name"], "PrototypeRuleBasedRiskModel")
        self.assertEqual(saved_risk["model_version"], "1.0")


if __name__ == "__main__":
    unittest.main()

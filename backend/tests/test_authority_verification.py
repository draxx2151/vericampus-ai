"""
VeriCampus AI — Stage 5: Authority Verification Automated Test Suite
Comprehensive suite (35+ test cases) verifying:
1. Provider interface contract and fallback implementations (Unavailable, DigiLocker, NAD, Issuer)
2. Status definitions: MATCH, MISMATCH, NOT_AVAILABLE, BLOCKED, ERROR, PENDING
3. Evidence strength hierarchy: STRONG, MODERATE, WEAK, NONE
4. Provider versioning and non-sensitive verification_id audit format
5. Future-ready consent model and record freshness/status fields
6. Government ID safety: Last-4 alone never produces STRONG evidence
7. Reusable field matching for all 4 core document types with Stage 3 normalizer reuse
8. Missing authority field marked as NOT_AVAILABLE (never mismatch)
9. Multi-stage gating (Stage 1 low-quality -> BLOCKED, Stage 2 slot mismatch -> BLOCKED, Stage 3 empty -> BLOCKED)
10. Stage 4 non-interference: Stage 4 warnings/discrepancies do NOT block Stage 5
11. No-network-call safety test (100% offline-safe, zero socket calls)
12. Error, timeout, and retry handling producing sanitized ERROR status
13. Sensitive PII masking across schemas and responses
14. Tenant isolation (student ownership, admin college isolation, cross-college 403)
15. Safe re-verification merge preserving authority verification and audit history
16. Non-punitive routing: NOT_AVAILABLE, BLOCKED, ERROR never reject; MISMATCH routes to NEEDS_REVIEW
17. Stage 6 Evidence Engine contract compliance
18. Dedicated API endpoint GET /{id}/authority-verification
"""
import sys
from pathlib import Path

# Ensure both backend/ and root are on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
root_dir = backend_dir.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import unittest
import uuid
import socket
from datetime import datetime
from unittest.mock import patch, MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi import HTTPException

# Ensure backend and ml imports work
from app.db.base import Base
from app.db.models.enums import DocumentType, ApplicationStatus, VerificationStatus, UserRole
from app.db.models.student import Student
from app.db.models.college import College
from app.db.models.scholarship_application import ScholarshipApplication
from app.db.models.document import Document
from app.db.models.verification_result import VerificationResult
from app.services.verification import VerificationService, MockAIVerifier

from ml.authority_verification import (
    AuthorityStatus,
    EvidenceStrength,
    ConsentStatus,
    RecordStatus,
    FieldMatchStatus,
    FieldComparisonResult,
    AuthorityVerificationResult,
    Stage5VerificationResult,
    AuthorityVerificationProvider,
    UnavailableProvider,
    DigiLockerProvider,
    NADProvider,
    IssuerProvider,
    AuthorityVerificationService,
    STAGE5_VERSION,
)
from ml.authority_verification.matching import (
    compare_names,
    compare_dates,
    compare_identifiers,
    match_government_id_fields,
    match_marksheet_fields,
    match_income_certificate_fields,
    match_domicile_certificate_fields,
)
from ml.authority_verification.scorer import synthesize_stage5_result


class SyntheticMockProvider(AuthorityVerificationProvider):
    """Synthetic test fixture provider for testing MATCH/MISMATCH pathways."""
    def __init__(self, records: dict):
        self.records = records

    @property
    def provider_name(self) -> str:
        return "synthetic_test_provider"

    def is_available(self) -> bool:
        return True

    def verify(self, document_type: str, extracted_fields: dict, context=None):
        auth_rec = self.records.get(document_type)
        if not auth_rec:
            return AuthorityVerificationResult(
                document_type=document_type,
                provider=self.provider_name,
                verification_id=f"av-test-{uuid.uuid4().hex[:8]}",
                status=AuthorityStatus.NOT_AVAILABLE,
                evidence_strength=EvidenceStrength.NONE,
                reason="No authority record found in test fixture.",
                is_available=True,
            )

        if document_type == "government_id":
            comps, strength, status = match_government_id_fields(extracted_fields, auth_rec)
        elif document_type == "marksheet":
            comps, strength, status = match_marksheet_fields(extracted_fields, auth_rec)
        elif document_type == "income_certificate":
            comps, strength, status = match_income_certificate_fields(extracted_fields, auth_rec)
        else:
            comps, strength, status = match_domicile_certificate_fields(extracted_fields, auth_rec)

        matched = [k for k, v in comps.items() if v.status == FieldMatchStatus.MATCH]
        mismatched = [k for k, v in comps.items() if v.status == FieldMatchStatus.MISMATCH]
        verified = list(comps.keys())

        return AuthorityVerificationResult(
            document_type=document_type,
            provider=self.provider_name,
            verification_id=f"av-test-{uuid.uuid4().hex[:8]}",
            status=status,
            evidence_strength=strength,
            consent_status=ConsentStatus.GRANTED,
            record_status=RecordStatus.ACTIVE,
            verified_fields=verified,
            matched_fields=matched,
            mismatched_fields=mismatched,
            field_comparisons=comps,
            reference_id="********1098" if document_type == "government_id" else None,
            reason=f"Synthetic evaluation resulted in {status.value}.",
            is_available=True,
        )


class TestAuthorityVerification(unittest.TestCase):
    """Comprehensive Stage 5 Authority Verification Test Suite."""

    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=cls.engine)
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

    def setUp(self):
        self.db = self.SessionLocal()
        self.college1_id = uuid.uuid4()
        self.college2_id = uuid.uuid4()
        code1 = f"ENG_{uuid.uuid4().hex[:6]}"
        code2 = f"SCI_{uuid.uuid4().hex[:6]}"

        col1 = College(id=self.college1_id, college_name="Engineering College A", college_code=code1)
        col2 = College(id=self.college2_id, college_name="Science College B", college_code=code2)
        self.db.add_all([col1, col2])

        self.student1_id = uuid.uuid4()
        self.student1 = Student(
            id=self.student1_id,
            college_id=self.college1_id,
            full_name="Amit Rajesh Patil",
            email=f"amit.{uuid.uuid4().hex[:6]}@example.edu",
        )
        self.db.add(self.student1)

        self.app1_id = uuid.uuid4()
        self.app1 = ScholarshipApplication(
            id=self.app1_id,
            student_id=self.student1_id,
            scholarship_name="Post Matric Scholarship to VJNT Students",
            application_number=f"APP-AUTH-{uuid.uuid4().hex[:6]}",
            status=ApplicationStatus.SUBMITTED,
        )
        self.db.add(self.app1)

        for dt in [DocumentType.GOVERNMENT_ID, DocumentType.MARKSHEET, DocumentType.INCOME_CERTIFICATE, DocumentType.DOMICILE_CERTIFICATE]:
            doc = Document(
                id=uuid.uuid4(),
                application_id=self.app1_id,
                document_type=dt,
                original_filename=f"{dt.value.lower()}.pdf",
                storage_path=f"storage/{dt.value.lower()}.pdf",
            )
            self.db.add(doc)

        self.db.commit()

    def tearDown(self):
        self.db.rollback()
        for table in reversed(Base.metadata.sorted_tables):
            try:
                self.db.execute(table.delete())
            except Exception:
                pass
        self.db.commit()
        self.db.close()

    # --------------------------------------------------------------------------
    # 1. Provider Interfaces and Fallbacks
    # --------------------------------------------------------------------------
    def test_01_unavailable_provider_default(self):
        """1. UnavailableProvider returns NOT_AVAILABLE with NONE evidence."""
        provider = UnavailableProvider()
        self.assertEqual(provider.provider_name, "unavailable")
        self.assertFalse(provider.is_available())
        res = provider.verify("government_id", {"name": "Amit Patil"})
        self.assertEqual(res.status, AuthorityStatus.NOT_AVAILABLE)
        self.assertEqual(res.evidence_strength, EvidenceStrength.NONE)
        self.assertFalse(res.is_available)
        self.assertTrue(res.verification_id.startswith("av-"))
        self.assertEqual(res.consent_status, ConsentStatus.NOT_REQUIRED)
        self.assertEqual(res.record_status, RecordStatus.NOT_AVAILABLE)

    def test_02_digilocker_provider_unconfigured(self):
        """2. DigiLockerProvider unconfigured returns NOT_AVAILABLE."""
        provider = DigiLockerProvider()
        self.assertFalse(provider.is_available())
        res = provider.verify("marksheet", {"student_name": "Amit Patil"})
        self.assertEqual(res.status, AuthorityStatus.NOT_AVAILABLE)
        self.assertEqual(res.evidence_strength, EvidenceStrength.NONE)
        self.assertEqual(res.consent_status, ConsentStatus.REQUIRED)
        self.assertIn("credentials", res.reason.lower())

    def test_03_nad_provider_unconfigured(self):
        """3. NADProvider unconfigured returns NOT_AVAILABLE."""
        provider = NADProvider()
        self.assertFalse(provider.is_available())
        res = provider.verify("marksheet", {"student_name": "Amit Patil"})
        self.assertEqual(res.status, AuthorityStatus.NOT_AVAILABLE)
        self.assertEqual(res.evidence_strength, EvidenceStrength.NONE)
        self.assertIn("depository", res.reason.lower())

    def test_04_issuer_provider_unconfigured(self):
        """4. IssuerProvider unconfigured returns NOT_AVAILABLE."""
        provider = IssuerProvider(issuer_code="MSBSHSE")
        self.assertFalse(provider.is_available())
        res = provider.verify("marksheet", {"student_name": "Amit Patil"})
        self.assertEqual(res.status, AuthorityStatus.NOT_AVAILABLE)
        self.assertIn("MSBSHSE", res.reason)

    # --------------------------------------------------------------------------
    # 2. Schemas, Statuses, and Versioning
    # --------------------------------------------------------------------------
    def test_05_authority_status_enum_invariants(self):
        """5. Validate AuthorityStatus enum values including BLOCKED and ERROR."""
        self.assertEqual(AuthorityStatus.MATCH.value, "MATCH")
        self.assertEqual(AuthorityStatus.MISMATCH.value, "MISMATCH")
        self.assertEqual(AuthorityStatus.NOT_AVAILABLE.value, "NOT_AVAILABLE")
        self.assertEqual(AuthorityStatus.BLOCKED.value, "BLOCKED")
        self.assertEqual(AuthorityStatus.ERROR.value, "ERROR")
        self.assertEqual(AuthorityStatus.PENDING.value, "PENDING")

    def test_06_evidence_strength_hierarchy(self):
        """6. Validate EvidenceStrength hierarchy."""
        self.assertEqual(EvidenceStrength.STRONG.value, "STRONG")
        self.assertEqual(EvidenceStrength.MODERATE.value, "MODERATE")
        self.assertEqual(EvidenceStrength.WEAK.value, "WEAK")
        self.assertEqual(EvidenceStrength.NONE.value, "NONE")

    def test_07_provider_versioning_and_verification_id(self):
        """7. Result contains valid provider_version and non-sensitive verification_id."""
        provider = UnavailableProvider()
        res = provider.verify("government_id", {})
        self.assertEqual(res.provider_version, "1.0.0")
        self.assertTrue(res.verification_id.startswith("av-"))
        self.assertNotIn("9876", res.verification_id)

    def test_08_consent_and_record_freshness_defaults(self):
        """8. ConsentStatus and RecordStatus default to NOT_REQUIRED and NOT_AVAILABLE."""
        provider = UnavailableProvider()
        res = provider.verify("government_id", {})
        self.assertEqual(res.consent_status, ConsentStatus.NOT_REQUIRED)
        self.assertEqual(res.record_status, RecordStatus.NOT_AVAILABLE)

    # --------------------------------------------------------------------------
    # 3. Government ID Last-4 Safety & Field Matching
    # --------------------------------------------------------------------------
    def test_09_govt_id_last4_alone_never_strong(self):
        """9. Government ID last-4 alone must NEVER produce STRONG evidence (max MODERATE/WEAK)."""
        # Case A: Last-4 matches, but name and DOB do NOT match
        comps, strength, status = match_government_id_fields(
            extracted={"id_number": "1234 5678 1098", "name": "Document Name", "date_of_birth": "2000-01-01"},
            authority={"id_number": "9999 0000 1098", "name": "Different Authority Name", "date_of_birth": "1999-05-05"},
        )
        self.assertEqual(status, AuthorityStatus.MISMATCH)  # Name/DOB conflict causes MISMATCH

        # Case B: Last-4 matches without other fields present -> WEAK evidence
        comps, strength, status = match_government_id_fields(
            extracted={"id_number": "1234 5678 1098"},
            authority={"id_number": "9999 0000 1098"},
        )
        self.assertEqual(status, AuthorityStatus.MATCH)
        self.assertEqual(strength, EvidenceStrength.WEAK)
        self.assertNotEqual(strength, EvidenceStrength.STRONG)

        # Case C: Last-4 matches AND name + DOB match -> MODERATE (never STRONG for last-4)
        comps, strength, status = match_government_id_fields(
            extracted={"id_number": "1234 5678 1098", "name": "Amit Patil", "date_of_birth": "2004-05-14"},
            authority={"id_number": "9999 0000 1098", "name": "Amit Patil", "date_of_birth": "2004-05-14"},
            is_full_authorized_match=False
        )
        self.assertEqual(status, AuthorityStatus.MATCH)
        self.assertEqual(strength, EvidenceStrength.MODERATE)
        self.assertNotEqual(strength, EvidenceStrength.STRONG)

    def test_10_govt_id_full_authorized_match_strong(self):
        """10. Full authorized ID match with verified fields produces STRONG evidence."""
        comps, strength, status = match_government_id_fields(
            extracted={"id_number": "987654321098", "name": "Amit Patil", "date_of_birth": "2004-05-14"},
            authority={"id_number": "987654321098", "name": "Amit Patil", "date_of_birth": "2004-05-14"},
            is_full_authorized_match=True
        )
        self.assertEqual(status, AuthorityStatus.MATCH)
        self.assertEqual(strength, EvidenceStrength.STRONG)

    def test_11_govt_id_last4_mismatch(self):
        """11. Government ID last-4 discrepancy causes MISMATCH."""
        comps, strength, status = match_government_id_fields(
            extracted={"id_number": "9876 5432 1098", "name": "Amit Patil"},
            authority={"id_number": "9876 5432 9999", "name": "Amit Patil"},
        )
        self.assertEqual(status, AuthorityStatus.MISMATCH)
        self.assertEqual(strength, EvidenceStrength.NONE)
        self.assertEqual(comps["id_number"].status, FieldMatchStatus.MISMATCH)

    # --------------------------------------------------------------------------
    # 4. Marksheet, Income, and Domicile Matching
    # --------------------------------------------------------------------------
    def test_12_marksheet_field_matching_tolerance(self):
        """12. Marksheet total marks matches within tolerance (+/- 2 marks)."""
        comps, strength, status = match_marksheet_fields(
            extracted={"student_name": "Amit Patil", "roll_number": "R100", "passing_year": "2024", "total_marks": "450"},
            authority={"student_name": "Amit Patil", "roll_number": "R100", "passing_year": "2024", "total_marks": "451"},
        )
        self.assertEqual(status, AuthorityStatus.MATCH)
        self.assertEqual(comps["total_marks"].status, FieldMatchStatus.MATCH)

    def test_13_marksheet_passing_year_mismatch(self):
        """13. Marksheet passing year conflict causes MISMATCH."""
        comps, strength, status = match_marksheet_fields(
            extracted={"student_name": "Amit Patil", "roll_number": "R100", "passing_year": "2024"},
            authority={"student_name": "Amit Patil", "roll_number": "R100", "passing_year": "2023"},
        )
        self.assertEqual(status, AuthorityStatus.MISMATCH)
        self.assertEqual(comps["passing_year"].status, FieldMatchStatus.MISMATCH)

    def test_14_income_certificate_matching_tolerance(self):
        """14. Income Certificate matches within Rs. 1,000 tolerance."""
        comps, strength, status = match_income_certificate_fields(
            extracted={"applicant_name": "Amit Patil", "certificate_number": "INC-01", "annual_income": "150000"},
            authority={"applicant_name": "Amit Patil", "certificate_number": "INC-01", "annual_income": "150500"},
        )
        self.assertEqual(status, AuthorityStatus.MATCH)
        self.assertEqual(comps["annual_income"].status, FieldMatchStatus.MATCH)

    def test_15_income_certificate_mismatch_exceeds_tolerance(self):
        """15. Income Certificate discrepancy exceeding tolerance causes MISMATCH."""
        comps, strength, status = match_income_certificate_fields(
            extracted={"applicant_name": "Amit Patil", "certificate_number": "INC-01", "annual_income": "150000"},
            authority={"applicant_name": "Amit Patil", "certificate_number": "INC-01", "annual_income": "250000"},
        )
        self.assertEqual(status, AuthorityStatus.MISMATCH)
        self.assertEqual(comps["annual_income"].status, FieldMatchStatus.MISMATCH)

    def test_16_domicile_certificate_matching(self):
        """16. Domicile Certificate matches applicant, certificate number, and state."""
        comps, strength, status = match_domicile_certificate_fields(
            extracted={"applicant_name": "Amit Patil", "certificate_number": "DOM-01", "state": "Maharashtra"},
            authority={"applicant_name": "Amit Patil", "certificate_number": "DOM-01", "state": "Maharashtra"},
        )
        self.assertEqual(status, AuthorityStatus.MATCH)
        self.assertEqual(comps["state"].status, FieldMatchStatus.MATCH)

    def test_17_domicile_certificate_state_mismatch(self):
        """17. Domicile Certificate state discrepancy causes MISMATCH."""
        comps, strength, status = match_domicile_certificate_fields(
            extracted={"applicant_name": "Amit Patil", "certificate_number": "DOM-01", "state": "Maharashtra"},
            authority={"applicant_name": "Amit Patil", "certificate_number": "DOM-01", "state": "Karnataka"},
        )
        self.assertEqual(status, AuthorityStatus.MISMATCH)
        self.assertEqual(comps["state"].status, FieldMatchStatus.MISMATCH)

    def test_18_missing_authority_field_is_not_available(self):
        """18. Missing authority field marked as NOT_AVAILABLE (never mismatch)."""
        res = compare_names(extracted_name="Amit Patil", authority_name=None)
        self.assertEqual(res.status, FieldMatchStatus.NOT_AVAILABLE)
        self.assertNotEqual(res.status, FieldMatchStatus.MISMATCH)

    def test_19_normalizer_reuse_token_permutation(self):
        """19. Name normalizer reordering matches correctly without forcing title-case."""
        res = compare_names("Patil Amit Rajesh", "Amit Rajesh Patil")
        self.assertEqual(res.status, FieldMatchStatus.MATCH)
        self.assertGreaterEqual(res.confidence, 0.95)

    def test_20_normalizer_reuse_flexible_iso_date(self):
        """20. Date comparison handles Indian DD/MM/YYYY vs ISO YYYY-MM-DD."""
        res = compare_dates("date_of_birth", "14/05/2004", "2004-05-14")
        self.assertEqual(res.status, FieldMatchStatus.MATCH)
        self.assertEqual(res.extracted_value, "2004-05-14")

    # --------------------------------------------------------------------------
    # 5. Multi-Stage Gating & Stage 4 Non-Interference
    # --------------------------------------------------------------------------
    def test_21_stage1_low_quality_gating_produces_blocked(self):
        """21. Stage 1 low-quality document causes Stage 5 to return BLOCKED (not MISMATCH)."""
        service = AuthorityVerificationService()
        res = service.verify_document(
            document_type="government_id",
            extracted_data={"name": "Amit Patil"},
            quality_info={"quality_score": 50.0, "quality_gate_status": "FAIL"},
        )
        self.assertEqual(res.status, AuthorityStatus.BLOCKED)
        self.assertEqual(res.evidence_strength, EvidenceStrength.NONE)
        self.assertIn("quality is insufficient", res.reason)

    def test_22_stage2_slot_mismatch_gating_produces_blocked(self):
        """22. Stage 2 slot mismatch causes Stage 5 to return BLOCKED."""
        service = AuthorityVerificationService()
        res = service.verify_document(
            document_type="government_id",
            extracted_data={"name": "Amit Patil"},
            classification_info={"classification_status": "DOCUMENT_TYPE_MISMATCH"},
        )
        self.assertEqual(res.status, AuthorityStatus.BLOCKED)
        self.assertIn("mismatch", res.reason.lower())

    def test_23_stage2_unknown_classification_produces_blocked(self):
        """23. Stage 2 UNKNOWN classification causes Stage 5 to return BLOCKED."""
        service = AuthorityVerificationService()
        res = service.verify_document(
            document_type="marksheet",
            extracted_data={"student_name": "Amit Patil"},
            classification_info={"classification_status": "UNKNOWN"},
        )
        self.assertEqual(res.status, AuthorityStatus.BLOCKED)

    def test_24_stage3_empty_extraction_produces_blocked(self):
        """24. Missing or empty Stage 3 extraction produces BLOCKED."""
        service = AuthorityVerificationService()
        res = service.verify_document(
            document_type="income_certificate",
            extracted_data={},
        )
        self.assertEqual(res.status, AuthorityStatus.BLOCKED)
        self.assertIn("missing or failed", res.reason)

    def test_25_stage4_tamper_warning_does_not_block_stage5(self):
        """25. Stage 4 advisory tamper warnings do NOT block Stage 5 execution."""
        mock_provider = SyntheticMockProvider({
            "government_id": {"name": "Amit Patil", "id_number": "987654321098"}
        })
        service = AuthorityVerificationService(provider=mock_provider)
        res = service.verify_application(
            extractions={"government_id": {"name": "Amit Patil", "id_number": "9876 5432 1098"}},
            tamper_results={"overall_status": "WARNING", "warnings": ["Local blur variance detected"]},
        )
        # Stage 5 should still evaluate government_id
        govt_res = res.documents["government_id"]
        self.assertEqual(govt_res.status, AuthorityStatus.MATCH)

    def test_26_stage4_critical_discrepancy_allows_stage5(self):
        """26. Stage 4 critical discrepancy allows Stage 5 to run as independent evidence."""
        mock_provider = SyntheticMockProvider({
            "marksheet": {"student_name": "Amit Patil", "passing_year": "2024", "roll_number": "R1"}
        })
        service = AuthorityVerificationService(provider=mock_provider)
        res = service.verify_application(
            extractions={"marksheet": {"student_name": "Amit Patil", "passing_year": "2024", "roll_number": "R1"}},
            tamper_results={"overall_status": "NEEDS_REVIEW", "critical_inconsistencies": ["DOB mismatch between ID and Marksheet"]},
        )
        self.assertEqual(res.documents["marksheet"].status, AuthorityStatus.MATCH)

    # --------------------------------------------------------------------------
    # 6. Offline Safety, Error Handling, and Retry
    # --------------------------------------------------------------------------
    def test_27_no_network_call_safety(self):
        """27. Automated regression asserting default UnavailableProvider makes zero socket calls."""
        with patch.object(socket.socket, "connect") as mock_connect:
            service = AuthorityVerificationService()
            res = service.verify_application(
                extractions={"government_id": {"name": "Amit Patil", "id_number": "1234 5678 1098"}}
            )
            # Assert socket.connect was NEVER called
            mock_connect.assert_not_called()
            self.assertEqual(res.overall_status, AuthorityStatus.NOT_AVAILABLE)

    def test_28_provider_error_and_timeout_produces_error_status(self):
        """28. Provider timeout/exception safely produces ERROR status without crash or rejection."""
        class FlakyProvider(AuthorityVerificationProvider):
            @property
            def provider_name(self):
                return "flaky"
            def is_available(self):
                return True
            def verify(self, document_type, extracted_fields, context=None, **kwargs):
                raise TimeoutError("Provider API gateway timeout")

        service = AuthorityVerificationService(provider=FlakyProvider())
        res = service.verify_document("government_id", {"name": "Amit Patil"})
        self.assertEqual(res.status, AuthorityStatus.ERROR)
        self.assertEqual(res.evidence_strength, EvidenceStrength.NONE)
        self.assertIn("timed out", res.reason.lower())

    def test_29_provider_retry_mechanism(self):
        """29. Provider retries transient connection errors up to max retries."""
        call_count = {"count": 0}

        class TransientProvider(AuthorityVerificationProvider):
            @property
            def provider_name(self):
                return "transient"
            def is_available(self):
                return True
            def verify(self, document_type, extracted_fields, context=None, **kwargs):
                call_count["count"] += 1
                if call_count["count"] < 2:
                    raise ConnectionError("Temporary connection dropped")
                return AuthorityVerificationResult(
                    document_type=document_type, provider="transient", verification_id="av-1",
                    status=AuthorityStatus.MATCH, reason="Success after retry",
                )

        service = AuthorityVerificationService(provider=TransientProvider())
        res = service.verify_document("government_id", {"name": "Amit Patil"})
        self.assertEqual(call_count["count"], 2)
        self.assertEqual(res.status, AuthorityStatus.MATCH)

    # --------------------------------------------------------------------------
    # 7. Sensitive PII Masking and Security
    # --------------------------------------------------------------------------
    def test_30_sensitive_id_masking_enforcement(self):
        """30. Raw 12-digit Aadhaar in reference_id is automatically masked."""
        res = AuthorityVerificationResult(
            document_type="government_id",
            provider="unavailable",
            verification_id="av-100",
            status=AuthorityStatus.NOT_AVAILABLE,
            evidence_strength=EvidenceStrength.NONE,
            reference_id="987654321098",  # Raw 12 digits
            reason="Test masking",
        )
        self.assertEqual(res.reference_id, "********1098")
        self.assertNotIn("98765432", res.reference_id)

    def test_31_tenant_isolation_student_ownership(self):
        """31. Student can only access their own authority verification result."""
        # Run verify_application to populate result
        VerificationService.verify_application(
            db=self.db,
            app_id_str=self.app1_id,
            user_id_str=self.student1_id,
            role=UserRole.STUDENT,
        )

        # Successful access by student owner
        res = VerificationService.get_authority_verification_result(
            db=self.db,
            app_id_str=self.app1_id,
            user_id_str=self.student1_id,
            role=UserRole.STUDENT,
        )
        self.assertIn("overall_status", res)
        self.assertEqual(res["application_id"], str(self.app1_id))

    def test_32_tenant_isolation_cross_student_forbidden(self):
        """32. Cross-student access returns HTTP 403 Forbidden."""
        peer_student_id = uuid.uuid4()
        with self.assertRaises(HTTPException) as ctx:
            VerificationService.get_authority_verification_result(
                db=self.db,
                app_id_str=self.app1_id,
                user_id_str=peer_student_id,
                role=UserRole.STUDENT,
            )
        self.assertEqual(ctx.exception.status_code, 403)

    def test_33_tenant_isolation_admin_same_college_allowed(self):
        """33. Admin from the same college can access authority verification."""
        res = VerificationService.get_authority_verification_result(
            db=self.db,
            app_id_str=self.app1_id,
            user_id_str=uuid.uuid4(),
            role=UserRole.ADMIN,
            user_college_id_str=self.college1_id,
        )
        self.assertIn("overall_status", res)

    def test_34_tenant_isolation_cross_college_forbidden(self):
        """34. Cross-college admin access returns HTTP 403 Forbidden."""
        with self.assertRaises(HTTPException) as ctx:
            VerificationService.get_authority_verification_result(
                db=self.db,
                app_id_str=self.app1_id,
                user_id_str=uuid.uuid4(),
                role=UserRole.ADMIN,
                user_college_id_str=self.college2_id,  # College 2 attempting College 1 application
            )
        self.assertEqual(ctx.exception.status_code, 403)

    # --------------------------------------------------------------------------
    # 8. Re-Verification Safe Merge & Non-Punitive Review Routing
    # --------------------------------------------------------------------------
    def test_35_reverification_preserves_authority_verification(self):
        """35. Re-verification safe merge preserves authority verification metadata."""
        # Initial verification run
        initial_res = VerificationService.verify_application(
            db=self.db,
            app_id_str=self.app1_id,
            user_id_str=self.student1_id,
            role=UserRole.STUDENT,
        )
        self.assertIn("authority_verification", initial_res)

        # Run re-verification
        re_res = VerificationService.verify_application(
            db=self.db,
            app_id_str=self.app1_id,
            user_id_str=self.student1_id,
            role=UserRole.STUDENT,
        )
        self.assertIn("authority_verification", re_res)
        self.assertEqual(re_res["authority_verification"]["stage_version"], STAGE5_VERSION)

    def test_36_non_punitive_routing_not_available_does_not_reject(self):
        """36. AuthorityStatus.NOT_AVAILABLE does not lower score or reject scholarship."""
        res = VerificationService.verify_application(
            db=self.db,
            app_id_str=self.app1_id,
            user_id_str=self.student1_id,
            role=UserRole.STUDENT,
        )
        self.assertNotEqual(res["verification_status"], "REJECTED")
        self.assertEqual(res["authority_verification"]["overall_status"], "NOT_AVAILABLE")

    def test_37_authority_mismatch_routes_to_needs_review(self):
        """37. AuthorityStatus.MISMATCH routes application to NEEDS_REVIEW (never REJECTED)."""
        mismatch_provider = SyntheticMockProvider({
            "government_id": {
                "name": "Amit Patil",
                "date_of_birth": "1990-01-01",  # Deliberate mismatch against 2004
                "id_number": "0000 0000 0000"
            }
        })
        mismatch_service = AuthorityVerificationService(provider=mismatch_provider)

        res = VerificationService.verify_application(
            db=self.db,
            app_id_str=self.app1_id,
            user_id_str=self.student1_id,
            role=UserRole.STUDENT,
            authority_service=mismatch_service,
        )
        self.assertEqual(res["verification_status"], "NEEDS_REVIEW")
        self.assertNotEqual(res["verification_status"], "REJECTED")
        self.assertEqual(res["authority_verification"]["overall_status"], "MISMATCH")
        self.assertTrue(res["authority_verification"]["review_required"])
        # Verify issue added
        has_auth_issue = any("Stage 5 Authority Mismatch" in issue for issue in res["issues"])
        self.assertTrue(has_auth_issue)

    def test_38_stage6_evidence_contract_non_negative(self):
        """38. Stage 6 contract: NOT_AVAILABLE, BLOCKED, and ERROR have review_required = False."""
        doc_unav = AuthorityVerificationResult(
            document_type="marksheet", provider="unavailable", verification_id="av-1",
            status=AuthorityStatus.NOT_AVAILABLE, reason="No provider",
        )
        doc_blocked = AuthorityVerificationResult(
            document_type="government_id", provider="unavailable", verification_id="av-2",
            status=AuthorityStatus.BLOCKED, reason="Low quality",
        )
        doc_error = AuthorityVerificationResult(
            document_type="income_certificate", provider="unavailable", verification_id="av-3",
            status=AuthorityStatus.ERROR, reason="Timeout",
        )

        synth_result = synthesize_stage5_result({
            "marksheet": doc_unav,
            "government_id": doc_blocked,
            "income_certificate": doc_error,
        })
        # Crucial contract check: None of these should trigger review_required = True
        self.assertFalse(synth_result.review_required)
        self.assertEqual(synth_result.overall_evidence_strength, EvidenceStrength.NONE)


if __name__ == "__main__":
    unittest.main()

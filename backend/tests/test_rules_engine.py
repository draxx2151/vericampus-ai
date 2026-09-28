import unittest
from datetime import date

from app.db.models.enums import DocumentType
from app.services.verification import (
    MockAIVerifier,
    MockScenario,
    ReadabilityScore,
    RulesEngine,
    NameMatcher,
    CheckStatus,
    GovernmentIdExtraction,
    MarksheetExtraction,
    IncomeCertificateExtraction,
    DomicileCertificateExtraction,
    DocumentExtractionResult,
)


class TestRulesEngine(unittest.TestCase):
    """
    Focused unit tests for Phase 6 Module 2 — Cross-Verification & Eligibility Rules Engine.
    Validates name matching, DOB comparison, ID masking, cross-document correlation,
    scheme eligibility, quality checks, scoring, and critical flags without database or network.
    """

    def setUp(self):
        self.engine = RulesEngine()
        self.mock_verifier = MockAIVerifier()

        # Standard Baseline Student Profile
        self.student_profile = {
            "full_name": "Test Student",
            "date_of_birth": "2004-01-15",
            "government_id_number": "TEST-1234-5678-9012"
        }

        # Standard Baseline Application (EBC Scheme: Income limit ₹8,00,000, Min marks 50%, Requires MH domicile)
        self.application = {
            "scholarship_name": "Rajarshi Chhatrapati Shahu Maharaj Shikshan Shulkh Shishyavrutti Yojna (EBC)"
        }

        # Baseline Clean Extractions for 4 Documents
        self.standard_extractions = {
            DocumentType.GOVERNMENT_ID: self.mock_verifier.extract_document("gov_id.pdf", DocumentType.GOVERNMENT_ID),
            DocumentType.MARKSHEET: self.mock_verifier.extract_document("marksheet.pdf", DocumentType.MARKSHEET),
            DocumentType.INCOME_CERTIFICATE: self.mock_verifier.extract_document("income.pdf", DocumentType.INCOME_CERTIFICATE),
            DocumentType.DOMICILE_CERTIFICATE: self.mock_verifier.extract_document("domicile.pdf", DocumentType.DOMICILE_CERTIFICATE),
        }

    # 1. Exact Name Match
    def test_01_exact_name_match(self):
        status, score, details, flag = NameMatcher.compare_names("Amit Kumar Patil", "Amit Kumar Patil")
        self.assertEqual(status, CheckStatus.PASS)
        self.assertEqual(score, 100.0)
        self.assertIsNone(flag)

    # 2. Case and Spacing Normalization
    def test_02_case_and_spacing_normalization(self):
        status, score, details, flag = NameMatcher.compare_names("amit kumar patil", "Amit   Kumar   Patil")
        self.assertEqual(status, CheckStatus.PASS)
        self.assertEqual(score, 100.0)
        self.assertIsNone(flag)

    # 3. Minor Name Variation (Initials & Middle Name Missing)
    def test_03_minor_name_variation(self):
        # Case A: Initial variation ("Amit K. Patil" vs "Amit Kumar Patil")
        status, score, details, flag = NameMatcher.compare_names("Amit K. Patil", "Amit Kumar Patil")
        self.assertEqual(status, CheckStatus.WARNING)
        self.assertEqual(score, 85.0)
        self.assertEqual(flag, "NAME_VARIATION")

        # Case B: Missing middle name ("Amit Patil" vs "Amit Kumar Patil")
        status2, score2, details2, flag2 = NameMatcher.compare_names("Amit Patil", "Amit Kumar Patil")
        self.assertEqual(status2, CheckStatus.WARNING)
        self.assertEqual(score2, 80.0)
        self.assertEqual(flag2, "NAME_VARIATION")

    # 4. Significant Name Mismatch
    def test_04_significant_name_mismatch(self):
        status, score, details, flag = NameMatcher.compare_names("Amit Patil", "Rahul Sharma")
        self.assertEqual(status, CheckStatus.FAIL)
        self.assertLess(score, 50.0)
        self.assertEqual(flag, "NAME_MISMATCH")

    # 5. DOB Match
    def test_05_dob_match(self):
        eval_result = self.engine.evaluate(
            student_data={"date_of_birth": "2004-01-15"},
            application_data=self.application,
            extractions=self.standard_extractions
        )
        dob_check = eval_result.field_checks["date_of_birth"]
        self.assertEqual(dob_check.status, CheckStatus.PASS)
        self.assertEqual(dob_check.score, 100.0)

    # 6. DOB Mismatch
    def test_06_dob_mismatch(self):
        eval_result = self.engine.evaluate(
            student_data={"date_of_birth": "2002-11-20"},  # Mismatch with 2004-01-15
            application_data=self.application,
            extractions=self.standard_extractions
        )
        dob_check = eval_result.field_checks["date_of_birth"]
        self.assertEqual(dob_check.status, CheckStatus.FAIL)
        self.assertEqual(dob_check.score, 0.0)
        self.assertIn("DOB_MISMATCH", eval_result.critical_flags)

    # 7. Government ID Match
    def test_07_government_id_match(self):
        eval_result = self.engine.evaluate(
            student_data={"government_id_number": "TEST 1234-5678-9012"},  # Formatting variation
            application_data=self.application,
            extractions=self.standard_extractions
        )
        id_check = eval_result.field_checks["government_id_number"]
        self.assertEqual(id_check.status, CheckStatus.PASS)
        self.assertEqual(id_check.score, 100.0)
        self.assertIn("****", id_check.details)  # Confirms privacy masking

    # 8. Government ID Mismatch
    def test_08_government_id_mismatch(self):
        eval_result = self.engine.evaluate(
            student_data={"government_id_number": "TEST-9999-0000-1111"},
            application_data=self.application,
            extractions=self.standard_extractions
        )
        id_check = eval_result.field_checks["government_id_number"]
        self.assertEqual(id_check.status, CheckStatus.FAIL)
        self.assertEqual(id_check.score, 0.0)
        self.assertIn("GOVERNMENT_ID_MISMATCH", eval_result.critical_flags)

    # 9. Cross-Document Name Consistency
    def test_09_cross_document_name_consistency(self):
        eval_result = self.engine.evaluate(
            student_data=self.student_profile,
            application_data=self.application,
            extractions=self.standard_extractions
        )
        cross_check = eval_result.field_checks["cross_document_name_consistency"]
        self.assertEqual(cross_check.status, CheckStatus.PASS)
        self.assertEqual(cross_check.score, 100.0)
        self.assertTrue(len(eval_result.cross_document_matches) > 0)

    # 10. Missing Extraction Field Handling
    def test_10_missing_extraction_field(self):
        eval_result = self.engine.evaluate(
            student_data={"full_name": "Test Student", "date_of_birth": None, "government_id_number": None},
            application_data=self.application,
            extractions=self.standard_extractions
        )
        dob_check = eval_result.field_checks["date_of_birth"]
        self.assertEqual(dob_check.status, CheckStatus.NOT_AVAILABLE)

    # 11. Maharashtra Domicile Pass
    def test_11_maharashtra_domicile_pass(self):
        eval_result = self.engine.evaluate(
            student_data=self.student_profile,
            application_data=self.application,
            extractions=self.standard_extractions
        )
        dom_check = eval_result.field_checks["domicile_eligibility"]
        self.assertEqual(dom_check.status, CheckStatus.PASS)
        self.assertEqual(dom_check.score, 100.0)

    # 12. Non-Maharashtra Domicile Failure
    def test_12_non_maharashtra_domicile(self):
        non_mh_extractions = dict(self.standard_extractions)
        non_mh_extractions[DocumentType.DOMICILE_CERTIFICATE] = self.mock_verifier.extract_document(
            "domicile.pdf",
            DocumentType.DOMICILE_CERTIFICATE,
            field_overrides={"state": "Karnataka", "is_maharashtra_domicile": False}
        )

        eval_result = self.engine.evaluate(
            student_data=self.student_profile,
            application_data=self.application,
            extractions=non_mh_extractions
        )
        dom_check = eval_result.field_checks["domicile_eligibility"]
        self.assertEqual(dom_check.status, CheckStatus.FAIL)
        self.assertEqual(dom_check.score, 0.0)
        self.assertIn("NON_MAHARASHTRA_DOMICILE", eval_result.critical_flags)

    # 13. Configured Income Threshold Pass
    def test_13_configured_income_threshold_pass(self):
        eval_result = self.engine.evaluate(
            student_data=self.student_profile,
            application_data=self.application,  # EBC Limit: ₹8,00,000; extracted income ₹2,50,000
            extractions=self.standard_extractions
        )
        inc_check = eval_result.field_checks["income_eligibility"]
        self.assertEqual(inc_check.status, CheckStatus.PASS)
        self.assertEqual(inc_check.score, 100.0)

    # 14. Configured Income Threshold Failure
    def test_14_configured_income_threshold_failure(self):
        high_income_extractions = dict(self.standard_extractions)
        high_income_extractions[DocumentType.INCOME_CERTIFICATE] = self.mock_verifier.extract_document(
            "income.pdf",
            DocumentType.INCOME_CERTIFICATE,
            field_overrides={"annual_income_inr": 950000.0}  # Exceeds ₹8,00,000 limit
        )

        eval_result = self.engine.evaluate(
            student_data=self.student_profile,
            application_data=self.application,
            extractions=high_income_extractions
        )
        inc_check = eval_result.field_checks["income_eligibility"]
        self.assertEqual(inc_check.status, CheckStatus.FAIL)
        self.assertEqual(inc_check.score, 0.0)
        self.assertIn("INCOME_LIMIT_EXCEEDED", eval_result.critical_flags)

    # 15. No Configured Income Threshold
    def test_15_no_configured_income_threshold(self):
        custom_engine = RulesEngine(scholarship_rules={"Custom Scheme Without Income Limit": {"minimum_percentage": None}})
        eval_result = custom_engine.evaluate(
            student_data=self.student_profile,
            application_data={"scholarship_name": "Custom Scheme Without Income Limit"},
            extractions=self.standard_extractions
        )
        inc_check = eval_result.field_checks["income_eligibility"]
        self.assertEqual(inc_check.status, CheckStatus.NOT_AVAILABLE)

    # 16. Marksheet Pass Result
    def test_16_marksheet_pass_result(self):
        eval_result = self.engine.evaluate(
            student_data=self.student_profile,
            application_data=self.application,
            extractions=self.standard_extractions
        )
        mark_check = eval_result.field_checks["marksheet_performance"]
        self.assertEqual(mark_check.status, CheckStatus.PASS)
        self.assertEqual(mark_check.score, 100.0)

    # 17. Marksheet Failure Result
    def test_17_marksheet_failure_result(self):
        fail_marksheet_extractions = dict(self.standard_extractions)
        fail_marksheet_extractions[DocumentType.MARKSHEET] = self.mock_verifier.extract_document(
            "marksheet.pdf",
            DocumentType.MARKSHEET,
            field_overrides={"percentage": 42.0, "result_status": "FAIL"}  # Below 50% & failed
        )

        eval_result = self.engine.evaluate(
            student_data=self.student_profile,
            application_data=self.application,
            extractions=fail_marksheet_extractions
        )
        mark_check = eval_result.field_checks["marksheet_performance"]
        self.assertEqual(mark_check.status, CheckStatus.FAIL)
        self.assertEqual(mark_check.score, 0.0)
        self.assertTrue(any("MARKSHEET" in f for f in eval_result.critical_flags))

    # 18. Unreadable Document Handling
    def test_18_unreadable_document(self):
        unreadable_extractions = dict(self.standard_extractions)
        unreadable_extractions[DocumentType.GOVERNMENT_ID] = self.mock_verifier.extract_document(
            "blurry.pdf",
            DocumentType.GOVERNMENT_ID,
            scenario=MockScenario.UNREADABLE
        )

        eval_result = self.engine.evaluate(
            student_data=self.student_profile,
            application_data=self.application,
            extractions=unreadable_extractions
        )
        read_check = eval_result.field_checks["document_readability"]
        self.assertEqual(read_check.status, CheckStatus.FAIL)
        self.assertTrue(any("UNREADABLE" in f for f in eval_result.critical_flags))
        self.assertEqual(eval_result.recommended_status, "NEEDS_REVIEW")

    # 19. Incomplete Extraction Handling
    def test_19_incomplete_extraction(self):
        incomplete_extractions = dict(self.standard_extractions)
        incomplete_extractions[DocumentType.MARKSHEET] = self.mock_verifier.extract_document(
            "incomplete.pdf",
            DocumentType.MARKSHEET,
            scenario=MockScenario.INCOMPLETE
        )

        eval_result = self.engine.evaluate(
            student_data=self.student_profile,
            application_data=self.application,
            extractions=incomplete_extractions
        )
        self.assertTrue(eval_result.field_checks["document_readability"].score < 100.0)
        self.assertTrue(len(eval_result.issues) > 0)

    # 20. Deterministic Score Calculation
    def test_20_deterministic_score(self):
        # High confidence complete pass evaluation
        eval1 = self.engine.evaluate(self.student_profile, self.application, self.standard_extractions)
        eval2 = self.engine.evaluate(self.student_profile, self.application, self.standard_extractions)

        self.assertEqual(eval1.overall_score, 100.0)
        self.assertEqual(eval1.overall_score, eval2.overall_score)
        self.assertEqual(eval1.overall_status, CheckStatus.PASS)
        self.assertEqual(eval1.recommended_status, "VERIFIED")

    # 21. Critical Flag Generation
    def test_21_critical_flag_generation(self):
        # Trigger multiple critical flags: DOB mismatch + Income limit exceeded
        bad_extractions = dict(self.standard_extractions)
        bad_extractions[DocumentType.INCOME_CERTIFICATE] = self.mock_verifier.extract_document(
            "income.pdf",
            DocumentType.INCOME_CERTIFICATE,
            field_overrides={"annual_income_inr": 1200000.0}
        )

        eval_result = self.engine.evaluate(
            student_data={**self.student_profile, "date_of_birth": "1999-05-10"},
            application_data=self.application,
            extractions=bad_extractions
        )

        self.assertEqual(eval_result.overall_status, CheckStatus.FAIL)
        self.assertEqual(eval_result.recommended_status, "NEEDS_REVIEW")
        self.assertIn("DOB_MISMATCH", eval_result.critical_flags)
        self.assertIn("INCOME_LIMIT_EXCEEDED", eval_result.critical_flags)
        self.assertTrue(len(eval_result.issues) >= 2)


if __name__ == "__main__":
    unittest.main()

"""
VeriCampus AI — Stage 5: Authority Verification Service Orchestrator
Coordinates provider execution, enforces Stage 1-4 pipeline gating,
safely handles timeouts/errors, and outputs Stage5VerificationResult.
"""
import uuid
import logging
from typing import Dict, Any, Optional

from .base import AuthorityVerificationProvider
from .providers.unavailable import UnavailableProvider
from .schemas import (
    AuthorityVerificationResult,
    Stage5VerificationResult,
    AuthorityStatus,
    EvidenceStrength,
    ConsentStatus,
    RecordStatus,
)
from .scorer import synthesize_stage5_result
from .config import (
    AUTHORITY_PROVIDER_TIMEOUT_SECONDS,
    AUTHORITY_PROVIDER_MAX_RETRIES,
)

logger = logging.getLogger("vericampus.authority_verification")


class AuthorityVerificationService:
    """
    Orchestrates Stage 5 Authority Verification for scholarship applications.
    """

    def __init__(self, provider: Optional[AuthorityVerificationProvider] = None):
        self.provider = provider if provider is not None else UnavailableProvider()

    def verify_document(
        self,
        document_type: str,
        extracted_data: Optional[Dict[str, Any]] = None,
        quality_info: Optional[Dict[str, Any]] = None,
        classification_info: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> AuthorityVerificationResult:
        """
        Executes authority verification for a single document with multi-stage gating.
        """
        verification_id = f"av-{uuid.uuid4().hex[:12]}"

        # 1. Stage 1 Quality Gate Check
        if quality_info:
            q_status = quality_info.get("quality_gate_status") or quality_info.get("status")
            q_score = quality_info.get("quality_score") or quality_info.get("overall_quality_score", 100.0)
            if q_status in ("FAIL", "REUPLOAD_REQUIRED") or (isinstance(q_score, (int, float)) and q_score < 70.0):
                return AuthorityVerificationResult(
                    document_type=document_type,
                    provider=self.provider.provider_name,
                    provider_version=self.provider.provider_version,
                    verification_id=verification_id,
                    status=AuthorityStatus.BLOCKED,
                    evidence_strength=EvidenceStrength.NONE,
                    consent_status=ConsentStatus.NOT_REQUIRED,
                    record_status=RecordStatus.NOT_AVAILABLE,
                    reason="Authority verification skipped because document quality is insufficient.",
                    is_available=self.provider.is_available(),
                )

        # 2. Stage 2 Classification Gate Check
        if classification_info:
            c_status = classification_info.get("classification_status") or classification_info.get("status")
            if c_status in ("DOCUMENT_TYPE_MISMATCH", "UNKNOWN"):
                return AuthorityVerificationResult(
                    document_type=document_type,
                    provider=self.provider.provider_name,
                    provider_version=self.provider.provider_version,
                    verification_id=verification_id,
                    status=AuthorityStatus.BLOCKED,
                    evidence_strength=EvidenceStrength.NONE,
                    consent_status=ConsentStatus.NOT_REQUIRED,
                    record_status=RecordStatus.NOT_AVAILABLE,
                    reason=f"Authority verification skipped due to document slot type mismatch ({c_status}).",
                    is_available=self.provider.is_available(),
                )

        # 3. Stage 3 Field Extraction Completeness Check
        fields: Dict[str, Any] = {}
        if extracted_data:
            # Handle DocumentFieldExtractionResult dict structure
            if "fields" in extracted_data and isinstance(extracted_data["fields"], dict):
                for f_name, f_val in extracted_data["fields"].items():
                    if isinstance(f_val, dict):
                        fields[f_name] = f_val.get("normalized_value") or f_val.get("display_value") or f_val.get("raw_value")
                    else:
                        fields[f_name] = f_val
            else:
                fields = dict(extracted_data)

        # Skip if zero fields could be read from document
        if not fields or not any(v for v in fields.values() if v is not None):
            return AuthorityVerificationResult(
                document_type=document_type,
                provider=self.provider.provider_name,
                provider_version=self.provider.provider_version,
                verification_id=verification_id,
                status=AuthorityStatus.BLOCKED,
                evidence_strength=EvidenceStrength.NONE,
                consent_status=ConsentStatus.NOT_REQUIRED,
                record_status=RecordStatus.NOT_AVAILABLE,
                reason="Authority verification skipped due to missing or failed field extraction.",
                is_available=self.provider.is_available(),
            )

        # 4. Invoke Provider with Error / Timeout / Retry Protection
        retries = 0
        last_error = None
        while retries <= AUTHORITY_PROVIDER_MAX_RETRIES:
            try:
                res = self.provider.verify(
                    document_type=document_type,
                    extracted_fields=fields,
                    context=context,
                )
                return res
            except TimeoutError as te:
                last_error = f"Connection timed out after {AUTHORITY_PROVIDER_TIMEOUT_SECONDS}s"
                retries += 1
            except ConnectionError as ce:
                last_error = "Network connection failure to authority provider"
                retries += 1
            except Exception as ex:
                last_error = f"Unexpected provider exception: {type(ex).__name__}"
                break

        # Sanitized error response (no raw stack traces or internal secrets)
        logger.warning("Stage 5 authority provider error on %s: %s", document_type, last_error)
        return AuthorityVerificationResult(
            document_type=document_type,
            provider=self.provider.provider_name,
            provider_version=self.provider.provider_version,
            verification_id=verification_id,
            status=AuthorityStatus.ERROR,
            evidence_strength=EvidenceStrength.NONE,
            consent_status=ConsentStatus.NOT_REQUIRED,
            record_status=RecordStatus.NOT_AVAILABLE,
            reason=f"Authority verification could not be completed: {last_error}",
            is_available=self.provider.is_available(),
        )

    def verify_application(
        self,
        extractions: Dict[str, Any],
        quality_results: Optional[Dict[str, Any]] = None,
        classification_results: Optional[Dict[str, Any]] = None,
        tamper_results: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Stage5VerificationResult:
        """
        Executes authority verification across all 4 required scholarship documents.
        """
        document_results: Dict[str, AuthorityVerificationResult] = {}

        # Standard 4 document types
        doc_types = ["government_id", "marksheet", "income_certificate", "domicile_certificate"]

        # Support both full 4-document applications and test subsets
        matched_types = [
            dt for dt in doc_types
            if dt in extractions or dt.upper() in extractions or dt.lower() in extractions
        ]
        target_docs = matched_types if matched_types else doc_types

        for dt in target_docs:
            ext_d = extractions.get(dt)
            if ext_d is None:
                ext_d = extractions.get(dt.upper()) or extractions.get(dt.lower())
            q_d = None
            if quality_results:
                q_d = quality_results.get(dt) or quality_results.get(dt.upper()) or quality_results.get(dt.lower())
            c_d = None
            if classification_results:
                c_d = classification_results.get(dt) or classification_results.get(dt.upper()) or classification_results.get(dt.lower())

            # Stage 4 signals do NOT automatically block Stage 5
            doc_res = self.verify_document(
                document_type=dt,
                extracted_data=ext_d,
                quality_info=q_d,
                classification_info=c_d,
                context=context,
            )
            document_results[dt] = doc_res

        return synthesize_stage5_result(document_results)

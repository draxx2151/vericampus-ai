import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useApplications } from '../../context/ApplicationContext';
import { api } from '../../services/api';
import StatusBadge from '../../components/StatusBadge';
import { 
  ShieldCheck, 
  FileText, 
  CheckCircle2, 
  AlertTriangle, 
  Info, 
  ArrowLeft,
  Sparkles,
  HelpCircle,
  Loader2,
  AlertCircle,
  Play,
  FileSearch,
  FileCheck,
  ExternalLink
} from 'lucide-react';

export default function VerificationResultPage() {
  const { token, currentUser } = useAuth();
  const { myApplication, refreshState } = useApplications();
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  useEffect(() => {
    refreshState();
  }, []);

  const loadVerification = async () => {
    const activeToken = token || localStorage.getItem('vericampus_token');
    if (!myApplication?.id || !activeToken) {
      setLoading(false);
      return;
    }

    setLoading(true);
    setErrorMsg(null);
    try {
      const data = await api.getVerificationResult(myApplication.id, activeToken);
      setResult(data);
    } catch (err) {
      // 404 means verification not yet run
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (myApplication?.id) {
      loadVerification();
    } else {
      setLoading(false);
    }
  }, [myApplication?.id, token]);

  const handleRunVerification = async () => {
    const activeToken = token || localStorage.getItem('vericampus_token');
    if (!myApplication?.id || !activeToken) return;

    setTriggering(true);
    setErrorMsg(null);
    try {
      await api.triggerVerification(myApplication.id, activeToken);
      await refreshState();
      await loadVerification();
    } catch (err) {
      setErrorMsg(err.message || "Failed to run verification pipeline.");
    } finally {
      setTriggering(false);
    }
  };

  if (loading) {
    return (
      <div className="p-12 text-center text-slate-500 flex flex-col items-center justify-center gap-3">
        <Loader2 className="w-8 h-8 text-teal animate-spin" />
        <span className="text-xs font-semibold">Loading verification report...</span>
      </div>
    );
  }

  if (!myApplication) {
    return (
      <div className="bg-white rounded-2xl p-8 border border-slate-200 text-center text-slate-500 shadow-sm space-y-4">
        <FileSearch className="w-12 h-12 text-slate-300 mx-auto" />
        <h3 className="text-base font-bold text-slate-800">No Application Found</h3>
        <p className="text-xs text-slate-500 max-w-md mx-auto">
          You have not initiated a scholarship application yet. Please start your application and upload required documents first.
        </p>
        <Link
          to="/student/select-scholarship"
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-teal hover:bg-teal-hover text-white text-xs font-bold rounded-xl transition-colors shadow-sm"
        >
          <span>Select Scholarship Scheme</span>
        </Link>
      </div>
    );
  }

  const uploadedCount = myApplication.documents_uploaded_count || (myApplication.documents ? myApplication.documents.length : 0);
  const docConfig = [
    { type: 'GOVERNMENT_ID', title: 'Government ID / Aadhaar' },
    { type: 'MARKSHEET', title: '10th / 12th Marksheet' },
    { type: 'INCOME_CERTIFICATE', title: 'Income Certificate' },
    { type: 'DOMICILE_CERTIFICATE', title: 'Domicile Certificate' }
  ];

  const extractedData = result?.extracted_data || {};
  const riskAnalysis = extractedData.risk_analysis || null;
  const documentQuality = result?.document_quality || extractedData.document_quality || null;
  const documentClassification = result?.document_classification || extractedData.document_classification || null;
  const fieldExtraction = extractedData.field_extraction || null;
  const tamperConsistency = result?.tamper_consistency || extractedData.tamper_consistency || null;
  const authorityVerification = result?.authority_verification || extractedData.authority_verification || null;
  const evidenceSummary = result?.evidence_summary || extractedData.evidence_summary || null;
  const fieldChecks = result?.field_checks || {};
  const crossDocMatches = result?.cross_document_matches || {};
  const issues = Array.isArray(result?.issues) ? result.issues : [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Link to="/student/dashboard" className="text-xs text-teal font-semibold hover:underline flex items-center gap-1">
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back to Dashboard</span>
            </Link>
          </div>
          <span className="text-xs font-semibold uppercase tracking-wider text-teal">Verification Audit Report</span>
          <h2 className="text-2xl font-bold text-navy mt-0.5">AI Assistive Document Verification</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Application: <span className="font-mono font-bold text-navy">{myApplication.application_number}</span> • Scheme: <span className="font-semibold text-slate-700">{myApplication.scholarship_name}</span>
          </p>
        </div>

        {result ? (
          <div className="text-right">
            <span className="text-xs text-slate-400 block mb-1">AI Evaluation Status</span>
            <StatusBadge status={result.verification_status} confidence={result.overall_score} />
          </div>
        ) : (
          <div className="text-right">
            <span className="text-xs text-slate-400 block mb-1">Current Status</span>
            <StatusBadge status={myApplication.status} />
          </div>
        )}
      </div>

      {errorMsg && (
        <div className="p-4 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-xl flex items-start gap-2.5">
          <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* When verification has NOT been triggered yet */}
      {!result ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-8 shadow-sm text-center space-y-4">
          <div className="w-16 h-16 bg-teal-50 text-teal rounded-2xl flex items-center justify-center mx-auto border border-teal/20">
            <Sparkles className="w-8 h-8" />
          </div>
          <h3 className="text-lg font-bold text-navy">AI Verification Pending</h3>
          <p className="text-xs text-slate-500 max-w-lg mx-auto">
            {uploadedCount === 4
              ? "All 4 required documents are uploaded. You can run automated verification to extract text, compare names across documents, and verify eligibility limits."
              : `You have uploaded ${uploadedCount} of 4 required documents. Upload all 4 documents to run automated verification.`}
          </p>

          <div className="pt-2">
            <button
              onClick={handleRunVerification}
              disabled={triggering || uploadedCount === 0}
              className="inline-flex items-center gap-2 px-6 py-3 bg-teal hover:bg-teal-hover text-white text-xs font-bold rounded-xl transition-all shadow-md disabled:opacity-50 disabled:pointer-events-none"
            >
              {triggering ? (
                <>
                  <Loader2 className="w-4 h-4 text-white animate-spin" />
                  <span>Processing OCR & Rules Engine...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  <span>Run Automated Verification</span>
                </>
              )}
            </button>
          </div>
        </div>
      ) : (
        /* When verification result IS available */
        <div className="space-y-6">
          {/* Overview Score & Prototype Disclaimer Card */}
          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <span className="text-xs text-slate-500 block">Overall Eligibility & Consistency Score</span>
                <div className="flex items-baseline gap-2 mt-1">
                  <span className="text-3xl font-extrabold text-navy font-mono">
                    {result.overall_score !== undefined && result.overall_score !== null ? Number(result.overall_score).toFixed(1) : 'N/A'}%
                  </span>
                  <span className="text-xs text-slate-500">composite match score</span>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <button
                  onClick={handleRunVerification}
                  disabled={triggering}
                  className="inline-flex items-center gap-1.5 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition-colors border border-slate-200"
                >
                  {triggering ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Sparkles className="w-3.5 h-3.5 text-teal" />
                  )}
                  <span>Re-run Verification</span>
                </button>
              </div>
            </div>

            <div className="p-3.5 bg-seafoam-light/70 border border-seafoam rounded-xl text-xs text-navy flex items-start gap-2.5">
              <Sparkles className="w-4 h-4 text-teal flex-shrink-0 mt-0.5" />
              <div className="leading-relaxed">
                <strong>Assistive AI Evaluation:</strong> This report represents automated OCR text extraction and rule-based consistency checks. It is designed to assist college verification officers and does not represent an automatic scholarship decision.
              </div>
            </div>

            {/* Official College Administrative Decision Status */}
            {myApplication.status === 'VERIFIED' ? (
              <div className="p-4 bg-emerald-50 border-2 border-emerald-300 rounded-xl text-xs text-emerald-950 flex items-start gap-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <h4 className="font-bold text-sm text-emerald-900">Application Approved by College Administration</h4>
                  <p>Your scholarship application has been reviewed and officially approved by the authorized college verification officer.</p>
                </div>
              </div>
            ) : myApplication.status === 'REJECTED' ? (
              <div className="p-4 bg-rose-50 border-2 border-rose-300 rounded-xl text-xs text-rose-950 flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <h4 className="font-bold text-sm text-rose-900">Application Not Approved</h4>
                  <p>Your scholarship application was not approved upon administrative review.</p>
                  {result?.issues?.find(i => i.includes('rejection reason') || i.includes('rejected by administration')) && (
                    <p className="mt-1 font-semibold text-rose-800">
                      Administrative Reason: {result.issues.find(i => i.includes('rejection reason') || i.includes('rejected by administration')).split(': ').pop()}
                    </p>
                  )}
                </div>
              </div>
            ) : null}
          </div>

          {/* Stage 1: Document Quality Gate Feedback */}
          {documentQuality && (
            <div className={`rounded-2xl p-6 border-2 shadow-sm space-y-4 ${
              documentQuality.quality_gate_status === 'REUPLOAD_REQUIRED'
                ? 'bg-rose-50/70 border-rose-300 text-rose-950'
                : documentQuality.quality_gate_status === 'WARNING'
                ? 'bg-amber-50/70 border-amber-300 text-amber-950'
                : 'bg-white border-slate-200 text-slate-800'
            }`}>
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <span className="text-[11px] font-bold uppercase tracking-wider text-teal">Stage 1: Document Quality Gate</span>
                  <h3 className="text-lg font-bold text-navy mt-0.5">Automated Image Quality Assessment</h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Evaluates visual clarity, scan lighting, and text readability.
                  </p>
                </div>
                <div className="text-right">
                  <span className={`text-xs font-extrabold px-3 py-1 rounded-full border ${
                    documentQuality.quality_gate_status === 'PASS'
                      ? 'bg-emerald-100 text-emerald-900 border-emerald-300'
                      : documentQuality.quality_gate_status === 'WARNING'
                      ? 'bg-amber-100 text-amber-900 border-amber-300'
                      : 'bg-rose-100 text-rose-900 border-rose-300'
                  }`}>
                    {documentQuality.quality_gate_status === 'REUPLOAD_REQUIRED' ? 'RE-UPLOAD REQUIRED' : documentQuality.quality_gate_status} ({documentQuality.overall_quality_score}/100)
                  </span>
                  <span className="text-[10px] text-slate-400 block mt-1">Tier: {documentQuality.overall_quality_level}</span>
                </div>
              </div>

              {documentQuality.quality_gate_status === 'REUPLOAD_REQUIRED' && (
                <div className="p-3.5 bg-rose-100/80 border border-rose-300 rounded-xl text-xs text-rose-900 space-y-2">
                  <div className="font-bold flex items-center gap-1.5 text-rose-950">
                    <AlertCircle className="w-4 h-4 text-rose-600" />
                    <span>Action Required: Please Re-upload Flagged Document(s)</span>
                  </div>
                  <p className="text-[11px] leading-relaxed">
                    One or more uploaded files could not be clearly read by our automated document processing system. Your application has not been rejected, but replacement files are required to proceed.
                  </p>
                  <Link
                    to="/student/upload-documents"
                    className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs rounded-lg transition-colors shadow-sm"
                  >
                    <span>Replace Document(s) Now</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </Link>
                </div>
              )}

              {/* Per-document breakdown */}
              {documentQuality.documents && (
                <div className="grid sm:grid-cols-2 gap-3 pt-2">
                  {Object.entries(documentQuality.documents).map(([docType, qInfo]) => (
                    <div key={docType} className={`p-3 rounded-xl border text-xs ${
                      qInfo.quality_gate_status === 'REUPLOAD_REQUIRED'
                        ? 'bg-white border-rose-300 text-rose-950'
                        : qInfo.quality_gate_status === 'WARNING'
                        ? 'bg-white border-amber-300 text-amber-950'
                        : 'bg-slate-50 border-slate-200 text-slate-700'
                    }`}>
                      <div className="flex items-center justify-between font-bold mb-1">
                        <span>{docType.replace(/_/g, ' ')}</span>
                        <span className="font-mono text-xs">{qInfo.quality_score}/100</span>
                      </div>
                      {qInfo.reasons && qInfo.reasons.length > 0 ? (
                        <ul className="text-[11px] text-slate-600 space-y-0.5 list-disc list-inside mt-1">
                          {qInfo.reasons.map((r, rIdx) => (
                            <li key={rIdx}>{r}</li>
                          ))}
                        </ul>
                      ) : (
                        <span className="text-[11px] text-emerald-700 font-medium">✓ Document is clear and readable</span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Stage 2: Document Classification Feedback */}
          {documentClassification && (
            <div className={`rounded-2xl p-6 border-2 shadow-sm space-y-4 ${
              documentClassification.overall_status === 'DOCUMENT_TYPE_MISMATCH' || documentClassification.overall_status === 'UNKNOWN'
                ? 'bg-rose-50/70 border-rose-300 text-rose-950'
                : documentClassification.overall_status === 'WARNING'
                ? 'bg-amber-50/70 border-amber-300 text-amber-950'
                : 'bg-white border-slate-200 text-slate-800'
            }`}>
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <span className="text-[11px] font-bold uppercase tracking-wider text-teal">Stage 2: AI Document Classification</span>
                  <h3 className="text-lg font-bold text-navy mt-0.5">Document Type & Slot Matching</h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Verifies each uploaded document corresponds to its requested scholarship slot.
                  </p>
                </div>
                <div className="text-right">
                  <span className={`text-xs font-extrabold px-3 py-1 rounded-full border ${
                    documentClassification.overall_status === 'PASS'
                      ? 'bg-emerald-100 text-emerald-900 border-emerald-300'
                      : documentClassification.overall_status === 'WARNING'
                      ? 'bg-amber-100 text-amber-900 border-amber-300'
                      : 'bg-rose-100 text-rose-900 border-rose-300'
                  }`}>
                    {documentClassification.overall_status === 'DOCUMENT_TYPE_MISMATCH'
                      ? 'MISMATCH DETECTED'
                      : documentClassification.overall_status}
                  </span>
                  <span className="text-[10px] text-slate-400 block mt-1">
                    {documentClassification.mismatched_documents?.length > 0
                      ? `${documentClassification.mismatched_documents.length} document(s) mismatched`
                      : 'All slots verified'}
                  </span>
                </div>
              </div>

              {(documentClassification.overall_status === 'DOCUMENT_TYPE_MISMATCH' || documentClassification.overall_status === 'UNKNOWN') && (
                <div className="p-3.5 bg-rose-100/80 border border-rose-300 rounded-xl text-xs text-rose-900 space-y-2">
                  <div className="font-bold flex items-center gap-1.5 text-rose-950">
                    <AlertCircle className="w-4 h-4 text-rose-600" />
                    <span>Action Required: Document Type Mismatch</span>
                  </div>
                  <p className="text-[11px] leading-relaxed">
                    Our AI document classifier detected that one or more uploaded files do not match the expected document type (for example, an Income Certificate uploaded in the Marksheet slot). Please upload the correct document to proceed.
                  </p>
                  <Link
                    to="/student/upload-documents"
                    className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs rounded-lg transition-colors shadow-sm"
                  >
                    <span>Replace Document(s) Now</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </Link>
                </div>
              )}

              {/* Per-document slot classification list */}
              {documentClassification.documents && (
                <div className="grid sm:grid-cols-2 gap-3 pt-2">
                  {Object.entries(documentClassification.documents).map(([docType, cInfo]) => (
                    <div
                      key={docType}
                      className={`p-3 rounded-xl border text-xs space-y-1.5 ${
                        cInfo.classification_status === 'DOCUMENT_TYPE_MISMATCH' || cInfo.classification_status === 'UNKNOWN'
                          ? 'bg-rose-100/40 border-rose-300'
                          : cInfo.classification_status === 'WARNING'
                          ? 'bg-amber-100/40 border-amber-300'
                          : 'bg-slate-50 border-slate-200'
                      }`}
                    >
                      <div className="flex items-center justify-between font-bold">
                        <span className="text-navy">{docType.replace(/_/g, ' ')}</span>
                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-mono font-bold ${
                          cInfo.classification_status === 'PASS'
                            ? 'bg-emerald-100 text-emerald-800'
                            : cInfo.classification_status === 'WARNING'
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-rose-100 text-rose-800'
                        }`}>
                          {cInfo.classification_status === 'PASS'
                            ? `MATCH (${(cInfo.confidence * 100).toFixed(0)}%)`
                            : cInfo.classification_status === 'DOCUMENT_TYPE_MISMATCH'
                            ? `MISMATCH (${cInfo.predicted_type ? cInfo.predicted_type.replace(/_/g, ' ') : 'N/A'})`
                            : cInfo.classification_status}
                        </span>
                      </div>

                      {cInfo.reasons && cInfo.reasons.length > 0 ? (
                        <ul className="text-[11px] text-rose-900 space-y-0.5 list-disc list-inside">
                          {cInfo.reasons.map((r, rIdx) => (
                            <li key={rIdx}>{r}</li>
                          ))}
                        </ul>
                      ) : (
                        <span className="text-[11px] text-emerald-700 font-medium">✓ Document matches requested slot</span>
                      )}

                      {cInfo.alternatives && cInfo.alternatives.length > 0 && (
                        <div className="text-[10px] text-slate-500 pt-0.5 flex flex-wrap gap-1">
                          <span className="text-slate-400">Predicted alternatives:</span>
                          {cInfo.alternatives.slice(0, 2).map((alt, aIdx) => (
                            <span key={aIdx} className="bg-white px-1.5 py-0.5 rounded border border-slate-200 text-slate-600">
                              {alt.class_name.replace(/_/g, ' ')} ({(alt.confidence * 100).toFixed(0)}%)
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Stage 4: Cross-Document Consistency Feedback */}
          {tamperConsistency && (
            <div className={`rounded-2xl p-6 border-2 shadow-sm space-y-4 ${
              tamperConsistency.overall_status === 'NEEDS_REVIEW'
                ? 'bg-amber-50/70 border-amber-300 text-amber-950'
                : tamperConsistency.overall_status === 'WARNING'
                ? 'bg-slate-50 border-slate-300 text-slate-800'
                : 'bg-white border-slate-200 text-slate-800'
            }`}>
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <span className="text-[11px] font-bold uppercase tracking-wider text-teal">Stage 4: Document Consistency</span>
                  <h3 className="text-lg font-bold text-navy mt-0.5">Cross-Document Verification</h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Checks that candidate names, dates of birth, and identity details are consistent across your uploaded records.
                  </p>
                </div>
                <div className="text-right">
                  <span className={`text-xs font-extrabold px-3 py-1 rounded-full border ${
                    tamperConsistency.overall_status === 'PASS'
                      ? 'bg-emerald-100 text-emerald-900 border-emerald-300'
                      : 'bg-amber-100 text-amber-900 border-amber-300'
                  }`}>
                    {tamperConsistency.overall_status === 'PASS' ? 'CONSISTENT' : 'REVIEW ADVISORY'}
                  </span>
                </div>
              </div>

              {tamperConsistency.review_required && (
                <div className="p-3.5 bg-amber-100/80 border border-amber-300 rounded-xl text-xs text-amber-900 space-y-1.5">
                  <div className="font-bold flex items-center gap-1.5 text-amber-950">
                    <Info className="w-4 h-4 text-amber-600" />
                    <span>Advisory Note: Cross-Document Variation Noted</span>
                  </div>
                  <p className="text-[11px] leading-relaxed">
                    A variation in details (such as date of birth or name formatting) was observed across your uploaded documents.
                    Your application is being reviewed by college administrators. You may be requested to present original physical documents for clarification during administrative review.
                  </p>
                </div>
              )}

              {/* Consistency Checks summary list */}
              {tamperConsistency.consistency_assessment?.checks?.length > 0 && (
                <div className="space-y-2 pt-1">
                  <span className="text-xs font-bold text-navy">Consistency Checklist:</span>
                  <div className="grid sm:grid-cols-2 gap-2">
                    {tamperConsistency.consistency_assessment.checks.map((chk, idx) => (
                      <div key={idx} className="p-2.5 rounded-lg border border-slate-200 bg-white text-xs flex items-start justify-between gap-2">
                        <div>
                          <span className="font-semibold text-slate-800 capitalize block text-[11px]">
                            {chk.check_name.replace(/_/g, ' ')}
                          </span>
                          <span className="text-[10px] text-slate-500 block mt-0.5">
                            {chk.reason}
                          </span>
                        </div>
                        <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded flex-shrink-0 ${
                          chk.status === 'PASS'
                            ? 'bg-emerald-100 text-emerald-800'
                            : 'bg-amber-100 text-amber-800'
                        }`}>
                          {chk.status === 'PASS' ? 'MATCH' : 'ADVISORY'}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Stage 5: External Authority Record Verification */}
          {authorityVerification && (
            <div className={`rounded-2xl p-6 border-2 shadow-sm space-y-4 ${
              authorityVerification.overall_status === 'MISMATCH'
                ? 'bg-amber-50/70 border-amber-300 text-amber-950'
                : 'bg-white border-slate-200 text-slate-800'
            }`}>
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <span className="text-[11px] font-bold uppercase tracking-wider text-teal">Stage 5: Authority Verification</span>
                  <h3 className="text-lg font-bold text-navy mt-0.5">External Record Confirmation</h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Cross-references your uploaded documents against authoritative academic and government registries when available.
                  </p>
                </div>
                <div className="text-right">
                  <span className={`text-xs font-extrabold px-3 py-1 rounded-full border ${
                    authorityVerification.overall_status === 'MATCH'
                      ? 'bg-emerald-100 text-emerald-900 border-emerald-300'
                      : authorityVerification.overall_status === 'MISMATCH'
                      ? 'bg-amber-100 text-amber-900 border-amber-300'
                      : 'bg-slate-100 text-slate-700 border-slate-300'
                  }`}>
                    {authorityVerification.overall_status === 'MATCH'
                      ? 'CONFIRMED'
                      : authorityVerification.overall_status === 'MISMATCH'
                      ? 'REVIEW ADVISORY'
                      : 'NOT CONFIGURED'}
                  </span>
                </div>
              </div>

              {authorityVerification.overall_status === 'NOT_AVAILABLE' && (
                <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-600 space-y-1">
                  <div className="font-semibold text-slate-800 flex items-center gap-1.5">
                    <Info className="w-4 h-4 text-teal" />
                    <span>External Registry Verification Unavailable</span>
                  </div>
                  <p className="text-[11px] leading-relaxed">
                    Automated external registry lookup (e.g. DigiLocker / Depository) is currently not configured in this prototype environment. Your application verification relies on uploaded scans and administrative review.
                  </p>
                </div>
              )}

              {authorityVerification.overall_status === 'BLOCKED' && (
                <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-600 space-y-1">
                  <div className="font-semibold text-slate-800 flex items-center gap-1.5">
                    <Info className="w-4 h-4 text-teal" />
                    <span>External Verification Deferred</span>
                  </div>
                  <p className="text-[11px] leading-relaxed">
                    External registry lookup was skipped because one or more documents require clearer scans or re-upload.
                  </p>
                </div>
              )}

              {authorityVerification.overall_status === 'MISMATCH' && (
                <div className="p-3.5 bg-amber-100/80 border border-amber-300 rounded-xl text-xs text-amber-900 space-y-1.5">
                  <div className="font-bold flex items-center gap-1.5 text-amber-950">
                    <AlertTriangle className="w-4 h-4 text-amber-600" />
                    <span>Advisory Notice: External Record Variation Noted</span>
                  </div>
                  <p className="text-[11px] leading-relaxed">
                    A variation was noted between your document details and external authority records. Your college administrator will inspect your original physical documents during review.
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Stage 6: Evidence & Decision Support Summary */}
          {evidenceSummary && (
            <div className={`rounded-2xl p-6 border-2 shadow-sm space-y-4 ${
              evidenceSummary.overall_evidence_state === 'HUMAN_REVIEW_REQUIRED'
                ? 'bg-amber-50/70 border-amber-300 text-amber-950'
                : 'bg-white border-slate-200 text-slate-800'
            }`}>
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <span className="text-[11px] font-bold uppercase tracking-wider text-teal">Stage 6: Decision Support</span>
                  <h3 className="text-lg font-bold text-navy mt-0.5">Verification Evidence Summary</h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Consolidated findings from all verification stages prepared for administrative committee review.
                  </p>
                </div>
                <div className="text-right">
                  <span className={`text-xs font-extrabold px-3 py-1 rounded-full border ${
                    evidenceSummary.overall_evidence_state === 'CLEAR_FOR_REVIEW'
                      ? 'bg-emerald-100 text-emerald-900 border-emerald-300'
                      : evidenceSummary.overall_evidence_state === 'HUMAN_REVIEW_REQUIRED'
                      ? 'bg-amber-100 text-amber-900 border-amber-300'
                      : 'bg-slate-100 text-slate-700 border-slate-300'
                  }`}>
                    {evidenceSummary.overall_evidence_state === 'CLEAR_FOR_REVIEW'
                      ? 'CLEAR FOR REVIEW'
                      : evidenceSummary.overall_evidence_state === 'HUMAN_REVIEW_REQUIRED'
                      ? 'OFFICER REVIEW NOTED'
                      : evidenceSummary.overall_evidence_state?.replace(/_/g, ' ')}
                  </span>
                </div>
              </div>

              {/* Explainable plain-language summary */}
              {evidenceSummary.explanation && (
                <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-700 space-y-1">
                  <div className="font-semibold text-slate-800 flex items-center gap-1.5">
                    <Info className="w-4 h-4 text-teal" />
                    <span>Evidence Summary:</span>
                  </div>
                  <p className="text-[11px] leading-relaxed">
                    {evidenceSummary.explanation}
                  </p>
                </div>
              )}

              {/* Supportive Findings Overview */}
              <div className="grid sm:grid-cols-3 gap-3 text-center">
                <div className="p-3 bg-emerald-50/50 rounded-xl border border-emerald-100">
                  <span className="text-[10px] font-bold text-emerald-800 block uppercase">Supporting Findings</span>
                  <span className="text-xl font-black text-emerald-700">
                    {evidenceSummary.supporting_evidence?.length || (evidenceSummary.strong_support_count + evidenceSummary.moderate_support_count + evidenceSummary.weak_support_count) || 0}
                  </span>
                </div>
                <div className="p-3 bg-amber-50/50 rounded-xl border border-amber-100">
                  <span className="text-[10px] font-bold text-amber-800 block uppercase">Review Advisories</span>
                  <span className="text-xl font-black text-amber-700">
                    {evidenceSummary.conflicting_evidence?.length || (evidenceSummary.strong_conflict_count + evidenceSummary.moderate_conflict_count + evidenceSummary.weak_conflict_count) || 0}
                  </span>
                </div>
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                  <span className="text-[10px] font-bold text-slate-600 block uppercase">General Warnings</span>
                  <span className="text-xl font-black text-slate-700">
                    {evidenceSummary.warnings?.length || 0}
                  </span>
                </div>
              </div>

              <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-400">
                <span>Verification assists the scholarship committee; all decisions are taken by university authorities.</span>
                <span className="font-semibold text-teal">VeriCampus AI</span>
              </div>
            </div>
          )}

          {/* Issues / Warnings Banner (if any) */}
          {issues.length > 0 && (
            <div className="bg-amber-50 border-2 border-amber-300 rounded-2xl p-6 shadow-sm">
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-6 h-6 text-amber-600 flex-shrink-0 mt-0.5" />
                <div className="space-y-2">
                  <h3 className="text-base font-bold text-amber-950">
                    Verification Alerts / Discrepancies ({issues.length})
                  </h3>
                  <p className="text-xs text-amber-900">
                    The automated engine highlighted the following items for administrative review:
                  </p>
                  <ul className="list-disc list-inside space-y-1 text-xs text-amber-900 mt-1">
                    {issues.map((iss, idx) => (
                      <li key={idx} className="leading-relaxed font-medium">{iss}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}

          {/* Risk Analysis Card */}
          {riskAnalysis && (
            <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <h3 className="text-lg font-bold text-navy flex items-center gap-2">
                    <ShieldCheck className="w-5 h-5 text-teal" />
                    Review Risk Analysis (Administrative Support)
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Heuristic anomaly indicators to prioritize manual inspection
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider border ${
                    riskAnalysis.risk_level === 'LOW'
                      ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                      : riskAnalysis.risk_level === 'MEDIUM'
                      ? 'bg-amber-100 text-amber-900 border-amber-300'
                      : 'bg-rose-100 text-rose-800 border-rose-300'
                  }`}>
                    {riskAnalysis.risk_level} RISK
                  </span>
                  <span className="font-mono text-sm font-bold text-navy bg-slate-100 px-2.5 py-1 rounded border border-slate-200">
                    Score: {riskAnalysis.risk_score ?? 0}/100
                  </span>
                </div>
              </div>

              {riskAnalysis.contributing_factors && riskAnalysis.contributing_factors.length > 0 ? (
                <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 text-xs">
                  <span className="font-bold text-slate-700 block mb-1">Identified Risk Factors:</span>
                  <ul className="list-disc list-inside space-y-1 text-slate-600">
                    {riskAnalysis.contributing_factors.map((f, i) => (
                      <li key={i}>{f}</li>
                    ))}
                  </ul>
                </div>
              ) : (
                <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                  <span>No high-risk inconsistencies or anomalies detected in uploaded documents.</span>
                </div>
              )}
            </div>
          )}

          {/* Rules Engine Field Checks Grid */}
          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
            <h3 className="text-lg font-bold text-navy mb-4 flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-teal" />
              Automated Eligibility & Field Verification Checks
            </h3>

            {Object.keys(fieldChecks).length === 0 ? (
              <p className="text-xs text-slate-400">No field checks recorded.</p>
            ) : (
              <div className="grid sm:grid-cols-2 gap-3">
                {Object.entries(fieldChecks).map(([key, check]) => {
                  const checkObj = typeof check === 'object' && check !== null ? check : { status: check, details: '' };
                  const isPass = checkObj.status === 'PASS' || checkObj.status === 'PASSED';
                  const isWarn = checkObj.status === 'WARNING';
                  const formattedKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

                  return (
                    <div
                      key={key}
                      className="p-3.5 rounded-xl border border-slate-100 bg-slate-50 flex items-start justify-between gap-3 text-xs"
                    >
                      <div className="flex items-start gap-2.5">
                        {isPass ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
                        ) : isWarn ? (
                          <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
                        ) : (
                          <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
                        )}
                        <div>
                          <h4 className="font-semibold text-slate-800">{formattedKey}</h4>
                          <p className="text-[11px] text-slate-500 mt-0.5">{checkObj.details || 'Check completed'}</p>
                        </div>
                      </div>
                      <StatusBadge status={checkObj.status} />
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* 4 Core Documents Extracted OCR Fields */}
          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
            <div>
              <span className="text-[11px] font-bold uppercase tracking-wider text-teal">Stage 3: OCR & Field Extraction</span>
              <h3 className="text-lg font-bold text-navy mt-0.5 flex items-center gap-2">
                <FileText className="w-5 h-5 text-teal" />
                Extracted Information Across 4 Core Documents
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Key details read directly from your uploaded scans. Sensitive numbers are automatically masked.
              </p>
            </div>

            <div className="grid sm:grid-cols-2 gap-4">
              {docConfig.map(({ type, title }) => {
                const s3Ext = fieldExtraction?.[type];
                const docExtraction = extractedData[type] || extractedData[type.toLowerCase()];
                const legacyFields = docExtraction?.fields || (typeof docExtraction === 'object' && !docExtraction?.extracted_text ? docExtraction : {});

                return (
                  <div key={type} className="p-4 rounded-xl border border-slate-200 bg-slate-50 flex flex-col justify-between space-y-3">
                    <div>
                      <div className="flex items-center justify-between pb-2 mb-3 border-b border-slate-200">
                        <div>
                          <span className="font-bold text-xs text-navy">{title}</span>
                          {s3Ext && s3Ext.overall_confidence > 0 && (
                            <span className="text-[10px] text-slate-400 block font-mono">
                              Confidence: {(s3Ext.overall_confidence * 100).toFixed(0)}%
                            </span>
                          )}
                        </div>
                        {s3Ext ? (
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider ${
                            s3Ext.extraction_status === 'COMPLETE'
                              ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                              : s3Ext.extraction_status === 'PARTIAL'
                              ? 'bg-amber-100 text-amber-800 border border-amber-200'
                              : s3Ext.extraction_status === 'LOW_DOCUMENT_QUALITY'
                              ? 'bg-rose-100 text-rose-800 border border-rose-200'
                              : s3Ext.extraction_status === 'DOCUMENT_TYPE_MISMATCH'
                              ? 'bg-rose-100 text-rose-800 border border-rose-200'
                              : 'bg-slate-200 text-slate-700'
                          }`}>
                            {s3Ext.extraction_status === 'COMPLETE' ? 'Complete' :
                             s3Ext.extraction_status === 'PARTIAL' ? 'Partially Extracted' :
                             s3Ext.extraction_status === 'LOW_DOCUMENT_QUALITY' ? 'Low Quality' :
                             s3Ext.extraction_status === 'DOCUMENT_TYPE_MISMATCH' ? 'Type Mismatch' :
                             s3Ext.extraction_status}
                          </span>
                        ) : docExtraction ? (
                          <span className="text-[10px] font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded">
                            Extracted
                          </span>
                        ) : (
                          <span className="text-[10px] font-bold text-slate-400 bg-slate-200 px-2 py-0.5 rounded">
                            Not Extracted
                          </span>
                        )}
                      </div>

                      {/* Stage 3 structured fields */}
                      {s3Ext && s3Ext.fields && Object.keys(s3Ext.fields).length > 0 ? (
                        <div className="space-y-1.5 text-xs">
                          {Object.entries(s3Ext.fields).map(([k, fData]) => {
                            if (k === 'subjects' && Array.isArray(fData.normalized_value) && fData.normalized_value.length > 0) {
                              return (
                                <div key={k} className="flex justify-between gap-2 border-b border-slate-100 pb-1 pt-0.5">
                                  <span className="text-slate-500 capitalize">Subjects Extracted:</span>
                                  <span className="font-semibold text-slate-800">
                                    {fData.normalized_value.length} subject(s) recorded
                                  </span>
                                </div>
                              );
                            }

                            const val = fData.display_value || fData.normalized_value || fData.raw_value;
                            const isFound = fData.extraction_status === 'EXTRACTED';

                            return (
                              <div key={k} className="flex justify-between gap-2 border-b border-slate-100 pb-1">
                                <span className="text-slate-500 capitalize">{k.replace(/_/g, ' ')}:</span>
                                <span className={`font-medium text-right truncate max-w-[170px] ${isFound ? 'text-slate-800' : 'text-slate-400 italic'}`}>
                                  {isFound ? String(val) : 'Not detected'}
                                </span>
                              </div>
                            );
                          })}

                          {s3Ext.extraction_status === 'PARTIAL' && (
                            <p className="text-[10px] text-amber-700 pt-1">
                              Note: Certain fields could not be automatically read. Your college verification officer will inspect these directly from your scan.
                            </p>
                          )}
                          {s3Ext.extraction_status === 'LOW_DOCUMENT_QUALITY' && (
                            <p className="text-[10px] text-rose-600 pt-1">
                              Image clarity is below threshold. A clearer scan may be requested.
                            </p>
                          )}
                        </div>
                      ) : docExtraction && legacyFields && Object.keys(legacyFields).length > 0 ? (
                        <div className="space-y-1.5 text-xs">
                          {Object.entries(legacyFields).map(([k, v]) => (
                            <div key={k} className="flex justify-between gap-2 border-b border-slate-100 pb-1">
                              <span className="text-slate-500 capitalize">{k.replace(/_/g, ' ')}:</span>
                              <span className="font-medium text-slate-800 text-right truncate max-w-[160px]">{String(v)}</span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-xs text-slate-400">No structured fields extracted from document.</p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Legal / Assistive Disclaimer */}
          <div className="bg-slate-100 rounded-xl p-4 text-xs text-slate-600 flex items-start gap-2.5 border border-slate-200">
            <HelpCircle className="w-4 h-4 text-teal flex-shrink-0 mt-0.5" />
            <div>
              <strong>Institutional Authority:</strong> Automated OCR verification serves strictly as decision support. Final scholarship eligibility, approvals, physical inspections, and rejections are governed exclusively by college scholarship administrators.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

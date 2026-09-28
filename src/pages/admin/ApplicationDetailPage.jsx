import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useApplications } from '../../context/ApplicationContext';
import { api } from '../../services/api';
import StatusBadge from '../../components/StatusBadge';
import { 
  ArrowLeft, 
  ShieldCheck, 
  AlertTriangle, 
  CheckCircle2, 
  Calendar, 
  User, 
  FileText, 
  Sparkles, 
  Check, 
  XCircle, 
  RotateCcw,
  MapPin,
  Clock,
  Eye,
  Loader2,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  Building,
  History,
  FileCheck,
  HelpCircle
} from 'lucide-react';

const REQUIRED_DOC_TYPES = [
  { key: 'GOVERNMENT_ID', label: 'Government ID / Aadhaar' },
  { key: 'MARKSHEET', label: '10th / 12th Marksheet' },
  { key: 'INCOME_CERTIFICATE', label: 'Income Certificate' },
  { key: 'DOMICILE_CERTIFICATE', label: 'Domicile Certificate' }
];

export default function ApplicationDetailPage() {
  const { id } = useParams();
  const { token, currentUser } = useAuth();
  const { refreshState } = useApplications();

  // Core Data States
  const [app, setApp] = useState(null);
  const [verificationResult, setVerificationResult] = useState(null);
  const [appointment, setAppointment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // UI States
  const [showOcrDetails, setShowOcrDetails] = useState(false);
  const [actionSuccess, setActionSuccess] = useState('');
  const [actionError, setActionError] = useState('');
  const [openingDocId, setOpeningDocId] = useState(null);

  // Modal States
  const [isApproveOpen, setIsApproveOpen] = useState(false);
  const [isCorrectionOpen, setIsCorrectionOpen] = useState(false);
  const [isPhysicalOpen, setIsPhysicalOpen] = useState(false);
  const [isCompletePhysicalOpen, setIsCompletePhysicalOpen] = useState(false);
  const [isRejectOpen, setIsRejectOpen] = useState(false);

  // Form Submissions
  const [submitting, setSubmitting] = useState(false);
  const [approveRemarks, setApproveRemarks] = useState('');
  const [correctionTypes, setCorrectionTypes] = useState([]);
  const [correctionReason, setCorrectionReason] = useState('');
  const [physicalDate, setPhysicalDate] = useState('');
  const [physicalTime, setPhysicalTime] = useState('10:30 AM');
  const [physicalVenue, setPhysicalVenue] = useState('Dean Office, Administrative Block Room 102');
  const [physicalPurpose, setPhysicalPurpose] = useState('Verify original certificates and documents');
  const [physicalInstructions, setPhysicalInstructions] = useState('Bring original certificates along with two photocopies.');
  const [completeResult, setCompleteResult] = useState('VERIFIED');
  const [completeRemarks, setCompleteRemarks] = useState('');
  const [rejectReason, setRejectReason] = useState('');
  const [rejectNotes, setRejectNotes] = useState('');

  // Initial Data Fetch
  const loadData = async () => {
    if (!token || !id) return;
    setLoading(true);
    setError(null);
    try {
      const appData = await api.getApplicationById(id, token);
      setApp(appData);

      // Fetch verification result if available
      try {
        const vrData = await api.getVerificationResult(id, token);
        setVerificationResult(vrData);
      } catch {
        setVerificationResult(null);
      }

      // Fetch appointment if available
      try {
        const apptData = await api.getPhysicalVerificationAppointment(id, token);
        setAppointment(apptData);
      } catch {
        setAppointment(null);
      }
    } catch (err) {
      setError(err.message || "Failed to load application details.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [id, token]);

  const showNotification = (msg, isErr = false) => {
    if (isErr) {
      setActionError(msg);
      setActionSuccess('');
      setTimeout(() => setActionError(''), 6000);
    } else {
      setActionSuccess(msg);
      setActionError('');
      setTimeout(() => setActionSuccess(''), 5000);
    }
  };

  // Document Viewing (Safe Authenticated Blob Streaming)
  const handleViewDoc = async (docId) => {
    if (!app || !docId) return;
    setOpeningDocId(docId);
    try {
      const blob = await api.fetchDocumentBlob(app.id, docId, token);
      const objectUrl = URL.createObjectURL(blob);
      window.open(objectUrl, '_blank');
      setTimeout(() => URL.revokeObjectURL(objectUrl), 60000);
    } catch (err) {
      showNotification(err.message || "Unable to view document file.", true);
    } finally {
      setOpeningDocId(null);
    }
  };

  // 1. Approve Application Action
  const handleApproveSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.adminApproveApplication(app.id, approveRemarks, token);
      setIsApproveOpen(false);
      setApproveRemarks('');
      showNotification("Application has been successfully verified and approved!");
      await loadData();
      await refreshState();
    } catch (err) {
      showNotification(err.message || "Failed to approve application.", true);
    } finally {
      setSubmitting(false);
    }
  };

  // 2. Request Document Correction Action
  const handleCorrectionSubmit = async (e) => {
    e.preventDefault();
    if (correctionTypes.length === 0) {
      showNotification("Please select at least one document type for correction.", true);
      return;
    }
    if (correctionReason.trim().length < 5) {
      showNotification("Correction reason must be at least 5 characters.", true);
      return;
    }
    setSubmitting(true);
    try {
      await api.adminRequestCorrection(app.id, {
        document_types: correctionTypes,
        reason: correctionReason.trim()
      }, token);
      setIsCorrectionOpen(false);
      setCorrectionTypes([]);
      setCorrectionReason('');
      showNotification("Document correction request submitted. Student notified.");
      await loadData();
      await refreshState();
    } catch (err) {
      showNotification(err.message || "Failed to submit correction request.", true);
    } finally {
      setSubmitting(false);
    }
  };

  // 3. Require Physical Verification Action
  const handlePhysicalSubmit = async (e) => {
    e.preventDefault();
    if (!physicalDate) {
      showNotification("Please specify the scheduled date.", true);
      return;
    }
    setSubmitting(true);
    try {
      await api.adminSchedulePhysicalVerification(app.id, {
        scheduled_date: physicalDate,
        scheduled_time: physicalTime,
        venue: physicalVenue,
        purpose: physicalPurpose,
        instructions: physicalInstructions
      }, token);
      setIsPhysicalOpen(false);
      showNotification("Physical verification appointment scheduled successfully!");
      await loadData();
      await refreshState();
    } catch (err) {
      showNotification(err.message || "Failed to schedule physical verification.", true);
    } finally {
      setSubmitting(false);
    }
  };

  // 4. Complete Physical Verification Action
  const handleCompletePhysicalSubmit = async (e) => {
    e.preventDefault();
    if (completeRemarks.trim().length < 3) {
      showNotification("Please provide verification remarks (minimum 3 characters).", true);
      return;
    }
    setSubmitting(true);
    try {
      await api.adminCompletePhysicalVerification(app.id, {
        result: completeResult,
        remarks: completeRemarks.trim()
      }, token);
      setIsCompletePhysicalOpen(false);
      setCompleteRemarks('');
      showNotification(`Physical verification marked as ${completeResult}!`);
      await loadData();
      await refreshState();
    } catch (err) {
      showNotification(err.message || "Failed to complete physical verification.", true);
    } finally {
      setSubmitting(false);
    }
  };

  // 5. Reject Application Action
  const handleRejectSubmit = async (e) => {
    e.preventDefault();
    if (rejectReason.trim().length < 5) {
      showNotification("Please provide a detailed rejection reason (minimum 5 characters).", true);
      return;
    }
    setSubmitting(true);
    try {
      await api.adminRejectApplication(app.id, {
        reason: rejectReason.trim(),
        notes: rejectNotes.trim()
      }, token);
      setIsRejectOpen(false);
      setRejectReason('');
      setRejectNotes('');
      showNotification("Application has been rejected by administration.", false);
      await loadData();
      await refreshState();
    } catch (err) {
      showNotification(err.message || "Failed to reject application.", true);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="p-12 text-center text-slate-500 flex flex-col items-center gap-3">
        <Loader2 className="w-8 h-8 text-teal animate-spin" />
        <span className="text-sm font-medium">Loading application review and verification details...</span>
      </div>
    );
  }

  if (error || !app) {
    return (
      <div className="p-8 max-w-xl mx-auto text-center space-y-4">
        <div className="p-4 bg-rose-50 border border-rose-200 text-rose-800 rounded-xl text-sm font-medium">
          {error || "Application not found."}
        </div>
        <Link to="/admin/applications" className="inline-flex items-center text-xs font-bold text-teal hover:underline">
          <ArrowLeft className="w-4 h-4 mr-1" /> Return to Applications Queue
        </Link>
      </div>
    );
  }

  const reviewHistory = verificationResult?.extracted_data?.review_history || [];
  const riskAnalysis = verificationResult?.risk_analysis || verificationResult?.extracted_data?.risk_analysis;
  const documentQuality = verificationResult?.document_quality || verificationResult?.extracted_data?.document_quality;
  const documentClassification = verificationResult?.document_classification || verificationResult?.extracted_data?.document_classification;
  const correctionRequest = app.correction_request || verificationResult?.extracted_data?.correction_request;
  const tamperConsistency = verificationResult?.tamper_consistency || verificationResult?.extracted_data?.tamper_consistency;
  const authorityVerification = verificationResult?.authority_verification || verificationResult?.extracted_data?.authority_verification;

  return (
    <div className="space-y-6 pb-12">
      {/* Back Button */}
      <Link to="/admin/applications" className="inline-flex items-center text-xs font-semibold text-teal hover:underline">
        <ArrowLeft className="w-4 h-4 mr-1" /> Back to All Applications
      </Link>

      {/* Success Notification Alert */}
      {actionSuccess && (
        <div className="bg-emerald-50 border border-emerald-300 rounded-xl p-4 text-xs font-bold text-emerald-900 flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {/* Error Notification Alert */}
      {actionError && (
        <div className="bg-rose-50 border border-rose-300 rounded-xl p-4 text-xs font-bold text-rose-900 flex items-center gap-2">
          <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0" />
          <span>{actionError}</span>
        </div>
      )}

      {/* 1. APPLICATION HEADER PROFILE BANNER */}
      <div className="bg-navy text-white rounded-2xl p-6 shadow-md flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="font-mono text-xs bg-navy-light px-2.5 py-0.5 rounded text-seafoam font-bold border border-slate-700">
              {app.application_number || app.id}
            </span>
            <span className="text-xs text-slate-300">
              Applied: {app.submitted_at ? new Date(app.submitted_at).toLocaleDateString() : (app.created_at ? new Date(app.created_at).toLocaleDateString() : 'N/A')}
            </span>
          </div>
          <h2 className="text-2xl font-bold text-white">{app.student_name}</h2>
          <p className="text-xs text-slate-300 mt-1">
            {app.scholarship_name} • Student ID: {app.student_id}
          </p>
        </div>

        <div className="flex flex-col items-end gap-2">
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400 font-medium">Final Decision Status:</span>
            <StatusBadge status={app.status} />
          </div>
          {verificationResult && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400 font-medium">AI Verification Status:</span>
              <StatusBadge status={verificationResult.verification_status} confidence={verificationResult.overall_score} />
            </div>
          )}
        </div>
      </div>

      {/* Active Correction Request Banner */}
      {correctionRequest && correctionRequest.status === 'PENDING' && (
        <div className="bg-amber-50 border-2 border-amber-400 rounded-2xl p-5 shadow-sm space-y-2">
          <div className="flex items-center gap-2 text-amber-950 font-bold text-sm">
            <AlertTriangle className="w-5 h-5 text-amber-600" />
            <span>Document Correction Pending from Student</span>
          </div>
          <p className="text-xs text-amber-900">
            <strong>Requested Documents:</strong> {Array.isArray(correctionRequest.document_types) ? correctionRequest.document_types.join(', ') : 'Document'}
          </p>
          <p className="text-xs text-amber-900">
            <strong>Reason:</strong> {correctionRequest.reason}
          </p>
          {correctionRequest.resolved_documents && correctionRequest.resolved_documents.length > 0 && (
            <p className="text-xs text-emerald-800">
              <strong>Replaced by Student:</strong> {correctionRequest.resolved_documents.join(', ')}
            </p>
          )}
        </div>
      )}

      {/* 2. FOUR REQUIRED DOCUMENTS GRID */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-bold text-navy flex items-center gap-2">
              <FileCheck className="w-5 h-5 text-teal" />
              Four Required Verification Documents
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Strictly verify all 4 uploaded mandatory document categories for this scheme
            </p>
          </div>
          <span className="text-xs font-semibold px-3 py-1 bg-slate-100 rounded-full text-slate-700 border border-slate-200">
            {app.documents?.length || 0} of 4 Uploaded
          </span>
        </div>

        <div className="grid sm:grid-cols-2 gap-4">
          {REQUIRED_DOC_TYPES.map(({ key, label }) => {
            const doc = app.documents?.find(d => d.document_type === key);
            const isOpening = openingDocId === doc?.id;
            return (
              <div key={key} className="p-4 rounded-xl border border-slate-200 bg-slate-50 flex flex-col justify-between space-y-3">
                <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                  <span className="font-bold text-sm text-navy">{label}</span>
                  {doc ? (
                    <StatusBadge status={doc.upload_status || 'UPLOADED'} />
                  ) : (
                    <span className="text-[10px] font-bold uppercase tracking-wider bg-slate-200 text-slate-600 px-2 py-0.5 rounded">
                      Not Uploaded
                    </span>
                  )}
                </div>

                {doc ? (
                  <div className="space-y-1.5 text-xs text-slate-600">
                    <div className="font-semibold text-slate-800 truncate" title={doc.original_filename}>
                      {doc.original_filename}
                    </div>
                    <div className="flex justify-between text-slate-400 text-[11px]">
                      <span>Size: {doc.file_size ? `${(doc.file_size / (1024 * 1024)).toFixed(2)} MB` : 'N/A'}</span>
                      <span>Uploaded: {doc.uploaded_at ? new Date(doc.uploaded_at).toLocaleDateString() : 'N/A'}</span>
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-slate-400 italic">Candidate has not uploaded this document yet.</p>
                )}

                <div className="pt-2 border-t border-slate-200 flex justify-end">
                  {doc ? (
                    <button
                      type="button"
                      disabled={isOpening}
                      onClick={() => handleViewDoc(doc.id)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-teal hover:bg-teal-hover text-white text-xs font-semibold rounded-lg transition-colors shadow-sm disabled:opacity-50"
                    >
                      {isOpening ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Eye className="w-3.5 h-3.5" />
                      )}
                      <span>{isOpening ? "Opening..." : "View Document"}</span>
                    </button>
                  ) : (
                    <span className="text-[11px] text-slate-400 font-medium">Document Unavailable</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 3. OVERALL AI VERIFICATION & RISK ANALYSIS ASSISTIVE SUMMARY */}
      {verificationResult ? (
        <div className="grid xl:grid-cols-4 lg:grid-cols-2 md:grid-cols-1 gap-6">
          {/* Stage 1: Document Quality Gate */}
          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-[11px] font-bold uppercase tracking-wider text-teal">Stage 1 Quality Gate</span>
                <h3 className="text-lg font-bold text-navy">Document Quality</h3>
              </div>
              {documentQuality ? (
                <div className="text-right">
                  <span className={`text-xs font-extrabold px-3 py-1 rounded-full border ${
                    documentQuality.quality_gate_status === 'PASS'
                      ? 'bg-emerald-100 text-emerald-900 border-emerald-300'
                      : documentQuality.quality_gate_status === 'WARNING'
                      ? 'bg-amber-100 text-amber-900 border-amber-300'
                      : 'bg-rose-100 text-rose-900 border-rose-300'
                  }`}>
                    {documentQuality.quality_gate_status === 'REUPLOAD_REQUIRED' ? 'RE-UPLOAD REQ' : documentQuality.quality_gate_status} ({documentQuality.overall_quality_score}/100)
                  </span>
                  <span className="text-[10px] text-slate-400 block mt-0.5">Tier: {documentQuality.overall_quality_level}</span>
                </div>
              ) : (
                <span className="text-xs text-slate-400">Not Evaluated</span>
              )}
            </div>

            <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-600 flex items-start gap-2">
              <CheckCircle2 className="w-4 h-4 text-teal flex-shrink-0 mt-0.5" />
              <p className="text-[11px] leading-relaxed">
                Evaluates physical document sharpness, lighting, borders, and OCR readability before downstream verification.
              </p>
            </div>

            {/* Per-document breakdown */}
            {documentQuality?.documents ? (
              <div className="space-y-1.5">
                <span className="text-xs font-bold text-navy">Document Quality Breakdown:</span>
                <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                  {Object.entries(documentQuality.documents).map(([docType, qInfo]) => (
                    <div key={docType} className={`p-2 rounded-lg border text-xs ${
                      qInfo.quality_gate_status === 'REUPLOAD_REQUIRED'
                        ? 'bg-rose-50 border-rose-200 text-rose-950'
                        : qInfo.quality_gate_status === 'WARNING'
                        ? 'bg-amber-50 border-amber-200 text-amber-950'
                        : 'bg-slate-50 border-slate-200 text-slate-800'
                    }`}>
                      <div className="flex items-center justify-between font-bold text-[11px]">
                        <span>{docType.replace(/_/g, ' ')}</span>
                        <span className="font-mono">{qInfo.quality_score}/100</span>
                      </div>
                      {qInfo.reasons && qInfo.reasons.length > 0 ? (
                        <ul className="text-[10px] text-slate-600 mt-1 space-y-0.5 list-disc list-inside">
                          {qInfo.reasons.map((r, rIdx) => (
                            <li key={rIdx}>{r}</li>
                          ))}
                        </ul>
                      ) : (
                        <span className="text-[10px] text-emerald-700 block mt-0.5">Passes automated quality checks</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-xs text-slate-400 italic">No document quality records available.</p>
            )}
          </div>

          {/* Stage 2: Document Classification */}
          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-[11px] font-bold uppercase tracking-wider text-teal">Stage 2 Classification</span>
                <h3 className="text-lg font-bold text-navy">Document Classification</h3>
              </div>
              {documentClassification ? (
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
                  <span className="text-[10px] text-slate-400 block mt-0.5">
                    {documentClassification.mismatched_documents?.length > 0
                      ? `${documentClassification.mismatched_documents.length} mismatched`
                      : 'All slots matched'}
                  </span>
                </div>
              ) : (
                <span className="text-xs text-slate-400">Not Evaluated</span>
              )}
            </div>

            <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-600 flex items-start gap-2">
              <FileCheck className="w-4 h-4 text-teal flex-shrink-0 mt-0.5" />
              <p className="text-[11px] leading-relaxed">
                Verifies that uploaded documents match their assigned scholarship slots before downstream extraction.
              </p>
            </div>

            {/* Per-document classification breakdown */}
            {documentClassification?.documents ? (
              <div className="space-y-1.5">
                <span className="text-xs font-bold text-navy">Document Slot Match Breakdown:</span>
                <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                  {Object.entries(documentClassification.documents).map(([docType, cInfo]) => (
                    <div key={docType} className={`p-2 rounded-lg border text-xs ${
                      cInfo.classification_status === 'DOCUMENT_TYPE_MISMATCH' || cInfo.classification_status === 'UNKNOWN'
                        ? 'bg-rose-50 border-rose-200 text-rose-950'
                        : cInfo.classification_status === 'WARNING'
                        ? 'bg-amber-50 border-amber-200 text-amber-950'
                        : 'bg-slate-50 border-slate-200 text-slate-800'
                    }`}>
                      <div className="flex items-center justify-between font-bold text-[11px]">
                        <span>{docType.replace(/_/g, ' ')}</span>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${
                          cInfo.classification_status === 'PASS'
                            ? 'bg-emerald-100 text-emerald-800'
                            : cInfo.classification_status === 'WARNING'
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-rose-100 text-rose-800'
                        }`}>
                          {cInfo.predicted_type ? cInfo.predicted_type.replace(/_/g, ' ') : 'N/A'} ({(cInfo.confidence * 100).toFixed(1)}%)
                        </span>
                      </div>
                      {cInfo.reasons && cInfo.reasons.length > 0 ? (
                        <ul className="text-[10px] text-slate-600 mt-1 space-y-0.5 list-disc list-inside">
                          {cInfo.reasons.map((r, rIdx) => (
                            <li key={rIdx}>{r}</li>
                          ))}
                        </ul>
                      ) : (
                        <span className="text-[10px] text-emerald-700 block mt-0.5">Matched to expected slot</span>
                      )}
                      {cInfo.alternatives && cInfo.alternatives.length > 0 && (
                        <div className="text-[9px] text-slate-400 mt-1 flex flex-wrap gap-1">
                          <span>Alt:</span>
                          {cInfo.alternatives.slice(0, 2).map((alt, aIdx) => (
                            <span key={aIdx} className="bg-white/80 px-1 rounded border border-slate-200">
                              {alt.class_name.replace(/_/g, ' ')} ({(alt.confidence * 100).toFixed(0)}%)
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-xs text-slate-400 italic">No document classification records available.</p>
            )}
          </div>

          {/* AI Verification Score & Issues */}
          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-[11px] font-bold uppercase tracking-wider text-teal">Assistive AI Engine</span>
                <h3 className="text-lg font-bold text-navy">AI Verification Evaluation</h3>
              </div>
              <div className="text-right">
                <span className="text-2xl font-black text-teal">{verificationResult.overall_score}%</span>
                <span className="text-[10px] text-slate-400 block">Overall Score</span>
              </div>
            </div>

            <div className="p-3 bg-seafoam-light border border-seafoam rounded-xl text-xs text-navy flex items-start gap-2">
              <Sparkles className="w-4 h-4 text-teal flex-shrink-0 mt-0.5" />
              <p className="text-[11px] leading-relaxed">
                <strong>Notice:</strong> This automated score and check matrix is an assistive review tool. All final verification decisions remain strictly with the administrative officer.
              </p>
            </div>

            {verificationResult.issues && verificationResult.issues.length > 0 ? (
              <div className="space-y-1.5">
                <span className="text-xs font-bold text-navy">Identified Issues & Discrepancies:</span>
                <div className="space-y-1 max-h-44 overflow-y-auto pr-1">
                  {verificationResult.issues.map((issue, idx) => (
                    <div key={idx} className="p-2 rounded-lg bg-amber-50 border border-amber-200 text-amber-950 text-xs flex items-start gap-2">
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-600 flex-shrink-0 mt-0.5" />
                      <span>{issue}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                <span>No critical discrepancies or scheme eligibility violations flagged.</span>
              </div>
            )}
          </div>

          {/* Prototype ML/AI Risk Analysis */}
          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-[11px] font-bold uppercase tracking-wider text-teal">Review-Risk Signal</span>
                <h3 className="text-lg font-bold text-navy">Administrative Review Risk</h3>
              </div>
              {riskAnalysis ? (
                <div className="text-right">
                  <span className={`text-xs font-extrabold px-3 py-1 rounded-full border ${
                    riskAnalysis.risk_level === 'LOW'
                      ? 'bg-emerald-100 text-emerald-900 border-emerald-300'
                      : riskAnalysis.risk_level === 'MEDIUM'
                      ? 'bg-amber-100 text-amber-900 border-amber-300'
                      : 'bg-rose-100 text-rose-900 border-rose-300'
                  }`}>
                    {riskAnalysis.risk_level} RISK ({riskAnalysis.risk_score})
                  </span>
                </div>
              ) : (
                <span className="text-xs text-slate-400">Not Evaluated</span>
              )}
            </div>

            <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-600 flex items-start gap-2">
              <ShieldCheck className="w-4 h-4 text-teal flex-shrink-0 mt-0.5" />
              <p className="text-[11px] leading-relaxed">
                Risk analysis is a review-assistance signal and does not independently determine approval or rejection.
              </p>
            </div>

            {riskAnalysis && riskAnalysis.explanation && riskAnalysis.explanation.length > 0 ? (
              <div className="space-y-1.5">
                <span className="text-xs font-bold text-navy">Risk Assessment Contributing Factors:</span>
                <ul className="space-y-1 text-xs text-slate-700 max-h-40 overflow-y-auto pr-1">
                  {riskAnalysis.explanation.map((factor, idx) => (
                    <li key={idx} className="p-2 rounded bg-slate-50 border border-slate-100 flex items-start gap-2 text-[11px]">
                      <span className="text-teal font-bold">•</span>
                      <span>{factor}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <p className="text-xs text-slate-400 italic">No additional risk contributing factors recorded.</p>
            )}
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm text-center py-8">
          <Clock className="w-8 h-8 text-slate-400 mx-auto mb-2" />
          <h4 className="font-bold text-navy text-sm">No Automated AI Verification Result Found</h4>
          <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
            This application has not been passed through automated OCR and eligibility rules engine verification.
          </p>
        </div>
      )}

      {/* 4. RULES ENGINE FIELD CHECKS & CROSS-DOCUMENT MATRIX */}
      {verificationResult && (
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
          <h3 className="text-lg font-bold text-navy flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-teal" />
            Rules Engine Field Consistency Checks
          </h3>

          <div className="grid sm:grid-cols-2 gap-3">
            {verificationResult.field_checks && Object.entries(verificationResult.field_checks).map(([checkKey, checkData]) => {
              const status = typeof checkData === 'object' && checkData !== null ? checkData.status : String(checkData);
              const details = typeof checkData === 'object' && checkData !== null ? checkData.details : '';
              const displayName = checkKey.replace(/_/g, ' ');

              return (
                <div key={checkKey} className="p-3.5 rounded-xl border border-slate-100 bg-slate-50 flex items-start justify-between gap-3">
                  <div>
                    <h4 className="font-bold text-xs text-slate-900 capitalize">{displayName}</h4>
                    {details && <p className="text-[11px] text-slate-500 mt-0.5">{details}</p>}
                  </div>
                  <StatusBadge status={status} />
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 4b. STAGE 4: TAMPER DETECTION & CROSS-DOCUMENT CONSISTENCY REVIEW */}
      {tamperConsistency && (
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 pb-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-bold uppercase tracking-wider text-teal">Stage 4 AI Verification</span>
                <span className="text-[10px] font-mono text-slate-400 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                  {tamperConsistency.stage_version || 'v1.0.0'}
                </span>
              </div>
              <h3 className="text-lg font-bold text-navy flex items-center gap-2 mt-0.5">
                <ShieldCheck className="w-5 h-5 text-teal" />
                Tamper Detection & Cross-Document Consistency Review
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Evaluates cross-document identity coherence and physical/structural image manipulation signals
              </p>
            </div>

            <div className="flex items-center gap-3">
              <div className="text-right">
                <span className="text-xs text-slate-400 block">Stage 4 Status</span>
                <span className={`text-xs font-extrabold px-3 py-1 rounded-full border ${
                  tamperConsistency.overall_status === 'PASS'
                    ? 'bg-emerald-100 text-emerald-900 border-emerald-300'
                    : tamperConsistency.overall_status === 'WARNING'
                    ? 'bg-amber-100 text-amber-900 border-amber-300'
                    : 'bg-rose-100 text-rose-900 border-rose-300'
                }`}>
                  {tamperConsistency.overall_status} ({tamperConsistency.overall_score}/100)
                </span>
              </div>
            </div>
          </div>

          {/* Action Alert Banner for Admin */}
          {tamperConsistency.review_required && (
            <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl flex items-start gap-3 text-xs text-rose-950">
              <AlertTriangle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
              <div className="space-y-1">
                <span className="font-bold block text-sm">Administrative Attention Recommended</span>
                <p className="leading-relaxed">
                  The automated consistency checker flagged critical discrepancies across applicant records.
                  Review the highlighted items below and consider physical certificate inspection or student clarification before final approval.
                </p>
              </div>
            </div>
          )}

          {/* Score Cards Grid */}
          <div className="grid md:grid-cols-2 gap-4">
            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/70 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-navy">Cross-Document Consistency Score</span>
                <span className={`font-mono text-xs font-bold px-2 py-0.5 rounded ${
                  (tamperConsistency.consistency_assessment?.overall_score || 0) >= 80
                    ? 'bg-emerald-100 text-emerald-800'
                    : (tamperConsistency.consistency_assessment?.overall_score || 0) >= 60
                    ? 'bg-amber-100 text-amber-800'
                    : 'bg-rose-100 text-rose-800'
                }`}>
                  {tamperConsistency.consistency_assessment?.overall_score ?? 'N/A'}/100
                </span>
              </div>
              <p className="text-[11px] text-slate-500 leading-relaxed">
                Verifies semantic alignment across names, DOB, masked ID numbers, marksheet math, and certificate dates.
              </p>
            </div>

            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/70 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-navy">Document Tamper Cleanliness Score</span>
                <span className={`font-mono text-xs font-bold px-2 py-0.5 rounded ${
                  (tamperConsistency.tamper_assessment?.overall_score || 0) >= 80
                    ? 'bg-emerald-100 text-emerald-800'
                    : (tamperConsistency.tamper_assessment?.overall_score || 0) >= 60
                    ? 'bg-amber-100 text-amber-800'
                    : 'bg-rose-100 text-rose-800'
                }`}>
                  {tamperConsistency.tamper_assessment?.overall_score ?? 'N/A'}/100
                </span>
              </div>
              <p className="text-[11px] text-slate-500 leading-relaxed">
                Analyzes Error Level Analysis (ELA), localized sharpness/blur, noise distribution, and editing software metadata.
              </p>
            </div>
          </div>

          {/* Cross-Document Consistency Matrix */}
          {tamperConsistency.consistency_assessment?.checks?.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="font-bold text-xs uppercase tracking-wider text-slate-700">
                  Cross-Document Consistency Checks ({tamperConsistency.consistency_assessment.checks.length})
                </h4>
              </div>

              <div className="rounded-xl border border-slate-200 overflow-hidden text-xs">
                <div className="divide-y divide-slate-100">
                  {tamperConsistency.consistency_assessment.checks.map((chk, cIdx) => (
                    <div key={cIdx} className="p-3.5 hover:bg-slate-50/80 transition-colors flex flex-col md:flex-row md:items-center justify-between gap-3">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-navy capitalize">
                            {chk.check_name.replace(/_/g, ' ')}
                          </span>
                          <span className="text-[10px] text-slate-400 bg-slate-100 px-2 py-0.5 rounded">
                            {chk.documents_compared.join(' ↔ ')}
                          </span>
                          {chk.match_type && (
                            <span className="text-[9px] font-mono px-1.5 py-0.5 bg-slate-200 text-slate-700 rounded">
                              {chk.match_type}
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-slate-600">
                          {chk.reason}
                        </p>
                        {chk.values_compared && Object.keys(chk.values_compared).length > 0 && (
                          <div className="flex flex-wrap gap-2 pt-1 text-[10px] text-slate-500">
                            {Object.entries(chk.values_compared).map(([kDoc, vVal]) => (
                              <span key={kDoc} className="bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200 font-mono">
                                <strong>{kDoc}:</strong> {String(vVal)}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>

                      <div className="flex-shrink-0">
                        <StatusBadge status={chk.status} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Tamper Signals Breakdown */}
          {tamperConsistency.tamper_assessment?.signals?.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="font-bold text-xs uppercase tracking-wider text-slate-700">
                  Visual, Structural & Metadata Tamper Signals
                </h4>
              </div>

              <div className="grid md:grid-cols-2 gap-3">
                {tamperConsistency.tamper_assessment.signals.map((sig, sIdx) => (
                  <div key={sIdx} className={`p-3 rounded-xl border text-xs space-y-1 ${
                    sig.status === 'WARNING'
                      ? 'bg-amber-50/70 border-amber-200 text-amber-950'
                      : sig.status === 'NEEDS_REVIEW'
                      ? 'bg-rose-50/70 border-rose-200 text-rose-950'
                      : 'bg-slate-50 border-slate-200 text-slate-800'
                  }`}>
                    <div className="flex items-center justify-between font-bold text-[11px]">
                      <span className="capitalize">{sig.signal_name.replace(/_/g, ' ')}</span>
                      <div className="flex items-center gap-1.5">
                        <span className="text-[9px] uppercase px-1.5 py-0.5 rounded bg-white/80 border font-mono">
                          {sig.category}
                        </span>
                        <StatusBadge status={sig.status} />
                      </div>
                    </div>
                    <p className="text-[11px] text-slate-600 leading-relaxed">
                      {sig.explanation}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* 4c. STAGE 5: AUTHORITY VERIFICATION / EXTERNAL RECORD VERIFICATION */}
      {authorityVerification && (
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 pb-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-bold uppercase tracking-wider text-teal">Stage 5 AI Verification</span>
                <span className="text-[10px] font-mono text-slate-400 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                  {authorityVerification.stage_version || 'v1.0.0'}
                </span>
              </div>
              <h3 className="text-lg font-bold text-navy flex items-center gap-2 mt-0.5">
                <Building className="w-5 h-5 text-teal" />
                Authority Verification / External Record Verification
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Independent cross-referencing against authoritative registries and depository records
              </p>
            </div>

            <div className="flex items-center gap-3">
              <div className="text-right">
                <span className="text-xs text-slate-400 block">Authority Status</span>
                <span className={`text-xs font-extrabold px-3 py-1 rounded-full border ${
                  authorityVerification.overall_status === 'MATCH'
                    ? 'bg-emerald-100 text-emerald-900 border-emerald-300'
                    : authorityVerification.overall_status === 'MISMATCH'
                    ? 'bg-rose-100 text-rose-900 border-rose-300'
                    : authorityVerification.overall_status === 'BLOCKED'
                    ? 'bg-slate-100 text-slate-700 border-slate-300'
                    : authorityVerification.overall_status === 'ERROR'
                    ? 'bg-amber-100 text-amber-900 border-amber-300'
                    : 'bg-blue-50 text-blue-800 border-blue-200'
                }`}>
                  {authorityVerification.overall_status === 'NOT_AVAILABLE'
                    ? 'UNAVAILABLE / NOT CONFIGURED'
                    : authorityVerification.overall_status === 'BLOCKED'
                    ? 'SKIPPED (PRIOR GATE)'
                    : authorityVerification.overall_status}
                </span>
                <span className="text-[10px] text-slate-400 block mt-0.5 font-mono">
                  Evidence: {authorityVerification.overall_evidence_strength || 'NONE'}
                </span>
              </div>
            </div>
          </div>

          {/* Informational / Alert Banners */}
          {authorityVerification.overall_status === 'MISMATCH' && (
            <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl flex items-start gap-3 text-xs text-rose-950">
              <AlertTriangle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
              <div className="space-y-1">
                <span className="font-bold block text-sm">Authority Record Mismatch — Administrative Review Recommended</span>
                <p className="leading-relaxed">
                  An authoritative record was returned, but one or more critical fields conflict with the uploaded document.
                  Review the highlighted field discrepancies below. Consider requesting physical verification before final approval.
                </p>
              </div>
            </div>
          )}

          {authorityVerification.overall_status === 'NOT_AVAILABLE' && (
            <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl flex items-start gap-3 text-xs text-slate-600">
              <HelpCircle className="w-4 h-4 text-teal flex-shrink-0 mt-0.5" />
              <div className="space-y-0.5">
                <span className="font-semibold text-slate-800">Authority Verification Unavailable (Prototype State)</span>
                <p className="text-[11px] leading-relaxed">
                  An authorized external verification provider (such as DigiLocker or NAD) is not configured in this deployment environment.
                  This is neutral informational status and does not negatively affect the verification score.
                </p>
              </div>
            </div>
          )}

          {authorityVerification.overall_status === 'BLOCKED' && (
            <div className="p-3.5 bg-amber-50/70 border border-amber-200 rounded-xl flex items-start gap-3 text-xs text-amber-900">
              <AlertCircle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
              <div className="space-y-0.5">
                <span className="font-semibold text-amber-950">Authority Verification Skipped (Quality / Classification Gate)</span>
                <p className="text-[11px] leading-relaxed">
                  Stage 5 was intentionally bypassed because earlier stages flagged document quality or slot mismatches requiring student re-upload.
                </p>
              </div>
            </div>
          )}

          {authorityVerification.overall_status === 'ERROR' && (
            <div className="p-3.5 bg-amber-50 border border-amber-200 rounded-xl flex items-start gap-3 text-xs text-amber-900">
              <AlertCircle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
              <div className="space-y-0.5">
                <span className="font-semibold text-amber-950">Authority Provider Technical Advisory</span>
                <p className="text-[11px] leading-relaxed">
                  The external provider experienced a temporary connection timeout or service unavailability. This does not indicate document fraud.
                </p>
              </div>
            </div>
          )}

          {/* Per-Document Authority Breakdown */}
          {authorityVerification.documents && Object.keys(authorityVerification.documents).length > 0 && (
            <div className="space-y-3">
              <h4 className="font-bold text-xs uppercase tracking-wider text-slate-700">
                Document-Level Authority Verification Records
              </h4>

              <div className="grid md:grid-cols-2 gap-4">
                {Object.entries(authorityVerification.documents).map(([docType, authRec]) => (
                  <div key={docType} className={`p-4 rounded-xl border text-xs space-y-2.5 ${
                    authRec.status === 'MISMATCH'
                      ? 'bg-rose-50/60 border-rose-200 text-rose-950'
                      : authRec.status === 'MATCH'
                      ? 'bg-emerald-50/60 border-emerald-200 text-emerald-950'
                      : authRec.status === 'BLOCKED'
                      ? 'bg-amber-50/40 border-amber-200 text-amber-950'
                      : 'bg-slate-50 border-slate-200 text-slate-800'
                  }`}>
                    <div className="flex items-center justify-between border-b border-slate-200/80 pb-2">
                      <div>
                        <span className="font-bold text-navy capitalize">{docType.replace(/_/g, ' ')}</span>
                        <span className="text-[10px] text-slate-400 block font-mono">
                          Provider: {authRec.provider} ({authRec.provider_version || '1.0.0'})
                        </span>
                      </div>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider ${
                        authRec.status === 'MATCH'
                          ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                          : authRec.status === 'MISMATCH'
                          ? 'bg-rose-100 text-rose-800 border border-rose-200'
                          : authRec.status === 'BLOCKED'
                          ? 'bg-slate-200 text-slate-700'
                          : 'bg-blue-100 text-blue-800'
                      }`}>
                        {authRec.status}
                      </span>
                    </div>

                    <div className="space-y-1 text-[11px]">
                      <div className="flex justify-between text-slate-500">
                        <span>Verification ID:</span>
                        <span className="font-mono text-slate-700">{authRec.verification_id}</span>
                      </div>
                      {authRec.reference_id && (
                        <div className="flex justify-between text-slate-500">
                          <span>Reference ID:</span>
                          <span className="font-mono font-bold text-slate-800">{authRec.reference_id}</span>
                        </div>
                      )}
                      <div className="flex justify-between text-slate-500">
                        <span>Evidence Strength:</span>
                        <span className="font-semibold text-slate-700">{authRec.evidence_strength || 'NONE'}</span>
                      </div>
                      <p className="text-[11px] text-slate-600 pt-1 italic">
                        {authRec.reason}
                      </p>
                    </div>

                    {/* Field Comparison Details */}
                    {authRec.field_comparisons && Object.keys(authRec.field_comparisons).length > 0 && (
                      <div className="pt-2 border-t border-slate-200/80 space-y-1">
                        <span className="text-[10px] font-bold text-slate-600 block">Compared Fields:</span>
                        <div className="space-y-1">
                          {Object.entries(authRec.field_comparisons).map(([fKey, fRes]) => (
                            <div key={fKey} className="flex items-center justify-between text-[10px] bg-white/70 p-1.5 rounded border border-slate-100">
                              <span className="capitalize text-slate-700">{fKey.replace(/_/g, ' ')}</span>
                              <span className={`px-1.5 py-0.5 rounded font-bold ${
                                fRes.status === 'MATCH'
                                  ? 'text-emerald-700 bg-emerald-50'
                                  : fRes.status === 'MISMATCH'
                                  ? 'text-rose-700 bg-rose-50'
                                  : 'text-slate-500 bg-slate-100'
                              }`}>
                                {fRes.status}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* 5. OCR EXTRACTED DATA EXPANDABLE SECTION */}
      {verificationResult && verificationResult.extracted_data && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <button
            onClick={() => setShowOcrDetails(!showOcrDetails)}
            className="w-full p-6 text-left flex items-center justify-between bg-white hover:bg-slate-50 transition-colors"
          >
            <div>
              <h3 className="text-lg font-bold text-navy flex items-center gap-2">
                <FileText className="w-5 h-5 text-teal" />
                OCR Extracted Document Data Fields
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Inspect structured text and metadata extracted directly from the candidate's documents
              </p>
            </div>
            <div className="flex items-center gap-2 text-xs font-bold text-teal">
              <span>{showOcrDetails ? "Hide OCR Details" : "View Extracted Fields"}</span>
              {showOcrDetails ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </div>
          </button>

          {showOcrDetails && (
            <div className="p-6 pt-0 border-t border-slate-100 space-y-6">
              <div className="grid md:grid-cols-2 gap-4 pt-4">
                {[
                  { key: 'GOVERNMENT_ID', title: 'Government ID / Identity Card' },
                  { key: 'MARKSHEET', title: '10th / 12th Academic Marksheet' },
                  { key: 'INCOME_CERTIFICATE', title: 'Annual Income Certificate' },
                  { key: 'DOMICILE_CERTIFICATE', title: 'State Domicile Certificate' },
                ].map(({ key, title }) => {
                  const s3Ext = verificationResult.extracted_data?.field_extraction?.[key];
                  const legacyExt = verificationResult.extracted_data?.[key];

                  return (
                    <div key={key} className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-3">
                      <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                        <div>
                          <h4 className="font-bold text-xs text-navy uppercase tracking-wider">
                            {title}
                          </h4>
                          {s3Ext && (
                            <span className="text-[10px] text-slate-500 block">
                              Extractor: {s3Ext.extractor_version || 'v1'} • Confidence: {((s3Ext.overall_confidence || 0) * 100).toFixed(0)}%
                            </span>
                          )}
                        </div>
                        {s3Ext ? (
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                            s3Ext.extraction_status === 'COMPLETE'
                              ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                              : s3Ext.extraction_status === 'PARTIAL'
                              ? 'bg-amber-100 text-amber-800 border border-amber-200'
                              : 'bg-rose-100 text-rose-800 border border-rose-200'
                          }`}>
                            {s3Ext.extraction_status}
                          </span>
                        ) : legacyExt ? (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-200 text-slate-700">
                            Extracted
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-400">
                            Not Found
                          </span>
                        )}
                      </div>

                      {/* Stage 3 Structured Fields */}
                      {s3Ext && s3Ext.fields && Object.keys(s3Ext.fields).length > 0 ? (
                        <div className="space-y-1.5 text-xs">
                          {Object.entries(s3Ext.fields).map(([fKey, fData]) => {
                            if (fKey === 'subjects' && Array.isArray(fData.normalized_value) && fData.normalized_value.length > 0) {
                              return (
                                <div key={fKey} className="pt-2 border-t border-slate-200/60">
                                  <span className="text-[11px] font-bold text-slate-700 block mb-1">
                                    Academic Subjects Breakdown ({fData.normalized_value.length}):
                                  </span>
                                  <div className="bg-white rounded-lg border border-slate-200 overflow-hidden text-[10px]">
                                    <table className="w-full text-left">
                                      <thead className="bg-slate-100/70 border-b border-slate-200 text-slate-600 font-semibold">
                                        <tr>
                                          <th className="p-1.5 pl-2">Subject</th>
                                          <th className="p-1.5 text-right">Marks</th>
                                          <th className="p-1.5 text-right">Max</th>
                                          <th className="p-1.5 pr-2 text-right">Grade</th>
                                        </tr>
                                      </thead>
                                      <tbody className="divide-y divide-slate-100 text-slate-700">
                                        {fData.normalized_value.map((subj, sIdx) => (
                                          <tr key={sIdx}>
                                            <td className="p-1.5 pl-2 font-medium">{subj.subject_name}</td>
                                            <td className="p-1.5 text-right font-mono">{subj.marks_obtained ?? '-'}</td>
                                            <td className="p-1.5 text-right font-mono">{subj.maximum_marks ?? '-'}</td>
                                            <td className="p-1.5 pr-2 text-right font-bold">{subj.grade ?? '-'}</td>
                                          </tr>
                                        ))}
                                      </tbody>
                                    </table>
                                  </div>
                                </div>
                              );
                            }

                            const displayVal = fData.display_value || fData.normalized_value || fData.raw_value;
                            const isExtracted = fData.extraction_status === 'EXTRACTED';

                            return (
                              <div key={fKey} className="flex items-center justify-between py-1 border-b border-slate-100 last:border-0">
                                <span className="text-slate-500 capitalize">{fKey.replace(/_/g, ' ')}:</span>
                                <div className="flex items-center gap-1.5">
                                  <span className={`font-semibold ${isExtracted ? 'text-slate-800' : 'text-slate-400 italic'}`}>
                                    {isExtracted ? String(displayVal) : 'Not Found'}
                                  </span>
                                  {isExtracted && fData.confidence > 0 && (
                                    <span className="text-[9px] font-mono px-1 py-0.2 bg-teal-50 text-teal rounded border border-teal/20">
                                      {(fData.confidence * 100).toFixed(0)}%
                                    </span>
                                  )}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      ) : legacyExt ? (
                        <div className="space-y-1 text-xs">
                          {Object.entries(legacyExt).map(([k, v]) => (
                            <div key={k} className="flex justify-between py-0.5">
                              <span className="text-slate-500 capitalize">{k.replace(/_/g, ' ')}:</span>
                              <span className="font-semibold text-slate-800">{String(v)}</span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-xs text-slate-400 italic">No structured extraction available.</p>
                      )}

                      {/* Warnings if any */}
                      {s3Ext && s3Ext.warnings && s3Ext.warnings.length > 0 && (
                        <div className="pt-2 border-t border-slate-200/60 text-[10px] text-amber-800 bg-amber-50/50 p-2 rounded">
                          <span className="font-bold">Extraction Notes:</span> {s3Ext.warnings.join(' • ')}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* 6. PHYSICAL VERIFICATION APPOINTMENT SECTION */}
      {appointment && (
        <div className="bg-teal-50 border-2 border-teal rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-teal/20 pb-3">
            <div>
              <span className="px-2.5 py-0.5 bg-teal text-white rounded text-[10px] font-bold uppercase tracking-wider">
                Official Appointment
              </span>
              <h3 className="text-lg font-bold text-navy mt-1 flex items-center gap-2">
                <Calendar className="w-5 h-5 text-teal" />
                Scheduled Physical Document Verification
              </h3>
            </div>
            <StatusBadge status={appointment.status} />
          </div>

          <div className="grid sm:grid-cols-3 gap-4 text-xs">
            <div className="bg-white p-3.5 rounded-xl border border-teal/20 space-y-1">
              <span className="text-slate-400 text-[11px] block">Date & Time</span>
              <span className="font-bold text-navy text-sm">{appointment.scheduled_date} at {appointment.scheduled_time}</span>
            </div>
            <div className="bg-white p-3.5 rounded-xl border border-teal/20 space-y-1">
              <span className="text-slate-400 text-[11px] block">Venue / Office Location</span>
              <span className="font-bold text-slate-800 text-xs">{appointment.venue}</span>
            </div>
            <div className="bg-white p-3.5 rounded-xl border border-teal/20 space-y-1">
              <span className="text-slate-400 text-[11px] block">Verification Purpose</span>
              <span className="font-medium text-slate-700 text-xs">{appointment.instructions || "Verify original certificates"}</span>
            </div>
          </div>

          {appointment.notes && (
            <div className="p-3 bg-white rounded-xl border border-teal/20 text-xs text-slate-700">
              <strong>Recorded Outcome / Notes:</strong> {appointment.notes}
            </div>
          )}

          {appointment.status === 'SCHEDULED' && (
            <div className="pt-2 flex justify-end">
              <button
                type="button"
                onClick={() => setIsCompletePhysicalOpen(true)}
                className="flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl shadow transition-colors"
              >
                <Check className="w-4 h-4" />
                <span>Complete Physical Verification Outcome</span>
              </button>
            </div>
          )}
        </div>
      )}

      {/* 7. REVIEW AUDIT HISTORY TIMELINE */}
      {reviewHistory && reviewHistory.length > 0 && (
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
          <h3 className="text-lg font-bold text-navy flex items-center gap-2">
            <History className="w-5 h-5 text-teal" />
            Administrative Review Audit Trail
          </h3>

          <div className="space-y-3">
            {reviewHistory.map((entry, idx) => (
              <div key={idx} className="p-4 rounded-xl border border-slate-100 bg-slate-50 flex flex-wrap items-start justify-between gap-4 text-xs">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-bold px-2 py-0.5 rounded bg-navy text-white text-[10px] tracking-wider uppercase">
                      {entry.action}
                    </span>
                    <span className="font-semibold text-slate-800">{entry.admin_name || 'Admin Officer'}</span>
                    <span className="text-slate-400 text-[11px]">({entry.admin_email})</span>
                  </div>
                  {entry.reason && (
                    <p className="text-slate-700 text-xs mt-1">
                      <strong>Remarks:</strong> {entry.reason}
                    </p>
                  )}
                  {entry.notes && entry.notes !== entry.reason && (
                    <p className="text-slate-600 text-xs mt-0.5">
                      <strong>Notes:</strong> {entry.notes}
                    </p>
                  )}
                </div>
                <div className="text-right text-slate-400 text-[11px]">
                  {entry.timestamp ? new Date(entry.timestamp).toLocaleString() : 'Recent'}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 8. ADMIN ACTIONS CONTROL CONSOLE */}
      <div className="bg-white rounded-2xl p-6 border-2 border-navy shadow-md space-y-4">
        <div className="flex items-center justify-between border-b border-slate-200 pb-3">
          <div>
            <span className="text-xs font-bold text-teal uppercase tracking-wider">Human-in-the-Loop Authority</span>
            <h3 className="text-lg font-bold text-navy">Administrative Final Review Actions</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Select an authoritative administrative action for this scholarship application:
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3 pt-2">
          {/* Action 1: Approve */}
          <button
            type="button"
            onClick={() => setIsApproveOpen(true)}
            disabled={app.status === 'REJECTED' || app.status === 'VERIFIED'}
            className="flex items-center gap-1.5 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-40 text-white font-bold text-xs rounded-xl shadow transition-colors"
          >
            <Check className="w-4 h-4" />
            <span>Approve Application</span>
          </button>

          {/* Action 2: Request Document Correction */}
          <button
            type="button"
            onClick={() => setIsCorrectionOpen(true)}
            disabled={app.status === 'REJECTED'}
            className="flex items-center gap-1.5 px-5 py-2.5 bg-amber-600 hover:bg-amber-700 disabled:opacity-40 text-white font-bold text-xs rounded-xl shadow transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
            <span>Request Document Correction</span>
          </button>

          {/* Action 3: Require Physical Verification */}
          <button
            type="button"
            onClick={() => setIsPhysicalOpen(true)}
            disabled={app.status === 'REJECTED'}
            className="flex items-center gap-1.5 px-5 py-2.5 bg-teal hover:bg-teal-hover disabled:opacity-40 text-white font-bold text-xs rounded-xl shadow transition-colors"
          >
            <Calendar className="w-4 h-4" />
            <span>Require Physical Verification</span>
          </button>

          {/* Action 4: Reject */}
          <button
            type="button"
            onClick={() => setIsRejectOpen(true)}
            disabled={app.status === 'REJECTED'}
            className="flex items-center gap-1.5 px-5 py-2.5 bg-rose-600 hover:bg-rose-700 disabled:opacity-40 text-white font-bold text-xs rounded-xl shadow transition-colors"
          >
            <XCircle className="w-4 h-4" />
            <span>Reject Application</span>
          </button>
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* MODAL 1: APPROVE APPLICATION CONFIRMATION                          */}
      {/* ------------------------------------------------------------------ */}
      {isApproveOpen && (
        <div className="fixed inset-0 z-50 bg-navy/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full border border-slate-200 overflow-hidden animate-in fade-in zoom-in duration-150">
            <div className="bg-navy text-white p-5 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                <h3 className="font-bold text-base">Approve Scholarship Application</h3>
              </div>
              <button onClick={() => setIsApproveOpen(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>

            <form onSubmit={handleApproveSubmit} className="p-6 space-y-4">
              <p className="text-xs text-slate-700 leading-relaxed">
                You are about to verify and approve <strong>{app.student_name}</strong>'s application for <strong>{app.scholarship_name}</strong>. This confirms all 4 required documents have been satisfactorily checked.
              </p>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Administrative Approval Remarks (Optional)
                </label>
                <textarea
                  value={approveRemarks}
                  onChange={(e) => setApproveRemarks(e.target.value)}
                  placeholder="e.g. All documents physically and digitally authenticated."
                  rows={3}
                  className="w-full p-2.5 border border-slate-300 rounded-xl text-xs focus:ring-2 focus:ring-teal outline-none"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsApproveOpen(false)}
                  className="px-4 py-2 text-xs font-bold text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex items-center gap-1.5 px-5 py-2 text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-700 rounded-xl shadow disabled:opacity-50"
                >
                  {submitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>{submitting ? "Approving..." : "Confirm Approval"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* MODAL 2: REQUEST DOCUMENT CORRECTION                               */}
      {/* ------------------------------------------------------------------ */}
      {isCorrectionOpen && (
        <div className="fixed inset-0 z-50 bg-navy/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full border border-slate-200 overflow-hidden animate-in fade-in zoom-in duration-150">
            <div className="bg-navy text-white p-5 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <RotateCcw className="w-5 h-5 text-amber-400" />
                <h3 className="font-bold text-base">Request Document Correction</h3>
              </div>
              <button onClick={() => setIsCorrectionOpen(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>

            <form onSubmit={handleCorrectionSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-bold text-navy mb-2">
                  Select Documents Requiring Replacement:
                </label>
                <div className="space-y-2">
                  {REQUIRED_DOC_TYPES.map(({ key, label }) => {
                    const isUploaded = app.documents?.some(d => d.document_type === key);
                    const isChecked = correctionTypes.includes(key);

                    return (
                      <label
                        key={key}
                        className={`flex items-center gap-2 p-2.5 rounded-xl border text-xs cursor-pointer transition-colors ${
                          !isUploaded
                            ? 'bg-slate-100 text-slate-400 border-slate-200 cursor-not-allowed'
                            : isChecked
                            ? 'bg-amber-50 text-amber-950 border-amber-300 font-semibold'
                            : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
                        }`}
                      >
                        <input
                          type="checkbox"
                          disabled={!isUploaded}
                          checked={isChecked}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setCorrectionTypes([...correctionTypes, key]);
                            } else {
                              setCorrectionTypes(correctionTypes.filter(t => t !== key));
                            }
                          }}
                          className="rounded text-teal focus:ring-teal"
                        />
                        <span>{label}</span>
                        {!isUploaded && <span className="text-[10px] text-slate-400 ml-auto">(Not uploaded)</span>}
                      </label>
                    );
                  })}
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-navy mb-1">
                  Justification / Correction Reason (Required, min 5 chars):
                </label>
                <textarea
                  required
                  minLength={5}
                  value={correctionReason}
                  onChange={(e) => setCorrectionReason(e.target.value)}
                  placeholder="e.g. Income certificate is blurry and the annual income figure is not clearly readable. Please provide a high-resolution scan."
                  rows={3}
                  className="w-full p-2.5 border border-slate-300 rounded-xl text-xs focus:ring-2 focus:ring-teal outline-none"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsCorrectionOpen(false)}
                  className="px-4 py-2 text-xs font-bold text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex items-center gap-1.5 px-5 py-2 text-xs font-bold text-white bg-amber-600 hover:bg-amber-700 rounded-xl shadow disabled:opacity-50"
                >
                  {submitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>{submitting ? "Submitting..." : "Send Correction Request"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* MODAL 3: REQUIRE PHYSICAL VERIFICATION                             */}
      {/* ------------------------------------------------------------------ */}
      {isPhysicalOpen && (
        <div className="fixed inset-0 z-50 bg-navy/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full border border-slate-200 overflow-hidden animate-in fade-in zoom-in duration-150">
            <div className="bg-navy text-white p-5 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Calendar className="w-5 h-5 text-seafoam" />
                <h3 className="font-bold text-base">Schedule Physical Verification</h3>
              </div>
              <button onClick={() => setIsPhysicalOpen(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>

            <form onSubmit={handlePhysicalSubmit} className="p-6 space-y-3.5">
              <div className="grid sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-navy mb-1">Appointment Date:</label>
                  <input
                    type="date"
                    required
                    value={physicalDate}
                    onChange={(e) => setPhysicalDate(e.target.value)}
                    className="w-full p-2 border border-slate-300 rounded-xl text-xs focus:ring-2 focus:ring-teal outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-navy mb-1">Appointment Time:</label>
                  <select
                    value={physicalTime}
                    onChange={(e) => setPhysicalTime(e.target.value)}
                    className="w-full p-2 border border-slate-300 rounded-xl text-xs focus:ring-2 focus:ring-teal outline-none"
                  >
                    <option value="09:30 AM">09:30 AM</option>
                    <option value="10:30 AM">10:30 AM</option>
                    <option value="11:30 AM">11:30 AM</option>
                    <option value="02:00 PM">02:00 PM</option>
                    <option value="03:30 PM">03:30 PM</option>
                    <option value="04:30 PM">04:30 PM</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-navy mb-1">Office Venue / Room:</label>
                <input
                  type="text"
                  required
                  minLength={3}
                  value={physicalVenue}
                  onChange={(e) => setPhysicalVenue(e.target.value)}
                  placeholder="e.g. Dean Office, Administrative Block Room 102"
                  className="w-full p-2 border border-slate-300 rounded-xl text-xs focus:ring-2 focus:ring-teal outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-navy mb-1">Purpose:</label>
                <input
                  type="text"
                  value={physicalPurpose}
                  onChange={(e) => setPhysicalPurpose(e.target.value)}
                  placeholder="e.g. Verify original caste and income certificates"
                  className="w-full p-2 border border-slate-300 rounded-xl text-xs focus:ring-2 focus:ring-teal outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-navy mb-1">Candidate Instructions:</label>
                <textarea
                  value={physicalInstructions}
                  onChange={(e) => setPhysicalInstructions(e.target.value)}
                  rows={2}
                  className="w-full p-2 border border-slate-300 rounded-xl text-xs focus:ring-2 focus:ring-teal outline-none resize-none"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsPhysicalOpen(false)}
                  className="px-4 py-2 text-xs font-bold text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex items-center gap-1.5 px-5 py-2 text-xs font-bold text-white bg-teal hover:bg-teal-hover rounded-xl shadow disabled:opacity-50"
                >
                  {submitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>{submitting ? "Scheduling..." : "Schedule Appointment"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* MODAL 4: COMPLETE PHYSICAL VERIFICATION                            */}
      {/* ------------------------------------------------------------------ */}
      {isCompletePhysicalOpen && (
        <div className="fixed inset-0 z-50 bg-navy/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full border border-slate-200 overflow-hidden animate-in fade-in zoom-in duration-150">
            <div className="bg-navy text-white p-5 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                <h3 className="font-bold text-base">Record Physical Verification Outcome</h3>
              </div>
              <button onClick={() => setIsCompletePhysicalOpen(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>

            <form onSubmit={handleCompletePhysicalSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-bold text-navy mb-2">Inspection Outcome Result:</label>
                <div className="grid grid-cols-2 gap-3">
                  <label className={`p-3 rounded-xl border text-xs font-bold flex items-center gap-2 cursor-pointer transition-colors ${
                    completeResult === 'VERIFIED'
                      ? 'bg-emerald-50 text-emerald-900 border-emerald-400'
                      : 'bg-white text-slate-700 border-slate-200'
                  }`}>
                    <input
                      type="radio"
                      name="result"
                      value="VERIFIED"
                      checked={completeResult === 'VERIFIED'}
                      onChange={() => setCompleteResult('VERIFIED')}
                      className="text-emerald-600 focus:ring-emerald-500"
                    />
                    <span>Verified (Passed)</span>
                  </label>

                  <label className={`p-3 rounded-xl border text-xs font-bold flex items-center gap-2 cursor-pointer transition-colors ${
                    completeResult === 'NOT_VERIFIED'
                      ? 'bg-amber-50 text-amber-900 border-amber-400'
                      : 'bg-white text-slate-700 border-slate-200'
                  }`}>
                    <input
                      type="radio"
                      name="result"
                      value="NOT_VERIFIED"
                      checked={completeResult === 'NOT_VERIFIED'}
                      onChange={() => setCompleteResult('NOT_VERIFIED')}
                      className="text-amber-600 focus:ring-amber-500"
                    />
                    <span>Not Verified (Issues)</span>
                  </label>
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-navy mb-1">
                  Inspection Remarks (Required, min 3 chars):
                </label>
                <textarea
                  required
                  minLength={3}
                  value={completeRemarks}
                  onChange={(e) => setCompleteRemarks(e.target.value)}
                  placeholder="e.g. Original income certificate and domicile certificate verified physically in the dean office."
                  rows={3}
                  className="w-full p-2.5 border border-slate-300 rounded-xl text-xs focus:ring-2 focus:ring-teal outline-none"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsCompletePhysicalOpen(false)}
                  className="px-4 py-2 text-xs font-bold text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex items-center gap-1.5 px-5 py-2 text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-700 rounded-xl shadow disabled:opacity-50"
                >
                  {submitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>{submitting ? "Recording..." : "Save Outcome"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* MODAL 5: REJECT APPLICATION CONFIRMATION                           */}
      {/* ------------------------------------------------------------------ */}
      {isRejectOpen && (
        <div className="fixed inset-0 z-50 bg-navy/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full border border-slate-200 overflow-hidden animate-in fade-in zoom-in duration-150">
            <div className="bg-rose-900 text-white p-5 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <XCircle className="w-5 h-5 text-rose-300" />
                <h3 className="font-bold text-base">Reject Scholarship Application</h3>
              </div>
              <button onClick={() => setIsRejectOpen(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>

            <form onSubmit={handleRejectSubmit} className="p-6 space-y-4">
              <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-900">
                <strong>Warning:</strong> Rejecting an application is a definitive decision. The student will be notified with the provided reason.
              </div>

              <div>
                <label className="block text-xs font-bold text-navy mb-1">
                  Rejection Reason (Required, min 5 chars):
                </label>
                <textarea
                  required
                  minLength={5}
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  placeholder="e.g. Document was confirmed to be invalid upon administrative verification."
                  rows={3}
                  className="w-full p-2.5 border border-slate-300 rounded-xl text-xs focus:ring-2 focus:ring-rose-500 outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Internal Administrative Notes (Optional):
                </label>
                <textarea
                  value={rejectNotes}
                  onChange={(e) => setRejectNotes(e.target.value)}
                  placeholder="Internal audit notes..."
                  rows={2}
                  className="w-full p-2.5 border border-slate-300 rounded-xl text-xs focus:ring-2 focus:ring-rose-500 outline-none resize-none"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsRejectOpen(false)}
                  className="px-4 py-2 text-xs font-bold text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex items-center gap-1.5 px-5 py-2 text-xs font-bold text-white bg-rose-600 hover:bg-rose-700 rounded-xl shadow disabled:opacity-50"
                >
                  {submitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>{submitting ? "Rejecting..." : "Confirm Rejection"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

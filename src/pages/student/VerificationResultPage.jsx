import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useApplications } from '../../context/ApplicationContext';
import StatusBadge from '../../components/StatusBadge';
import { 
  ShieldCheck, 
  FileText, 
  CheckCircle2, 
  AlertTriangle, 
  Info, 
  ArrowLeft,
  Calendar,
  Sparkles,
  HelpCircle
} from 'lucide-react';

export default function VerificationResultPage() {
  const { currentUser } = useAuth();
  const { applications, refreshState } = useApplications();
  const [app, setApp] = useState(null);

  useEffect(() => {
    refreshState();
  }, []);

  useEffect(() => {
    if (applications.length > 0 && currentUser) {
      const found = applications.find(a => a.studentId === currentUser.id) || applications[0];
      setApp(found);
    }
  }, [applications, currentUser]);

  if (!app) return <div className="p-8 text-center text-slate-500">Loading result...</div>;

  const docKeys = [
    { key: 'govId', title: 'Government ID / Aadhaar' },
    { key: 'marksheet', title: '10th/12th Marksheet' },
    { key: 'incomeCert', title: 'Income Certificate' },
    { key: 'domicileCert', title: 'Domicile Certificate' }
  ];

  return (
    <div className="space-y-6">
      {/* Header & Overall Status */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
          <div>
            <span className="text-xs font-semibold uppercase tracking-wider text-teal">Verification Audit Report</span>
            <h2 className="text-2xl font-bold text-navy mt-0.5">AI Assistive Verification Result</h2>
            <p className="text-xs text-slate-500">Application ID: {app.id} | Candidate: {app.studentName}</p>
          </div>
          <StatusBadge status={app.overallStatus} confidence={app.aiConfidence} />
        </div>

        {/* Prototype Confidence Notice */}
        <div className="p-3 bg-seafoam-light border border-seafoam rounded-xl text-xs text-navy flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-teal flex-shrink-0" />
            <span>
              <strong>Verification Confidence: {app.aiConfidence}%</strong> — Prototype-generated assistive verification indicator.
            </span>
          </div>
          <span className="text-[11px] text-slate-500 hidden sm:inline">Rule-Based OCR & Cross-Check Matrix</span>
        </div>
      </div>

      {/* Flagged Alert if Needs Review */}
      {app.overallStatus === 'NEEDS_REVIEW' && (
        <div className="bg-amber-50 border-2 border-amber-300 rounded-2xl p-6 shadow-sm">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-6 h-6 text-amber-600 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="text-base font-bold text-amber-900">Flagged Issue: Name Mismatch Detected</h3>
              <p className="text-xs text-amber-800 mt-1">
                The AI verification engine detected a minor name variation across uploaded documents:
              </p>
              <ul className="list-disc list-inside mt-2 text-xs text-amber-900 space-y-1">
                <li>Government ID: <strong>Amit Patil</strong></li>
                <li>10th/12th Marksheet: <strong>Amit Kumar Patil</strong></li>
                <li>Income Certificate: <strong>Amit P. Patil</strong></li>
              </ul>
              <p className="text-xs text-amber-800 mt-2 font-medium">
                Administrative review is required to verify identity consistency. An administrator may schedule a physical verification meeting.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Cross-Document Consistency Matrix */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
        <h3 className="text-lg font-bold text-navy mb-4 flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-teal" />
          Cross-Document Consistency Checks
        </h3>

        <div className="space-y-3">
          {app.crossDocumentChecks && app.crossDocumentChecks.map((item, idx) => (
            <div key={idx} className="p-4 rounded-xl border border-slate-100 bg-slate-50 flex items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                {item.status === 'PASSED' ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
                ) : item.status === 'WARNING' ? (
                  <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                ) : (
                  <Info className="w-5 h-5 text-sky-600 flex-shrink-0 mt-0.5" />
                )}
                <div>
                  <h4 className="font-semibold text-slate-800 text-sm">{item.check}</h4>
                  <p className="text-xs text-slate-500 mt-0.5">{item.details}</p>
                </div>
              </div>
              <span className={`px-2.5 py-1 rounded text-[11px] font-bold uppercase tracking-wider ${
                item.status === 'PASSED' ? 'bg-emerald-100 text-emerald-800' :
                item.status === 'WARNING' ? 'bg-amber-100 text-amber-900' : 'bg-slate-200 text-slate-700'
              }`}>
                {item.status}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Extracted Data Fields per 4 Documents */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
        <h3 className="text-lg font-bold text-navy mb-4">4 Core Document Extractions</h3>

        <div className="grid sm:grid-cols-2 gap-4">
          {docKeys.map(({ key, title }) => {
            const doc = app.documents[key];
            return (
              <div key={key} className="p-4 rounded-xl border border-slate-200 bg-slate-50">
                <div className="flex items-center justify-between pb-2 mb-3 border-b border-slate-200">
                  <span className="font-semibold text-sm text-navy">{title}</span>
                  <StatusBadge status={doc ? doc.status : 'PENDING'} />
                </div>

                {doc && doc.extractedData ? (
                  <div className="space-y-1.5 text-xs">
                    {Object.entries(doc.extractedData).map(([field, val]) => (
                      <div key={field} className="flex justify-between">
                        <span className="text-slate-500 capitalize">{field.replace(/([A-Z])/g, ' $1')}:</span>
                        <span className="font-medium text-slate-800">{val}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-400">Document data unavailable</p>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Administrative Disclaimer Footer */}
      <div className="bg-slate-100 rounded-xl p-4 text-xs text-slate-600 flex items-start gap-2 border border-slate-200">
        <HelpCircle className="w-4 h-4 text-teal flex-shrink-0 mt-0.5" />
        <div>
          <strong>Assistive Verification Scope:</strong> The AI engine performs preliminary OCR extraction, field comparison, and consistency checks. The final decision regarding scholarship approval or physical verification scheduling remains under the sole authority of the administrator.
        </div>
      </div>
    </div>
  );
}

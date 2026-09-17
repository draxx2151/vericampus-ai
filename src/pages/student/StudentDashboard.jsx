import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useApplications } from '../../context/ApplicationContext';
import StatusBadge from '../../components/StatusBadge';
import { 
  FileCheck, 
  UploadCloud, 
  ShieldCheck, 
  Calendar, 
  Sparkles, 
  AlertCircle, 
  Clock, 
  ChevronRight,
  MapPin,
  FileText
} from 'lucide-react';

export default function StudentDashboard() {
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

  if (!app) {
    return (
      <div className="p-8 text-center text-slate-500">
        Loading student application profile...
      </div>
    );
  }

  const docKeys = [
    { key: 'govId', title: 'Government ID / Aadhaar' },
    { key: 'marksheet', title: '10th/12th Marksheet' },
    { key: 'incomeCert', title: 'Income Certificate' },
    { key: 'domicileCert', title: 'Domicile Certificate' }
  ];

  return (
    <div className="space-y-6">
      {/* Welcome Banner */}
      <div className="bg-navy text-white rounded-2xl p-6 sm:p-8 shadow-md relative overflow-hidden">
        <div className="relative z-10">
          <div className="flex flex-wrap items-center justify-between gap-4 mb-3">
            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-seafoam">Student Portal</span>
              <h2 className="text-2xl sm:text-3xl font-bold mt-1">Hello, {app.studentName} 👋</h2>
            </div>
            <StatusBadge status={app.overallStatus} confidence={app.aiConfidence} />
          </div>

          <div className="grid sm:grid-cols-3 gap-4 mt-6 pt-4 border-t border-slate-700/60 text-xs">
            <div>
              <span className="text-slate-400 block">Application ID</span>
              <span className="font-mono font-bold text-white text-sm">{app.id}</span>
            </div>
            <div>
              <span className="text-slate-400 block">Scholarship Program</span>
              <span className="font-semibold text-white text-sm">{app.scholarship}</span>
            </div>
            <div>
              <span className="text-slate-400 block">Verification Status</span>
              <span className="font-semibold text-seafoam text-sm">
                {app.overallStatus === 'VERIFIED' ? 'AI Verification Completed' : 
                 app.overallStatus === 'NEEDS_REVIEW' ? 'Requires Admin Review' : 'Processing Documents'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* APPOINTMENT CARD (IF SCHEDULED BY ADMIN) */}
      {app.appointment && (
        <div className="bg-teal-50 border-2 border-teal rounded-2xl p-6 shadow-sm">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-teal text-white rounded-xl">
                <Calendar className="w-6 h-6" />
              </div>
              <div>
                <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-teal text-white rounded">
                  Action Required
                </span>
                <h3 className="text-lg font-bold text-navy mt-1">Physical Document Verification Appointment</h3>
              </div>
            </div>
            <span className="text-xs font-semibold bg-emerald-100 text-emerald-800 px-3 py-1 rounded-full border border-emerald-300">
              Status: {app.appointment.status}
            </span>
          </div>

          <div className="grid sm:grid-cols-3 gap-4 mt-4 pt-4 border-t border-teal/20 text-xs text-slate-700">
            <div>
              <span className="text-slate-500 block font-medium">Date & Time</span>
              <span className="font-bold text-navy text-sm">📅 {app.appointment.date} at {app.appointment.time}</span>
            </div>
            <div>
              <span className="text-slate-500 block font-medium">Venue Location</span>
              <span className="font-semibold text-slate-800 text-sm flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5 text-teal" /> {app.appointment.venue}
              </span>
            </div>
            <div>
              <span className="text-slate-500 block font-medium">Scheduled By</span>
              <span className="font-semibold text-slate-800 text-sm">{app.appointment.scheduledBy}</span>
            </div>
          </div>

          <div className="mt-4 p-3 bg-white rounded-xl border border-teal/30 text-xs text-slate-600">
            <strong>Purpose:</strong> {app.appointment.purpose}. Please bring your original physical documents for verification.
          </div>
        </div>
      )}

      {/* Flagged Issue Alert (If Needs Review) */}
      {app.overallStatus === 'NEEDS_REVIEW' && !app.appointment && (
        <div className="bg-amber-50 border border-amber-300 rounded-xl p-4 text-xs text-amber-900 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
          <div>
            <span className="font-bold text-sm block">AI Assisted Audit Alert: Name Variation Detected</span>
            <span>Your application is currently flagged for administrative review due to a name inconsistency across documents. An admin officer will review or schedule a physical verification meeting if needed.</span>
          </div>
        </div>
      )}

      {/* Progress & 4 Document Cards Overview */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-lg font-bold text-navy">Scholarship Verification Documents</h3>
            <p className="text-xs text-slate-500">4 required core documents for eligibility verification</p>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-xs font-semibold text-slate-700">
              {app.documentsUploadedCount} / 4 Documents Uploaded
            </span>
            <div className="w-32 bg-slate-100 h-2.5 rounded-full overflow-hidden">
              <div
                className="bg-teal h-full transition-all"
                style={{ width: `${(app.documentsUploadedCount / 4) * 100}%` }}
              />
            </div>
          </div>
        </div>

        {/* 4 Document Status Grid */}
        <div className="grid sm:grid-cols-2 md:grid-cols-4 gap-4">
          {docKeys.map(({ key, title }) => {
            const doc = app.documents[key];
            return (
              <div key={key} className="p-4 rounded-xl border border-slate-200 bg-slate-50 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold text-navy">{title}</span>
                    {doc ? (
                      <FileCheck className="w-4 h-4 text-emerald-600" />
                    ) : (
                      <Clock className="w-4 h-4 text-slate-400" />
                    )}
                  </div>
                  <p className="text-xs text-slate-500 truncate">
                    {doc ? doc.file : "Not uploaded yet"}
                  </p>
                </div>
                <div className="mt-3 pt-2 border-t border-slate-200 flex items-center justify-between">
                  <span className="text-[11px] font-medium text-slate-400">Status</span>
                  <StatusBadge status={doc ? doc.status : 'PENDING'} />
                </div>
              </div>
            );
          })}
        </div>

        {/* Quick Action Navigation */}
        <div className="mt-6 pt-6 border-t border-slate-100 flex flex-wrap items-center justify-between gap-4">
          <Link
            to="/student/documents"
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-teal hover:bg-teal-hover text-white font-bold text-xs shadow-sm transition-colors"
          >
            <UploadCloud className="w-4 h-4" />
            <span>Upload / Manage Documents</span>
          </Link>

          <Link
            to="/student/verification"
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-navy hover:bg-navy-light text-white font-bold text-xs shadow-sm transition-colors"
          >
            <ShieldCheck className="w-4 h-4 text-seafoam" />
            <span>View AI Verification Results</span>
            <ChevronRight className="w-4 h-4 text-slate-300" />
          </Link>
        </div>
      </div>
    </div>
  );
}

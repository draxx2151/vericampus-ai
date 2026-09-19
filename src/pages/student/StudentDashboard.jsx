import React, { useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useApplications } from '../../context/ApplicationContext';
import StatusBadge from '../../components/StatusBadge';
import { 
  FileCheck, 
  UploadCloud, 
  ShieldCheck, 
  Calendar, 
  AlertCircle, 
  Clock, 
  ChevronRight,
  MapPin,
  FilePlus,
  ArrowRight
} from 'lucide-react';

export default function StudentDashboard() {
  const { currentUser } = useAuth();
  const { myApplication, refreshState } = useApplications();
  const navigate = useNavigate();

  useEffect(() => {
    refreshState();
  }, []);

  const studentName = currentUser?.full_name || currentUser?.name || 'Student';

  const docTypes = [
    { type: 'GOVERNMENT_ID', title: 'Government ID / Aadhaar' },
    { type: 'MARKSHEET', title: '10th / 12th Marksheet' },
    { type: 'INCOME_CERTIFICATE', title: 'Income Certificate' },
    { type: 'DOMICILE_CERTIFICATE', title: 'Domicile Certificate' }
  ];

  const getUploadedDoc = (typeKey) => {
    if (!myApplication || !myApplication.documents) return null;
    return myApplication.documents.find(
      d => d.document_type === typeKey || d.document_type === typeKey.toLowerCase()
    );
  };

  const uploadedCount = myApplication ? (myApplication.documents_uploaded_count || (myApplication.documents ? myApplication.documents.length : 0)) : 0;

  return (
    <div className="space-y-6">
      {/* Welcome Banner */}
      <div className="bg-navy text-white rounded-2xl p-6 sm:p-8 shadow-md relative overflow-hidden">
        <div className="relative z-10">
          <div className="flex flex-wrap items-center justify-between gap-4 mb-3">
            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-seafoam">Student Portal</span>
              <h2 className="text-2xl sm:text-3xl font-bold mt-1">Hello, {studentName} 👋</h2>
            </div>
            {myApplication ? (
              <StatusBadge status={myApplication.status} />
            ) : (
              <span className="px-3 py-1 rounded-full text-xs font-bold bg-slate-700 text-slate-300 border border-slate-600">
                Status: Not Started
              </span>
            )}
          </div>

          <div className="grid sm:grid-cols-3 gap-4 mt-6 pt-4 border-t border-slate-700/60 text-xs">
            <div>
              <span className="text-slate-400 block">Application Number</span>
              <span className="font-mono font-bold text-white text-sm">
                {myApplication ? myApplication.application_number : 'No application started yet'}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block">Scholarship Program</span>
              <span className="font-semibold text-white text-sm">
                {myApplication ? myApplication.scholarship_name : 'None selected'}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block">Verification Status</span>
              <span className="font-semibold text-seafoam text-sm">
                {myApplication ? (
                  myApplication.status === 'VERIFIED' ? 'AI Verification Completed' : 
                  myApplication.status === 'NEEDS_REVIEW' ? 'Requires Admin Review' : 
                  myApplication.status === 'DRAFT' ? 'Draft Application (Upload Documents)' : 'Processing Documents'
                ) : 'Not started'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* EMPTY DASHBOARD STATE FOR NEW STUDENT */}
      {!myApplication ? (
        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-sm text-center">
            <div className="w-16 h-16 bg-teal-50 text-teal rounded-2xl flex items-center justify-center mx-auto mb-4 border border-teal/20">
              <FilePlus className="w-8 h-8" />
            </div>
            <h3 className="text-xl font-bold text-navy mb-2">Scholarship Application</h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto mb-6">
              You haven't started your scholarship application yet. Select an official MahaDBT scholarship program to initiate your application.
            </p>
            <Link
              to="/student/select-scholarship"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-teal hover:bg-teal-hover text-white font-bold text-xs shadow-md transition-colors"
            >
              <UploadCloud className="w-4 h-4" />
              <span>Start Scholarship Application</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>

          {/* Empty Document Overview Grid */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-lg font-bold text-navy">Required Core Documents</h3>
                <p className="text-xs text-slate-500">4 required core documents for eligibility verification</p>
              </div>
              <span className="text-xs font-semibold text-slate-400 bg-slate-100 px-3 py-1 rounded-full border border-slate-200">
                0 / 4 Uploaded
              </span>
            </div>

            <div className="grid sm:grid-cols-2 md:grid-cols-4 gap-4">
              {docTypes.map(({ type, title }) => (
                <div key={type} className="p-4 rounded-xl border border-slate-200 bg-slate-50 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-bold text-navy">{title}</span>
                      <Clock className="w-4 h-4 text-slate-400" />
                    </div>
                    <p className="text-xs text-slate-400 font-medium">Not Uploaded</p>
                  </div>
                  <div className="mt-3 pt-2 border-t border-slate-200 flex items-center justify-between">
                    <span className="text-[11px] font-medium text-slate-400">Status</span>
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider bg-slate-200 px-2 py-0.5 rounded">
                      Not Uploaded
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : (
        /* ACTIVE APPLICATION DASHBOARD */
        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-lg font-bold text-navy">Scholarship Verification Documents</h3>
                <p className="text-xs text-slate-500">4 required core documents for eligibility verification</p>
              </div>

              <div className="flex items-center gap-3">
                <span className="text-xs font-semibold text-slate-700">
                  {uploadedCount} / 4 Documents Uploaded
                </span>
                <div className="w-32 bg-slate-100 h-2.5 rounded-full overflow-hidden">
                  <div
                    className="bg-teal h-full transition-all"
                    style={{ width: `${(uploadedCount / 4) * 100}%` }}
                  />
                </div>
              </div>
            </div>

            {/* 4 Document Status Grid */}
            <div className="grid sm:grid-cols-2 md:grid-cols-4 gap-4">
              {docTypes.map(({ type, title }) => {
                const doc = getUploadedDoc(type);
                return (
                  <div key={type} className="p-4 rounded-xl border border-slate-200 bg-slate-50 flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-bold text-navy">{title}</span>
                        {doc ? (
                          <FileCheck className="w-4 h-4 text-emerald-600" />
                        ) : (
                          <Clock className="w-4 h-4 text-slate-400" />
                        )}
                      </div>
                      <p className="text-xs font-medium text-slate-600 truncate">
                        {doc ? doc.original_filename : "Not Uploaded"}
                      </p>
                    </div>
                    <div className="mt-3 pt-2 border-t border-slate-200 flex items-center justify-between">
                      <span className="text-[11px] font-medium text-slate-400">Status</span>
                      {doc ? (
                        <StatusBadge status={doc.upload_status || 'UPLOADED'} />
                      ) : (
                        <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider bg-slate-200 px-2 py-0.5 rounded">
                          Not Uploaded
                        </span>
                      )}
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
                <span>View Verification Details</span>
                <ChevronRight className="w-4 h-4 text-slate-300" />
              </Link>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

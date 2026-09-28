import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useApplications } from '../../context/ApplicationContext';
import { api } from '../../services/api';
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
  ArrowRight,
  CheckCircle2
} from 'lucide-react';

export default function StudentDashboard() {
  const { currentUser, token } = useAuth();
  const { myApplication, refreshState } = useApplications();
  const navigate = useNavigate();

  const [appointment, setAppointment] = useState(null);
  const [loadingAppointment, setLoadingAppointment] = useState(false);

  useEffect(() => {
    refreshState();
  }, []);

  useEffect(() => {
    const loadAppointment = async () => {
      const activeToken = token || localStorage.getItem('vericampus_token');
      if (!activeToken) return;
      try {
        const appt = await api.getMyPhysicalVerificationAppointment(activeToken);
        setAppointment(appt);
      } catch (err) {
        setAppointment(null);
      }
    };
    loadAppointment();
  }, [token, myApplication?.status]);

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
  const isCorrectionPending = myApplication?.correction_request?.status === 'PENDING';

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
          {/* Active Correction Request Banner */}
          {isCorrectionPending && (
            <div className="bg-amber-50 border-2 border-amber-300 rounded-2xl p-6 shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="flex items-start gap-3.5 max-w-2xl">
                  <div className="p-2.5 bg-amber-100 text-amber-800 rounded-xl mt-0.5 flex-shrink-0">
                    <AlertCircle className="w-6 h-6 text-amber-700" />
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-bold uppercase tracking-wider bg-amber-200 text-amber-900 px-2 py-0.5 rounded border border-amber-300">
                        Action Required
                      </span>
                      <h3 className="text-base font-bold text-amber-950">
                        Document Correction Requested by Administrator
                      </h3>
                    </div>
                    <p className="text-xs text-amber-900 leading-relaxed">
                      <strong>Reviewing Officer's Instructions:</strong> "{myApplication.correction_request.reason}"
                    </p>
                    <div className="flex flex-wrap items-center gap-2 pt-1">
                      <span className="text-xs font-semibold text-amber-950">Flagged Document(s):</span>
                      {myApplication.correction_request.document_types?.map((typeKey) => {
                        const title = docTypes.find(d => d.type === typeKey)?.title || typeKey;
                        const isResolved = myApplication.correction_request.resolved_documents?.includes(typeKey);
                        return (
                          <span
                            key={typeKey}
                            className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${
                              isResolved
                                ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                                : 'bg-amber-200 text-amber-950 border-amber-400 font-bold'
                            }`}
                          >
                            {title} {isResolved ? '✓ (Replaced)' : '• Action Required'}
                          </span>
                        );
                      })}
                    </div>
                  </div>
                </div>

                <Link
                  to="/student/documents"
                  className="px-5 py-2.5 bg-amber-600 hover:bg-amber-700 text-white font-bold text-xs rounded-xl transition-colors shadow-sm flex items-center gap-2 whitespace-nowrap"
                >
                  <UploadCloud className="w-4 h-4" />
                  <span>Replace Flagged Documents</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
            </div>
          )}

          {/* Physical Verification Section */}
          {(appointment || myApplication.status === 'PHYSICAL_VERIFICATION_REQUIRED' || myApplication.status === 'PHYSICAL_VERIFICATION_COMPLETED') && (
            <div className={`rounded-2xl p-6 border-2 shadow-sm ${
              appointment?.status === 'COMPLETED' || myApplication.status === 'PHYSICAL_VERIFICATION_COMPLETED'
                ? 'bg-emerald-50 border-emerald-300'
                : 'bg-teal-50 border-teal'
            }`}>
              <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-teal/20">
                <div className="flex items-center gap-3">
                  <div className={`p-2.5 rounded-xl ${
                    appointment?.status === 'COMPLETED' || myApplication.status === 'PHYSICAL_VERIFICATION_COMPLETED'
                      ? 'bg-emerald-100 text-emerald-800'
                      : 'bg-teal text-white'
                  }`}>
                    <Calendar className="w-6 h-6" />
                  </div>
                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-teal">
                      College Administration Notice
                    </span>
                    <h3 className="text-lg font-bold text-navy">
                      Physical Document Verification
                    </h3>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {appointment ? (
                    <StatusBadge status={appointment.status} />
                  ) : (
                    <StatusBadge status="PHYSICAL_VERIFICATION_REQUIRED" />
                  )}
                  {myApplication.status === 'PHYSICAL_VERIFICATION_COMPLETED' && (
                    <StatusBadge status="PHYSICAL_VERIFICATION_COMPLETED" />
                  )}
                </div>
              </div>

              {appointment ? (
                <div className="grid sm:grid-cols-3 gap-4 mt-4 text-xs">
                  <div className="bg-white p-3.5 rounded-xl border border-teal/20">
                    <span className="text-slate-500 block mb-1">Scheduled Date & Time</span>
                    <span className="font-bold text-navy text-sm flex items-center gap-1.5">
                      <Clock className="w-4 h-4 text-teal" />
                      {appointment.scheduled_date || 'Date TBD'} at {appointment.scheduled_time || 'Time TBD'}
                    </span>
                  </div>

                  <div className="bg-white p-3.5 rounded-xl border border-teal/20">
                    <span className="text-slate-500 block mb-1">Venue / Location</span>
                    <span className="font-semibold text-slate-800 text-xs flex items-center gap-1.5">
                      <MapPin className="w-4 h-4 text-teal flex-shrink-0" />
                      <span className="truncate">{appointment.venue || 'College Administrative Office'}</span>
                    </span>
                  </div>

                  <div className="bg-white p-3.5 rounded-xl border border-teal/20">
                    <span className="text-slate-500 block mb-1">Purpose & Instructions</span>
                    <span className="text-slate-800 text-xs line-clamp-2">
                      {appointment.instructions || appointment.notes || 'Original certificates verification'}
                    </span>
                  </div>
                </div>
              ) : (
                <div className="mt-4 p-3.5 bg-white rounded-xl border border-teal/20 text-xs text-slate-700">
                  Physical verification is required by college administration. Your verification officer is scheduling the appointment date and venue. Please check back shortly.
                </div>
              )}

              <div className="mt-4 pt-4 border-t border-teal/20 flex flex-wrap items-center justify-between gap-3 text-xs">
                <p className="text-slate-600">
                  {appointment?.status === 'COMPLETED' || myApplication.status === 'PHYSICAL_VERIFICATION_COMPLETED'
                    ? "In-person inspection completed successfully. Your application is under final administrative review."
                    : "Note: In-person appointments are conducted strictly by college verification officers. Please carry your original documents."}
                </p>
                <Link
                  to="/student/appointment"
                  className="text-teal font-bold hover:underline flex items-center gap-1"
                >
                  <span>View Full Appointment Details</span>
                  <ChevronRight className="w-4 h-4" />
                </Link>
              </div>
            </div>
          )}

          {/* Document Overview Grid */}
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
                const isFlaggedForCorrection = isCorrectionPending && myApplication?.correction_request?.document_types?.includes(type);
                const isCorrectionResolved = myApplication?.correction_request?.resolved_documents?.includes(type);

                return (
                  <div
                    key={type}
                    className={`p-4 rounded-xl border flex flex-col justify-between ${
                      isFlaggedForCorrection
                        ? 'border-amber-400 bg-amber-50/30'
                        : 'border-slate-200 bg-slate-50'
                    }`}
                  >
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
                      {isFlaggedForCorrection ? (
                        <span className="text-[10px] font-bold text-amber-900 uppercase tracking-wider bg-amber-200 border border-amber-300 px-2 py-0.5 rounded">
                          Correction Needed
                        </span>
                      ) : isCorrectionResolved ? (
                        <span className="text-[10px] font-bold text-emerald-800 uppercase tracking-wider bg-emerald-100 border border-emerald-300 px-2 py-0.5 rounded">
                          Replaced
                        </span>
                      ) : doc ? (
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

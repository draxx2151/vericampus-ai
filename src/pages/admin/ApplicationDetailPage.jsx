import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useApplications } from '../../context/ApplicationContext';
import { api } from '../../services/api';
import StatusBadge from '../../components/StatusBadge';
import MeetingSchedulerModal from '../../components/MeetingSchedulerModal';
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
  Clock
} from 'lucide-react';

export default function ApplicationDetailPage() {
  const { id } = useParams();
  const { applications, refreshState } = useApplications();
  const [app, setApp] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [actionSuccess, setActionSuccess] = useState('');

  useEffect(() => {
    refreshState();
  }, [id]);

  useEffect(() => {
    if (applications.length > 0) {
      const found = applications.find(a => a.id === id) || applications[0];
      setApp(found);
    }
  }, [applications, id]);

  if (!app) return <div className="p-8 text-center text-slate-500">Loading application detail...</div>;

  const handleStatusChange = async (newStatus) => {
    try {
      await api.updateApplicationStatus(app.id, newStatus);
      await refreshState();
      setActionSuccess(`Application status successfully updated to ${newStatus}`);
      setTimeout(() => setActionSuccess(''), 4000);
    } catch (err) {
      console.error(err);
    }
  };

  const handleScheduleMeetingSubmit = async (meetingData) => {
    try {
      await api.scheduleMeeting(app.id, meetingData);
      await refreshState();
      setActionSuccess('Physical verification meeting scheduled! Student dashboard & notifications updated.');
      setTimeout(() => setActionSuccess(''), 5000);
    } catch (err) {
      console.error(err);
    }
  };

  const docKeys = [
    { key: 'govId', title: 'Government ID / Aadhaar' },
    { key: 'marksheet', title: '10th/12th Marksheet' },
    { key: 'incomeCert', title: 'Income Certificate' },
    { key: 'domicileCert', title: 'Domicile Certificate' }
  ];

  return (
    <div className="space-y-6">
      {/* Back Button */}
      <Link to="/admin/applications" className="inline-flex items-center text-xs font-semibold text-teal hover:underline">
        <ArrowLeft className="w-4 h-4 mr-1" /> Back to All Applications
      </Link>

      {/* Action Notification Alert */}
      {actionSuccess && (
        <div className="bg-emerald-50 border border-emerald-300 rounded-xl p-4 text-xs font-bold text-emerald-900 flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 text-emerald-600" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {/* Header Profile Banner */}
      <div className="bg-navy text-white rounded-2xl p-6 shadow-md flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-xs bg-navy-light px-2.5 py-0.5 rounded text-seafoam font-bold border border-slate-700">
              {app.id}
            </span>
            <span className="text-xs text-slate-300">Applied: {app.appliedDate}</span>
          </div>
          <h2 className="text-2xl font-bold text-white">{app.studentName}</h2>
          <p className="text-xs text-slate-300 mt-0.5">{app.scholarship} | ID: {app.studentId}</p>
        </div>

        <div className="flex items-center gap-3">
          <StatusBadge status={app.overallStatus} confidence={app.aiConfidence} />
        </div>
      </div>

      {/* Flagged Alert Box (For Amit Patil / Needs Review) */}
      {app.overallStatus === 'NEEDS_REVIEW' && (
        <div className="bg-amber-50 border-2 border-amber-400 rounded-2xl p-6 shadow-sm">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-6 h-6 text-amber-600 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="text-base font-bold text-amber-950">AI Audit Alert: Name Variation Flagged</h3>
                <p className="text-xs text-amber-900 mt-1">
                  The AI OCR extraction engine detected inconsistencies in the student's name across submitted documents:
                </p>
                <div className="grid sm:grid-cols-3 gap-2 mt-3 text-xs bg-white/80 p-3 rounded-lg border border-amber-200">
                  <div>
                    <span className="text-slate-500 block">Govt Aadhaar:</span>
                    <strong className="text-slate-900 font-semibold">Amit Patil</strong>
                  </div>
                  <div>
                    <span className="text-slate-500 block">HSC Marksheet:</span>
                    <strong className="text-amber-900 font-bold">Amit Kumar Patil</strong>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Income Cert:</span>
                    <strong className="text-amber-900 font-bold">Amit P. Patil</strong>
                  </div>
                </div>
              </div>
            </div>

            <button
              onClick={() => setIsModalOpen(true)}
              className="flex items-center gap-1.5 px-4 py-2.5 bg-teal hover:bg-teal-hover text-white font-bold text-xs rounded-xl shadow-sm transition-colors flex-shrink-0"
            >
              <Calendar className="w-4 h-4" />
              <span>Schedule Physical Verification</span>
            </button>
          </div>
        </div>
      )}

      {/* Scheduled Appointment Card */}
      {app.appointment && (
        <div className="bg-teal-50 border border-teal rounded-2xl p-5 text-xs text-navy space-y-3">
          <div className="flex items-center justify-between">
            <span className="font-bold text-sm text-navy flex items-center gap-2">
              <Calendar className="w-4 h-4 text-teal" /> Scheduled Physical Verification Meeting
            </span>
            <span className="font-bold bg-emerald-100 text-emerald-800 px-2.5 py-0.5 rounded">
              {app.appointment.status}
            </span>
          </div>
          <div className="grid sm:grid-cols-3 gap-2 pt-2 border-t border-teal/20 text-slate-700">
            <div><strong>Date & Time:</strong> {app.appointment.date} at {app.appointment.time}</div>
            <div><strong>Location:</strong> {app.appointment.venue}</div>
            <div><strong>Scheduled By:</strong> {app.appointment.scheduledBy}</div>
          </div>
        </div>
      )}

      {/* Cross-Document Checks Matrix */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
        <h3 className="text-lg font-bold text-navy mb-4 flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-teal" />
          AI Assistive Cross-Document Check Findings
        </h3>

        <div className="space-y-3">
          {app.crossDocumentChecks && app.crossDocumentChecks.map((item, idx) => (
            <div key={idx} className="p-4 rounded-xl border border-slate-100 bg-slate-50 flex items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                {item.status === 'PASSED' ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
                ) : (
                  <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                )}
                <div>
                  <h4 className="font-semibold text-slate-800 text-sm">{item.check}</h4>
                  <p className="text-xs text-slate-500 mt-0.5">{item.details}</p>
                </div>
              </div>
              <span className={`px-2.5 py-1 rounded text-[11px] font-bold ${
                item.status === 'PASSED' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-900'
              }`}>
                {item.status}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* 4 Core Document OCR Extractions */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
        <h3 className="text-lg font-bold text-navy mb-4">OCR Extracted Data Fields (4 Documents)</h3>

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
                    <div className="text-slate-400 text-[11px] mb-1">File: {doc.file}</div>
                    {Object.entries(doc.extractedData).map(([field, val]) => (
                      <div key={field} className="flex justify-between">
                        <span className="text-slate-500 capitalize">{field.replace(/([A-Z])/g, ' $1')}:</span>
                        <span className="font-medium text-slate-900">{val}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-400">Not uploaded</p>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Admin Final Decision Control Section */}
      <div className="bg-white rounded-2xl p-6 border-2 border-navy shadow-md">
        <div className="mb-4">
          <span className="text-xs font-bold text-teal uppercase tracking-wider">Human-in-the-Loop Authority</span>
          <h3 className="text-lg font-bold text-navy">Administrative Final Review & Decision</h3>
          <p className="text-xs text-slate-500 mt-0.5">
            The AI provides preliminary extractions and flags. As an administrator, select the final status decision:
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => handleStatusChange('VERIFIED')}
            className="flex items-center gap-1.5 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl shadow transition-colors"
          >
            <Check className="w-4 h-4" />
            <span>Approve Application</span>
          </button>

          <button
            onClick={() => handleStatusChange('NEEDS_REVIEW')}
            className="flex items-center gap-1.5 px-4 py-2.5 bg-amber-600 hover:bg-amber-700 text-white font-bold text-xs rounded-xl shadow transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
            <span>Mark Needs Review</span>
          </button>

          <button
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-1.5 px-4 py-2.5 bg-teal hover:bg-teal-hover text-white font-bold text-xs rounded-xl shadow transition-colors"
          >
            <Calendar className="w-4 h-4" />
            <span>Schedule Physical Meeting</span>
          </button>

          <button
            onClick={() => handleStatusChange('REJECTED')}
            className="flex items-center gap-1.5 px-4 py-2.5 bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs rounded-xl shadow transition-colors"
          >
            <XCircle className="w-4 h-4" />
            <span>Reject Application</span>
          </button>
        </div>
      </div>

      {/* Meeting Scheduler Modal */}
      <MeetingSchedulerModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSchedule={handleScheduleMeetingSubmit}
        studentName={app.studentName}
        applicationId={app.id}
      />
    </div>
  );
}

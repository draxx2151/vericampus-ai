import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useApplications } from '../../context/ApplicationContext';
import { api } from '../../services/api';
import StatusBadge from '../../components/StatusBadge';
import { 
  Calendar, 
  Clock, 
  MapPin, 
  CheckCircle2, 
  AlertCircle, 
  FileText, 
  Loader2, 
  ArrowLeft,
  Info
} from 'lucide-react';

export default function StudentAppointmentPage() {
  const { token } = useAuth();
  const { myApplication, refreshState } = useApplications();
  const [appointment, setAppointment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    refreshState();
  }, []);

  useEffect(() => {
    const fetchAppointment = async () => {
      const activeToken = token || localStorage.getItem('vericampus_token');
      if (!activeToken) {
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);
      try {
        const appt = await api.getMyPhysicalVerificationAppointment(activeToken);
        setAppointment(appt);
      } catch (err) {
        // If 404, appt remains null
        setAppointment(null);
      } finally {
        setLoading(false);
      }
    };

    fetchAppointment();
  }, [token, myApplication?.status]);

  if (loading) {
    return (
      <div className="p-12 text-center text-slate-500 flex flex-col items-center justify-center gap-3">
        <Loader2 className="w-8 h-8 text-teal animate-spin" />
        <span className="text-xs font-semibold">Loading physical verification status...</span>
      </div>
    );
  }

  const isPhysicalRequired = myApplication?.status === 'PHYSICAL_VERIFICATION_REQUIRED';
  const isPhysicalCompleted = myApplication?.status === 'PHYSICAL_VERIFICATION_COMPLETED' || appointment?.status === 'COMPLETED';

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
          <h2 className="text-xl font-bold text-navy flex items-center gap-2">
            <Calendar className="w-6 h-6 text-teal" />
            Physical Verification Appointment
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Official in-person document verification schedule and instructions
          </p>
        </div>

        {appointment && (
          <div className="flex items-center gap-2">
            <StatusBadge status={appointment.status} />
            {isPhysicalCompleted && (
              <StatusBadge status="PHYSICAL_VERIFICATION_COMPLETED" />
            )}
          </div>
        )}
      </div>

      {/* Appointment Card */}
      {appointment ? (
        <div className={`border-2 rounded-2xl p-6 sm:p-8 shadow-sm space-y-6 ${
          isPhysicalCompleted ? 'bg-emerald-50 border-emerald-300' : 'bg-teal-50 border-teal'
        }`}>
          <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-teal/20">
            <div>
              <span className={`px-2.5 py-1 rounded text-[10px] font-bold uppercase tracking-wider ${
                isPhysicalCompleted ? 'bg-emerald-600 text-white' : 'bg-teal text-white'
              }`}>
                {isPhysicalCompleted ? 'Verification Completed' : 'Appointment Confirmed'}
              </span>
              <h3 className="text-2xl font-bold text-navy mt-2">
                In-Person Document Inspection
              </h3>
              <p className="text-xs text-slate-600 mt-0.5">
                Application: <span className="font-mono font-bold text-navy">{appointment.application_number || myApplication?.application_number}</span>
              </p>
            </div>
            <div className="text-right">
              <span className="text-xs text-slate-500 block mb-1">Current Appointment Status</span>
              <StatusBadge status={appointment.status} />
            </div>
          </div>

          {/* Schedule & Venue Grid */}
          <div className="grid sm:grid-cols-2 gap-6 text-sm">
            <div className="bg-white p-5 rounded-xl border border-teal/20 space-y-4 shadow-sm">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-teal/10 text-teal rounded-lg flex-shrink-0">
                  <Calendar className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-xs text-slate-500 block">Scheduled Date</span>
                  <span className="font-bold text-navy text-base">{appointment.scheduled_date || 'Date to be confirmed'}</span>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-teal/10 text-teal rounded-lg flex-shrink-0">
                  <Clock className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-xs text-slate-500 block">Scheduled Time</span>
                  <span className="font-bold text-navy text-base">{appointment.scheduled_time || 'Time to be confirmed'}</span>
                </div>
              </div>
            </div>

            <div className="bg-white p-5 rounded-xl border border-teal/20 space-y-4 shadow-sm">
              <div className="flex items-start gap-3">
                <div className="p-2.5 bg-teal/10 text-teal rounded-lg mt-0.5 flex-shrink-0">
                  <MapPin className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-xs text-slate-500 block">Venue / Office Location</span>
                  <span className="font-semibold text-slate-800 text-sm leading-relaxed">{appointment.venue || 'College Administrative Building'}</span>
                </div>
              </div>

              <div className="pt-2 border-t border-slate-100 text-xs text-slate-600">
                <span className="font-semibold text-slate-700">Instructions:</span> {appointment.instructions || 'Bring all 4 original certificates.'}
              </div>
            </div>
          </div>

          {/* Admin Completion Notes */}
          {appointment.notes && (
            <div className="bg-white p-4 rounded-xl border border-teal/20 text-xs">
              <span className="font-bold text-navy block mb-1">Administrative Remarks / Outcome:</span>
              <p className="text-slate-700">{appointment.notes}</p>
            </div>
          )}

          {/* Mandatory Checklist */}
          <div className="bg-white p-6 rounded-xl border border-teal/20 space-y-3 text-xs shadow-sm">
            <h4 className="font-bold text-navy text-sm flex items-center gap-2">
              <FileText className="w-4 h-4 text-teal" />
              Required Original Documents Checklist:
            </h4>
            <ul className="grid sm:grid-cols-2 gap-2.5 text-slate-700 mt-2">
              <li className="flex items-center gap-2 bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                <span>Original Government ID / Aadhaar Card</span>
              </li>
              <li className="flex items-center gap-2 bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                <span>Original 10th & 12th Marksheets / Grade Cards</span>
              </li>
              <li className="flex items-center gap-2 bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                <span>Original Income Certificate (Tahsildar Issued)</span>
              </li>
              <li className="flex items-center gap-2 bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                <span>Original Maharashtra Domicile Certificate</span>
              </li>
            </ul>
            <p className="text-[11px] text-slate-500 pt-2 border-t border-slate-100">
              Please also carry two self-attested photocopies of each required document.
            </p>
          </div>
        </div>
      ) : isPhysicalRequired ? (
        <div className="bg-amber-50 border-2 border-amber-300 rounded-2xl p-8 shadow-sm">
          <div className="flex items-start gap-3.5">
            <Calendar className="w-8 h-8 text-amber-600 flex-shrink-0 mt-0.5" />
            <div className="space-y-2">
              <h3 className="text-lg font-bold text-amber-950">
                Physical Verification Pending Scheduling
              </h3>
              <p className="text-xs text-amber-900 leading-relaxed max-w-2xl">
                The college administration has flagged your scholarship application for mandatory physical verification of your original documents.
                Your assigned verification officer is preparing your appointment schedule. Once the date, time, and venue are confirmed, they will appear on this page.
              </p>
              <div className="pt-2 text-xs text-amber-800">
                <strong>Important:</strong> Please ensure you have your original Government ID, Marksheet, Income Certificate, and Domicile Certificate ready for inspection.
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-2xl p-10 border border-slate-200 text-center text-slate-500 shadow-sm">
          <Calendar className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <h3 className="text-base font-bold text-slate-800">No Physical Verification Scheduled</h3>
          <p className="text-xs text-slate-500 mt-1.5 max-w-md mx-auto">
            Your scholarship application currently does not require in-person document submission. If an administrator schedules an in-person review, appointment details will appear here.
          </p>
          <div className="mt-6">
            <Link
              to="/student/dashboard"
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-navy hover:bg-navy-light text-white text-xs font-bold rounded-xl transition-colors shadow-sm"
            >
              <span>Return to Student Dashboard</span>
            </Link>
          </div>
        </div>
      )}

      {/* Official Human-in-the-Loop Assistive Disclaimer */}
      <div className="bg-slate-100 rounded-xl p-4 text-xs text-slate-600 flex items-start gap-2.5 border border-slate-200">
        <Info className="w-4 h-4 text-teal flex-shrink-0 mt-0.5" />
        <div>
          <strong>Institutional Authority:</strong> Physical verification appointments are scheduled and recorded exclusively by designated college verification officers. Students cannot self-schedule or modify appointment schedules.
        </div>
      </div>
    </div>
  );
}

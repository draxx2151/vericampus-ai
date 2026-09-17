import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useApplications } from '../../context/ApplicationContext';
import { Calendar, Clock, MapPin, CheckCircle2, AlertCircle, FileText } from 'lucide-react';

export default function StudentAppointmentPage() {
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

  if (!app) return <div className="p-8 text-center text-slate-500">Loading...</div>;

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
        <h2 className="text-xl font-bold text-navy flex items-center gap-2">
          <Calendar className="w-6 h-6 text-teal" />
          Physical Verification Appointment Status
        </h2>
        <p className="text-xs text-slate-500 mt-1">
          Details for in-person document submission or original certificate verification
        </p>
      </div>

      {app.appointment ? (
        <div className="bg-teal-50 border-2 border-teal rounded-2xl p-6 shadow-sm space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-teal/20">
            <div>
              <span className="px-2.5 py-1 bg-teal text-white rounded text-xs font-bold uppercase tracking-wider">
                Meeting Confirmed
              </span>
              <h3 className="text-2xl font-bold text-navy mt-2">Physical Document Verification</h3>
            </div>
            <div className="text-right">
              <span className="text-xs text-slate-500 block">Status</span>
              <span className="text-sm font-bold text-emerald-700 bg-emerald-100 px-3 py-1 rounded-full border border-emerald-300">
                {app.appointment.status}
              </span>
            </div>
          </div>

          <div className="grid sm:grid-cols-2 gap-6 text-sm">
            <div className="bg-white p-4 rounded-xl border border-teal/20 space-y-3">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-teal/10 text-teal rounded-lg">
                  <Calendar className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-xs text-slate-500 block">Scheduled Date</span>
                  <span className="font-bold text-navy text-base">{app.appointment.date}</span>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-teal/10 text-teal rounded-lg">
                  <Clock className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-xs text-slate-500 block">Scheduled Time</span>
                  <span className="font-bold text-navy text-base">{app.appointment.time}</span>
                </div>
              </div>
            </div>

            <div className="bg-white p-4 rounded-xl border border-teal/20 space-y-3">
              <div className="flex items-start gap-3">
                <div className="p-2.5 bg-teal/10 text-teal rounded-lg mt-0.5">
                  <MapPin className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-xs text-slate-500 block">Venue / Office Location</span>
                  <span className="font-semibold text-slate-800 text-sm">{app.appointment.venue}</span>
                </div>
              </div>

              <div className="pt-2 border-t border-slate-100 text-xs text-slate-600">
                <span className="font-semibold text-slate-700">Scheduled By:</span> {app.appointment.scheduledBy}
              </div>
            </div>
          </div>

          {/* Guidelines Checklist */}
          <div className="bg-white p-5 rounded-xl border border-teal/20 space-y-3 text-xs">
            <h4 className="font-bold text-navy text-sm flex items-center gap-2">
              <FileText className="w-4 h-4 text-teal" />
              What to Bring for Verification:
            </h4>
            <ul className="space-y-2 text-slate-700">
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                Original Government ID / Aadhaar Card
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                Original 10th & 12th Marksheets / Certificates
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                Original Income Certificate issued by Tahsildar
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                Original Domicile Certificate
              </li>
            </ul>
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-2xl p-8 border border-slate-200 text-center text-slate-500">
          <Calendar className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <h3 className="text-base font-bold text-slate-700">No Physical Verification Scheduled</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
            Your application currently does not require physical document submission. If the administrator schedules an appointment, details will appear here.
          </p>
        </div>
      )}
    </div>
  );
}

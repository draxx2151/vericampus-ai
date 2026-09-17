import React, { useEffect } from 'react';
import { useApplications } from '../../context/ApplicationContext';
import { Calendar, Clock, MapPin, User, FileCheck } from 'lucide-react';

export default function AdminAppointmentsPage() {
  const { applications, refreshState } = useApplications();

  useEffect(() => {
    refreshState();
  }, []);

  const scheduledApps = applications.filter(a => a.appointment);

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
        <h2 className="text-xl font-bold text-navy flex items-center gap-2">
          <Calendar className="w-6 h-6 text-teal" />
          Scheduled Physical Verification Meetings
        </h2>
        <p className="text-xs text-slate-500 mt-1">
          Manage in-person document verification schedules for candidates
        </p>
      </div>

      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
        {scheduledApps.length === 0 ? (
          <div className="text-center py-8 text-slate-400 text-xs">
            No physical verification meetings scheduled yet. Open an application detail view to schedule one.
          </div>
        ) : (
          <div className="space-y-4">
            {scheduledApps.map((app) => (
              <div key={app.id} className="p-5 rounded-xl border border-slate-200 bg-slate-50 flex flex-wrap items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono text-xs font-bold text-teal bg-teal/10 px-2 py-0.5 rounded">
                      {app.id}
                    </span>
                    <span className="text-xs text-slate-500">{app.scholarship}</span>
                  </div>
                  <h4 className="text-base font-bold text-navy">{app.studentName}</h4>
                  <p className="text-xs text-slate-600 mt-1 flex items-center gap-1">
                    <MapPin className="w-3.5 h-3.5 text-teal" /> {app.appointment.venue}
                  </p>
                </div>

                <div className="text-right text-xs space-y-1">
                  <div className="font-bold text-navy text-sm flex items-center gap-1 justify-end">
                    <Calendar className="w-4 h-4 text-teal" />
                    <span>{app.appointment.date} at {app.appointment.time}</span>
                  </div>
                  <div className="text-slate-500">Scheduled by: {app.appointment.scheduledBy}</div>
                  <span className="inline-block mt-1 px-2.5 py-0.5 bg-emerald-100 text-emerald-800 text-[10px] font-bold rounded">
                    {app.appointment.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

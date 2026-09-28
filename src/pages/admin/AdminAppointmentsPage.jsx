import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useApplications } from '../../context/ApplicationContext';
import { api } from '../../services/api';
import StatusBadge from '../../components/StatusBadge';
import { Calendar, Clock, MapPin, User, FileCheck, Eye, Loader2, AlertCircle } from 'lucide-react';

export default function AdminAppointmentsPage() {
  const { token } = useAuth();
  const { applications, refreshState, loading: appsLoading } = useApplications();
  const [appointmentsMap, setAppointmentsMap] = useState({});
  const [loadingAppts, setLoadingAppts] = useState(false);

  useEffect(() => {
    refreshState();
  }, []);

  useEffect(() => {
    const loadAppointments = async () => {
      const activeToken = token || localStorage.getItem('vericampus_token');
      if (!activeToken || applications.length === 0) return;

      setLoadingAppts(true);
      const map = {};
      await Promise.all(
        applications.map(async (app) => {
          try {
            const appt = await api.getPhysicalVerificationAppointment(app.id, activeToken);
            if (appt) {
              map[app.id] = appt;
            }
          } catch (err) {
            // No appointment for this app
          }
        })
      );
      setAppointmentsMap(map);
      setLoadingAppts(false);
    };

    loadAppointments();
  }, [applications, token]);

  const physicalApps = applications.filter(app => {
    return (
      appointmentsMap[app.id] ||
      app.status === 'PHYSICAL_VERIFICATION_REQUIRED' ||
      app.status === 'PHYSICAL_VERIFICATION_COMPLETED' ||
      app.appointment
    );
  });

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-navy flex items-center gap-2">
            <Calendar className="w-6 h-6 text-teal" />
            Physical Verification Appointments
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Manage in-person document verification schedules and recorded inspection outcomes
          </p>
        </div>

        <span className="text-xs font-semibold text-slate-600 bg-slate-100 px-3 py-1.5 rounded-full border border-slate-200">
          {physicalApps.length} Candidate(s) in Physical Queue
        </span>
      </div>

      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
        {loadingAppts || appsLoading ? (
          <div className="p-12 text-center text-slate-500 flex flex-col items-center justify-center gap-3">
            <Loader2 className="w-8 h-8 text-teal animate-spin" />
            <span className="text-xs font-semibold">Loading physical appointments schedule...</span>
          </div>
        ) : physicalApps.length === 0 ? (
          <div className="text-center py-12 text-slate-400 text-xs space-y-2">
            <Calendar className="w-10 h-10 text-slate-300 mx-auto" />
            <p className="font-semibold text-slate-700">No physical verification appointments scheduled yet.</p>
            <p className="text-slate-400">To require physical verification, open an application from the queue and select "Require Physical Verification".</p>
          </div>
        ) : (
          <div className="space-y-4">
            {physicalApps.map((app) => {
              const appt = appointmentsMap[app.id] || app.appointment;
              const appNum = app.application_number || app.id;
              const studentName = app.student_name || app.studentName || 'Student';
              const scholarship = app.scholarship_name || app.scholarship || 'Scholarship';

              return (
                <div
                  key={app.id}
                  className="p-5 rounded-xl border border-slate-200 bg-slate-50 flex flex-wrap items-center justify-between gap-4 hover:border-slate-300 transition-all"
                >
                  <div className="space-y-1.5 max-w-md">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-teal bg-teal/10 px-2.5 py-0.5 rounded border border-teal/20">
                        {appNum}
                      </span>
                      <span className="text-xs text-slate-500 truncate" title={scholarship}>{scholarship}</span>
                    </div>

                    <h4 className="text-base font-bold text-navy">{studentName}</h4>

                    {appt ? (
                      <p className="text-xs text-slate-600 flex items-center gap-1.5">
                        <MapPin className="w-3.5 h-3.5 text-teal flex-shrink-0" />
                        <span>{appt.venue || 'College Administrative Office'}</span>
                      </p>
                    ) : (
                      <p className="text-xs text-amber-700 flex items-center gap-1.5">
                        <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                        <span>Action needed: Appointment date & venue pending scheduling</span>
                      </p>
                    )}
                  </div>

                  <div className="flex flex-wrap items-center gap-6">
                    <div className="text-right text-xs space-y-1">
                      {appt ? (
                        <>
                          <div className="font-bold text-navy text-sm flex items-center gap-1.5 justify-end">
                            <Clock className="w-4 h-4 text-teal" />
                            <span>{appt.scheduled_date || 'Date TBD'} at {appt.scheduled_time || 'Time TBD'}</span>
                          </div>
                          <div className="flex items-center gap-2 justify-end">
                            <StatusBadge status={appt.status || 'SCHEDULED'} />
                            <StatusBadge status={app.status} />
                          </div>
                        </>
                      ) : (
                        <div className="text-right space-y-1">
                          <span className="text-xs font-bold text-amber-700 block">Pending Schedule</span>
                          <StatusBadge status={app.status} />
                        </div>
                      )}
                    </div>

                    <Link
                      to={`/admin/applications/${app.id}`}
                      className="inline-flex items-center gap-1.5 px-4 py-2 bg-navy hover:bg-navy-light text-white text-xs font-semibold rounded-lg transition-colors shadow-sm"
                    >
                      <Eye className="w-3.5 h-3.5 text-seafoam" />
                      <span>Review / Manage</span>
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

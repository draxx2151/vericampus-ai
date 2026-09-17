import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useApplications } from '../../context/ApplicationContext';
import { api } from '../../services/api';
import { Bell, CheckCircle2, AlertTriangle, Calendar, Info } from 'lucide-react';

export default function StudentNotificationsPage() {
  const { currentUser } = useAuth();
  const { fetchNotifications, notifications } = useApplications();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (currentUser) {
      fetchNotifications('STUDENT', currentUser.id).finally(() => setLoading(false));
    }
  }, [currentUser]);

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
        <h2 className="text-xl font-bold text-navy flex items-center gap-2">
          <Bell className="w-6 h-6 text-teal" />
          Student Notifications Timeline
        </h2>
        <p className="text-xs text-slate-500 mt-1">
          Real-time updates regarding AI verification status and appointment schedules
        </p>
      </div>

      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
        {notifications.length === 0 ? (
          <div className="text-center py-8 text-slate-400 text-xs">No notifications yet.</div>
        ) : (
          notifications.map((notif) => (
            <div key={notif.id} className="p-4 rounded-xl border border-slate-100 bg-slate-50 flex items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                {notif.title.includes('Meeting') || notif.title.includes('Appointment') ? (
                  <Calendar className="w-5 h-5 text-teal flex-shrink-0 mt-0.5" />
                ) : notif.title.includes('Alert') || notif.title.includes('Review') ? (
                  <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                ) : (
                  <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
                )}
                <div>
                  <h4 className="font-bold text-navy text-sm">{notif.title}</h4>
                  <p className="text-xs text-slate-600 mt-0.5">{notif.message}</p>
                  <span className="text-[11px] text-slate-400 block mt-1">{notif.timestamp}</span>
                </div>
              </div>
              <span className="text-[10px] font-semibold bg-seafoam-light text-navy px-2 py-0.5 rounded border border-seafoam">
                {notif.applicationId}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

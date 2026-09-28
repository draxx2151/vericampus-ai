import React, { useState, useEffect } from 'react';
import { useApplications } from '../../context/ApplicationContext';
import { 
  Bell, 
  ShieldAlert, 
  CheckCircle2, 
  Calendar, 
  AlertTriangle, 
  FileText, 
  Info, 
  Check, 
  CheckCheck 
} from 'lucide-react';

export default function AdminNotificationsPage() {
  const { 
    fetchNotifications, 
    notifications, 
    unreadCount, 
    markNotificationAsRead, 
    markAllNotificationsAsRead 
  } = useApplications();
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    fetchNotifications().finally(() => setLoading(false));
  }, []);

  const handleMarkAll = async () => {
    setActionLoading(true);
    try {
      await markAllNotificationsAsRead();
    } finally {
      setActionLoading(false);
    }
  };

  const getEventIcon = (eventType) => {
    switch (eventType) {
      case 'APPLICATION_APPROVED':
        return <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />;
      case 'APPLICATION_REJECTED':
        return <ShieldAlert className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />;
      case 'CORRECTION_REQUESTED':
        return <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />;
      case 'PHYSICAL_VERIFICATION_SCHEDULED':
      case 'PHYSICAL_VERIFICATION_COMPLETED':
        return <Calendar className="w-5 h-5 text-teal flex-shrink-0 mt-0.5" />;
      case 'DOCUMENT_REPLACED':
        return <FileText className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />;
      case 'VERIFICATION_COMPLETED':
        return <CheckCircle2 className="w-5 h-5 text-teal flex-shrink-0 mt-0.5" />;
      default:
        return <Info className="w-5 h-5 text-navy flex-shrink-0 mt-0.5" />;
    }
  };

  const formatDate = (isoString) => {
    if (!isoString) return '';
    try {
      const date = new Date(isoString);
      return date.toLocaleString(undefined, {
        dateStyle: 'medium',
        timeStyle: 'short'
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-navy flex items-center gap-2">
              <Bell className="w-6 h-6 text-teal" />
              Admin Audit & Workflow Alerts Log
            </h2>
            {unreadCount > 0 && (
              <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-700 border border-rose-200">
                {unreadCount} unread
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Real-time audit alerts, verification status, and student application actions
          </p>
        </div>

        {unreadCount > 0 && (
          <button
            onClick={handleMarkAll}
            disabled={actionLoading}
            className="self-start sm:self-auto inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-navy bg-slate-100 hover:bg-slate-200 border border-slate-200 transition-colors disabled:opacity-50"
          >
            <CheckCheck className="w-3.5 h-3.5 text-teal" />
            Mark all as read
          </button>
        )}
      </div>

      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-3">
        {loading ? (
          <div className="text-center py-8 text-slate-400 text-xs">Loading notifications...</div>
        ) : notifications.length === 0 ? (
          <div className="text-center py-8 text-slate-400 text-xs">No admin audit alerts or notifications currently.</div>
        ) : (
          notifications.map((notif) => {
            const appNum = notif.event_metadata?.application_number || 
              (notif.application_id ? `App #${notif.application_id.slice(0, 8)}` : null);

            return (
              <div 
                key={notif.id} 
                className={`p-4 rounded-xl border transition-colors flex items-start justify-between gap-4 ${
                  notif.is_read 
                    ? 'border-slate-100 bg-slate-50/60' 
                    : 'border-teal/30 bg-teal/5 shadow-xs'
                }`}
              >
                <div className="flex items-start gap-3 flex-1 min-w-0">
                  {getEventIcon(notif.event_type)}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h4 className={`font-bold text-sm ${notif.is_read ? 'text-slate-700' : 'text-navy'}`}>
                        {notif.title}
                      </h4>
                      {!notif.is_read && (
                        <span className="text-[10px] font-semibold bg-teal/15 text-teal px-2 py-0.5 rounded-full">
                          New
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-600 mt-1 whitespace-pre-wrap">{notif.message}</p>
                    <div className="flex items-center gap-3 mt-2 text-[11px] text-slate-400">
                      <span>{formatDate(notif.created_at)}</span>
                      {notif.read_at && (
                        <span className="text-[10px] text-slate-400 italic">
                          (Read {formatDate(notif.read_at)})
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex flex-col items-end gap-2 flex-shrink-0">
                  {appNum && (
                    <span className="text-[10px] font-semibold bg-seafoam-light text-navy px-2 py-0.5 rounded border border-seafoam">
                      {appNum}
                    </span>
                  )}
                  {!notif.is_read && (
                    <button
                      onClick={() => markNotificationAsRead(notif.id)}
                      className="inline-flex items-center gap-1 text-[11px] font-medium text-teal hover:text-teal-hover hover:underline"
                    >
                      <Check className="w-3 h-3" />
                      Mark read
                    </button>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

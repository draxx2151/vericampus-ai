import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useApplications } from '../context/ApplicationContext';
import { 
  LayoutDashboard, 
  FileText, 
  UploadCloud, 
  ShieldCheck, 
  Calendar, 
  Bell, 
  Users, 
  ClipboardCheck 
} from 'lucide-react';

export default function Sidebar() {
  const { role } = useAuth();
  const { unreadCount } = useApplications();

  const studentLinks = [
    { to: '/student/dashboard', icon: LayoutDashboard, label: 'Overview' },
    { to: '/student/documents', icon: UploadCloud, label: 'Upload Documents' },
    { to: '/student/verification', icon: ShieldCheck, label: 'AI Verification Result' },
    { to: '/student/appointment', icon: Calendar, label: 'Appointment Status' },
    { to: '/student/notifications', icon: Bell, label: 'Notifications', hasBadge: true },
  ];

  const adminLinks = [
    { to: '/admin/dashboard', icon: LayoutDashboard, label: 'Admin Metrics' },
    { to: '/admin/applications', icon: ClipboardCheck, label: 'All Applications' },
    { to: '/admin/appointments', icon: Calendar, label: 'Scheduled Meetings' },
    { to: '/admin/notifications', icon: Bell, label: 'Audit Alerts', hasBadge: true },
  ];

  const links = role === 'ADMIN' ? adminLinks : studentLinks;

  return (
    <aside className="w-64 bg-white border-r border-slate-200 min-h-[calc(100vh-4rem)] p-4 flex flex-col justify-between">
      <div>
        <div className="px-3 py-2 text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
          {role === 'ADMIN' ? 'Admin Workflow Portal' : 'Student Scholarship Portal'}
        </div>
        <nav className="space-y-1">
          {links.map((link) => {
            const Icon = link.icon;
            return (
              <NavLink
                key={link.to}
                to={link.to}
                className={({ isActive }) =>
                  `flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-seafoam-light text-navy font-semibold border-l-4 border-teal'
                      : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                  }`
                }
              >
                <div className="flex items-center gap-3">
                  <Icon className="w-5 h-5 text-teal" />
                  <span>{link.label}</span>
                </div>
                {link.hasBadge && unreadCount > 0 && (
                  <span className="px-1.5 py-0.5 rounded-full text-[10px] font-bold bg-rose-500 text-white min-w-[1.25rem] text-center">
                    {unreadCount}
                  </span>
                )}
              </NavLink>
            );
          })}
        </nav>
      </div>

      <div className="bg-slate-50 rounded-lg p-3 border border-slate-200 text-xs text-slate-500">
        <div className="font-semibold text-navy mb-1">VeriCampus AI Engine</div>
        <div>OCR & Rule-Based Field Extraction Active (v1.0 Demo)</div>
      </div>
    </aside>
  );
}

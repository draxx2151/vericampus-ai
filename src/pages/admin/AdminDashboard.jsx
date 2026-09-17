import React, { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useApplications } from '../../context/ApplicationContext';
import DashboardCard from '../../components/DashboardCard';
import StatusBadge from '../../components/StatusBadge';
import { 
  ClipboardCheck, 
  CheckCircle2, 
  AlertTriangle, 
  Calendar, 
  Eye, 
  ArrowRight,
  ShieldAlert,
  Users
} from 'lucide-react';

export default function AdminDashboard() {
  const { applications, refreshState } = useApplications();

  useEffect(() => {
    refreshState();
  }, []);

  const total = applications.length;
  const verified = applications.filter(a => a.overallStatus === 'VERIFIED').length;
  const needsReview = applications.filter(a => a.overallStatus === 'NEEDS_REVIEW').length;
  const meetingsRequired = applications.filter(a => a.meetingRequired || a.appointment).length;

  return (
    <div className="space-y-6">
      {/* Overview Metric Cards */}
      <div className="grid sm:grid-cols-2 md:grid-cols-4 gap-4">
        <DashboardCard
          title="Total Applications"
          value={total}
          subtitle="Scholarship Submissions"
          icon={Users}
          color="navy"
        />
        <DashboardCard
          title="Verified"
          value={verified}
          subtitle="AI Passed Verification"
          icon={CheckCircle2}
          color="emerald"
        />
        <DashboardCard
          title="Needs Review"
          value={needsReview}
          subtitle="Requires Admin Inspection"
          icon={AlertTriangle}
          color="amber"
        />
        <DashboardCard
          title="Meetings Required"
          value={meetingsRequired}
          subtitle="Physical In-Person Verification"
          icon={Calendar}
          color="teal"
        />
      </div>

      {/* Main Demo Action Banner: Flagged Review Priority */}
      {needsReview > 0 && (
        <div className="bg-amber-50 border-2 border-amber-300 rounded-2xl p-6 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="p-3 bg-amber-500 text-white rounded-xl">
                <ShieldAlert className="w-6 h-6" />
              </div>
              <div>
                <span className="px-2.5 py-0.5 rounded text-[10px] font-extrabold uppercase tracking-wider bg-amber-200 text-amber-900">
                  Priority Review Queue
                </span>
                <h3 className="text-lg font-bold text-amber-950 mt-1">
                  Application Flagged for Name Variation (Amit Patil)
                </h3>
                <p className="text-xs text-amber-900 mt-0.5">
                  OCR detection flagged name mismatch across Marksheet & Income Certificate.
                </p>
              </div>
            </div>

            <Link
              to="/admin/applications/VC-2026-002"
              className="flex items-center gap-2 px-5 py-2.5 bg-amber-600 hover:bg-amber-700 text-white font-bold text-xs rounded-xl transition-colors shadow-md"
            >
              <Eye className="w-4 h-4" />
              <span>Review Application VC-2026-002</span>
            </Link>
          </div>
        </div>
      )}

      {/* Quick Applications Table */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-bold text-navy">Incoming Applications Overview</h3>
            <p className="text-xs text-slate-500">Real-time status of candidate applications</p>
          </div>
          <Link
            to="/admin/applications"
            className="text-xs font-semibold text-teal hover:underline flex items-center gap-1"
          >
            <span>View All Applications</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th className="py-3 px-4">Application ID</th>
                <th className="py-3 px-4">Student Name</th>
                <th className="py-3 px-4">Scholarship</th>
                <th className="py-3 px-4">Docs</th>
                <th className="py-3 px-4">AI Verification</th>
                <th className="py-3 px-4">Meeting Status</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs text-slate-700">
              {applications.map((app) => (
                <tr key={app.id} className="hover:bg-slate-50/80 transition-colors">
                  <td className="py-3 px-4 font-mono font-bold text-navy">{app.id}</td>
                  <td className="py-3 px-4 font-semibold text-slate-900">{app.studentName}</td>
                  <td className="py-3 px-4">{app.scholarship}</td>
                  <td className="py-3 px-4 font-medium">{app.documentsUploadedCount} / 4</td>
                  <td className="py-3 px-4">
                    <StatusBadge status={app.overallStatus} confidence={app.aiConfidence} />
                  </td>
                  <td className="py-3 px-4">
                    {app.appointment ? (
                      <span className="text-teal font-semibold">Scheduled</span>
                    ) : app.meetingRequired ? (
                      <span className="text-amber-600 font-semibold">Required</span>
                    ) : (
                      <span className="text-slate-400">Not Required</span>
                    )}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <Link
                      to={`/admin/applications/${app.id}`}
                      className="px-3 py-1 bg-navy text-white text-[11px] font-semibold rounded hover:bg-navy-light transition-colors"
                    >
                      View
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

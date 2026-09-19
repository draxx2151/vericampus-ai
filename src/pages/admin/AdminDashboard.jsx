import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useApplications } from '../../context/ApplicationContext';
import { api } from '../../services/api';
import DashboardCard from '../../components/DashboardCard';
import StatusBadge from '../../components/StatusBadge';
import { 
  CheckCircle2, 
  AlertTriangle, 
  Calendar, 
  ArrowRight,
  Users,
  Building,
  Save,
  CheckCircle,
  AlertCircle
} from 'lucide-react';

export default function AdminDashboard() {
  const { token, currentUser } = useAuth();
  const { applications, refreshState } = useApplications();

  const [collegeInfo, setCollegeInfo] = useState(null);
  const [newCollegeCode, setNewCollegeCode] = useState('');
  const [savingCode, setSavingCode] = useState(false);
  const [codeMessage, setCodeMessage] = useState(null);
  const [codeError, setCodeError] = useState(null);

  useEffect(() => {
    refreshState();
    if (token) {
      loadCollegeInfo();
    }
  }, [token]);

  const loadCollegeInfo = async () => {
    try {
      const data = await api.getAdminCollege(token);
      setCollegeInfo(data);
      setNewCollegeCode(data.college_code || '');
    } catch (err) {
      console.error("Failed to load admin college info:", err);
    }
  };

  const handleUpdateCollegeCode = async (e) => {
    e.preventDefault();
    if (!newCollegeCode.trim()) return;
    setSavingCode(true);
    setCodeMessage(null);
    setCodeError(null);

    try {
      const res = await api.updateCollegeCode(newCollegeCode, token);
      setCodeMessage(`Student College Code updated to "${res.college_code}"!`);
      loadCollegeInfo();
    } catch (err) {
      setCodeError(err.message || "Failed to update college code");
    } finally {
      setSavingCode(false);
    }
  };

  const total = applications.length;
  const verified = applications.filter(a => a.status === 'VERIFIED').length;
  const needsReview = applications.filter(a => a.status === 'NEEDS_REVIEW').length;
  const physicalReq = applications.filter(a => a.status === 'PHYSICAL_VERIFICATION_REQUIRED').length;

  return (
    <div className="space-y-6">
      {/* College & Admin Info Header + College Code Management Widget */}
      <div className="bg-navy text-white rounded-2xl p-6 shadow-md">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <span className="text-xs font-semibold uppercase tracking-wider text-seafoam">
              {collegeInfo?.college_name || "College Administrator"}
            </span>
            <h2 className="text-2xl font-bold mt-0.5">
              Welcome, {currentUser?.full_name || "Admin Officer"}
            </h2>
            <p className="text-xs text-slate-300 mt-1">
              Department: {currentUser?.department || "Scholarship Cell"} • Designation: {currentUser?.designation || "Verification Officer"}
            </p>
          </div>

          {/* Student-Facing College Code Configuration Form */}
          <div className="bg-slate-800/80 border border-slate-700 p-4 rounded-xl max-w-sm w-full">
            <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-seafoam mb-2">
              <Building className="w-4 h-4" />
              <span>Student-Facing College Code</span>
            </div>

            {codeMessage && (
              <div className="mb-2 p-2 bg-emerald-900/60 border border-emerald-500/50 rounded text-xs text-emerald-200 flex items-center gap-1.5">
                <CheckCircle className="w-3.5 h-3.5 flex-shrink-0" />
                <span>{codeMessage}</span>
              </div>
            )}

            {codeError && (
              <div className="mb-2 p-2 bg-rose-900/60 border border-rose-500/50 rounded text-xs text-rose-200 flex items-center gap-1.5">
                <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                <span>{codeError}</span>
              </div>
            )}

            <form onSubmit={handleUpdateCollegeCode} className="flex items-center gap-2">
              <input
                type="text"
                value={newCollegeCode}
                onChange={(e) => setNewCollegeCode(e.target.value.toUpperCase())}
                placeholder="e.g. COLLEGE001"
                required
                className="w-full px-3 py-1.5 bg-slate-900 border border-slate-600 rounded-lg text-xs uppercase font-mono tracking-wider text-white focus:outline-none focus:border-seafoam"
              />
              <button
                type="submit"
                disabled={savingCode}
                className="px-3 py-1.5 bg-teal hover:bg-teal-hover text-white font-bold text-xs rounded-lg transition-colors flex items-center gap-1 shadow-sm whitespace-nowrap disabled:opacity-50"
              >
                <Save className="w-3.5 h-3.5" />
                <span>{savingCode ? "Saving..." : "Set Code"}</span>
              </button>
            </form>
            <p className="text-[10px] text-slate-400 mt-1.5">
              Give this code to your students for registration.
            </p>
          </div>
        </div>
      </div>

      {/* Overview Metric Cards */}
      <div className="grid sm:grid-cols-2 md:grid-cols-4 gap-4">
        <DashboardCard
          title="Total Applications"
          value={total}
          subtitle="College Submissions"
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
          title="Physical Verification"
          value={physicalReq}
          subtitle="In-Person Appointment"
          icon={Calendar}
          color="teal"
        />
      </div>

      {/* Quick Applications Table */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-bold text-navy">Incoming Applications Overview</h3>
            <p className="text-xs text-slate-500">Real-time status of candidate applications for your college</p>
          </div>
          <Link
            to="/admin/applications"
            className="text-xs font-semibold text-teal hover:underline flex items-center gap-1"
          >
            <span>View All Applications</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>

        {applications.length === 0 ? (
          <div className="p-8 text-center text-slate-500 text-xs">
            No student applications submitted for your college yet. Provide your College Code to students to begin receiving applications.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th className="py-3 px-4">Application Number</th>
                  <th className="py-3 px-4">Student Name</th>
                  <th className="py-3 px-4">Scholarship Program</th>
                  <th className="py-3 px-4">Uploaded Docs</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-xs text-slate-700">
                {applications.map((app) => (
                  <tr key={app.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3 px-4 font-mono font-bold text-navy">{app.application_number}</td>
                    <td className="py-3 px-4 font-semibold text-slate-900">{app.student_name}</td>
                    <td className="py-3 px-4">{app.scholarship_name}</td>
                    <td className="py-3 px-4 font-medium">{app.documents_uploaded_count || (app.documents ? app.documents.length : 0)} / 4</td>
                    <td className="py-3 px-4">
                      <StatusBadge status={app.status} />
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
        )}
      </div>
    </div>
  );
}

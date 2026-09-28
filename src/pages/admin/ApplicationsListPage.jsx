import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useApplications } from '../../context/ApplicationContext';
import StatusBadge from '../../components/StatusBadge';
import { ClipboardCheck, Filter, Search, Eye, ArrowRight } from 'lucide-react';

export default function ApplicationsListPage() {
  const { applications, refreshState, loading } = useApplications();
  const [filter, setFilter] = useState('ALL');
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    refreshState();
  }, []);

  const filteredApps = applications.filter(app => {
    const status = app.status || app.overallStatus || '';
    const matchesFilter = filter === 'ALL' || status === filter;

    const studentName = app.student_name || app.studentName || '';
    const appNum = app.application_number || app.id || '';
    const scholarship = app.scholarship_name || app.scholarship || '';

    const term = searchTerm.toLowerCase();
    const matchesSearch = 
      studentName.toLowerCase().includes(term) ||
      appNum.toLowerCase().includes(term) ||
      scholarship.toLowerCase().includes(term);

    return matchesFilter && matchesSearch;
  });

  const filterOptions = [
    { key: 'ALL', label: 'All Applications' },
    { key: 'NEEDS_REVIEW', label: 'Needs Review' },
    { key: 'PHYSICAL_VERIFICATION_REQUIRED', label: 'Physical Verification' },
    { key: 'VERIFIED', label: 'AI Verified' },
    { key: 'APPROVED', label: 'Approved' },
    { key: 'REJECTED', label: 'Rejected' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-navy flex items-center gap-2">
            <ClipboardCheck className="w-6 h-6 text-teal" />
            Scholarship Applications Queue
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Review incoming student applications, AI OCR findings, and physical meeting requests
          </p>
        </div>

        {/* Search */}
        <div className="relative">
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search by student name or application #..."
            className="pl-9 pr-4 py-2 border border-slate-300 rounded-xl text-xs w-72 focus:ring-2 focus:ring-teal outline-none"
          />
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-slate-200 pb-2">
        {filterOptions.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition-colors ${
              filter === key
                ? 'bg-navy text-white shadow-sm'
                : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
        {filteredApps.length === 0 ? (
          <div className="py-12 text-center text-slate-500 text-xs space-y-2">
            <ClipboardCheck className="w-10 h-10 text-slate-300 mx-auto" />
            <p className="font-semibold text-slate-700">No applications match your filter or search criteria.</p>
            <p className="text-slate-400">Try adjusting your filters or search term above.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th className="py-3 px-4">Application #</th>
                  <th className="py-3 px-4">Student Name</th>
                  <th className="py-3 px-4">Scholarship Scheme</th>
                  <th className="py-3 px-4">Submission Date</th>
                  <th className="py-3 px-4">Documents</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-xs text-slate-700">
                {filteredApps.map((app) => {
                  const appNum = app.application_number || app.id;
                  const studentName = app.student_name || app.studentName || 'Student';
                  const scholarship = app.scholarship_name || app.scholarship || 'Scholarship Scheme';
                  const dateStr = app.submitted_at
                    ? new Date(app.submitted_at).toLocaleDateString()
                    : (app.created_at ? new Date(app.created_at).toLocaleDateString() : 'Draft');
                  const docCount = app.documents_uploaded_count ?? (app.documents ? app.documents.length : 0);
                  const status = app.status || app.overallStatus;

                  return (
                    <tr key={app.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="py-3.5 px-4 font-mono font-bold text-navy">{appNum}</td>
                      <td className="py-3.5 px-4 font-semibold text-slate-900">{studentName}</td>
                      <td className="py-3.5 px-4 max-w-[220px] truncate" title={scholarship}>{scholarship}</td>
                      <td className="py-3.5 px-4 text-slate-500">{dateStr}</td>
                      <td className="py-3.5 px-4 font-medium">{docCount} / 4</td>
                      <td className="py-3.5 px-4">
                        <StatusBadge status={status} />
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <Link
                          to={`/admin/applications/${app.id}`}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-teal hover:bg-teal-hover text-white text-xs font-semibold rounded-lg transition-colors shadow-sm"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          <span>View & Audit</span>
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

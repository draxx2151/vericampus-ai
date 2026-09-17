import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useApplications } from '../../context/ApplicationContext';
import StatusBadge from '../../components/StatusBadge';
import { ClipboardCheck, Filter, Search, Eye } from 'lucide-react';

export default function ApplicationsListPage() {
  const { applications, refreshState } = useApplications();
  const [filter, setFilter] = useState('ALL');
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    refreshState();
  }, []);

  const filteredApps = applications.filter(app => {
    const matchesFilter = filter === 'ALL' || app.overallStatus === filter;
    const matchesSearch = app.studentName.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          app.id.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  return (
    <div className="space-y-6">
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
            placeholder="Search by ID or name..."
            className="pl-9 pr-4 py-2 border border-slate-300 rounded-xl text-xs w-64 focus:ring-2 focus:ring-teal outline-none"
          />
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2 border-b border-slate-200 pb-2">
        {['ALL', 'VERIFIED', 'NEEDS_REVIEW', 'PROCESSING'].map((statusKey) => (
          <button
            key={statusKey}
            onClick={() => setFilter(statusKey)}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition-colors ${
              filter === statusKey
                ? 'bg-navy text-white'
                : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'
            }`}
          >
            {statusKey === 'ALL' ? 'All Applications' : statusKey.replace('_', ' ')}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th className="py-3 px-4">App ID</th>
                <th className="py-3 px-4">Student Name</th>
                <th className="py-3 px-4">Scholarship</th>
                <th className="py-3 px-4">Applied Date</th>
                <th className="py-3 px-4">Documents</th>
                <th className="py-3 px-4">AI Verification</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs text-slate-700">
              {filteredApps.map((app) => (
                <tr key={app.id} className="hover:bg-slate-50/80 transition-colors">
                  <td className="py-3.5 px-4 font-mono font-bold text-navy">{app.id}</td>
                  <td className="py-3.5 px-4 font-semibold text-slate-900">{app.studentName}</td>
                  <td className="py-3.5 px-4">{app.scholarship}</td>
                  <td className="py-3.5 px-4 text-slate-500">{app.appliedDate}</td>
                  <td className="py-3.5 px-4 font-medium">{app.documentsUploadedCount} / 4</td>
                  <td className="py-3.5 px-4">
                    <StatusBadge status={app.overallStatus} confidence={app.aiConfidence} />
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    <Link
                      to={`/admin/applications/${app.id}`}
                      className="inline-flex items-center gap-1 px-3 py-1.5 bg-teal hover:bg-teal-hover text-white text-xs font-semibold rounded-lg transition-colors shadow-sm"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      <span>View & Audit</span>
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

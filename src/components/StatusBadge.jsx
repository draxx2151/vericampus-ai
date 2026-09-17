import React from 'react';
import { CheckCircle2, AlertTriangle, Clock, Calendar, XCircle } from 'lucide-react';

export default function StatusBadge({ status, confidence }) {
  let colorStyle = "bg-slate-100 text-slate-700 border-slate-200";
  let icon = <Clock className="w-4 h-4 mr-1.5" />;
  let label = status;

  switch (status) {
    case 'VERIFIED':
    case 'PASSED':
    case 'APPROVED':
      colorStyle = "bg-emerald-50 text-emerald-800 border-emerald-200";
      icon = <CheckCircle2 className="w-4 h-4 mr-1.5 text-emerald-600" />;
      label = "Verified";
      break;
    case 'NEEDS_REVIEW':
    case 'FLAGGED':
    case 'WARNING':
      colorStyle = "bg-amber-50 text-amber-900 border-amber-300";
      icon = <AlertTriangle className="w-4 h-4 mr-1.5 text-amber-600" />;
      label = "Needs Review";
      break;
    case 'PROCESSING':
    case 'PENDING':
    case 'READY_FOR_AI':
      colorStyle = "bg-sky-50 text-sky-800 border-sky-200";
      icon = <Clock className="w-4 h-4 mr-1.5 text-sky-600 animate-spin" />;
      label = status === 'READY_FOR_AI' ? "Ready for AI" : "Processing";
      break;
    case 'SCHEDULED':
      colorStyle = "bg-teal-50 text-teal-900 border-teal-300";
      icon = <Calendar className="w-4 h-4 mr-1.5 text-teal-700" />;
      label = "Meeting Scheduled";
      break;
    case 'REJECTED':
      colorStyle = "bg-rose-50 text-rose-800 border-rose-200";
      icon = <XCircle className="w-4 h-4 mr-1.5 text-rose-600" />;
      label = "Rejected";
      break;
    default:
      label = status;
  }

  return (
    <div className="inline-flex items-center">
      <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border ${colorStyle}`}>
        {icon}
        {label}
      </span>
      {confidence !== undefined && confidence !== null && (
        <span className="ml-2 text-xs font-medium text-slate-500 bg-slate-100 px-2 py-0.5 rounded border border-slate-200" title="Prototype-generated indicator">
          {confidence}% AI Confidence *
        </span>
      )}
    </div>
  );
}

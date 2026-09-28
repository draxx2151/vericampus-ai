import React from 'react';
import { CheckCircle2, AlertTriangle, Clock, Calendar, XCircle } from 'lucide-react';

export default function StatusBadge({ status, confidence }) {
  let colorStyle = "bg-slate-100 text-slate-700 border-slate-200";
  let icon = <Clock className="w-3.5 h-3.5 mr-1.5" />;
  let label = status || "Unknown";

  switch (status) {
    case 'VERIFIED':
    case 'APPROVED':
      colorStyle = "bg-emerald-50 text-emerald-800 border-emerald-300";
      icon = <CheckCircle2 className="w-3.5 h-3.5 mr-1.5 text-emerald-600" />;
      label = "Verified";
      break;
    case 'PASS':
    case 'PASSED':
      colorStyle = "bg-emerald-50 text-emerald-800 border-emerald-300";
      icon = <CheckCircle2 className="w-3.5 h-3.5 mr-1.5 text-emerald-600" />;
      label = "Pass";
      break;
    case 'RESOLVED':
      colorStyle = "bg-emerald-50 text-emerald-800 border-emerald-300";
      icon = <CheckCircle2 className="w-3.5 h-3.5 mr-1.5 text-emerald-600" />;
      label = "Resolved";
      break;
    case 'NEEDS_REVIEW':
      colorStyle = "bg-amber-50 text-amber-900 border-amber-300";
      icon = <AlertTriangle className="w-3.5 h-3.5 mr-1.5 text-amber-600" />;
      label = "Needs Review";
      break;
    case 'WARNING':
    case 'FLAGGED':
      colorStyle = "bg-amber-50 text-amber-900 border-amber-300";
      icon = <AlertTriangle className="w-3.5 h-3.5 mr-1.5 text-amber-600" />;
      label = "Warning";
      break;
    case 'FAIL':
    case 'FAILED':
      colorStyle = "bg-rose-50 text-rose-800 border-rose-300";
      icon = <XCircle className="w-3.5 h-3.5 mr-1.5 text-rose-600" />;
      label = "Failed";
      break;
    case 'REJECTED':
      colorStyle = "bg-rose-50 text-rose-800 border-rose-300";
      icon = <XCircle className="w-3.5 h-3.5 mr-1.5 text-rose-600" />;
      label = "Rejected";
      break;
    case 'PHYSICAL_VERIFICATION_REQUIRED':
      colorStyle = "bg-teal-50 text-teal-900 border-teal-300";
      icon = <Calendar className="w-3.5 h-3.5 mr-1.5 text-teal-700" />;
      label = "Physical Verification Required";
      break;
    case 'PHYSICAL_VERIFICATION_COMPLETED':
      colorStyle = "bg-emerald-50 text-emerald-900 border-emerald-300";
      icon = <CheckCircle2 className="w-3.5 h-3.5 mr-1.5 text-emerald-700" />;
      label = "Physical Verification Completed";
      break;
    case 'SCHEDULED':
      colorStyle = "bg-teal-50 text-teal-900 border-teal-300";
      icon = <Calendar className="w-3.5 h-3.5 mr-1.5 text-teal-700" />;
      label = "Scheduled";
      break;
    case 'COMPLETED':
      colorStyle = "bg-emerald-50 text-emerald-800 border-emerald-300";
      icon = <CheckCircle2 className="w-3.5 h-3.5 mr-1.5 text-emerald-600" />;
      label = "Completed";
      break;
    case 'CANCELLED':
      colorStyle = "bg-slate-100 text-slate-700 border-slate-300";
      icon = <XCircle className="w-3.5 h-3.5 mr-1.5 text-slate-500" />;
      label = "Cancelled";
      break;
    case 'DRAFT':
      colorStyle = "bg-slate-100 text-slate-700 border-slate-300";
      icon = <Clock className="w-3.5 h-3.5 mr-1.5 text-slate-500" />;
      label = "Draft";
      break;
    case 'SUBMITTED':
      colorStyle = "bg-sky-50 text-sky-800 border-sky-300";
      icon = <Clock className="w-3.5 h-3.5 mr-1.5 text-sky-600" />;
      label = "Submitted";
      break;
    case 'UNDER_AI_VERIFICATION':
    case 'PROCESSING':
    case 'READY_FOR_AI':
      colorStyle = "bg-sky-50 text-sky-800 border-sky-300";
      icon = <Clock className="w-3.5 h-3.5 mr-1.5 text-sky-600 animate-spin" />;
      label = status === 'UNDER_AI_VERIFICATION' ? "Under AI Verification" : "Processing";
      break;
    case 'PENDING':
      colorStyle = "bg-amber-50 text-amber-800 border-amber-200";
      icon = <Clock className="w-3.5 h-3.5 mr-1.5 text-amber-600" />;
      label = "Pending";
      break;
    case 'UPLOADED':
      colorStyle = "bg-emerald-50 text-emerald-800 border-emerald-200";
      icon = <CheckCircle2 className="w-3.5 h-3.5 mr-1.5 text-emerald-600" />;
      label = "Uploaded";
      break;
    case 'NOT_AVAILABLE':
      colorStyle = "bg-slate-100 text-slate-500 border-slate-200";
      icon = <Clock className="w-3.5 h-3.5 mr-1.5 text-slate-400" />;
      label = "Not Available";
      break;
    default:
      label = String(status || '').replace(/_/g, ' ');
  }

  return (
    <div className="inline-flex items-center">
      <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border ${colorStyle}`}>
        {icon}
        <span className="capitalize">{label}</span>
      </span>
      {confidence !== undefined && confidence !== null && (
        <span className="ml-2 text-[11px] font-medium text-slate-600 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
          {confidence}% Score
        </span>
      )}
    </div>
  );
}

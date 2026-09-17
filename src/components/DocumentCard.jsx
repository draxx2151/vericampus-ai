import React, { useState } from 'react';
import { FileText, Upload, CheckCircle2, AlertCircle, FileCheck, Sparkles } from 'lucide-react';
import StatusBadge from './StatusBadge';

export default function DocumentCard({
  title,
  required = true,
  docData,
  onUpload,
  onUseDemo
}) {
  const [isUploading, setIsUploading] = useState(false);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setIsUploading(true);
      setTimeout(() => {
        onUpload(file);
        setIsUploading(false);
      }, 400);
    }
  };

  const handleDemoClick = () => {
    setIsUploading(true);
    setTimeout(() => {
      onUseDemo();
      setIsUploading(false);
    }, 300);
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:border-slate-300 transition-all flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <div className="p-2 bg-seafoam-light text-teal rounded-lg">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <h4 className="font-semibold text-slate-900 text-sm">{title}</h4>
              <span className="text-[11px] font-medium text-slate-400">PDF, JPG, PNG (Max 5MB)</span>
            </div>
          </div>
          {required && (
            <span className="px-2 py-0.5 text-[10px] font-bold tracking-wider uppercase bg-rose-50 text-rose-700 rounded border border-rose-200">
              Required
            </span>
          )}
        </div>

        {/* Upload Status Details */}
        {docData ? (
          <div className="my-4 p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs">
            <div className="flex items-center justify-between font-medium text-slate-700 mb-1">
              <span className="truncate max-w-[180px] flex items-center gap-1.5 text-navy font-semibold">
                <FileCheck className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                {docData.file}
              </span>
              <StatusBadge status={docData.status} />
            </div>
            <div className="text-slate-400 text-[11px] mt-1">
              Uploaded: {docData.uploadTime || "Just now"}
            </div>

            {/* Extracted fields snippet */}
            {docData.extractedData && (
              <div className="mt-2 pt-2 border-t border-slate-200 space-y-1 text-slate-600">
                <div className="font-medium text-[11px] text-teal flex items-center gap-1">
                  <Sparkles className="w-3 h-3" /> Extracted Fields:
                </div>
                {docData.extractedData.fullName && (
                  <div className="flex justify-between text-[11px]">
                    <span className="text-slate-500">Name:</span>
                    <span className="font-semibold text-slate-800">{docData.extractedData.fullName}</span>
                  </div>
                )}
                {docData.extractedData.idNumber && (
                  <div className="flex justify-between text-[11px]">
                    <span className="text-slate-500">ID Number:</span>
                    <span className="font-mono text-slate-800">{docData.extractedData.idNumber}</span>
                  </div>
                )}
                {docData.extractedData.percentage && (
                  <div className="flex justify-between text-[11px]">
                    <span className="text-slate-500">Marks:</span>
                    <span className="font-semibold text-slate-800">{docData.extractedData.percentage}</span>
                  </div>
                )}
                {docData.extractedData.annualIncome && (
                  <div className="flex justify-between text-[11px]">
                    <span className="text-slate-500">Annual Income:</span>
                    <span className="font-semibold text-slate-800">{docData.extractedData.annualIncome}</span>
                  </div>
                )}
                {docData.extractedData.state && (
                  <div className="flex justify-between text-[11px]">
                    <span className="text-slate-500">State:</span>
                    <span className="font-semibold text-slate-800">{docData.extractedData.state}</span>
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          <div className="my-4 p-4 border-2 border-dashed border-slate-200 rounded-lg text-center bg-slate-50/50">
            <p className="text-xs text-slate-500">No file uploaded yet</p>
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="pt-2 flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <label className="flex-1 cursor-pointer flex items-center justify-center gap-1.5 px-3 py-2 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-lg border border-slate-300 transition-colors shadow-sm">
            <Upload className="w-3.5 h-3.5 text-slate-500" />
            <span>{docData ? "Replace File" : "Choose File"}</span>
            <input
              type="file"
              accept=".pdf,.jpg,.jpeg,.png"
              className="hidden"
              onChange={handleFileChange}
              disabled={isUploading}
            />
          </label>

          <button
            type="button"
            onClick={handleDemoClick}
            disabled={isUploading}
            className="flex items-center gap-1 px-3 py-2 bg-seafoam-light hover:bg-seafoam text-navy text-xs font-semibold rounded-lg border border-seafoam transition-colors shadow-sm"
            title="Auto-fill with realistic demo document data"
          >
            <Sparkles className="w-3.5 h-3.5 text-teal" />
            <span>{docData ? "Re-Fill Demo" : "Use Demo Document"}</span>
          </button>
        </div>
      </div>
    </div>
  );
}

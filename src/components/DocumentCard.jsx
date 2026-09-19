import React, { useState } from 'react';
import { FileText, Upload, AlertCircle, FileCheck, Loader2, Eye } from 'lucide-react';
import StatusBadge from './StatusBadge';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';

export default function DocumentCard({
  title,
  required = true,
  docData,
  applicationId,
  onUpload,
  onView
}) {
  const { token } = useAuth();
  const [isUploading, setIsUploading] = useState(false);
  const [isOpening, setIsOpening] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  const MAX_SIZE_BYTES = 2621440; // 2.5 MiB
  const ALLOWED_EXTENSIONS = ['.pdf', '.jpg', '.jpeg', '.png'];

  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setErrorMsg(null);

    // Client-side pre-validation
    if (file.size > MAX_SIZE_BYTES) {
      setErrorMsg("File exceeds the maximum allowed size of 2.5 MB.");
      e.target.value = '';
      return;
    }

    const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setErrorMsg("Invalid file format. Only PDF, JPG, JPEG, and PNG files are allowed.");
      e.target.value = '';
      return;
    }

    setIsUploading(true);
    try {
      await onUpload(file);
    } catch (err) {
      setErrorMsg(err.message || "Failed to upload document.");
    } finally {
      setIsUploading(false);
      e.target.value = '';
    }
  };

  const handleViewDocument = async () => {
    if (!docData) return;
    setErrorMsg(null);

    if (onView) {
      setIsOpening(true);
      try {
        await onView(docData);
      } catch (err) {
        setErrorMsg(err.message || "Unable to open document. Please try again.");
      } finally {
        setIsOpening(false);
      }
      return;
    }

    const appId = docData.application_id || applicationId;
    const docId = docData.id;
    const activeToken = token || localStorage.getItem('vericampus_token');

    if (!appId || !docId || !activeToken) {
      setErrorMsg("Unable to open document. Please try again.");
      return;
    }

    setIsOpening(true);
    try {
      const blob = await api.fetchDocumentBlob(appId, docId, activeToken);
      const objectUrl = URL.createObjectURL(blob);
      window.open(objectUrl, '_blank');
      setTimeout(() => URL.revokeObjectURL(objectUrl), 60000);
    } catch (err) {
      setErrorMsg("Unable to open document. Please try again.");
    } finally {
      setIsOpening(false);
    }
  };

  const filename = docData ? (docData.original_filename || docData.file || "Document File") : null;
  const uploadTime = docData ? (docData.uploaded_at ? new Date(docData.uploaded_at).toLocaleString() : docData.uploadTime || "Uploaded") : null;
  const fileSizeFormatted = docData && docData.file_size ? `${(docData.file_size / (1024 * 1024)).toFixed(2)} MB` : null;

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
              <span className="text-[11px] font-medium text-slate-400">PDF, JPG, PNG (Max 2.5 MB)</span>
            </div>
          </div>
          {required && (
            <span className="px-2 py-0.5 text-[10px] font-bold tracking-wider uppercase bg-rose-50 text-rose-700 rounded border border-rose-200">
              Required
            </span>
          )}
        </div>

        {/* Error alert banner */}
        {errorMsg && (
          <div className="my-2 p-2.5 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Upload Status Details */}
        {docData ? (
          <div className="my-3 p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs">
            <div className="flex items-center justify-between font-medium text-slate-700 mb-1">
              <span className="truncate max-w-[200px] flex items-center gap-1.5 text-navy font-semibold" title={filename}>
                <FileCheck className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                {filename}
              </span>
              <StatusBadge status={docData.upload_status || docData.status || 'UPLOADED'} />
            </div>
            <div className="text-slate-400 text-[11px] mt-1 flex justify-between">
              <span>Uploaded: {uploadTime}</span>
              {fileSizeFormatted && <span>{fileSizeFormatted}</span>}
            </div>
          </div>
        ) : (
          <div className="my-3 p-4 border-2 border-dashed border-slate-200 rounded-lg text-center bg-slate-50/50">
            <p className="text-xs text-slate-500">No file uploaded yet</p>
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="pt-2 flex flex-col gap-2">
        {docData ? (
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleViewDocument}
              disabled={isOpening || isUploading}
              className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-navy hover:bg-navy-light text-white text-xs font-semibold rounded-lg transition-colors shadow-sm ${isOpening || isUploading ? 'opacity-50 pointer-events-none' : ''}`}
            >
              {isOpening ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 text-seafoam animate-spin" />
                  <span>Opening...</span>
                </>
              ) : (
                <>
                  <Eye className="w-3.5 h-3.5 text-seafoam" />
                  <span>View Document</span>
                </>
              )}
            </button>

            <label className={`flex-1 cursor-pointer flex items-center justify-center gap-1.5 px-3 py-2 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-lg border border-slate-300 transition-colors shadow-sm ${isUploading || isOpening ? 'opacity-50 pointer-events-none' : ''}`}>
              {isUploading ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 text-teal animate-spin" />
                  <span>Uploading...</span>
                </>
              ) : (
                <>
                  <Upload className="w-3.5 h-3.5 text-slate-500" />
                  <span>Replace File</span>
                </>
              )}
              <input
                type="file"
                accept=".pdf,.jpg,.jpeg,.png"
                className="hidden"
                onChange={handleFileChange}
                disabled={isUploading || isOpening}
              />
            </label>
          </div>
        ) : (
          <label className={`cursor-pointer flex items-center justify-center gap-1.5 px-3 py-2 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-lg border border-slate-300 transition-colors shadow-sm ${isUploading ? 'opacity-50 pointer-events-none' : ''}`}>
            {isUploading ? (
              <>
                <Loader2 className="w-3.5 h-3.5 text-teal animate-spin" />
                <span>Uploading...</span>
              </>
            ) : (
              <>
                <Upload className="w-3.5 h-3.5 text-slate-500" />
                <span>Choose File</span>
              </>
            )}
            <input
              type="file"
              accept=".pdf,.jpg,.jpeg,.png"
              className="hidden"
              onChange={handleFileChange}
              disabled={isUploading}
            />
          </label>
        )}
      </div>
    </div>
  );
}

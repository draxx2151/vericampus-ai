import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useApplications } from '../../context/ApplicationContext';
import { api } from '../../services/api';
import DocumentCard from '../../components/DocumentCard';
import { UploadCloud, FileCheck, ArrowRight } from 'lucide-react';

export default function DocumentUploadPage() {
  const { token } = useAuth();
  const { myApplication, refreshState } = useApplications();
  const navigate = useNavigate();

  useEffect(() => {
    refreshState();
  }, []);

  const docConfig = [
    { type: 'GOVERNMENT_ID', title: 'Government ID / Aadhaar' },
    { type: 'MARKSHEET', title: '10th / 12th Marksheet' },
    { type: 'INCOME_CERTIFICATE', title: 'Income Certificate' },
    { type: 'DOMICILE_CERTIFICATE', title: 'Domicile Certificate' }
  ];

  const getUploadedDoc = (typeKey) => {
    if (!myApplication || !myApplication.documents) return null;
    return myApplication.documents.find(
      d => d.document_type === typeKey || d.document_type === typeKey.toLowerCase()
    );
  };

  const handleUploadSingle = async (documentType, fileObj) => {
    if (!myApplication) return;
    await api.uploadDocument(myApplication.id, documentType, fileObj, token);
    await refreshState();
  };

  const uploadedCount = myApplication ? (myApplication.documents_uploaded_count || (myApplication.documents ? myApplication.documents.length : 0)) : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-navy flex items-center gap-2">
            <UploadCloud className="w-6 h-6 text-teal" />
            Scholarship Document Upload
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Upload exactly four required documents for eligibility verification (PDF, JPG, PNG — Max 2.5 MB per file)
          </p>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-xs font-semibold text-slate-700">
            {uploadedCount} / 4 Documents Uploaded
          </span>
          <div className="w-32 bg-slate-100 h-2.5 rounded-full overflow-hidden">
            <div
              className="bg-teal h-full transition-all"
              style={{ width: `${(uploadedCount / 4) * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* 4 Required Document Cards */}
      <div className="grid sm:grid-cols-2 gap-6">
        {docConfig.map(({ type, title }) => (
          <DocumentCard
            key={type}
            title={title}
            required={true}
            applicationId={myApplication?.id}
            docData={getUploadedDoc(type)}
            onUpload={(file) => handleUploadSingle(type, file)}
          />
        ))}
      </div>

      {/* Navigation Footer */}
      <div className="bg-navy text-white rounded-2xl p-6 shadow-md flex flex-wrap items-center justify-between gap-4">
        <div>
          <h3 className="font-bold text-base text-white flex items-center gap-2">
            <FileCheck className="w-5 h-5 text-seafoam" />
            Application Overview
          </h3>
          <p className="text-xs text-slate-300 mt-1">
            {uploadedCount === 4
              ? "All 4 required documents have been successfully uploaded to your scholarship profile."
              : `${uploadedCount} of 4 documents uploaded. Please upload all required documents.`}
          </p>
        </div>

        <button
          onClick={() => navigate('/student/dashboard')}
          className="flex items-center gap-2 px-6 py-3 bg-teal hover:bg-teal-hover text-white font-bold text-xs rounded-xl transition-all shadow-md"
        >
          <span>Return to Student Dashboard</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}


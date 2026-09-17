import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useApplications } from '../../context/ApplicationContext';
import { api } from '../../services/api';
import DocumentCard from '../../components/DocumentCard';
import AIProcessingStepper from '../../components/AIProcessingStepper';
import { UploadCloud, Sparkles, ShieldCheck, ArrowRight, CheckCircle2 } from 'lucide-react';

export default function DocumentUploadPage() {
  const { currentUser } = useAuth();
  const { applications, refreshState } = useApplications();
  const [app, setApp] = useState(null);
  const [isProcessingAI, setIsProcessingAI] = useState(false);
  const [uploadingDoc, setUploadingDoc] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    refreshState();
  }, []);

  useEffect(() => {
    if (applications.length > 0 && currentUser) {
      const found = applications.find(a => a.studentId === currentUser.id) || applications[0];
      setApp(found);
    }
  }, [applications, currentUser]);

  if (!app) return <div className="p-8 text-center text-slate-500">Loading...</div>;

  const handleUploadSingle = async (documentType, fileObj) => {
    setUploadingDoc(documentType);
    try {
      await api.uploadDocument(app.id, documentType, fileObj);
      await refreshState();
    } catch (err) {
      console.error(err);
    } finally {
      setUploadingDoc(null);
    }
  };

  const handleUseDemoSingle = async (documentType) => {
    setUploadingDoc(documentType);
    try {
      await api.uploadDocument(app.id, documentType, null);
      await refreshState();
    } catch (err) {
      console.error(err);
    } finally {
      setUploadingDoc(null);
    }
  };

  const handleFillAllDemoDocs = async () => {
    setUploadingDoc("ALL");
    try {
      await api.uploadDocument(app.id, 'Government ID', null);
      await api.uploadDocument(app.id, '10th/12th Marksheet', null);
      await api.uploadDocument(app.id, 'Income Certificate', null);
      await api.uploadDocument(app.id, 'Domicile Certificate', null);
      await refreshState();
    } catch (err) {
      console.error(err);
    } finally {
      setUploadingDoc(null);
    }
  };

  const handleStartAIVerification = () => {
    setIsProcessingAI(true);
  };

  const handleAIComplete = async () => {
    try {
      await api.runAIVerification(app.id);
      await refreshState();
      navigate('/student/verification');
    } catch (err) {
      console.error(err);
      setIsProcessingAI(false);
    }
  };

  const docConfig = [
    { type: 'Government ID', key: 'govId' },
    { type: '10th/12th Marksheet', key: 'marksheet' },
    { type: 'Income Certificate', key: 'incomeCert' },
    { type: 'Domicile Certificate', key: 'domicileCert' }
  ];

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
            Upload exactly four required documents for initial AI field verification & consistency checking
          </p>
        </div>

        <button
          onClick={handleFillAllDemoDocs}
          disabled={uploadingDoc !== null}
          className="flex items-center gap-2 px-4 py-2 bg-seafoam-light hover:bg-seafoam text-navy text-xs font-bold rounded-xl border border-seafoam transition-all shadow-sm"
          title="Fills all 4 required documents instantly for presentation demonstration"
        >
          <Sparkles className="w-4 h-4 text-teal" />
          <span>Fill All 4 Demo Documents</span>
        </button>
      </div>

      {/* AI Processing Stepper Screen */}
      {isProcessingAI ? (
        <AIProcessingStepper onComplete={handleAIComplete} />
      ) : (
        <>
          {/* 4 Required Document Cards */}
          <div className="grid sm:grid-cols-2 gap-6">
            {docConfig.map(({ type, key }) => (
              <DocumentCard
                key={key}
                title={type}
                required={true}
                docData={app.documents[key]}
                onUpload={(file) => handleUploadSingle(type, file)}
                onUseDemo={() => handleUseDemoSingle(type)}
              />
            ))}
          </div>

          {/* Verification Trigger Banner */}
          <div className="bg-navy text-white rounded-2xl p-6 shadow-md flex flex-wrap items-center justify-between gap-4">
            <div>
              <h3 className="font-bold text-base text-white flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-seafoam" />
                Ready for AI Verification Simulation
              </h3>
              <p className="text-xs text-slate-300 mt-1">
                {app.documentsUploadedCount === 4
                  ? "All 4 required documents present. Click below to start initial AI field extraction & cross-document check."
                  : `${app.documentsUploadedCount} of 4 documents uploaded. Click 'Fill All 4 Demo Documents' above to prepare instantly.`}
              </p>
            </div>

            <button
              onClick={handleStartAIVerification}
              className="flex items-center gap-2 px-6 py-3 bg-teal hover:bg-teal-hover text-white font-bold text-sm rounded-xl transition-all shadow-md"
            >
              <span>Start AI Verification</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </>
      )}
    </div>
  );
}

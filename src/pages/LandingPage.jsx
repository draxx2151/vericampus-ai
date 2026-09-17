import React from 'react';
import { Link } from 'react-router-dom';
import { GraduationCap, Building2, Shield, Sparkles, CheckCircle2, ArrowRight } from 'lucide-react';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-between">
      {/* Header Banner */}
      <header className="bg-navy text-white py-6 border-b border-navy-light shadow-md">
        <div className="max-w-6xl mx-auto px-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 bg-teal rounded-xl flex items-center justify-center text-white shadow-md">
              <Shield className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                VeriCampus <span className="text-seafoam font-extrabold">AI</span>
              </h1>
              <p className="text-xs text-slate-300">
                AI-Powered Scholarship Document Verification & Workflow Automation
              </p>
            </div>
          </div>
          <div className="text-xs text-slate-300 font-medium hidden sm:block bg-navy-light px-3 py-1.5 rounded-full border border-slate-700">
            Frontend Prototype Demo
          </div>
        </div>
      </header>

      {/* Main Content Body */}
      <main className="max-w-5xl mx-auto px-4 py-12 flex-1 flex flex-col items-center justify-center">
        {/* Hero Slogan & Subtitle */}
        <div className="text-center max-w-2xl mb-12">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full text-xs font-semibold bg-seafoam-light text-navy border border-seafoam mb-4 shadow-sm">
            <Sparkles className="w-4 h-4 text-teal" />
            <span>Assistance Engine for Scholarship Authorities</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-navy tracking-tight leading-tight mb-3">
            Upload. Verify. Track.
          </h2>
          <p className="text-sm sm:text-base text-slate-600 font-normal">
            Automating scholarship document checking with OCR extractions and cross-document consistency checks, leaving final authority in human admin hands.
          </p>
        </div>

        {/* Dual Role Selector Cards */}
        <div className="grid md:grid-cols-2 gap-8 w-full max-w-4xl">
          {/* STUDENT ROLE CARD */}
          <div className="bg-white rounded-2xl border-2 border-slate-200 hover:border-teal p-8 shadow-md hover:shadow-xl transition-all flex flex-col justify-between group">
            <div>
              <div className="w-14 h-14 rounded-2xl bg-teal/10 text-teal flex items-center justify-center mb-6 group-hover:scale-105 transition-transform">
                <GraduationCap className="w-8 h-8" />
              </div>
              <h3 className="text-2xl font-bold text-navy mb-2 flex items-center gap-2">
                🎓 STUDENT PORTAL
              </h3>
              <p className="text-sm text-slate-600 mb-6 leading-relaxed">
                Upload your required 4 scholarship documents, simulate AI verification in real-time, and track your application status or physical appointment details.
              </p>

              <div className="space-y-2 mb-8 text-xs text-slate-500 border-t border-slate-100 pt-4">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                  <span>Upload 4 Core Scholarship Documents</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                  <span>Simulate instant AI verification flow</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                  <span>View physical verification appointments</span>
                </div>
              </div>
            </div>

            <Link
              to="/student-login"
              className="w-full py-3.5 px-6 rounded-xl bg-teal hover:bg-teal-hover text-white font-bold text-sm flex items-center justify-center gap-2 shadow-md hover:shadow transition-all"
            >
              <span>Student Login</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>

          {/* ADMIN ROLE CARD */}
          <div className="bg-white rounded-2xl border-2 border-slate-200 hover:border-navy p-8 shadow-md hover:shadow-xl transition-all flex flex-col justify-between group">
            <div>
              <div className="w-14 h-14 rounded-2xl bg-navy/10 text-navy flex items-center justify-center mb-6 group-hover:scale-105 transition-transform">
                <Building2 className="w-8 h-8" />
              </div>
              <h3 className="text-2xl font-bold text-navy mb-2 flex items-center gap-2">
                👨‍💼 ADMIN PORTAL
              </h3>
              <p className="text-sm text-slate-600 mb-6 leading-relaxed">
                Review AI-assisted verification reports, audit OCR field extractions, handle flagged inconsistencies, and schedule physical document verification meetings.
              </p>

              <div className="space-y-2 mb-8 text-xs text-slate-500 border-t border-slate-100 pt-4">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                  <span>Review AI document OCR field findings</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                  <span>Inspect cross-document name mismatches</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                  <span>Schedule physical verification appointments</span>
                </div>
              </div>
            </div>

            <Link
              to="/admin-login"
              className="w-full py-3.5 px-6 rounded-xl bg-navy hover:bg-navy-light text-white font-bold text-sm flex items-center justify-center gap-2 shadow-md hover:shadow transition-all"
            >
              <span>Admin Login</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>

        {/* Workflow Summary Pill */}
        <div className="mt-12 bg-white rounded-xl p-4 border border-slate-200 text-xs text-slate-600 flex flex-wrap items-center justify-center gap-3 text-center max-w-3xl">
          <span className="font-semibold text-navy">Workflow:</span>
          <span>1. Upload 4 Documents</span>
          <span className="text-slate-300">→</span>
          <span>2. AI Extraction & Flagging</span>
          <span className="text-slate-300">→</span>
          <span>3. Admin Review & Decision</span>
          <span className="text-slate-300">→</span>
          <span>4. Scheduled Meeting (If required)</span>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-4 text-center text-xs text-slate-500">
        <p>VeriCampus AI — Assistive Scholarship Verification & Workflow Automation Prototype</p>
      </footer>
    </div>
  );
}

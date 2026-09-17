import React, { useState, useEffect } from 'react';
import { CheckCircle2, Loader2, Sparkles, ShieldAlert, Cpu } from 'lucide-react';

const STEPS = [
  { id: 1, label: "Reading uploaded document files & OCR parsing" },
  { id: 2, label: "Extracting key fields (Name, DOB, ID, Income, State)" },
  { id: 3, label: "Checking mandatory field completeness" },
  { id: 4, label: "Comparing information consistency across documents" },
  { id: 5, label: "Evaluating scholarship eligibility & threshold rules" },
  { id: 6, label: "Generating prototype AI verification report" }
];

export default function AIProcessingStepper({ onComplete }) {
  const [currentStep, setCurrentStep] = useState(1);
  const [isFinished, setIsFinished] = useState(false);

  useEffect(() => {
    if (currentStep <= STEPS.length) {
      const timer = setTimeout(() => {
        setCurrentStep(prev => prev + 1);
      }, 400); // Progress every 400ms
      return () => clearTimeout(timer);
    } else {
      setIsFinished(true);
      const finishTimer = setTimeout(() => {
        if (onComplete) onComplete();
      }, 500);
      return () => clearTimeout(finishTimer);
    }
  }, [currentStep, onComplete]);

  return (
    <div className="bg-white rounded-xl border border-teal/30 p-6 shadow-md max-w-xl mx-auto my-6">
      <div className="flex items-center gap-3 mb-6 pb-4 border-b border-slate-100">
        <div className="w-10 h-10 rounded-lg bg-navy text-seafoam flex items-center justify-center">
          <Cpu className="w-6 h-6 animate-pulse" />
        </div>
        <div>
          <h3 className="text-lg font-bold text-navy flex items-center gap-2">
            VeriCampus AI Verification Engine
            <span className="text-xs font-normal text-teal bg-teal/10 px-2 py-0.5 rounded border border-teal/20">
              Assisting Verification
            </span>
          </h3>
          <p className="text-xs text-slate-500">
            Running OCR extraction, cross-field validation, and rule checking...
          </p>
        </div>
      </div>

      <div className="space-y-4">
        {STEPS.map((step) => {
          const isDone = currentStep > step.id;
          const isCurrent = currentStep === step.id;

          return (
            <div key={step.id} className="flex items-center gap-3 text-sm">
              <div className="flex-shrink-0">
                {isDone ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                ) : isCurrent ? (
                  <Loader2 className="w-5 h-5 text-teal animate-spin" />
                ) : (
                  <div className="w-5 h-5 rounded-full border-2 border-slate-200 flex items-center justify-center text-[10px] font-bold text-slate-400">
                    {step.id}
                  </div>
                )}
              </div>
              <span className={`font-medium ${
                isDone ? 'text-slate-800' : isCurrent ? 'text-teal font-semibold' : 'text-slate-400'
              }`}>
                {step.label}
              </span>
            </div>
          );
        })}
      </div>

      {/* Progress Bar */}
      <div className="mt-6 pt-4 border-t border-slate-100">
        <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
          <div
            className="bg-teal h-full transition-all duration-300 ease-out"
            style={{ width: `${Math.min(100, Math.round(((currentStep - 1) / STEPS.length) * 100))}%` }}
          />
        </div>
        <div className="flex justify-between text-xs text-slate-400 mt-2">
          <span>Processing Step {Math.min(STEPS.length, currentStep)} of {STEPS.length}</span>
          <span>{Math.min(100, Math.round(((currentStep - 1) / STEPS.length) * 100))}% Complete</span>
        </div>
      </div>
    </div>
  );
}

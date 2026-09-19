import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useApplications } from '../../context/ApplicationContext';
import { api } from '../../services/api';
import { GraduationCap, ArrowLeft, CheckCircle, ShieldCheck, AlertCircle, ArrowRight } from 'lucide-react';

export default function SelectScholarshipPage() {
  const { token } = useAuth();
  const { myApplication, refreshState } = useApplications();
  const [schemes, setSchemes] = useState([]);
  const [selectedScheme, setSelectedScheme] = useState('');
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    // If student already has an application, redirect to dashboard immediately (1-app rule)
    if (myApplication) {
      navigate('/student/dashboard');
      return;
    }
    loadSchemes();
  }, [myApplication]);

  const loadSchemes = async () => {
    setFetching(true);
    try {
      const data = await api.getScholarshipSchemes();
      setSchemes(data);
      if (data.length > 0) {
        setSelectedScheme(data[0]);
      }
    } catch (err) {
      console.error(err);
      setError("Failed to load official scholarship schemes.");
    } finally {
      setFetching(false);
    }
  };

  const handleCreateApplication = async (e) => {
    e.preventDefault();
    if (!selectedScheme) return;
    setLoading(true);
    setError(null);

    try {
      const savedToken = token || localStorage.getItem('vericampus_token');
      await api.createApplication(selectedScheme, savedToken);
      await refreshState();
      navigate('/student/dashboard');
    } catch (err) {
      console.error(err);
      setError(err.message || "Failed to create application. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <Link to="/student/dashboard" className="inline-flex items-center text-xs font-semibold text-teal hover:underline">
        <ArrowLeft className="w-4 h-4 mr-1" /> Back to Student Dashboard
      </Link>

      <div className="bg-navy text-white rounded-2xl p-6 sm:p-8 shadow-md">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2.5 bg-teal text-white rounded-xl">
            <GraduationCap className="w-6 h-6" />
          </div>
          <div>
            <span className="text-xs font-semibold uppercase tracking-wider text-seafoam">MahaDBT Official Schemes</span>
            <h2 className="text-2xl font-bold">Select Scholarship Program</h2>
          </div>
        </div>
        <p className="text-xs text-slate-300 max-w-2xl mt-1">
          Select your applicable scholarship scheme to initiate your VeriCampus AI document verification application. You may apply for exactly one scheme per student account.
        </p>
      </div>

      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl flex items-start gap-2.5 text-xs text-rose-800">
          <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {fetching ? (
        <div className="p-12 text-center text-slate-500 text-xs">
          Loading official scholarship schemes from server...
        </div>
      ) : (
        <form onSubmit={handleCreateApplication} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {schemes.map((scheme, idx) => {
              const isSelected = selectedScheme === scheme;
              return (
                <div
                  key={idx}
                  onClick={() => setSelectedScheme(scheme)}
                  className={`p-5 rounded-2xl border cursor-pointer transition-all flex flex-col justify-between ${
                    isSelected
                      ? 'bg-teal-50/70 border-2 border-teal shadow-md'
                      : 'bg-white border-slate-200 hover:border-slate-300 shadow-sm'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3">
                      <div className={`mt-0.5 w-5 h-5 rounded-full border flex items-center justify-center flex-shrink-0 ${
                        isSelected ? 'border-teal bg-teal text-white' : 'border-slate-300 bg-white'
                      }`}>
                        {isSelected && <CheckCircle className="w-3.5 h-3.5" />}
                      </div>
                      <div>
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-0.5">
                          Scheme #{idx + 1}
                        </span>
                        <h4 className="text-sm font-bold text-navy leading-snug">
                          {scheme}
                        </h4>
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
                    <span>Department of Higher / Technical Education</span>
                    <span className="font-semibold text-teal">Verification Ready</span>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="pt-4 flex justify-end">
            <button
              type="submit"
              disabled={loading || !selectedScheme}
              className="flex items-center gap-2 px-8 py-3 bg-teal hover:bg-teal-hover text-white font-bold text-sm rounded-xl shadow-md transition-colors disabled:opacity-50"
            >
              <span>{loading ? "Creating Application..." : "Confirm & Create Application"}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

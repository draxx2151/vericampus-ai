import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { DEMO_USERS } from '../data/mockData';
import { GraduationCap, ArrowLeft, Sparkles, Lock, Mail } from 'lucide-react';

export default function StudentLogin() {
  const [email, setEmail] = useState('amit.patil@example.edu');
  const [password, setPassword] = useState('password123');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await api.login('STUDENT', email, password);
      login('STUDENT', res.user);
      navigate('/student/dashboard');
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleQuickDemoLogin = async (studentUser) => {
    setLoading(true);
    try {
      const res = await api.login('STUDENT', studentUser.email, 'password123');
      login('STUDENT', res.user);
      navigate('/student/dashboard');
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <Link to="/" className="inline-flex items-center text-xs font-semibold text-teal hover:underline mb-4">
          <ArrowLeft className="w-4 h-4 mr-1" /> Back to Role Selection
        </Link>

        <div className="flex justify-center">
          <div className="w-12 h-12 rounded-xl bg-teal text-white flex items-center justify-center shadow-md">
            <GraduationCap className="w-7 h-7" />
          </div>
        </div>
        <h2 className="mt-4 text-center text-2xl font-bold tracking-tight text-navy">
          Student Portal Login
        </h2>
        <p className="mt-1 text-center text-xs text-slate-500">
          Upload scholarship documents and track verification status
        </p>
      </div>

      <div className="mt-6 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow-md sm:rounded-xl border border-slate-200 sm:px-10">
          <form className="space-y-4" onSubmit={handleLoginSubmit}>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Student Email / ID
              </label>
              <div className="relative">
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="w-full pl-10 pr-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-teal focus:border-teal outline-none"
                  placeholder="student@example.edu"
                />
                <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Password
              </label>
              <div className="relative">
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="w-full pl-10 pr-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-teal focus:border-teal outline-none"
                  placeholder="••••••••"
                />
                <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 px-4 bg-teal hover:bg-teal-hover text-white font-bold text-sm rounded-lg transition-colors shadow-sm"
            >
              {loading ? "Logging in..." : "Login as Student"}
            </button>
          </form>

          {/* QUICK DEMO LOGIN BUTTONS */}
          <div className="mt-6 pt-6 border-t border-slate-200">
            <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-1">
              <Sparkles className="w-3.5 h-3.5 text-teal" /> Instant Demo Logins:
            </div>
            
            <div className="space-y-2">
              <button
                type="button"
                onClick={() => handleQuickDemoLogin(DEMO_USERS.students[0])} // Amit Patil
                className="w-full py-2 px-3 text-xs font-semibold bg-amber-50 hover:bg-amber-100 text-amber-900 border border-amber-200 rounded-lg transition-colors flex items-center justify-between"
              >
                <span>Demo 1: Amit Patil (Needs Review / Mismatch Flow)</span>
                <span className="text-[10px] bg-amber-200 text-amber-900 px-1.5 py-0.5 rounded font-mono">Main Demo</span>
              </button>

              <button
                type="button"
                onClick={() => handleQuickDemoLogin(DEMO_USERS.students[1])} // Rahul Sharma
                className="w-full py-2 px-3 text-xs font-semibold bg-emerald-50 hover:bg-emerald-100 text-emerald-900 border border-emerald-200 rounded-lg transition-colors flex items-center justify-between"
              >
                <span>Demo 2: Rahul Sharma (Verified Flow)</span>
                <span className="text-[10px] bg-emerald-200 text-emerald-900 px-1.5 py-0.5 rounded font-mono">Verified</span>
              </button>

              <button
                type="button"
                onClick={() => handleQuickDemoLogin(DEMO_USERS.students[2])} // Sneha Kulkarni
                className="w-full py-2 px-3 text-xs font-semibold bg-teal-50 hover:bg-teal-100 text-teal-900 border border-teal-200 rounded-lg transition-colors flex items-center justify-between"
              >
                <span>Demo 3: Sneha Kulkarni (Meeting Scheduled)</span>
                <span className="text-[10px] bg-teal-200 text-teal-900 px-1.5 py-0.5 rounded font-mono">Scheduled</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

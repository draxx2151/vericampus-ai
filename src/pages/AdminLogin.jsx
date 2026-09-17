import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { DEMO_USERS } from '../data/mockData';
import { Building2, ArrowLeft, Sparkles, Lock, Mail, ShieldCheck } from 'lucide-react';

export default function AdminLogin() {
  const [email, setEmail] = useState('admin@vericampus.edu');
  const [password, setPassword] = useState('admin123');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await api.login('ADMIN', email, password);
      login('ADMIN', res.user);
      navigate('/admin/dashboard');
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleQuickDemoLogin = async () => {
    setLoading(true);
    try {
      const res = await api.login('ADMIN', DEMO_USERS.admin.email, 'admin123');
      login('ADMIN', res.user);
      navigate('/admin/dashboard');
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <Link to="/" className="inline-flex items-center text-xs font-semibold text-navy hover:underline mb-4">
          <ArrowLeft className="w-4 h-4 mr-1" /> Back to Role Selection
        </Link>

        <div className="flex justify-center">
          <div className="w-12 h-12 rounded-xl bg-navy text-seafoam flex items-center justify-center shadow-md">
            <Building2 className="w-7 h-7" />
          </div>
        </div>
        <h2 className="mt-4 text-center text-2xl font-bold tracking-tight text-navy">
          Admin Verification Portal
        </h2>
        <p className="mt-1 text-center text-xs text-slate-500">
          Review AI-assisted document verification and manage physical appointments
        </p>
      </div>

      <div className="mt-6 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow-md sm:rounded-xl border border-slate-200 sm:px-10">
          <form className="space-y-4" onSubmit={handleLoginSubmit}>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Admin Officer Email / ID
              </label>
              <div className="relative">
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="w-full pl-10 pr-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-navy focus:border-navy outline-none"
                  placeholder="admin@vericampus.edu"
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
                  className="w-full pl-10 pr-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-navy focus:border-navy outline-none"
                  placeholder="••••••••"
                />
                <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 px-4 bg-navy hover:bg-navy-light text-white font-bold text-sm rounded-lg transition-colors shadow-sm"
            >
              {loading ? "Authenticating..." : "Login as Administrator"}
            </button>
          </form>

          {/* QUICK DEMO LOGIN BUTTON */}
          <div className="mt-6 pt-6 border-t border-slate-200">
            <button
              type="button"
              onClick={handleQuickDemoLogin}
              className="w-full py-2.5 px-3 text-xs font-semibold bg-navy-light text-white hover:bg-slate-700 rounded-lg transition-colors flex items-center justify-center gap-2 shadow-sm"
            >
              <ShieldCheck className="w-4 h-4 text-seafoam" />
              <span>Demo Login as Admin (Dr. V. K. Deshmukh)</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

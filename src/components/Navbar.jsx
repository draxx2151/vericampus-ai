import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Shield, User, LogOut, GraduationCap, Building2, Bell } from 'lucide-react';

export default function Navbar() {
  const { currentUser, logout, role } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <header className="bg-navy text-white shadow-md sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Logo & Platform Name */}
        <Link to="/" className="flex items-center gap-3 group">
          <div className="w-10 h-10 rounded-lg bg-teal flex items-center justify-center text-white shadow-sm group-hover:bg-teal-hover transition-colors">
            <Shield className="w-6 h-6" />
          </div>
          <div>
            <div className="font-bold text-lg leading-tight text-white flex items-center gap-2">
              VeriCampus <span className="text-seafoam font-extrabold">AI</span>
            </div>
            <div className="text-xs text-slate-300 font-normal">
              Scholarship Verification & Workflow Automation
            </div>
          </div>
        </Link>

        {/* User Role & Navigation Controls */}
        <div className="flex items-center gap-4">
          {currentUser ? (
            <div className="flex items-center gap-3">
              <span className={`inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold ${
                role === 'ADMIN' ? 'bg-amber-400 text-navy' : 'bg-seafoam text-navy'
              }`}>
                {role === 'ADMIN' ? (
                  <Building2 className="w-3.5 h-3.5 mr-1" />
                ) : (
                  <GraduationCap className="w-3.5 h-3.5 mr-1" />
                )}
                {role === 'ADMIN' ? 'ADMINISTRATOR' : 'STUDENT'}
              </span>

              <div className="hidden sm:block text-right">
                <div className="text-sm font-medium text-white">{currentUser.name}</div>
                <div className="text-xs text-slate-300">{currentUser.email}</div>
              </div>

              <button
                onClick={handleLogout}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium text-slate-200 bg-navy-light hover:bg-slate-700 hover:text-white transition-colors border border-slate-700"
                title="Logout to landing page"
              >
                <LogOut className="w-4 h-4" />
                <span>Logout</span>
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Link
                to="/student-login"
                className="px-3.5 py-1.5 rounded-md text-xs font-semibold text-white bg-teal hover:bg-teal-hover transition-colors shadow-sm"
              >
                Student Portal
              </Link>
              <Link
                to="/admin-login"
                className="px-3.5 py-1.5 rounded-md text-xs font-semibold text-slate-200 bg-navy-light border border-slate-600 hover:bg-slate-700 hover:text-white transition-colors"
              >
                Admin Portal
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

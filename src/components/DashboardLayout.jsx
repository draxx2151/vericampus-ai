import React from 'react';
import { Outlet, Navigate } from 'react-router-dom';
import Navbar from './Navbar';
import Sidebar from './Sidebar';
import { useAuth } from '../context/AuthContext';

export default function DashboardLayout({ requiredRole }) {
  const { currentUser, role } = useAuth();

  if (!currentUser) {
    return <Navigate to={requiredRole === 'ADMIN' ? '/admin-login' : '/student-login'} replace />;
  }

  if (requiredRole && role !== requiredRole) {
    return <Navigate to={role === 'ADMIN' ? '/admin/dashboard' : '/student/dashboard'} replace />;
  }

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <Navbar />
      <div className="flex-1 flex max-w-7xl w-full mx-auto">
        <Sidebar />
        <main className="flex-1 p-6 md:p-8 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

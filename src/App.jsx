import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';

// Public pages
import LandingPage from './pages/LandingPage';
import StudentLogin from './pages/StudentLogin';
import StudentRegister from './pages/StudentRegister';
import AdminLogin from './pages/AdminLogin';
import AdminRegister from './pages/AdminRegister';

// Layout
import DashboardLayout from './components/DashboardLayout';

// Student Pages
import StudentDashboard from './pages/student/StudentDashboard';
import SelectScholarshipPage from './pages/student/SelectScholarshipPage';
import DocumentUploadPage from './pages/student/DocumentUploadPage';
import VerificationResultPage from './pages/student/VerificationResultPage';
import StudentAppointmentPage from './pages/student/StudentAppointmentPage';
import StudentNotificationsPage from './pages/student/StudentNotificationsPage';

// Admin Pages
import AdminDashboard from './pages/admin/AdminDashboard';
import ApplicationsListPage from './pages/admin/ApplicationsListPage';
import ApplicationDetailPage from './pages/admin/ApplicationDetailPage';
import AdminAppointmentsPage from './pages/admin/AdminAppointmentsPage';
import AdminNotificationsPage from './pages/admin/AdminNotificationsPage';

export default function App() {
  return (
    <Routes>
      {/* 1. Landing / Entry Page (Role Selection ONLY) */}
      <Route path="/" element={<LandingPage />} />
      <Route path="/student-login" element={<StudentLogin />} />
      <Route path="/student-register" element={<StudentRegister />} />
      <Route path="/admin-login" element={<AdminLogin />} />
      <Route path="/admin-register" element={<AdminRegister />} />

      {/* 2. Protected Student Dashboard Routes */}
      <Route element={<DashboardLayout requiredRole="STUDENT" />}>
        <Route path="/student/dashboard" element={<StudentDashboard />} />
        <Route path="/student/select-scholarship" element={<SelectScholarshipPage />} />
        <Route path="/student/documents" element={<DocumentUploadPage />} />
        <Route path="/student/verification" element={<VerificationResultPage />} />
        <Route path="/student/appointment" element={<StudentAppointmentPage />} />
        <Route path="/student/notifications" element={<StudentNotificationsPage />} />
      </Route>

      {/* 3. Protected Admin Dashboard Routes */}
      <Route element={<DashboardLayout requiredRole="ADMIN" />}>
        <Route path="/admin/dashboard" element={<AdminDashboard />} />
        <Route path="/admin/applications" element={<ApplicationsListPage />} />
        <Route path="/admin/applications/:id" element={<ApplicationDetailPage />} />
        <Route path="/admin/appointments" element={<AdminAppointmentsPage />} />
        <Route path="/admin/notifications" element={<AdminNotificationsPage />} />
      </Route>

      {/* Fallback route */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

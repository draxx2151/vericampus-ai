import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { api } from '../services/api';
import { GraduationCap, ArrowLeft, CheckCircle2, AlertCircle, Lock, Mail, User, Phone, MapPin, Calendar, Building, FileText } from 'lucide-react';

export default function StudentRegister() {
  const [formData, setFormData] = useState({
    college_code: '',
    full_name: '',
    email: '',
    password: '',
    phone_number: '',
    government_id_number: '',
    date_of_birth: '',
    address: ''
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successData, setSuccessData] = useState(null);
  const navigate = useNavigate();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (error) setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const res = await api.registerStudent(formData);
      setSuccessData(res.student);
    } catch (err) {
      setError(err.message || 'Registration failed. Please check your details.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-10 px-4 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-lg">
        <Link to="/student-login" className="inline-flex items-center text-xs font-semibold text-teal hover:underline mb-4">
          <ArrowLeft className="w-4 h-4 mr-1" /> Back to Student Login
        </Link>

        <div className="flex justify-center">
          <div className="w-12 h-12 rounded-xl bg-teal text-white flex items-center justify-center shadow-md">
            <GraduationCap className="w-7 h-7" />
          </div>
        </div>
        <h2 className="mt-4 text-center text-2xl font-bold tracking-tight text-navy">
          Create Student Account
        </h2>
        <p className="mt-1 text-center text-xs text-slate-500">
          Register to apply for scholarships and track document verification
        </p>
      </div>

      <div className="mt-6 sm:mx-auto sm:w-full sm:max-w-lg">
        <div className="bg-white py-8 px-4 shadow-md sm:rounded-xl border border-slate-200 sm:px-10">
          {successData ? (
            <div className="text-center py-4">
              <div className="w-16 h-16 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto mb-4">
                <CheckCircle2 className="w-10 h-10" />
              </div>
              <h3 className="text-lg font-bold text-navy mb-2">Registration Successful!</h3>
              <p className="text-xs text-slate-600 mb-6 max-w-sm mx-auto">
                Welcome, <span className="font-semibold text-navy">{successData.full_name}</span>. Your student account has been registered under your college. Please log in with your email and password to access the portal.
              </p>
              <div className="bg-slate-50 rounded-lg p-3 text-left mb-6 text-xs text-slate-700 space-y-1 border border-slate-200">
                <p><span className="font-semibold text-slate-500">Email:</span> {successData.email}</p>
                <p><span className="font-semibold text-slate-500">Student ID:</span> {successData.id}</p>
                <p><span className="font-semibold text-slate-500">College ID:</span> {successData.college_id}</p>
              </div>
              <button
                onClick={() => navigate('/student-login')}
                className="w-full py-2.5 px-4 bg-teal hover:bg-teal-hover text-white font-bold text-sm rounded-lg transition-colors shadow-sm"
              >
                Proceed to Student Login
              </button>
            </div>
          ) : (
            <form className="space-y-4" onSubmit={handleSubmit}>
              {error && (
                <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg flex items-start gap-2 text-xs text-rose-800">
                  <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
                  <span>{error}</span>
                </div>
              )}

              {/* College Code */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  College Code <span className="text-rose-500">*</span>
                </label>
                <div className="relative">
                  <input
                    type="text"
                    name="college_code"
                    value={formData.college_code}
                    onChange={handleChange}
                    required
                    className="w-full pl-10 pr-3 py-2 border border-slate-300 rounded-lg text-sm uppercase font-mono tracking-wider focus:ring-2 focus:ring-teal focus:border-teal outline-none"
                    placeholder="e.g. COLLEGE001"
                  />
                  <Building className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                </div>
              </div>

              {/* Full Name & Email */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                    Full Name <span className="text-rose-500">*</span>
                  </label>
                  <div className="relative">
                    <input
                      type="text"
                      name="full_name"
                      value={formData.full_name}
                      onChange={handleChange}
                      required
                      className="w-full pl-10 pr-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-teal focus:border-teal outline-none"
                      placeholder="e.g. Jaysh Telgote"
                    />
                    <User className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                    Email Address <span className="text-rose-500">*</span>
                  </label>
                  <div className="relative">
                    <input
                      type="email"
                      name="email"
                      value={formData.email}
                      onChange={handleChange}
                      required
                      className="w-full pl-10 pr-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-teal focus:border-teal outline-none"
                      placeholder="student@example.edu"
                    />
                    <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                  </div>
                </div>
              </div>

              {/* Password & Phone */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                    Password <span className="text-rose-500">*</span>
                  </label>
                  <div className="relative">
                    <input
                      type="password"
                      name="password"
                      value={formData.password}
                      onChange={handleChange}
                      required
                      className="w-full pl-10 pr-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-teal focus:border-teal outline-none"
                      placeholder="••••••••"
                    />
                    <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                    Phone Number
                  </label>
                  <div className="relative">
                    <input
                      type="tel"
                      name="phone_number"
                      value={formData.phone_number}
                      onChange={handleChange}
                      className="w-full pl-10 pr-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-teal focus:border-teal outline-none"
                      placeholder="+91 98765 43210"
                    />
                    <Phone className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                  </div>
                </div>
              </div>

              {/* Government ID & Date of Birth */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                    Government ID (Aadhaar)
                  </label>
                  <div className="relative">
                    <input
                      type="text"
                      name="government_id_number"
                      value={formData.government_id_number}
                      onChange={handleChange}
                      className="w-full pl-10 pr-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-teal focus:border-teal outline-none"
                      placeholder="XXXX-XXXX-1234"
                    />
                    <FileText className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                    Date of Birth
                  </label>
                  <div className="relative">
                    <input
                      type="date"
                      name="date_of_birth"
                      value={formData.date_of_birth}
                      onChange={handleChange}
                      className="w-full pl-10 pr-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-teal focus:border-teal outline-none"
                    />
                    <Calendar className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                  </div>
                </div>
              </div>

              {/* Address */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Residential Address
                </label>
                <div className="relative">
                  <input
                    type="text"
                    name="address"
                    value={formData.address}
                    onChange={handleChange}
                    className="w-full pl-10 pr-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-teal focus:border-teal outline-none"
                    placeholder="City, State"
                  />
                  <MapPin className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                </div>
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-2.5 px-4 bg-teal hover:bg-teal-hover text-white font-bold text-sm rounded-lg transition-colors shadow-sm disabled:opacity-50"
                >
                  {loading ? "Registering Account..." : "Create Account"}
                </button>
              </div>

              <div className="text-center pt-2">
                <p className="text-xs text-slate-500">
                  Already have an account?{' '}
                  <Link to="/student-login" className="font-semibold text-teal hover:underline">
                    Login here
                  </Link>
                </p>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}

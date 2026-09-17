import React, { useState } from 'react';
import { Calendar, Clock, MapPin, FileCheck, X, Check } from 'lucide-react';

export default function MeetingSchedulerModal({ isOpen, onClose, onSchedule, studentName, applicationId }) {
  const [date, setDate] = useState('2026-09-25');
  const [time, setTime] = useState('11:30 AM');
  const [venue, setVenue] = useState('Administrative Block, Room 204, VeriCampus Main Campus');
  const [purpose, setPurpose] = useState('Physical Document Verification & Original Signature Check');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setTimeout(() => {
      onSchedule({ date, time, venue, purpose });
      setIsSubmitting(false);
      onClose();
    }, 400);
  };

  return (
    <div className="fixed inset-0 z-50 bg-navy/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full border border-slate-200 overflow-hidden animate-in fade-in zoom-in duration-150">
        {/* Header */}
        <div className="bg-navy text-white p-5 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-teal rounded-lg">
              <Calendar className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="font-bold text-base">Schedule Physical Verification</h3>
              <p className="text-xs text-slate-300">Application ID: {applicationId} ({studentName})</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-300 hover:text-white p-1 rounded-lg hover:bg-slate-700 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Select Appointment Date
            </label>
            <div className="relative">
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                required
                className="w-full pl-10 pr-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-800 focus:ring-2 focus:ring-teal focus:border-teal outline-none"
              />
              <Calendar className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Select Appointment Time
            </label>
            <div className="relative">
              <select
                value={time}
                onChange={(e) => setTime(e.target.value)}
                className="w-full pl-10 pr-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-800 focus:ring-2 focus:ring-teal focus:border-teal outline-none"
              >
                <option value="09:30 AM">09:30 AM</option>
                <option value="10:30 AM">10:30 AM</option>
                <option value="11:30 AM">11:30 AM</option>
                <option value="02:00 PM">02:00 PM</option>
                <option value="03:30 PM">03:30 PM</option>
              </select>
              <Clock className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Meeting Venue / Office Location
            </label>
            <div className="relative">
              <input
                type="text"
                value={venue}
                onChange={(e) => setVenue(e.target.value)}
                required
                className="w-full pl-10 pr-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-800 focus:ring-2 focus:ring-teal focus:border-teal outline-none"
              />
              <MapPin className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Verification Purpose / Instructions
            </label>
            <div className="relative">
              <textarea
                value={purpose}
                onChange={(e) => setPurpose(e.target.value)}
                rows={2}
                required
                className="w-full pl-10 pr-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-800 focus:ring-2 focus:ring-teal focus:border-teal outline-none resize-none"
              />
              <FileCheck className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
            </div>
          </div>

          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-900">
            <strong>Note:</strong> Scheduling this meeting will automatically update the student's dashboard and trigger a notification for physical document verification.
          </div>

          <div className="pt-3 flex items-center justify-end gap-3 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-teal hover:bg-teal-hover rounded-lg transition-colors shadow-sm"
            >
              <Check className="w-4 h-4" />
              <span>{isSubmitting ? "Scheduling..." : "Schedule Meeting"}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

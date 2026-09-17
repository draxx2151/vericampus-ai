import React from 'react';

export default function DashboardCard({ title, value, subtitle, icon: Icon, color = "teal" }) {
  const colorMap = {
    teal: "bg-teal/10 text-teal border-teal/20",
    amber: "bg-amber-500/10 text-amber-700 border-amber-500/20",
    emerald: "bg-emerald-500/10 text-emerald-700 border-emerald-500/20",
    navy: "bg-navy/10 text-navy border-navy/20",
    rose: "bg-rose-500/10 text-rose-700 border-rose-500/20"
  };

  return (
    <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm hover:shadow transition-shadow flex items-start justify-between">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">{title}</p>
        <h3 className="text-2xl font-bold text-slate-900 leading-tight">{value}</h3>
        {subtitle && <p className="text-xs text-slate-500 mt-1">{subtitle}</p>}
      </div>
      {Icon && (
        <div className={`p-3 rounded-lg border ${colorMap[color] || colorMap.teal}`}>
          <Icon className="w-6 h-6" />
        </div>
      )}
    </div>
  );
}

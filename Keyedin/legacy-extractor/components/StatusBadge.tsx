import React from 'react';
import clsx from 'clsx';

interface StatusBadgeProps {
  status: 'success' | 'warning' | 'error' | 'neutral' | 'pending';
  label: string;
  pulse?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, label, pulse = false }) => {
  const colors = {
    success: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    warning: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    error: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
    neutral: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
    pending: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  };

  const dots = {
    success: 'bg-emerald-400',
    warning: 'bg-amber-400',
    error: 'bg-rose-400',
    neutral: 'bg-slate-400',
    pending: 'bg-blue-400',
  };

  return (
    <div className={clsx(
      'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border',
      colors[status]
    )}>
      <span className={clsx(
        'w-1.5 h-1.5 rounded-full mr-2',
        dots[status],
        pulse && 'animate-pulse'
      )} />
      {label}
    </div>
  );
};
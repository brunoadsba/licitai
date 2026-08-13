'use client';

import type { ReactNode } from 'react';

type AlertVariant = 'error' | 'warning' | 'info' | 'success';

interface AlertBannerProps {
  variant: AlertVariant;
  title: string;
  children?: ReactNode;
  action?: ReactNode;
  className?: string;
}

const VARIANT_CONFIG: Record<
  AlertVariant,
  { border: string; text: string; icon: string; iconPath: string }
> = {
  error: {
    border: 'border-red-500/20',
    text: 'text-red-400',
    icon: 'text-red-400',
    iconPath:
      'M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z',
  },
  warning: {
    border: 'border-yellow-500/20',
    text: 'text-yellow-400',
    icon: 'text-yellow-400',
    iconPath:
      'M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z',
  },
  info: {
    border: 'border-blue-500/20',
    text: 'text-blue-400',
    icon: 'text-blue-400',
    iconPath:
      'M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z',
  },
  success: {
    border: 'border-green-500/20',
    text: 'text-green-400',
    icon: 'text-green-400',
    iconPath:
      'M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
  },
};

export default function AlertBanner({
  variant,
  title,
  children,
  action,
  className = '',
}: AlertBannerProps) {
  const config = VARIANT_CONFIG[variant];
  const role = variant === 'error' || variant === 'warning' ? 'alert' : 'status';

  return (
    <div
      role={role}
      className={`glass-card p-4 flex items-start gap-3 ${config.border} ${className}`}
    >
      <svg
        className={`w-5 h-5 shrink-0 mt-0.5 ${config.icon}`}
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={1.5}
        aria-hidden="true"
      >
        <path strokeLinecap="round" strokeLinejoin="round" d={config.iconPath} />
      </svg>
      <div className="min-w-0 flex-1">
        <p className={`text-sm font-medium ${config.text}`}>{title}</p>
        {children && (
          <div className={`text-sm mt-0.5 ${variant === 'error' || variant === 'warning' ? 'text-red-400/70' : 'text-gray-400'}`}>
            {children}
          </div>
        )}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}
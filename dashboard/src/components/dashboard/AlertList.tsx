'use client';

import { cn, formatDateTime } from '@/lib/utils';
import { AlertCircle, AlertTriangle, Info, ChevronRight } from 'lucide-react';
import type { AlertItem } from '@/types';
import Link from 'next/link';

interface AlertListProps {
  alerts: AlertItem[];
  delay?: number;
}

export function AlertList({ alerts, delay = 0 }: AlertListProps) {
  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-amber-500" />;
      default:
        return <Info className="h-4 w-4 text-blue-500" />;
    }
  };

  const getSeverityBg = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-50 border-red-200';
      case 'warning':
        return 'bg-amber-50 border-amber-200';
      default:
        return 'bg-blue-50 border-blue-200';
    }
  };

  return (
    <div
      className="card p-5 opacity-0 animate-slide-up"
      style={{ animationDelay: `${delay}ms`, animationFillMode: 'forwards' }}
    >
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-navy-900">Recent Alerts</h3>
        <Link
          href="/budget?tab=alerts"
          className="flex items-center gap-1 text-xs font-medium text-navy-600 transition-colors hover:text-navy-900"
        >
          View all
          <ChevronRight className="h-3 w-3" />
        </Link>
      </div>

      {alerts.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <div className="mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-emerald-50">
            <svg
              className="h-6 w-6 text-emerald-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>
          <p className="text-sm font-medium text-navy-700">All clear!</p>
          <p className="text-xs text-navy-500">No active alerts</p>
        </div>
      ) : (
        <div className="space-y-2">
          {alerts.map((alert, index) => (
            <div
              key={alert.id}
              className={cn(
                'flex items-start gap-3 rounded-lg border p-3 opacity-0 animate-fade-in',
                getSeverityBg(alert.severity)
              )}
              style={{
                animationDelay: `${delay + 100 + index * 50}ms`,
                animationFillMode: 'forwards',
              }}
            >
              {getSeverityIcon(alert.severity)}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-navy-800">{alert.message}</p>
                <div className="mt-1 flex items-center gap-2">
                  <span className="text-xs text-navy-500">{alert.entity}</span>
                  <span className="text-navy-300">•</span>
                  <span className="text-xs text-navy-500">
                    {formatDateTime(alert.created_at)}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

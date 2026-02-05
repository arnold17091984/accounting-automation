'use client';

import { cn } from '@/lib/utils';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import type { KPIData } from '@/types';

interface KPICardProps {
  data: KPIData;
  icon?: React.ReactNode;
  delay?: number;
}

export function KPICard({ data, icon, delay = 0 }: KPICardProps) {
  const { label, formatted_value, change_percent, change_direction } = data;

  const getTrendIcon = () => {
    switch (change_direction) {
      case 'up':
        return <TrendingUp className="h-4 w-4" />;
      case 'down':
        return <TrendingDown className="h-4 w-4" />;
      default:
        return <Minus className="h-4 w-4" />;
    }
  };

  const getTrendColor = () => {
    if (label === 'Expenses') {
      // For expenses, up is bad, down is good
      return change_direction === 'up'
        ? 'text-red-600 bg-red-50'
        : change_direction === 'down'
          ? 'text-emerald-600 bg-emerald-50'
          : 'text-navy-500 bg-navy-50';
    }
    // For everything else, up is good, down is bad
    return change_direction === 'up'
      ? 'text-emerald-600 bg-emerald-50'
      : change_direction === 'down'
        ? 'text-red-600 bg-red-50'
        : 'text-navy-500 bg-navy-50';
  };

  return (
    <div
      className="card card-hover p-5 opacity-0 animate-slide-up"
      style={{ animationDelay: `${delay}ms`, animationFillMode: 'forwards' }}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-navy-500">{label}</p>
          <p className="mt-1 text-2xl font-semibold text-navy-900 currency">
            {formatted_value}
          </p>
        </div>
        {icon && (
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-navy-100/50 text-navy-600">
            {icon}
          </div>
        )}
      </div>

      {change_percent !== null && (
        <div className="mt-4 flex items-center gap-2">
          <span
            className={cn(
              'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium',
              getTrendColor()
            )}
          >
            {getTrendIcon()}
            {Math.abs(change_percent).toFixed(1)}%
          </span>
          <span className="text-xs text-navy-500">vs last month</span>
        </div>
      )}
    </div>
  );
}

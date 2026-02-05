'use client';

import { cn, formatCurrency } from '@/lib/utils';
import type { BudgetStatus } from '@/types';

interface BudgetGaugeProps {
  data: BudgetStatus;
  delay?: number;
}

export function BudgetGauge({ data, delay = 0 }: BudgetGaugeProps) {
  const { entity_name, utilization_percent, status, budget_total, actual_total } = data;

  const getStatusColor = () => {
    switch (status) {
      case 'ok':
        return 'bg-emerald-500';
      case 'warning':
        return 'bg-amber-500';
      case 'critical':
      case 'exceeded':
        return 'bg-red-500';
      default:
        return 'bg-navy-400';
    }
  };

  const getStatusBadge = () => {
    switch (status) {
      case 'ok':
        return 'OK';
      case 'warning':
        return '⚠️';
      case 'critical':
      case 'exceeded':
        return '🔴';
      default:
        return '';
    }
  };

  return (
    <div
      className="flex items-center gap-4 rounded-lg border border-navy-100 bg-white p-3 opacity-0 animate-slide-up"
      style={{ animationDelay: `${delay}ms`, animationFillMode: 'forwards' }}
    >
      <div className="min-w-[100px]">
        <p className="text-sm font-medium text-navy-700">{entity_name}</p>
      </div>

      <div className="flex-1">
        <div className="progress-bar">
          <div
            className={cn('progress-fill', getStatusColor())}
            style={{ width: `${Math.min(utilization_percent, 100)}%` }}
          />
        </div>
      </div>

      <div className="flex items-center gap-3 min-w-[120px] justify-end">
        <span className="text-sm font-medium text-navy-700 currency">
          {utilization_percent.toFixed(0)}%
        </span>
        <span className="text-sm">{getStatusBadge()}</span>
      </div>
    </div>
  );
}

interface BudgetGaugeListProps {
  items: BudgetStatus[];
}

export function BudgetGaugeList({ items }: BudgetGaugeListProps) {
  return (
    <div
      className="card p-5 opacity-0 animate-slide-up"
      style={{ animationDelay: '200ms', animationFillMode: 'forwards' }}
    >
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-navy-900">Budget Utilization</h3>
        <span className="text-xs text-navy-500">Current Month</span>
      </div>

      <div className="space-y-3">
        {items.map((item, index) => (
          <BudgetGauge
            key={item.entity}
            data={item}
            delay={250 + index * 50}
          />
        ))}
      </div>
    </div>
  );
}

'use client';

import { useState, useEffect } from 'react';
import { Header } from '@/components/layout/Header';
import { DataTable, Pagination } from '@/components/common/DataTable';
import { StatusBadge } from '@/components/common/StatusBadge';
import { formatCurrency, formatPercent, getCurrentPeriod, getPeriodLabel, cn } from '@/lib/utils';
import { Download, Calendar, TrendingUp, TrendingDown, AlertTriangle } from 'lucide-react';
import type { BudgetItem, BudgetSummary } from '@/types';

// Mock data
const mockBudgetData: BudgetSummary = {
  entity: 'tours',
  entity_name: 'Tours BGC/BSM',
  period: 'February 2026',
  total_budget: 2000000,
  total_actual: 1650000,
  total_variance: 350000,
  overall_utilization: 82.5,
  items: [
    {
      account_code: '5100',
      account_name: 'Salaries',
      category: 'salary',
      budget_amount: 500000,
      actual_amount: 485000,
      variance_amount: 15000,
      variance_percent: -3,
      utilization_percent: 97,
      status: 'ok',
    },
    {
      account_code: '5200',
      account_name: 'Office Rental',
      category: 'expense',
      budget_amount: 100000,
      actual_amount: 100000,
      variance_amount: 0,
      variance_percent: 0,
      utilization_percent: 100,
      status: 'ok',
    },
    {
      account_code: '5300',
      account_name: 'Credit Card',
      category: 'expense',
      budget_amount: 200000,
      actual_amount: 215000,
      variance_amount: -15000,
      variance_percent: 7.5,
      utilization_percent: 107.5,
      status: 'exceeded',
    },
    {
      account_code: '5400',
      account_name: 'Travel & Transportation',
      category: 'expense',
      budget_amount: 50000,
      actual_amount: 62000,
      variance_amount: -12000,
      variance_percent: 24,
      utilization_percent: 124,
      status: 'exceeded',
    },
    {
      account_code: '5500',
      account_name: 'Utilities',
      category: 'expense',
      budget_amount: 30000,
      actual_amount: 22000,
      variance_amount: 8000,
      variance_percent: -26.7,
      utilization_percent: 73.3,
      status: 'warning',
    },
    {
      account_code: '5600',
      account_name: 'Network & Internet',
      category: 'expense',
      budget_amount: 25000,
      actual_amount: 18000,
      variance_amount: 7000,
      variance_percent: -28,
      utilization_percent: 72,
      status: 'warning',
    },
    {
      account_code: '5700',
      account_name: 'Marketing',
      category: 'expense',
      budget_amount: 80000,
      actual_amount: 45000,
      variance_amount: 35000,
      variance_percent: -43.8,
      utilization_percent: 56.3,
      status: 'ok',
    },
  ],
};

export default function BudgetPage() {
  const [data, setData] = useState<BudgetSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState(getCurrentPeriod());

  useEffect(() => {
    const fetchData = async () => {
      await new Promise((resolve) => setTimeout(resolve, 500));
      setData(mockBudgetData);
      setLoading(false);
    };

    fetchData();
  }, [period]);

  const columns = [
    {
      key: 'account_name',
      header: 'Account',
      render: (item: BudgetItem) => (
        <div>
          <p className="font-medium text-navy-900">{item.account_name}</p>
          <p className="text-xs text-navy-500">{item.account_code}</p>
        </div>
      ),
    },
    {
      key: 'budget_amount',
      header: 'Budget',
      align: 'right' as const,
      render: (item: BudgetItem) => (
        <span className="currency text-navy-700">
          {formatCurrency(item.budget_amount)}
        </span>
      ),
    },
    {
      key: 'actual_amount',
      header: 'Actual',
      align: 'right' as const,
      render: (item: BudgetItem) => (
        <span className="currency text-navy-700">
          {formatCurrency(item.actual_amount)}
        </span>
      ),
    },
    {
      key: 'variance_amount',
      header: 'Variance',
      align: 'right' as const,
      render: (item: BudgetItem) => (
        <span
          className={cn(
            'currency',
            item.variance_amount >= 0 ? 'currency-positive' : 'currency-negative'
          )}
        >
          {item.variance_amount >= 0 ? '+' : ''}
          {formatCurrency(item.variance_amount)}
        </span>
      ),
    },
    {
      key: 'utilization_percent',
      header: 'Utilization',
      align: 'center' as const,
      render: (item: BudgetItem) => (
        <div className="flex items-center justify-center gap-2">
          <div className="w-16 progress-bar">
            <div
              className={cn(
                'progress-fill',
                item.status === 'ok'
                  ? 'bg-emerald-500'
                  : item.status === 'warning'
                    ? 'bg-amber-500'
                    : 'bg-red-500'
              )}
              style={{ width: `${Math.min(item.utilization_percent, 100)}%` }}
            />
          </div>
          <span className="text-sm font-medium text-navy-700 w-12 text-right">
            {item.utilization_percent.toFixed(0)}%
          </span>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      align: 'center' as const,
      render: (item: BudgetItem) => <StatusBadge status={item.status} />,
    },
  ];

  return (
    <div className="min-h-screen">
      <Header
        title="Budget Management"
        subtitle={data?.period || 'Loading...'}
      />

      <div className="p-6">
        {/* Summary Cards */}
        {data && (
          <div className="mb-6 grid gap-4 md:grid-cols-4">
            <div className="card p-4 opacity-0 animate-slide-up" style={{ animationDelay: '0ms', animationFillMode: 'forwards' }}>
              <p className="text-sm text-navy-500">Total Budget</p>
              <p className="mt-1 text-xl font-semibold text-navy-900 currency">
                {formatCurrency(data.total_budget)}
              </p>
            </div>
            <div className="card p-4 opacity-0 animate-slide-up" style={{ animationDelay: '75ms', animationFillMode: 'forwards' }}>
              <p className="text-sm text-navy-500">Actual Spending</p>
              <p className="mt-1 text-xl font-semibold text-navy-900 currency">
                {formatCurrency(data.total_actual)}
              </p>
            </div>
            <div className="card p-4 opacity-0 animate-slide-up" style={{ animationDelay: '150ms', animationFillMode: 'forwards' }}>
              <p className="text-sm text-navy-500">Variance</p>
              <p
                className={cn(
                  'mt-1 text-xl font-semibold currency',
                  data.total_variance >= 0 ? 'currency-positive' : 'currency-negative'
                )}
              >
                {data.total_variance >= 0 ? '+' : ''}
                {formatCurrency(data.total_variance)}
              </p>
            </div>
            <div className="card p-4 opacity-0 animate-slide-up" style={{ animationDelay: '225ms', animationFillMode: 'forwards' }}>
              <p className="text-sm text-navy-500">Utilization</p>
              <div className="mt-1 flex items-center gap-2">
                <p className="text-xl font-semibold text-navy-900">
                  {data.overall_utilization.toFixed(1)}%
                </p>
                {data.overall_utilization > 100 && (
                  <AlertTriangle className="h-5 w-5 text-red-500" />
                )}
              </div>
            </div>
          </div>
        )}

        {/* Controls */}
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="relative">
              <Calendar className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-navy-400" />
              <input
                type="month"
                value={period}
                onChange={(e) => setPeriod(e.target.value)}
                className="input pl-10 w-48"
              />
            </div>
          </div>
          <button className="btn btn-secondary px-4 py-2 text-sm">
            <Download className="mr-2 h-4 w-4" />
            Export CSV
          </button>
        </div>

        {/* Table */}
        <div className="card overflow-hidden opacity-0 animate-slide-up" style={{ animationDelay: '300ms', animationFillMode: 'forwards' }}>
          <DataTable
            columns={columns}
            data={data?.items || []}
            keyField="account_code"
            loading={loading}
            emptyMessage="No budget data available"
          />
        </div>
      </div>
    </div>
  );
}

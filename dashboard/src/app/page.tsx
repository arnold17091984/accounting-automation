'use client';

import { useEffect, useState } from 'react';
import { Header } from '@/components/layout/Header';
import { KPICard } from '@/components/dashboard/KPICard';
import { BudgetGaugeList } from '@/components/dashboard/BudgetGauge';
import { AlertList } from '@/components/dashboard/AlertList';
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Clock,
} from 'lucide-react';
import type { DashboardSummary } from '@/types';

// Mock data for demonstration
const mockDashboardData: DashboardSummary = {
  period: 'February 2026',
  kpis: [
    {
      label: 'Revenue',
      value: 5200000,
      formatted_value: '₱5.2M',
      change_percent: 12.5,
      change_direction: 'up',
    },
    {
      label: 'Expenses',
      value: 3100000,
      formatted_value: '₱3.1M',
      change_percent: 5.2,
      change_direction: 'up',
    },
    {
      label: 'Profit',
      value: 2100000,
      formatted_value: '₱2.1M',
      change_percent: 24.1,
      change_direction: 'up',
    },
    {
      label: 'Pending Approvals',
      value: 3,
      formatted_value: '3 items',
      change_percent: null,
      change_direction: null,
    },
  ],
  budget_status: [
    {
      entity: 'solaire',
      entity_name: 'Solaire',
      utilization_percent: 68,
      status: 'ok',
      budget_total: 5000000,
      actual_total: 3400000,
    },
    {
      entity: 'cod',
      entity_name: 'COD',
      utilization_percent: 89,
      status: 'warning',
      budget_total: 4000000,
      actual_total: 3560000,
    },
    {
      entity: 'tours',
      entity_name: 'Tours BGC/BSM',
      utilization_percent: 102,
      status: 'exceeded',
      budget_total: 2000000,
      actual_total: 2040000,
    },
    {
      entity: 'royce',
      entity_name: 'Royce Clark',
      utilization_percent: 45,
      status: 'ok',
      budget_total: 3000000,
      actual_total: 1350000,
    },
    {
      entity: 'midori',
      entity_name: 'Midori no Mart',
      utilization_percent: 72,
      status: 'warning',
      budget_total: 1500000,
      actual_total: 1080000,
    },
  ],
  recent_alerts: [
    {
      id: 1,
      entity: 'COD',
      message: 'Budget for Office Expenses reached 90%',
      severity: 'warning',
      created_at: '2026-02-05T10:30:00Z',
    },
    {
      id: 2,
      entity: 'Tours',
      message: 'Monthly budget exceeded by 2%',
      severity: 'critical',
      created_at: '2026-02-04T15:45:00Z',
    },
  ],
  pending_approvals_count: 3,
  pending_approvals_total: 45000,
};

const kpiIcons = [
  <TrendingUp key="revenue" className="h-5 w-5" />,
  <TrendingDown key="expenses" className="h-5 w-5" />,
  <DollarSign key="profit" className="h-5 w-5" />,
  <Clock key="pending" className="h-5 w-5" />,
];

export default function DashboardPage() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simulate API call
    const fetchData = async () => {
      // In production, this would call the actual API
      // const response = await getDashboardSummary();
      await new Promise((resolve) => setTimeout(resolve, 500));
      setData(mockDashboardData);
      setLoading(false);
    };

    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen">
        <Header title="Dashboard" subtitle="Loading..." />
        <div className="p-6">
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="skeleton h-32 rounded-xl" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="min-h-screen">
      <Header title="Dashboard" subtitle={data.period} />

      <div className="p-6">
        {/* KPI Cards */}
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {data.kpis.map((kpi, index) => (
            <KPICard
              key={kpi.label}
              data={kpi}
              icon={kpiIcons[index]}
              delay={index * 75}
            />
          ))}
        </div>

        {/* Main content grid */}
        <div className="mt-6 grid gap-6 lg:grid-cols-3">
          {/* Budget Gauges - takes 2 columns */}
          <div className="lg:col-span-2">
            <BudgetGaugeList items={data.budget_status} />
          </div>

          {/* Alerts - takes 1 column */}
          <div className="lg:col-span-1">
            <AlertList alerts={data.recent_alerts} delay={300} />
          </div>
        </div>

        {/* Quick Actions */}
        <div
          className="mt-6 card p-5 opacity-0 animate-slide-up"
          style={{ animationDelay: '400ms', animationFillMode: 'forwards' }}
        >
          <h3 className="mb-4 text-sm font-semibold text-navy-900">
            Quick Actions
          </h3>
          <div className="flex flex-wrap gap-3">
            <a
              href="/fund-requests/new"
              className="btn btn-primary px-4 py-2 text-sm"
            >
              Create Fund Request
            </a>
            <a
              href="/approvals"
              className="btn btn-secondary px-4 py-2 text-sm"
            >
              View Pending Approvals ({data.pending_approvals_count})
            </a>
            <a href="/budget" className="btn btn-secondary px-4 py-2 text-sm">
              Budget Overview
            </a>
            <a
              href="/transactions"
              className="btn btn-secondary px-4 py-2 text-sm"
            >
              Recent Transactions
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}

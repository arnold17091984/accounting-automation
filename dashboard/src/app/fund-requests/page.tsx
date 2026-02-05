'use client';

import { useState, useEffect } from 'react';
import { Header } from '@/components/layout/Header';
import { DataTable, Pagination } from '@/components/common/DataTable';
import { StatusBadge } from '@/components/common/StatusBadge';
import { formatCurrency, formatDate, ENTITIES, cn } from '@/lib/utils';
import { Plus, Download, FileSpreadsheet, Eye, ChevronRight } from 'lucide-react';
import Link from 'next/link';
import type { FundRequestSummary } from '@/types';

// Mock data
const mockFundRequests: FundRequestSummary[] = [
  {
    id: 1,
    entity: 'tours',
    request_date: '2026-02-03',
    payment_date: '2026-02-05',
    period_label: 'February 2026 - 1st Half',
    section_a_total: 6331702,
    section_b_total: 100365,
    overall_total: 7716267,
    current_fund_balance: 2172452,
    remaining_fund: 97799,
    status: 'approved',
    approved_by: 'admin',
    approved_at: '2026-02-04T10:30:00Z',
    google_drive_url: 'https://drive.google.com/file/123',
    created_at: '2026-02-03T09:00:00Z',
  },
  {
    id: 2,
    entity: 'tours',
    request_date: '2026-01-18',
    payment_date: '2026-01-20',
    period_label: 'January 2026 - 2nd Half',
    section_a_total: 5892450,
    section_b_total: 1000000,
    overall_total: 6892450,
    current_fund_balance: 1850000,
    remaining_fund: 125000,
    status: 'approved',
    approved_by: 'admin',
    approved_at: '2026-01-19T14:00:00Z',
    google_drive_url: 'https://drive.google.com/file/124',
    created_at: '2026-01-18T09:00:00Z',
  },
  {
    id: 3,
    entity: 'solaire',
    request_date: '2026-02-03',
    payment_date: '2026-02-05',
    period_label: 'February 2026 - 1st Half',
    section_a_total: 4500000,
    section_b_total: 250000,
    overall_total: 4750000,
    current_fund_balance: null,
    remaining_fund: null,
    status: 'sent',
    approved_by: null,
    approved_at: null,
    google_drive_url: 'https://drive.google.com/file/125',
    created_at: '2026-02-03T11:00:00Z',
  },
];

export default function FundRequestsPage() {
  const [fundRequests, setFundRequests] = useState<FundRequestSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const totalPages = 2;

  useEffect(() => {
    const fetchData = async () => {
      await new Promise((resolve) => setTimeout(resolve, 500));
      setFundRequests(mockFundRequests);
      setLoading(false);
    };

    fetchData();
  }, [page]);

  const columns = [
    {
      key: 'payment_date',
      header: 'Payment Date',
      render: (item: FundRequestSummary) => (
        <div>
          <p className="font-medium text-navy-900">{formatDate(item.payment_date)}</p>
          <p className="text-xs text-navy-500">{item.period_label}</p>
        </div>
      ),
    },
    {
      key: 'entity',
      header: 'Entity',
      render: (item: FundRequestSummary) => (
        <span className="text-sm text-navy-700">
          {ENTITIES.find((e) => e.code === item.entity)?.name || item.entity}
        </span>
      ),
    },
    {
      key: 'section_a_total',
      header: 'Section A',
      align: 'right' as const,
      render: (item: FundRequestSummary) => (
        <span className="currency text-sm text-navy-600">
          {formatCurrency(item.section_a_total)}
        </span>
      ),
    },
    {
      key: 'section_b_total',
      header: 'Section B',
      align: 'right' as const,
      render: (item: FundRequestSummary) => (
        <span className="currency text-sm text-navy-600">
          {formatCurrency(item.section_b_total)}
        </span>
      ),
    },
    {
      key: 'overall_total',
      header: 'Total',
      align: 'right' as const,
      render: (item: FundRequestSummary) => (
        <span className="currency font-semibold text-navy-900">
          {formatCurrency(item.overall_total)}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      align: 'center' as const,
      render: (item: FundRequestSummary) => (
        <StatusBadge
          status={item.status}
          label={item.status.charAt(0).toUpperCase() + item.status.slice(1)}
        />
      ),
    },
    {
      key: 'actions',
      header: '',
      align: 'right' as const,
      render: (item: FundRequestSummary) => (
        <div className="flex items-center justify-end gap-2">
          {item.google_drive_url && (
            <a
              href={item.google_drive_url}
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-ghost p-2"
              title="Download Excel"
            >
              <FileSpreadsheet className="h-4 w-4" />
            </a>
          )}
          <Link
            href={`/fund-requests/${item.id}`}
            className="btn btn-ghost p-2"
            title="View Details"
          >
            <Eye className="h-4 w-4" />
          </Link>
        </div>
      ),
    },
  ];

  return (
    <div className="min-h-screen">
      <Header title="Fund Requests" subtitle="Manage fund disbursement requests" />

      <div className="p-6">
        {/* Summary Cards */}
        <div className="mb-6 grid gap-4 sm:grid-cols-3">
          <div className="card p-4 opacity-0 animate-slide-up" style={{ animationDelay: '0ms', animationFillMode: 'forwards' }}>
            <p className="text-sm text-navy-500">This Month</p>
            <p className="mt-1 text-2xl font-semibold text-navy-900 currency">
              {formatCurrency(
                fundRequests
                  .filter(
                    (r) =>
                      new Date(r.payment_date).getMonth() === new Date().getMonth()
                  )
                  .reduce((sum, r) => sum + r.overall_total, 0)
              )}
            </p>
          </div>
          <div className="card p-4 opacity-0 animate-slide-up" style={{ animationDelay: '75ms', animationFillMode: 'forwards' }}>
            <p className="text-sm text-navy-500">Pending Approval</p>
            <p className="mt-1 text-2xl font-semibold text-navy-900">
              {fundRequests.filter((r) => r.status === 'sent' || r.status === 'draft').length}
            </p>
          </div>
          <div className="card p-4 opacity-0 animate-slide-up" style={{ animationDelay: '150ms', animationFillMode: 'forwards' }}>
            <p className="text-sm text-navy-500">Total Requests</p>
            <p className="mt-1 text-2xl font-semibold text-navy-900">
              {fundRequests.length}
            </p>
          </div>
        </div>

        {/* Actions */}
        <div className="mb-4 flex items-center justify-between">
          <div className="text-sm text-navy-600">
            Showing {fundRequests.length} fund requests
          </div>
          <Link
            href="/fund-requests/new"
            className="btn btn-primary px-4 py-2 text-sm"
          >
            <Plus className="mr-2 h-4 w-4" />
            New Fund Request
          </Link>
        </div>

        {/* Table */}
        <div className="card overflow-hidden opacity-0 animate-slide-up" style={{ animationDelay: '200ms', animationFillMode: 'forwards' }}>
          <DataTable
            columns={columns}
            data={fundRequests}
            keyField="id"
            loading={loading}
            emptyMessage="No fund requests found"
          />
          <Pagination
            currentPage={page}
            totalPages={totalPages}
            onPageChange={setPage}
          />
        </div>
      </div>
    </div>
  );
}

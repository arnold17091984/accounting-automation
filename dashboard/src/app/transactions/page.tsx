'use client';

import { useState, useEffect } from 'react';
import { Header } from '@/components/layout/Header';
import { DataTable, Pagination } from '@/components/common/DataTable';
import { StatusBadge } from '@/components/common/StatusBadge';
import { formatCurrency, formatDate, cn, ENTITIES } from '@/lib/utils';
import { Search, Filter, Download, AlertCircle } from 'lucide-react';
import type { Transaction, TransactionListResponse } from '@/types';

// Mock data
const mockTransactions: Transaction[] = [
  {
    id: '1',
    source: 'credit_card',
    source_bank: 'BDO',
    entity: 'tours',
    txn_date: '2026-02-05',
    description: 'Office Supplies - National Bookstore',
    merchant: 'National Bookstore',
    amount: 2500,
    currency: 'PHP',
    account_code: '5400',
    account_name: 'Office Supplies',
    category: 'expense',
    classification_method: 'claude',
    classification_confidence: 0.95,
    approved: true,
    approved_by: null,
    anomaly_flag: false,
    anomaly_reason: null,
    created_at: '2026-02-05T10:30:00Z',
  },
  {
    id: '2',
    source: 'credit_card',
    source_bank: 'UnionBank',
    entity: 'solaire',
    txn_date: '2026-02-04',
    description: 'Client Entertainment',
    merchant: 'Resorts World Manila',
    amount: 15000,
    currency: 'PHP',
    account_code: '5500',
    account_name: 'Entertainment',
    category: 'expense',
    classification_method: 'lookup',
    classification_confidence: 1.0,
    approved: false,
    approved_by: null,
    anomaly_flag: true,
    anomaly_reason: 'Amount 50% higher than average for this category',
    created_at: '2026-02-04T18:45:00Z',
  },
  {
    id: '3',
    source: 'expense_form',
    source_bank: null,
    entity: 'cod',
    txn_date: '2026-02-03',
    description: 'Transportation - Grab',
    merchant: 'Grab Philippines',
    amount: 850,
    currency: 'PHP',
    account_code: '5300',
    account_name: 'Transportation',
    category: 'expense',
    classification_method: 'lookup',
    classification_confidence: 1.0,
    approved: true,
    approved_by: 'user123',
    anomaly_flag: false,
    anomaly_reason: null,
    created_at: '2026-02-03T14:20:00Z',
  },
  {
    id: '4',
    source: 'payroll',
    source_bank: null,
    entity: 'tours',
    txn_date: '2026-02-01',
    description: 'February 2026 - 1st Half Payroll',
    merchant: null,
    amount: 485000,
    currency: 'PHP',
    account_code: '5100',
    account_name: 'Salaries',
    category: 'salary',
    classification_method: 'human',
    classification_confidence: 1.0,
    approved: true,
    approved_by: 'admin',
    anomaly_flag: false,
    anomaly_reason: null,
    created_at: '2026-02-01T09:00:00Z',
  },
  {
    id: '5',
    source: 'credit_card',
    source_bank: 'GCash',
    entity: 'midori',
    txn_date: '2026-02-05',
    description: 'Inventory Purchase',
    merchant: 'Puregold',
    amount: 35000,
    currency: 'PHP',
    account_code: '5200',
    account_name: 'Cost of Sales',
    category: 'cos',
    classification_method: 'claude',
    classification_confidence: 0.88,
    approved: false,
    approved_by: null,
    anomaly_flag: false,
    anomaly_reason: null,
    created_at: '2026-02-05T16:30:00Z',
  },
];

const sourceOptions = ['credit_card', 'expense_form', 'payroll', 'game_record', 'pos'];
const categoryOptions = ['expense', 'salary', 'commission', 'cos', 'revenue', 'bank_charge'];

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [entityFilter, setEntityFilter] = useState('');
  const [sourceFilter, setSourceFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      await new Promise((resolve) => setTimeout(resolve, 500));
      setTransactions(mockTransactions);
      setTotalPages(3);
      setLoading(false);
    };

    fetchData();
  }, [page, entityFilter, sourceFilter, categoryFilter]);

  const columns = [
    {
      key: 'txn_date',
      header: 'Date',
      width: '100px',
      render: (item: Transaction) => (
        <span className="text-sm text-navy-600">{formatDate(item.txn_date)}</span>
      ),
    },
    {
      key: 'description',
      header: 'Description',
      render: (item: Transaction) => (
        <div className="max-w-[300px]">
          <p className="truncate font-medium text-navy-900">
            {item.description || item.merchant || 'No description'}
          </p>
          <div className="mt-0.5 flex items-center gap-2 text-xs text-navy-500">
            <span>{item.source.replace('_', ' ')}</span>
            {item.source_bank && (
              <>
                <span className="text-navy-300">•</span>
                <span>{item.source_bank}</span>
              </>
            )}
          </div>
        </div>
      ),
    },
    {
      key: 'entity',
      header: 'Entity',
      render: (item: Transaction) => (
        <span className="text-sm text-navy-600">
          {ENTITIES.find((e) => e.code === item.entity)?.name || item.entity}
        </span>
      ),
    },
    {
      key: 'category',
      header: 'Category',
      render: (item: Transaction) => (
        <div>
          <p className="text-sm text-navy-700">{item.account_name || '-'}</p>
          <p className="text-xs text-navy-500">{item.category || 'uncategorized'}</p>
        </div>
      ),
    },
    {
      key: 'amount',
      header: 'Amount',
      align: 'right' as const,
      render: (item: Transaction) => (
        <span className="currency font-medium text-navy-900">
          {formatCurrency(item.amount, item.currency)}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      align: 'center' as const,
      render: (item: Transaction) => (
        <div className="flex items-center justify-center gap-2">
          {item.anomaly_flag && (
            <div className="group relative">
              <AlertCircle className="h-4 w-4 text-amber-500" />
              <div className="absolute bottom-full left-1/2 mb-2 hidden -translate-x-1/2 whitespace-nowrap rounded bg-navy-900 px-2 py-1 text-xs text-white group-hover:block">
                {item.anomaly_reason}
              </div>
            </div>
          )}
          <StatusBadge
            status={item.approved ? 'approved' : 'pending'}
            label={item.approved ? 'Approved' : 'Pending'}
          />
        </div>
      ),
    },
  ];

  return (
    <div className="min-h-screen">
      <Header title="Transactions" subtitle="View and manage all transactions" />

      <div className="p-6">
        {/* Search and Filters */}
        <div className="mb-4 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-navy-400" />
              <input
                type="text"
                placeholder="Search transactions..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="input w-64 pl-10"
              />
            </div>
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={cn(
                'btn px-4 py-2 text-sm',
                showFilters ? 'btn-primary' : 'btn-secondary'
              )}
            >
              <Filter className="mr-2 h-4 w-4" />
              Filters
            </button>
          </div>
          <button className="btn btn-secondary px-4 py-2 text-sm">
            <Download className="mr-2 h-4 w-4" />
            Export
          </button>
        </div>

        {/* Filter Panel */}
        {showFilters && (
          <div className="mb-4 card p-4 opacity-0 animate-slide-up" style={{ animationFillMode: 'forwards' }}>
            <div className="grid gap-4 sm:grid-cols-3">
              <div>
                <label className="mb-1 block text-sm font-medium text-navy-700">
                  Entity
                </label>
                <select
                  value={entityFilter}
                  onChange={(e) => setEntityFilter(e.target.value)}
                  className="input"
                >
                  <option value="">All Entities</option>
                  {ENTITIES.map((entity) => (
                    <option key={entity.code} value={entity.code}>
                      {entity.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-navy-700">
                  Source
                </label>
                <select
                  value={sourceFilter}
                  onChange={(e) => setSourceFilter(e.target.value)}
                  className="input"
                >
                  <option value="">All Sources</option>
                  {sourceOptions.map((source) => (
                    <option key={source} value={source}>
                      {source.replace('_', ' ')}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-navy-700">
                  Category
                </label>
                <select
                  value={categoryFilter}
                  onChange={(e) => setCategoryFilter(e.target.value)}
                  className="input"
                >
                  <option value="">All Categories</option>
                  {categoryOptions.map((cat) => (
                    <option key={cat} value={cat}>
                      {cat}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        )}

        {/* Table */}
        <div className="card overflow-hidden">
          <DataTable
            columns={columns}
            data={transactions}
            keyField="id"
            loading={loading}
            emptyMessage="No transactions found"
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

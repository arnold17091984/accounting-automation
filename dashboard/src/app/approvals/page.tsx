'use client';

import { useState, useEffect } from 'react';
import { Header } from '@/components/layout/Header';
import { Modal } from '@/components/common/Modal';
import { StatusBadge } from '@/components/common/StatusBadge';
import { formatCurrency, formatDateTime, ENTITIES, cn } from '@/lib/utils';
import { Check, X, MessageSquare, Clock, DollarSign, FileText } from 'lucide-react';
import type { ApprovalItem } from '@/types';

// Mock data
const mockApprovals: ApprovalItem[] = [
  {
    id: 1,
    request_type: 'expense',
    reference_id: 'txn-001',
    entity: 'tours',
    amount: 15000,
    description: 'Client Entertainment - Resorts World Manila',
    status: 'pending',
    requested_by: 'user123',
    requested_at: '2026-02-05T10:30:00Z',
    telegram_msg_id: '12345',
    notes: null,
  },
  {
    id: 2,
    request_type: 'transfer',
    reference_id: null,
    entity: 'solaire',
    amount: 250000,
    description: 'Payroll Transfer - February 1st Half',
    status: 'pending',
    requested_by: 'system',
    requested_at: '2026-02-04T09:00:00Z',
    telegram_msg_id: '12346',
    notes: 'Auto-generated from payroll system',
  },
  {
    id: 3,
    request_type: 'budget_override',
    reference_id: null,
    entity: 'cod',
    amount: 50000,
    description: 'Marketing budget override for Q1 campaign',
    status: 'pending',
    requested_by: 'marketing_team',
    requested_at: '2026-02-03T14:20:00Z',
    telegram_msg_id: '12347',
    notes: 'Requires management approval',
  },
];

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<ApprovalItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedApproval, setSelectedApproval] = useState<ApprovalItem | null>(null);
  const [actionModal, setActionModal] = useState<'approve' | 'reject' | null>(null);
  const [notes, setNotes] = useState('');
  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      await new Promise((resolve) => setTimeout(resolve, 500));
      setApprovals(mockApprovals);
      setLoading(false);
    };

    fetchData();
  }, []);

  const handleApprove = async (approval: ApprovalItem) => {
    setProcessing(true);
    await new Promise((resolve) => setTimeout(resolve, 1000));
    setApprovals(approvals.filter((a) => a.id !== approval.id));
    setActionModal(null);
    setSelectedApproval(null);
    setNotes('');
    setProcessing(false);
  };

  const handleReject = async (approval: ApprovalItem) => {
    if (!notes.trim()) return;
    setProcessing(true);
    await new Promise((resolve) => setTimeout(resolve, 1000));
    setApprovals(approvals.filter((a) => a.id !== approval.id));
    setActionModal(null);
    setSelectedApproval(null);
    setNotes('');
    setProcessing(false);
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'expense':
        return <DollarSign className="h-5 w-5" />;
      case 'transfer':
        return <FileText className="h-5 w-5" />;
      case 'budget_override':
        return <Clock className="h-5 w-5" />;
      default:
        return <FileText className="h-5 w-5" />;
    }
  };

  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'expense':
        return 'Expense';
      case 'transfer':
        return 'Transfer';
      case 'budget_override':
        return 'Budget Override';
      case 'pl_review':
        return 'P&L Review';
      default:
        return type;
    }
  };

  return (
    <div className="min-h-screen">
      <Header title="Approvals" subtitle={`${approvals.length} pending requests`} />

      <div className="p-6">
        {/* Stats Cards */}
        <div className="mb-6 grid gap-4 sm:grid-cols-3">
          <div className="card p-4 opacity-0 animate-slide-up" style={{ animationDelay: '0ms', animationFillMode: 'forwards' }}>
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-50 text-amber-600">
                <Clock className="h-5 w-5" />
              </div>
              <div>
                <p className="text-2xl font-semibold text-navy-900">{approvals.length}</p>
                <p className="text-sm text-navy-500">Pending</p>
              </div>
            </div>
          </div>
          <div className="card p-4 opacity-0 animate-slide-up" style={{ animationDelay: '75ms', animationFillMode: 'forwards' }}>
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-50 text-emerald-600">
                <Check className="h-5 w-5" />
              </div>
              <div>
                <p className="text-2xl font-semibold text-navy-900">24</p>
                <p className="text-sm text-navy-500">Approved (7 days)</p>
              </div>
            </div>
          </div>
          <div className="card p-4 opacity-0 animate-slide-up" style={{ animationDelay: '150ms', animationFillMode: 'forwards' }}>
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-navy-100 text-navy-600">
                <DollarSign className="h-5 w-5" />
              </div>
              <div>
                <p className="text-2xl font-semibold text-navy-900 currency">
                  {formatCurrency(
                    approvals.reduce((sum, a) => sum + (a.amount || 0), 0)
                  )}
                </p>
                <p className="text-sm text-navy-500">Total Pending</p>
              </div>
            </div>
          </div>
        </div>

        {/* Approval Cards */}
        {loading ? (
          <div className="space-y-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="skeleton h-32 rounded-xl" />
            ))}
          </div>
        ) : approvals.length === 0 ? (
          <div className="card flex flex-col items-center justify-center py-16 text-center">
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-emerald-50">
              <Check className="h-8 w-8 text-emerald-500" />
            </div>
            <h3 className="text-lg font-semibold text-navy-900">All caught up!</h3>
            <p className="mt-1 text-sm text-navy-500">No pending approvals</p>
          </div>
        ) : (
          <div className="space-y-4">
            {approvals.map((approval, index) => (
              <div
                key={approval.id}
                className="card p-5 opacity-0 animate-slide-up"
                style={{
                  animationDelay: `${200 + index * 75}ms`,
                  animationFillMode: 'forwards',
                }}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-4">
                    <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-navy-100 text-navy-600">
                      {getTypeIcon(approval.request_type)}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold text-navy-900">
                          {approval.description}
                        </h3>
                        <span className="badge bg-navy-100 text-navy-600">
                          {getTypeLabel(approval.request_type)}
                        </span>
                      </div>
                      <div className="mt-1 flex items-center gap-3 text-sm text-navy-500">
                        <span>
                          {ENTITIES.find((e) => e.code === approval.entity)?.name ||
                            approval.entity}
                        </span>
                        <span className="text-navy-300">•</span>
                        <span>{formatDateTime(approval.requested_at)}</span>
                        {approval.notes && (
                          <>
                            <span className="text-navy-300">•</span>
                            <span className="italic">{approval.notes}</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    {approval.amount && (
                      <p className="text-xl font-semibold text-navy-900 currency">
                        {formatCurrency(approval.amount)}
                      </p>
                    )}
                  </div>
                </div>

                <div className="mt-4 flex items-center justify-end gap-2">
                  <button
                    onClick={() => {
                      setSelectedApproval(approval);
                      setActionModal('reject');
                    }}
                    className="btn btn-danger px-4 py-2 text-sm"
                  >
                    <X className="mr-1.5 h-4 w-4" />
                    Reject
                  </button>
                  <button
                    onClick={() => {
                      setSelectedApproval(approval);
                      setActionModal('approve');
                    }}
                    className="btn btn-success px-4 py-2 text-sm"
                  >
                    <Check className="mr-1.5 h-4 w-4" />
                    Approve
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Approve Modal */}
      <Modal
        isOpen={actionModal === 'approve'}
        onClose={() => {
          setActionModal(null);
          setSelectedApproval(null);
          setNotes('');
        }}
        title="Confirm Approval"
        size="sm"
      >
        {selectedApproval && (
          <div>
            <p className="text-sm text-navy-600">
              Are you sure you want to approve this {getTypeLabel(selectedApproval.request_type).toLowerCase()}?
            </p>
            <div className="mt-4 rounded-lg bg-navy-50 p-4">
              <p className="font-medium text-navy-900">{selectedApproval.description}</p>
              {selectedApproval.amount && (
                <p className="mt-1 text-lg font-semibold text-navy-900 currency">
                  {formatCurrency(selectedApproval.amount)}
                </p>
              )}
            </div>
            <div className="mt-4">
              <label className="mb-1 block text-sm font-medium text-navy-700">
                Notes (optional)
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                className="input"
                rows={2}
                placeholder="Add any notes..."
              />
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => {
                  setActionModal(null);
                  setSelectedApproval(null);
                  setNotes('');
                }}
                className="btn btn-secondary px-4 py-2"
              >
                Cancel
              </button>
              <button
                onClick={() => handleApprove(selectedApproval)}
                disabled={processing}
                className="btn btn-success px-4 py-2"
              >
                {processing ? 'Processing...' : 'Approve'}
              </button>
            </div>
          </div>
        )}
      </Modal>

      {/* Reject Modal */}
      <Modal
        isOpen={actionModal === 'reject'}
        onClose={() => {
          setActionModal(null);
          setSelectedApproval(null);
          setNotes('');
        }}
        title="Reject Request"
        size="sm"
      >
        {selectedApproval && (
          <div>
            <p className="text-sm text-navy-600">
              Please provide a reason for rejecting this request.
            </p>
            <div className="mt-4 rounded-lg bg-red-50 p-4">
              <p className="font-medium text-navy-900">{selectedApproval.description}</p>
              {selectedApproval.amount && (
                <p className="mt-1 text-lg font-semibold text-navy-900 currency">
                  {formatCurrency(selectedApproval.amount)}
                </p>
              )}
            </div>
            <div className="mt-4">
              <label className="mb-1 block text-sm font-medium text-navy-700">
                Reason <span className="text-red-500">*</span>
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                className="input"
                rows={3}
                placeholder="Enter rejection reason..."
                required
              />
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => {
                  setActionModal(null);
                  setSelectedApproval(null);
                  setNotes('');
                }}
                className="btn btn-secondary px-4 py-2"
              >
                Cancel
              </button>
              <button
                onClick={() => handleReject(selectedApproval)}
                disabled={processing || !notes.trim()}
                className="btn btn-danger px-4 py-2"
              >
                {processing ? 'Processing...' : 'Reject'}
              </button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

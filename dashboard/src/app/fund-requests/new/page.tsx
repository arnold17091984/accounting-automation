'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Header } from '@/components/layout/Header';
import { formatCurrency, ENTITIES } from '@/lib/utils';
import { Plus, Trash2, Save, Send, ArrowLeft } from 'lucide-react';
import Link from 'next/link';

interface LineItem {
  id: string;
  description: string;
  amount: number;
  category?: string;
  notes?: string;
}

interface ProjectExpense {
  id: string;
  project_name: string;
  amount: number;
}

export default function NewFundRequestPage() {
  const router = useRouter();
  const [entity, setEntity] = useState('tours');
  const [paymentDate, setPaymentDate] = useState('');

  // Section A items (Regular expenses)
  const [sectionAItems, setSectionAItems] = useState<LineItem[]>([
    { id: '1', description: '', amount: 0 },
  ]);

  // Section B items (Others)
  const [sectionBItems, setSectionBItems] = useState<LineItem[]>([
    { id: '1', description: '', amount: 0 },
  ]);

  // Reference info
  const [currentBalance, setCurrentBalance] = useState<number | null>(null);
  const [projectExpenses, setProjectExpenses] = useState<ProjectExpense[]>([
    { id: '1', project_name: '', amount: 0 },
  ]);

  const [saving, setSaving] = useState(false);

  // Calculate totals
  const sectionATotal = sectionAItems.reduce((sum, item) => sum + (item.amount || 0), 0);
  const sectionBTotal = sectionBItems.reduce((sum, item) => sum + (item.amount || 0), 0);
  const overallTotal = sectionATotal + sectionBTotal;
  const projectExpensesTotal = projectExpenses.reduce((sum, pe) => sum + (pe.amount || 0), 0);
  const remainingFund = currentBalance ? currentBalance - projectExpensesTotal : null;

  const addSectionAItem = () => {
    setSectionAItems([
      ...sectionAItems,
      { id: Date.now().toString(), description: '', amount: 0 },
    ]);
  };

  const addSectionBItem = () => {
    setSectionBItems([
      ...sectionBItems,
      { id: Date.now().toString(), description: '', amount: 0 },
    ]);
  };

  const addProjectExpense = () => {
    setProjectExpenses([
      ...projectExpenses,
      { id: Date.now().toString(), project_name: '', amount: 0 },
    ]);
  };

  const updateSectionAItem = (id: string, field: string, value: string | number) => {
    setSectionAItems(
      sectionAItems.map((item) =>
        item.id === id ? { ...item, [field]: value } : item
      )
    );
  };

  const updateSectionBItem = (id: string, field: string, value: string | number) => {
    setSectionBItems(
      sectionBItems.map((item) =>
        item.id === id ? { ...item, [field]: value } : item
      )
    );
  };

  const updateProjectExpense = (id: string, field: string, value: string | number) => {
    setProjectExpenses(
      projectExpenses.map((pe) =>
        pe.id === id ? { ...pe, [field]: value } : pe
      )
    );
  };

  const removeSectionAItem = (id: string) => {
    if (sectionAItems.length > 1) {
      setSectionAItems(sectionAItems.filter((item) => item.id !== id));
    }
  };

  const removeSectionBItem = (id: string) => {
    if (sectionBItems.length > 1) {
      setSectionBItems(sectionBItems.filter((item) => item.id !== id));
    }
  };

  const removeProjectExpense = (id: string) => {
    if (projectExpenses.length > 1) {
      setProjectExpenses(projectExpenses.filter((pe) => pe.id !== id));
    }
  };

  const handleSave = async (send: boolean = false) => {
    setSaving(true);
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1500));
    setSaving(false);
    router.push('/fund-requests');
  };

  return (
    <div className="min-h-screen">
      <Header title="New Fund Request" subtitle="Create a new fund disbursement request" />

      <div className="p-6">
        {/* Back button */}
        <Link
          href="/fund-requests"
          className="mb-6 inline-flex items-center text-sm text-navy-600 hover:text-navy-900"
        >
          <ArrowLeft className="mr-1 h-4 w-4" />
          Back to Fund Requests
        </Link>

        <div className="grid gap-6 lg:grid-cols-3">
          {/* Main form - 2 columns */}
          <div className="lg:col-span-2 space-y-6">
            {/* Basic Info */}
            <div className="card p-5">
              <h3 className="mb-4 text-sm font-semibold text-navy-900">Basic Information</h3>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-sm font-medium text-navy-700">
                    Entity
                  </label>
                  <select
                    value={entity}
                    onChange={(e) => setEntity(e.target.value)}
                    className="input"
                  >
                    {ENTITIES.map((e) => (
                      <option key={e.code} value={e.code}>
                        {e.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-navy-700">
                    Payment Date
                  </label>
                  <input
                    type="date"
                    value={paymentDate}
                    onChange={(e) => setPaymentDate(e.target.value)}
                    className="input"
                  />
                </div>
              </div>
            </div>

            {/* Section A */}
            <div className="card p-5">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-navy-900">A. Regular Expenses</h3>
                  <p className="text-xs text-navy-500">Fixed recurring expenses</p>
                </div>
                <button onClick={addSectionAItem} className="btn btn-secondary px-3 py-1.5 text-sm">
                  <Plus className="mr-1 h-4 w-4" />
                  Add Row
                </button>
              </div>

              <div className="space-y-3">
                {/* Header */}
                <div className="grid grid-cols-12 gap-3 text-xs font-semibold text-navy-500 uppercase tracking-wider">
                  <div className="col-span-1">#</div>
                  <div className="col-span-7">Description</div>
                  <div className="col-span-3 text-right">Amount (PHP)</div>
                  <div className="col-span-1"></div>
                </div>

                {/* Items */}
                {sectionAItems.map((item, index) => (
                  <div key={item.id} className="grid grid-cols-12 gap-3 items-center">
                    <div className="col-span-1 text-sm text-navy-500">{index + 1}</div>
                    <div className="col-span-7">
                      <input
                        type="text"
                        value={item.description}
                        onChange={(e) => updateSectionAItem(item.id, 'description', e.target.value)}
                        className="input"
                        placeholder="e.g., Office Rental"
                      />
                    </div>
                    <div className="col-span-3">
                      <input
                        type="number"
                        value={item.amount || ''}
                        onChange={(e) => updateSectionAItem(item.id, 'amount', parseFloat(e.target.value) || 0)}
                        className="input text-right currency"
                        placeholder="0"
                      />
                    </div>
                    <div className="col-span-1 flex justify-center">
                      <button
                        onClick={() => removeSectionAItem(item.id)}
                        className="btn btn-ghost p-1 text-navy-400 hover:text-red-500"
                        disabled={sectionAItems.length === 1}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                ))}

                {/* Subtotal */}
                <div className="grid grid-cols-12 gap-3 items-center pt-3 border-t border-navy-100">
                  <div className="col-span-8 text-sm font-semibold text-navy-700">Sub-Total Section A</div>
                  <div className="col-span-3 text-right">
                    <span className="text-lg font-semibold text-navy-900 currency bg-gold-100 px-3 py-1 rounded">
                      {formatCurrency(sectionATotal)}
                    </span>
                  </div>
                  <div className="col-span-1"></div>
                </div>
              </div>
            </div>

            {/* Section B */}
            <div className="card p-5">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-navy-900">B. Others</h3>
                  <p className="text-xs text-navy-500">One-time or irregular expenses</p>
                </div>
                <button onClick={addSectionBItem} className="btn btn-secondary px-3 py-1.5 text-sm">
                  <Plus className="mr-1 h-4 w-4" />
                  Add Row
                </button>
              </div>

              <div className="space-y-3">
                {/* Header */}
                <div className="grid grid-cols-12 gap-3 text-xs font-semibold text-navy-500 uppercase tracking-wider">
                  <div className="col-span-1">#</div>
                  <div className="col-span-7">Description</div>
                  <div className="col-span-3 text-right">Amount (PHP)</div>
                  <div className="col-span-1"></div>
                </div>

                {/* Items */}
                {sectionBItems.map((item, index) => (
                  <div key={item.id} className="grid grid-cols-12 gap-3 items-center">
                    <div className="col-span-1 text-sm text-navy-500">{index + 1}</div>
                    <div className="col-span-7">
                      <input
                        type="text"
                        value={item.description}
                        onChange={(e) => updateSectionBItem(item.id, 'description', e.target.value)}
                        className="input"
                        placeholder="e.g., Consultation Fee"
                      />
                    </div>
                    <div className="col-span-3">
                      <input
                        type="number"
                        value={item.amount || ''}
                        onChange={(e) => updateSectionBItem(item.id, 'amount', parseFloat(e.target.value) || 0)}
                        className="input text-right currency"
                        placeholder="0"
                      />
                    </div>
                    <div className="col-span-1 flex justify-center">
                      <button
                        onClick={() => removeSectionBItem(item.id)}
                        className="btn btn-ghost p-1 text-navy-400 hover:text-red-500"
                        disabled={sectionBItems.length === 1}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                ))}

                {/* Subtotal */}
                <div className="grid grid-cols-12 gap-3 items-center pt-3 border-t border-navy-100">
                  <div className="col-span-8 text-sm font-semibold text-navy-700">Sub-Total Section B</div>
                  <div className="col-span-3 text-right">
                    <span className="text-lg font-semibold text-navy-900 currency bg-gold-100 px-3 py-1 rounded">
                      {formatCurrency(sectionBTotal)}
                    </span>
                  </div>
                  <div className="col-span-1"></div>
                </div>
              </div>
            </div>
          </div>

          {/* Sidebar - 1 column */}
          <div className="space-y-6">
            {/* Overall Total */}
            <div className="card p-5 bg-navy-900 text-white">
              <p className="text-sm text-navy-300">OVERALL TOTAL</p>
              <p className="mt-2 text-3xl font-bold currency">{formatCurrency(overallTotal)}</p>
            </div>

            {/* Reference Info */}
            <div className="card p-5">
              <h3 className="mb-4 text-sm font-semibold text-navy-900">Reference Information</h3>

              <div className="space-y-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-navy-700">
                    Current Fund Balance
                  </label>
                  <input
                    type="number"
                    value={currentBalance || ''}
                    onChange={(e) => setCurrentBalance(parseFloat(e.target.value) || null)}
                    className="input text-right currency"
                    placeholder="Enter current balance"
                  />
                </div>

                <div>
                  <div className="mb-2 flex items-center justify-between">
                    <label className="text-sm font-medium text-navy-700">Project Expenses</label>
                    <button
                      onClick={addProjectExpense}
                      className="text-xs text-navy-600 hover:text-navy-900"
                    >
                      + Add Project
                    </button>
                  </div>
                  <div className="space-y-2">
                    {projectExpenses.map((pe) => (
                      <div key={pe.id} className="flex gap-2">
                        <input
                          type="text"
                          value={pe.project_name}
                          onChange={(e) => updateProjectExpense(pe.id, 'project_name', e.target.value)}
                          className="input flex-1 text-sm"
                          placeholder="Project name"
                        />
                        <input
                          type="number"
                          value={pe.amount || ''}
                          onChange={(e) => updateProjectExpense(pe.id, 'amount', parseFloat(e.target.value) || 0)}
                          className="input w-28 text-right text-sm currency"
                          placeholder="0"
                        />
                        <button
                          onClick={() => removeProjectExpense(pe.id)}
                          className="btn btn-ghost p-1 text-navy-400 hover:text-red-500"
                          disabled={projectExpenses.length === 1}
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="border-t border-navy-100 pt-4">
                  <div className="flex justify-between text-sm">
                    <span className="text-navy-600">Project Expenses Total</span>
                    <span className="font-medium text-navy-900 currency">
                      {formatCurrency(projectExpensesTotal)}
                    </span>
                  </div>
                  {remainingFund !== null && (
                    <div className="mt-2 flex justify-between text-sm">
                      <span className="text-navy-600">Remaining Fund</span>
                      <span
                        className={`font-semibold currency ${
                          remainingFund < 0 ? 'text-red-600' : 'text-emerald-600'
                        }`}
                      >
                        {formatCurrency(remainingFund)}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="space-y-2">
              <button
                onClick={() => handleSave(true)}
                disabled={saving}
                className="btn btn-primary w-full px-4 py-3"
              >
                <Send className="mr-2 h-4 w-4" />
                {saving ? 'Sending...' : 'Send to Telegram'}
              </button>
              <button
                onClick={() => handleSave(false)}
                disabled={saving}
                className="btn btn-secondary w-full px-4 py-2.5"
              >
                <Save className="mr-2 h-4 w-4" />
                Save as Draft
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

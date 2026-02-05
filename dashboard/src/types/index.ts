export interface KPIData {
  label: string;
  value: number;
  formatted_value: string;
  change_percent: number | null;
  change_direction: 'up' | 'down' | 'neutral' | null;
}

export interface BudgetStatus {
  entity: string;
  entity_name: string;
  utilization_percent: number;
  status: 'ok' | 'warning' | 'critical' | 'exceeded';
  budget_total: number;
  actual_total: number;
}

export interface AlertItem {
  id: number;
  entity: string;
  message: string;
  severity: 'info' | 'warning' | 'critical';
  created_at: string;
}

export interface DashboardSummary {
  period: string;
  kpis: KPIData[];
  budget_status: BudgetStatus[];
  recent_alerts: AlertItem[];
  pending_approvals_count: number;
  pending_approvals_total: number;
}

export interface BudgetItem {
  account_code: string;
  account_name: string;
  category: string;
  budget_amount: number;
  actual_amount: number;
  variance_amount: number;
  variance_percent: number;
  utilization_percent: number;
  status: 'ok' | 'warning' | 'critical' | 'exceeded';
}

export interface BudgetSummary {
  entity: string;
  entity_name: string;
  period: string;
  total_budget: number;
  total_actual: number;
  total_variance: number;
  overall_utilization: number;
  items: BudgetItem[];
}

export interface Transaction {
  id: string;
  source: string;
  source_bank: string | null;
  entity: string;
  txn_date: string;
  description: string | null;
  merchant: string | null;
  amount: number;
  currency: string;
  account_code: string | null;
  account_name: string | null;
  category: string | null;
  classification_method: string | null;
  classification_confidence: number | null;
  approved: boolean;
  approved_by: string | null;
  anomaly_flag: boolean;
  anomaly_reason: string | null;
  created_at: string;
}

export interface TransactionListResponse {
  items: Transaction[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ApprovalItem {
  id: number;
  request_type: string;
  reference_id: string | null;
  entity: string | null;
  amount: number | null;
  description: string | null;
  status: string;
  requested_by: string | null;
  requested_at: string;
  telegram_msg_id: string | null;
  notes: string | null;
}

export interface ApprovalListResponse {
  items: ApprovalItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface FundRequestSummary {
  id: number;
  entity: string;
  request_date: string;
  payment_date: string;
  period_label: string | null;
  section_a_total: number;
  section_b_total: number;
  overall_total: number;
  current_fund_balance: number | null;
  remaining_fund: number | null;
  status: string;
  approved_by: string | null;
  approved_at: string | null;
  google_drive_url: string | null;
  created_at: string;
}

export interface FundRequestListResponse {
  items: FundRequestSummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface FundRequestItem {
  id?: number;
  description: string;
  amount: number;
  category?: string;
  vendor?: string;
  notes?: string;
}

export interface ProjectExpense {
  project_name: string;
  amount: number;
}

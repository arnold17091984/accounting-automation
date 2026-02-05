-- =============================================================================
-- Accounting Automation System - Database Schema
-- =============================================================================
-- PostgreSQL 15+
-- Run: psql -h localhost -U accounting -d accounting_automation -f schema.sql
-- =============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- -----------------------------------------------------------------------------
-- Table: transactions
-- All financial transactions from all sources
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS transactions (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source                      VARCHAR(50) NOT NULL,       -- 'credit_card', 'game_record', 'expense_form', 'payroll', 'pos'
    source_bank                 VARCHAR(50),                -- 'unionbank', 'bdo', 'gcash', null
    entity                      VARCHAR(50) NOT NULL,       -- 'solaire', 'cod', 'royce', 'manila_junket', 'tours', 'midori'
    txn_date                    DATE NOT NULL,
    description                 TEXT,
    merchant                    VARCHAR(255),
    amount                      DECIMAL(15,2) NOT NULL,
    currency                    VARCHAR(3) DEFAULT 'PHP',
    account_code                VARCHAR(50),                -- chart of accounts code
    account_name                VARCHAR(255),               -- chart of accounts name
    category                    VARCHAR(100),               -- 'revenue', 'expense', 'salary', 'commission', 'company_car', 'depreciation', 'cos', 'bank_charge'
    classification_method       VARCHAR(20),                -- 'lookup', 'claude', 'human'
    classification_confidence   DECIMAL(3,2),               -- 0.00–1.00
    qb_journal_id               VARCHAR(100),               -- QuickBooks journal entry ID after posting
    duplicate_flag              BOOLEAN DEFAULT FALSE,
    anomaly_flag                BOOLEAN DEFAULT FALSE,
    anomaly_reason              TEXT,
    approved                    BOOLEAN DEFAULT FALSE,
    approved_by                 VARCHAR(100),
    approved_at                 TIMESTAMP,
    raw_data                    JSONB,                      -- original source data
    created_at                  TIMESTAMP DEFAULT NOW(),
    updated_at                  TIMESTAMP DEFAULT NOW()
);

-- Indexes for transactions
CREATE INDEX IF NOT EXISTS idx_txn_entity_date ON transactions(entity, txn_date);
CREATE INDEX IF NOT EXISTS idx_txn_source ON transactions(source);
CREATE INDEX IF NOT EXISTS idx_txn_merchant ON transactions(merchant);
CREATE INDEX IF NOT EXISTS idx_txn_category ON transactions(category);
CREATE INDEX IF NOT EXISTS idx_txn_anomaly ON transactions(anomaly_flag) WHERE anomaly_flag = TRUE;
CREATE INDEX IF NOT EXISTS idx_txn_pending_approval ON transactions(approved) WHERE approved = FALSE;
CREATE INDEX IF NOT EXISTS idx_txn_created_at ON transactions(created_at);

-- -----------------------------------------------------------------------------
-- Table: merchant_lookup
-- Known merchant → category mappings for fast classification
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS merchant_lookup (
    id                  SERIAL PRIMARY KEY,
    merchant_pattern    VARCHAR(255) NOT NULL,      -- regex or exact match pattern
    account_code        VARCHAR(50) NOT NULL,
    account_name        VARCHAR(255) NOT NULL,
    entity_default      VARCHAR(50),                -- default entity assignment (null = all entities)
    category            VARCHAR(100) NOT NULL,
    confidence          DECIMAL(3,2) DEFAULT 1.00,
    source              VARCHAR(20) DEFAULT 'manual', -- 'manual', 'claude_learned'
    usage_count         INTEGER DEFAULT 0,
    last_used_at        TIMESTAMP,
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_merchant_pattern ON merchant_lookup(merchant_pattern);
CREATE INDEX IF NOT EXISTS idx_merchant_category ON merchant_lookup(category);
CREATE INDEX IF NOT EXISTS idx_merchant_usage ON merchant_lookup(usage_count DESC);

-- -----------------------------------------------------------------------------
-- Table: budgets
-- Monthly budget per entity per account
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS budgets (
    id              SERIAL PRIMARY KEY,
    entity          VARCHAR(50) NOT NULL,
    account_code    VARCHAR(50) NOT NULL,
    account_name    VARCHAR(255) NOT NULL,
    category        VARCHAR(100) NOT NULL,
    year            INTEGER NOT NULL,
    month           INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    budget_amount   DECIMAL(15,2) NOT NULL,
    qb_budget_id    VARCHAR(100),
    notes           TEXT,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_budget_entity_account_period
    ON budgets(entity, account_code, year, month);
CREATE INDEX IF NOT EXISTS idx_budget_period ON budgets(year, month);

-- -----------------------------------------------------------------------------
-- Table: budget_alerts
-- Log of threshold alerts sent
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS budget_alerts (
    id              SERIAL PRIMARY KEY,
    entity          VARCHAR(50) NOT NULL,
    account_code    VARCHAR(50) NOT NULL,
    account_name    VARCHAR(255),
    year            INTEGER NOT NULL,
    month           INTEGER NOT NULL,
    threshold_pct   INTEGER NOT NULL,           -- 70, 90, 100
    actual_amount   DECIMAL(15,2) NOT NULL,
    budget_amount   DECIMAL(15,2) NOT NULL,
    actual_pct      DECIMAL(5,2) NOT NULL,
    telegram_msg_id VARCHAR(100),
    acknowledged    BOOLEAN DEFAULT FALSE,
    acknowledged_by VARCHAR(100),
    acknowledged_at TIMESTAMP,
    sent_at         TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alert_entity_period ON budget_alerts(entity, year, month);
CREATE INDEX IF NOT EXISTS idx_alert_threshold ON budget_alerts(threshold_pct);
CREATE INDEX IF NOT EXISTS idx_alert_unacknowledged ON budget_alerts(acknowledged) WHERE acknowledged = FALSE;

-- -----------------------------------------------------------------------------
-- Table: approval_log
-- All approval actions (expenses, P&L review, transfers, budget overrides)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS approval_log (
    id              SERIAL PRIMARY KEY,
    request_type    VARCHAR(50) NOT NULL,       -- 'expense', 'pl_review', 'transfer', 'budget_override'
    reference_id    UUID,                       -- FK to transactions or other table
    reference_table VARCHAR(50),                -- 'transactions', 'transfers', etc.
    amount          DECIMAL(15,2),
    entity          VARCHAR(50),
    description     TEXT,
    status          VARCHAR(20) NOT NULL,       -- 'pending', 'approved', 'rejected', 'auto_approved'
    requested_by    VARCHAR(100),               -- telegram user ID or system
    requested_at    TIMESTAMP DEFAULT NOW(),
    decided_at      TIMESTAMP,
    decided_by      VARCHAR(100),               -- telegram user ID
    telegram_msg_id VARCHAR(100),
    notes           TEXT,
    metadata        JSONB                       -- additional context
);

CREATE INDEX IF NOT EXISTS idx_approval_status ON approval_log(status);
CREATE INDEX IF NOT EXISTS idx_approval_type ON approval_log(request_type);
CREATE INDEX IF NOT EXISTS idx_approval_pending ON approval_log(status) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_approval_reference ON approval_log(reference_id);

-- -----------------------------------------------------------------------------
-- Table: audit_log
-- All system actions for debugging and compliance
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_log (
    id              SERIAL PRIMARY KEY,
    action          VARCHAR(100) NOT NULL,      -- 'workflow_run', 'qb_post', 'telegram_send', 'claude_classify', etc.
    workflow        VARCHAR(100),               -- n8n workflow name
    entity          VARCHAR(50),
    user_id         VARCHAR(100),               -- telegram user ID or 'system'
    details         JSONB,                      -- action-specific details
    status          VARCHAR(20) NOT NULL,       -- 'success', 'error', 'warning'
    error_message   TEXT,
    duration_ms     INTEGER,                    -- execution duration
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_status ON audit_log(status);
CREATE INDEX IF NOT EXISTS idx_audit_workflow ON audit_log(workflow);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_errors ON audit_log(status) WHERE status = 'error';

-- -----------------------------------------------------------------------------
-- Table: claude_api_log
-- Log all Claude API calls for cost tracking and improvement
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS claude_api_log (
    id              SERIAL PRIMARY KEY,
    purpose         VARCHAR(100) NOT NULL,      -- 'classify', 'ocr', 'anomaly', 'budget_analysis'
    model           VARCHAR(100) NOT NULL,
    prompt_tokens   INTEGER,
    completion_tokens INTEGER,
    total_tokens    INTEGER,
    prompt_hash     VARCHAR(64),                -- SHA256 of prompt for dedup analysis
    response_hash   VARCHAR(64),                -- SHA256 of response
    latency_ms      INTEGER,
    success         BOOLEAN DEFAULT TRUE,
    error_message   TEXT,
    entity          VARCHAR(50),
    metadata        JSONB,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_claude_purpose ON claude_api_log(purpose);
CREATE INDEX IF NOT EXISTS idx_claude_created ON claude_api_log(created_at);
CREATE INDEX IF NOT EXISTS idx_claude_model ON claude_api_log(model);

-- -----------------------------------------------------------------------------
-- Table: file_uploads
-- Track uploaded files (CSV, PDF statements)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS file_uploads (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename        VARCHAR(255) NOT NULL,
    file_type       VARCHAR(20) NOT NULL,       -- 'csv', 'pdf', 'xlsx'
    source_bank     VARCHAR(50),
    entity          VARCHAR(50),
    file_size       INTEGER,
    file_hash       VARCHAR(64),                -- SHA256 for dedup
    storage_path    TEXT,                       -- local path or Google Drive ID
    uploaded_by     VARCHAR(100),               -- telegram user ID
    processed       BOOLEAN DEFAULT FALSE,
    processed_at    TIMESTAMP,
    transaction_count INTEGER,                  -- number of transactions extracted
    error_message   TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_upload_hash ON file_uploads(file_hash);
CREATE INDEX IF NOT EXISTS idx_upload_processed ON file_uploads(processed);
CREATE INDEX IF NOT EXISTS idx_upload_entity ON file_uploads(entity);

-- -----------------------------------------------------------------------------
-- Functions and Triggers
-- -----------------------------------------------------------------------------

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at trigger to relevant tables
DROP TRIGGER IF EXISTS update_transactions_updated_at ON transactions;
CREATE TRIGGER update_transactions_updated_at
    BEFORE UPDATE ON transactions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_merchant_lookup_updated_at ON merchant_lookup;
CREATE TRIGGER update_merchant_lookup_updated_at
    BEFORE UPDATE ON merchant_lookup
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_budgets_updated_at ON budgets;
CREATE TRIGGER update_budgets_updated_at
    BEFORE UPDATE ON budgets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to increment merchant usage count
CREATE OR REPLACE FUNCTION increment_merchant_usage(pattern VARCHAR)
RETURNS VOID AS $$
BEGIN
    UPDATE merchant_lookup
    SET usage_count = usage_count + 1,
        last_used_at = NOW()
    WHERE merchant_pattern = pattern;
END;
$$ language 'plpgsql';

-- -----------------------------------------------------------------------------
-- Views
-- -----------------------------------------------------------------------------

-- View: Monthly spending summary by entity and category
CREATE OR REPLACE VIEW v_monthly_spending AS
SELECT
    entity,
    category,
    DATE_TRUNC('month', txn_date) AS month,
    COUNT(*) AS transaction_count,
    SUM(amount) AS total_amount,
    AVG(amount) AS avg_amount
FROM transactions
WHERE category IN ('expense', 'salary', 'commission', 'company_car', 'cos', 'bank_charge')
GROUP BY entity, category, DATE_TRUNC('month', txn_date);

-- View: Budget variance summary
CREATE OR REPLACE VIEW v_budget_variance AS
SELECT
    b.entity,
    b.account_code,
    b.account_name,
    b.year,
    b.month,
    b.budget_amount,
    COALESCE(SUM(t.amount), 0) AS actual_amount,
    b.budget_amount - COALESCE(SUM(t.amount), 0) AS variance,
    CASE
        WHEN b.budget_amount > 0
        THEN ROUND((COALESCE(SUM(t.amount), 0) / b.budget_amount) * 100, 2)
        ELSE 0
    END AS utilization_pct
FROM budgets b
LEFT JOIN transactions t ON
    t.entity = b.entity
    AND t.account_code = b.account_code
    AND EXTRACT(YEAR FROM t.txn_date) = b.year
    AND EXTRACT(MONTH FROM t.txn_date) = b.month
GROUP BY b.entity, b.account_code, b.account_name, b.year, b.month, b.budget_amount;

-- View: Pending approvals
CREATE OR REPLACE VIEW v_pending_approvals AS
SELECT
    id,
    request_type,
    entity,
    amount,
    description,
    requested_by,
    requested_at,
    telegram_msg_id,
    AGE(NOW(), requested_at) AS pending_duration
FROM approval_log
WHERE status = 'pending'
ORDER BY requested_at;

-- View: Classification accuracy by entity
CREATE OR REPLACE VIEW v_classification_stats AS
SELECT
    entity,
    classification_method,
    COUNT(*) AS count,
    AVG(classification_confidence) AS avg_confidence,
    SUM(CASE WHEN anomaly_flag THEN 1 ELSE 0 END) AS anomaly_count
FROM transactions
WHERE classification_method IS NOT NULL
GROUP BY entity, classification_method;

-- =============================================================================
-- End of Schema
-- =============================================================================

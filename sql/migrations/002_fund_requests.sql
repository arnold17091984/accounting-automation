-- =============================================================================
-- Migration: 002_fund_requests.sql
-- Phase 7: Fund Request System Tables
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Table: recurring_expenses
-- Master table for fixed recurring expenses (rent, subscriptions, etc.)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS recurring_expenses (
    id                  SERIAL PRIMARY KEY,
    entity              VARCHAR(50) NOT NULL,
    description         TEXT NOT NULL,
    category            VARCHAR(100),           -- 'rental', 'legal', 'utilities', 'subscription', etc.
    amount              DECIMAL(15,2) NOT NULL,
    currency            VARCHAR(3) DEFAULT 'PHP',
    frequency           VARCHAR(20) NOT NULL,   -- 'monthly', 'quarterly', 'semi-monthly', 'annual'
    payment_day         INTEGER,                -- Day of month for payment (1-31)
    vendor              VARCHAR(255),
    account_code        VARCHAR(50),            -- Chart of accounts code
    notes               TEXT,
    is_active           BOOLEAN DEFAULT TRUE,
    last_payment_date   DATE,
    next_payment_date   DATE,
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recurring_entity ON recurring_expenses(entity);
CREATE INDEX IF NOT EXISTS idx_recurring_active ON recurring_expenses(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_recurring_next_payment ON recurring_expenses(next_payment_date);
CREATE INDEX IF NOT EXISTS idx_recurring_category ON recurring_expenses(category);

-- Apply updated_at trigger
DROP TRIGGER IF EXISTS update_recurring_expenses_updated_at ON recurring_expenses;
CREATE TRIGGER update_recurring_expenses_updated_at
    BEFORE UPDATE ON recurring_expenses
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- -----------------------------------------------------------------------------
-- Table: fund_requests
-- Fund request headers (one per request submission)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fund_requests (
    id                      SERIAL PRIMARY KEY,
    entity                  VARCHAR(50) NOT NULL,
    request_date            DATE NOT NULL,
    payment_date            DATE NOT NULL,          -- Target payment date (5th or 20th)
    period_label            VARCHAR(50),            -- e.g., "February 2026 - 1st Half"

    -- Section totals
    section_a_total         DECIMAL(15,2) DEFAULT 0,  -- Regular/recurring expenses
    section_b_total         DECIMAL(15,2) DEFAULT 0,  -- Other/one-time expenses
    overall_total           DECIMAL(15,2) DEFAULT 0,

    -- Fund balance info (reference)
    current_fund_balance    DECIMAL(15,2),
    project_expenses_total  DECIMAL(15,2),
    remaining_fund          DECIMAL(15,2),

    -- File storage
    excel_file_path         TEXT,
    google_drive_id         VARCHAR(255),
    google_drive_url        TEXT,

    -- Telegram delivery
    telegram_chat_id        VARCHAR(100),
    telegram_msg_id         VARCHAR(100),

    -- Status tracking
    status                  VARCHAR(20) DEFAULT 'draft',  -- 'draft', 'sent', 'approved', 'rejected'
    approved_by             VARCHAR(100),
    approved_at             TIMESTAMP,
    rejection_reason        TEXT,

    -- Audit
    created_by              VARCHAR(100),
    created_at              TIMESTAMP DEFAULT NOW(),
    updated_at              TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fund_req_entity ON fund_requests(entity);
CREATE INDEX IF NOT EXISTS idx_fund_req_payment_date ON fund_requests(payment_date);
CREATE INDEX IF NOT EXISTS idx_fund_req_status ON fund_requests(status);
CREATE INDEX IF NOT EXISTS idx_fund_req_created ON fund_requests(created_at);

DROP TRIGGER IF EXISTS update_fund_requests_updated_at ON fund_requests;
CREATE TRIGGER update_fund_requests_updated_at
    BEFORE UPDATE ON fund_requests
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- -----------------------------------------------------------------------------
-- Table: fund_request_items
-- Line items for each fund request
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fund_request_items (
    id                  SERIAL PRIMARY KEY,
    fund_request_id     INTEGER NOT NULL REFERENCES fund_requests(id) ON DELETE CASCADE,
    section             VARCHAR(1) NOT NULL CHECK (section IN ('A', 'B')),  -- 'A' or 'B'
    line_number         INTEGER NOT NULL,           -- Order within section
    description         TEXT NOT NULL,
    amount              DECIMAL(15,2) NOT NULL,
    currency            VARCHAR(3) DEFAULT 'PHP',
    category            VARCHAR(100),               -- 'rental', 'salary', 'credit_card', etc.
    vendor              VARCHAR(255),
    account_code        VARCHAR(50),
    reference_id        UUID,                       -- Link to transactions or recurring_expenses
    reference_type      VARCHAR(50),                -- 'recurring_expense', 'transaction', 'manual'
    notes               TEXT,
    created_at          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fund_item_request ON fund_request_items(fund_request_id);
CREATE INDEX IF NOT EXISTS idx_fund_item_section ON fund_request_items(fund_request_id, section);

-- -----------------------------------------------------------------------------
-- Table: fund_request_projects
-- Project-wise expense breakdown (reference info in fund request)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fund_request_projects (
    id                  SERIAL PRIMARY KEY,
    fund_request_id     INTEGER NOT NULL REFERENCES fund_requests(id) ON DELETE CASCADE,
    project_name        VARCHAR(255) NOT NULL,
    amount              DECIMAL(15,2) NOT NULL,
    currency            VARCHAR(3) DEFAULT 'PHP',
    notes               TEXT,
    created_at          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fund_proj_request ON fund_request_projects(fund_request_id);

-- -----------------------------------------------------------------------------
-- Table: bank_balances
-- Track fund/bank account balances over time
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bank_balances (
    id                  SERIAL PRIMARY KEY,
    entity              VARCHAR(50) NOT NULL,
    account_name        VARCHAR(255) NOT NULL,      -- e.g., "Main Operating Fund", "BDO Savings"
    account_number      VARCHAR(50),                -- Last 4 digits or reference
    bank                VARCHAR(100),               -- 'unionbank', 'bdo', 'gcash', 'cash'
    balance             DECIMAL(15,2) NOT NULL,
    currency            VARCHAR(3) DEFAULT 'PHP',
    balance_date        DATE NOT NULL,
    balance_type        VARCHAR(20) DEFAULT 'closing',  -- 'opening', 'closing', 'intraday'
    source              VARCHAR(50) DEFAULT 'manual',   -- 'manual', 'api', 'statement'
    notes               TEXT,
    created_by          VARCHAR(100),
    created_at          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bank_bal_entity ON bank_balances(entity);
CREATE INDEX IF NOT EXISTS idx_bank_bal_date ON bank_balances(entity, balance_date);
CREATE UNIQUE INDEX IF NOT EXISTS idx_bank_bal_unique ON bank_balances(entity, account_name, balance_date, balance_type);

-- -----------------------------------------------------------------------------
-- Views for Fund Requests
-- -----------------------------------------------------------------------------

-- View: Fund request summary with item counts
CREATE OR REPLACE VIEW v_fund_request_summary AS
SELECT
    fr.id,
    fr.entity,
    fr.request_date,
    fr.payment_date,
    fr.period_label,
    fr.section_a_total,
    fr.section_b_total,
    fr.overall_total,
    fr.current_fund_balance,
    fr.remaining_fund,
    fr.status,
    fr.approved_by,
    fr.approved_at,
    fr.created_at,
    COUNT(DISTINCT CASE WHEN fri.section = 'A' THEN fri.id END) AS section_a_items,
    COUNT(DISTINCT CASE WHEN fri.section = 'B' THEN fri.id END) AS section_b_items,
    fr.google_drive_url
FROM fund_requests fr
LEFT JOIN fund_request_items fri ON fri.fund_request_id = fr.id
GROUP BY fr.id;

-- View: Upcoming recurring expenses
CREATE OR REPLACE VIEW v_upcoming_recurring AS
SELECT
    re.*,
    CASE
        WHEN re.frequency = 'monthly' THEN re.amount
        WHEN re.frequency = 'quarterly' THEN re.amount / 3
        WHEN re.frequency = 'semi-monthly' THEN re.amount * 2
        WHEN re.frequency = 'annual' THEN re.amount / 12
        ELSE re.amount
    END AS monthly_equivalent
FROM recurring_expenses re
WHERE re.is_active = TRUE
ORDER BY re.next_payment_date;

-- View: Current fund balances by entity
CREATE OR REPLACE VIEW v_current_balances AS
SELECT DISTINCT ON (entity, account_name)
    entity,
    account_name,
    account_number,
    bank,
    balance,
    currency,
    balance_date,
    source
FROM bank_balances
ORDER BY entity, account_name, balance_date DESC;

-- =============================================================================
-- End of Migration
-- =============================================================================

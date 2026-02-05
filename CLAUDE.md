# CLAUDE.md — Accounting Automation System

## Project Overview

An automated accounting system for BK Keyforce / BETRNK Group that processes financial data across 6 business entities (Solaire, COD, Royce Clark, Manila Junket, Tours BGC/BSM, Midori no Mart). The system ingests data from multiple sources, classifies transactions using Claude API, manages budgets, and delivers reports via Telegram Bot.

**Reference:** See `ARCHITECTURE.md` for the full system design, data flows, and implementation roadmap.

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Orchestration | n8n (self-hosted) | Workflow automation, scheduling, routing |
| AI | Claude API (Sonnet) | Transaction classification, OCR, anomaly detection, report generation |
| Accounting | QuickBooks Online API | Ledger, journal entries, P&L reports, budgets |
| Database | PostgreSQL | Transaction store, merchant lookup, audit logs |
| Notifications | Telegram Bot API | Approvals, alerts, file upload, command interface |
| File Generation | Python (openpyxl, python-pptx, reportlab, matplotlib) | Excel, PowerPoint, PDF output |
| File Storage | Google Drive API | Report archiving and sharing |
| Banking | UnionBank API, BDO (manual/RPA) | Transfers, statements |
| RPA Fallback | Playwright | Bank portal automation when API unavailable |
| Dashboard | Next.js + Chart.js | Real-time executive dashboard (Phase 6) |

---

## Project Structure

```
accounting-automation/
├── CLAUDE.md                        # This file
├── ARCHITECTURE.md                  # Full system design document
├── docker-compose.yml               # n8n + PostgreSQL + services
├── .env.example                     # Environment variables template
│
├── n8n-workflows/                   # Exported n8n workflow JSONs
│   ├── 01-monthly-pl-pipeline.json
│   ├── 02-credit-card-ingestion.json
│   ├── 03-budget-variance-monitor.json
│   ├── 04-expense-approval.json
│   ├── 05-payroll-transfer.json
│   ├── 06-bank-reconciliation.json
│   ├── 07-tax-filing-support.json
│   ├── 08-telegram-command-handler.json
│   └── 09-daily-weekly-reports.json
│
├── python/                          # Python scripts called by n8n
│   ├── requirements.txt
│   ├── pl_generator/
│   │   ├── __init__.py
│   │   ├── excel_builder.py         # openpyxl P&L Excel generation
│   │   ├── pptx_builder.py          # python-pptx PowerPoint generation
│   │   ├── consolidation.py         # 3-junket FS consolidation
│   │   └── templates/               # Jinja2 / Excel templates per entity
│   │       ├── solaire_template.xlsx
│   │       ├── cod_template.xlsx
│   │       ├── royce_template.xlsx
│   │       ├── manila_junket_template.xlsx
│   │       ├── tours_template.xlsx
│   │       ├── midori_template.xlsx
│   │       └── pptx_template.pptx
│   │
│   ├── card_processor/
│   │   ├── __init__.py
│   │   ├── csv_parsers/             # Bank-specific CSV parsers
│   │   │   ├── unionbank.py
│   │   │   ├── bdo.py
│   │   │   ├── gcash.py
│   │   │   └── generic.py
│   │   ├── pdf_extractor.py         # Claude Vision PDF OCR
│   │   ├── categorizer.py           # Claude-based transaction categorization
│   │   ├── duplicate_detector.py    # Cross-reference dedup logic
│   │   └── merchant_lookup.py       # Merchant → category lookup table
│   │
│   ├── budget/
│   │   ├── __init__.py
│   │   ├── variance_calculator.py   # Budget vs actual computation
│   │   ├── threshold_checker.py     # Alert threshold logic
│   │   ├── historical_analyzer.py   # Claude-based budget suggestions
│   │   └── report_generator.py      # Budget report formatting
│   │
│   ├── tax/
│   │   ├── __init__.py
│   │   ├── bir_calculator.py        # Tax computation per form type
│   │   ├── form_generator.py        # PDF form generation
│   │   └── tax_rules.yaml           # Externalized tax rates and rules
│   │
│   ├── bank/
│   │   ├── __init__.py
│   │   ├── ub_template_generator.py # UnionBank transfer CSV builder
│   │   ├── reconciliation.py        # Bank recon logic
│   │   └── rpa_fallback.py          # Playwright scripts for bank portals
│   │
│   └── telegram/
│       ├── __init__.py
│       ├── bot_commands.py           # /budget, /pl, /cash, etc.
│       ├── approval_handler.py       # Inline keyboard approval logic
│       ├── file_handler.py           # CSV/PDF upload processing
│       └── report_formatter.py       # Telegram message formatting
│
├── config/
│   ├── chart_of_accounts.yaml       # Master chart of accounts
│   ├── entity_config.yaml           # 6 entity definitions and QB class mappings
│   ├── budget_thresholds.yaml       # Alert threshold config (70%, 90%, 100%)
│   ├── merchant_mappings.json       # Known merchant → category lookup
│   ├── telegram_acl.yaml            # User ID whitelist and permission levels
│   └── bank_parsers.yaml            # CSV column mappings per bank
│
├── prompts/                         # Claude API prompt templates
│   ├── classify_transaction.md      # Transaction categorization prompt
│   ├── anomaly_detection.md         # Anomaly flagging prompt
│   ├── pdf_ocr_extract.md           # PDF statement extraction prompt
│   ├── budget_analysis.md           # Historical budget suggestion prompt
│   ├── tax_calculation.md           # Tax computation prompt
│   └── report_narrative.md          # Executive summary generation prompt
│
├── sql/
│   ├── schema.sql                   # PostgreSQL schema
│   ├── seed_merchants.sql           # Initial merchant lookup data
│   └── migrations/                  # Schema migrations
│
├── tests/
│   ├── test_csv_parsers.py
│   ├── test_categorizer.py
│   ├── test_budget_variance.py
│   ├── test_duplicate_detector.py
│   ├── test_pl_generator.py
│   └── fixtures/                    # Sample CSV/PDF/data for testing
│       ├── sample_ub_statement.csv
│       ├── sample_bdo_statement.pdf
│       ├── sample_gcash_export.csv
│       ├── sample_game_record.csv
│       └── sample_payroll.csv
│
└── docs/
    ├── setup-guide.md               # Infrastructure setup instructions
    ├── n8n-workflow-guide.md         # How to modify n8n workflows
    ├── telegram-bot-setup.md        # Bot registration and config
    ├── quickbooks-setup.md          # QB Classes, Budgets, API setup
    └── runbook.md                   # Operational procedures and troubleshooting
```

---

## Environment Variables

```bash
# .env.example

# n8n
N8N_HOST=0.0.0.0
N8N_PORT=5678
N8N_PROTOCOL=https
N8N_ENCRYPTION_KEY=<generate-random-key>
WEBHOOK_URL=https://n8n.yourdomain.com

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=accounting_automation
POSTGRES_USER=accounting
POSTGRES_PASSWORD=<strong-password>

# Claude API
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-sonnet-4-5-20250929

# QuickBooks
QB_CLIENT_ID=<qb-client-id>
QB_CLIENT_SECRET=<qb-client-secret>
QB_REALM_ID=<qb-company-id>
QB_REDIRECT_URI=https://n8n.yourdomain.com/qb/callback
QB_REFRESH_TOKEN=<stored-in-n8n-credentials>

# Telegram
TELEGRAM_BOT_TOKEN=<bot-token-from-botfather>
TELEGRAM_WEBHOOK_SECRET=<random-secret>
TELEGRAM_ADMIN_IDS=123456789,987654321

# Google
GOOGLE_SERVICE_ACCOUNT_KEY=<path-to-service-account.json>
GOOGLE_DRIVE_FOLDER_ID=<shared-drive-folder-id>

# UnionBank (if API available)
UB_CLIENT_ID=<ub-client-id>
UB_CLIENT_SECRET=<ub-client-secret>
UB_PARTNER_ID=<ub-partner-id>
```

---

## Database Schema (Core Tables)

```sql
-- Transactions: all financial transactions from all sources
CREATE TABLE transactions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source          VARCHAR(50) NOT NULL,      -- 'credit_card', 'game_record', 'expense_form', 'payroll', 'pos'
    source_bank     VARCHAR(50),               -- 'unionbank', 'bdo', 'gcash', null
    entity          VARCHAR(50) NOT NULL,      -- 'solaire', 'cod', 'royce', 'manila_junket', 'tours', 'midori'
    txn_date        DATE NOT NULL,
    description     TEXT,
    merchant        VARCHAR(255),
    amount          DECIMAL(15,2) NOT NULL,
    currency        VARCHAR(3) DEFAULT 'PHP',
    account_code    VARCHAR(50),               -- chart of accounts code
    account_name    VARCHAR(255),              -- chart of accounts name
    category        VARCHAR(100),              -- 'revenue', 'expense', 'salary', 'commission', 'company_car', 'depreciation', 'cos', 'bank_charge'
    classification_method VARCHAR(20),         -- 'lookup', 'claude', 'human'
    classification_confidence DECIMAL(3,2),    -- 0.00–1.00
    qb_journal_id   VARCHAR(100),             -- QuickBooks journal entry ID after posting
    duplicate_flag   BOOLEAN DEFAULT FALSE,
    anomaly_flag     BOOLEAN DEFAULT FALSE,
    anomaly_reason   TEXT,
    approved         BOOLEAN DEFAULT FALSE,
    approved_by      VARCHAR(100),
    approved_at      TIMESTAMP,
    raw_data         JSONB,                    -- original source data
    created_at       TIMESTAMP DEFAULT NOW(),
    updated_at       TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_txn_entity_date ON transactions(entity, txn_date);
CREATE INDEX idx_txn_source ON transactions(source);
CREATE INDEX idx_txn_merchant ON transactions(merchant);
CREATE INDEX idx_txn_anomaly ON transactions(anomaly_flag) WHERE anomaly_flag = TRUE;

-- Merchant lookup: known merchant → category mappings
CREATE TABLE merchant_lookup (
    id              SERIAL PRIMARY KEY,
    merchant_pattern VARCHAR(255) NOT NULL,    -- regex or exact match
    account_code    VARCHAR(50) NOT NULL,
    account_name    VARCHAR(255) NOT NULL,
    entity_default  VARCHAR(50),               -- default entity assignment
    category        VARCHAR(100) NOT NULL,
    confidence      DECIMAL(3,2) DEFAULT 1.00,
    source          VARCHAR(20) DEFAULT 'manual', -- 'manual', 'claude_learned'
    usage_count     INTEGER DEFAULT 0,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_merchant_pattern ON merchant_lookup(merchant_pattern);

-- Budgets: monthly budget per entity per account
CREATE TABLE budgets (
    id              SERIAL PRIMARY KEY,
    entity          VARCHAR(50) NOT NULL,
    account_code    VARCHAR(50) NOT NULL,
    account_name    VARCHAR(255) NOT NULL,
    category        VARCHAR(100) NOT NULL,
    year            INTEGER NOT NULL,
    month           INTEGER NOT NULL,          -- 1-12
    budget_amount   DECIMAL(15,2) NOT NULL,
    qb_budget_id    VARCHAR(100),
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_budget_entity_account_period ON budgets(entity, account_code, year, month);

-- Budget alerts: log of threshold alerts sent
CREATE TABLE budget_alerts (
    id              SERIAL PRIMARY KEY,
    entity          VARCHAR(50) NOT NULL,
    account_code    VARCHAR(50) NOT NULL,
    year            INTEGER NOT NULL,
    month           INTEGER NOT NULL,
    threshold_pct   INTEGER NOT NULL,          -- 70, 90, 100
    actual_amount   DECIMAL(15,2) NOT NULL,
    budget_amount   DECIMAL(15,2) NOT NULL,
    actual_pct      DECIMAL(5,2) NOT NULL,
    telegram_msg_id VARCHAR(100),
    sent_at         TIMESTAMP DEFAULT NOW()
);

-- Approval log: all approval actions
CREATE TABLE approval_log (
    id              SERIAL PRIMARY KEY,
    request_type    VARCHAR(50) NOT NULL,       -- 'expense', 'pl_review', 'transfer', 'budget_override'
    reference_id    UUID,                       -- FK to transactions or other table
    amount          DECIMAL(15,2),
    entity          VARCHAR(50),
    status          VARCHAR(20) NOT NULL,       -- 'pending', 'approved', 'rejected', 'auto_approved'
    requested_at    TIMESTAMP DEFAULT NOW(),
    decided_at      TIMESTAMP,
    decided_by      VARCHAR(100),              -- telegram user ID
    telegram_msg_id VARCHAR(100),
    notes           TEXT
);

-- Audit log: all system actions
CREATE TABLE audit_log (
    id              SERIAL PRIMARY KEY,
    action          VARCHAR(100) NOT NULL,     -- 'workflow_run', 'qb_post', 'telegram_send', etc.
    workflow        VARCHAR(100),
    entity          VARCHAR(50),
    details         JSONB,
    status          VARCHAR(20) NOT NULL,      -- 'success', 'error', 'warning'
    error_message   TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);
```

---

## Claude API Prompt Guidelines

### Transaction Classification

When calling Claude API for transaction classification, always include:

1. **System prompt** with the full chart of accounts (from `config/chart_of_accounts.yaml`)
2. **Entity context** — which entity this data belongs to
3. **Few-shot examples** — include 5–10 correctly classified examples from the same entity
4. **Output format** — always request structured JSON

```python
# Example classification call
system_prompt = f"""
You are an accounting classification engine for {entity_name}.
Chart of accounts: {chart_of_accounts_yaml}

Classify each transaction into exactly one account.
Output ONLY valid JSON array. No explanation.

Categories: revenue, commission, salary, expense, company_car, depreciation, cos, bank_charge
"""

user_prompt = f"""
Classify these transactions. For each, provide:
- account_code, account_name, category, confidence (0.0-1.0)
- anomaly: true/false (flag if amount is >30% different from typical for this category)
- anomaly_reason: string (if anomaly is true)

Transactions:
{json.dumps(transactions)}

Few-shot examples of correct classifications for {entity_name}:
{json.dumps(few_shot_examples)}
"""
```

### Response Parsing

Always wrap Claude API responses in try/catch. Strip markdown fences before JSON parsing:

```python
def parse_claude_response(response_text: str) -> list[dict]:
    cleaned = response_text.strip()
    cleaned = cleaned.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Log error, flag for human review
        logger.error(f"Failed to parse Claude response: {cleaned[:200]}")
        raise ClassificationError("Claude response was not valid JSON")
```

### PDF OCR Extraction

For credit card PDF statements, use Claude's vision capability:

```python
# Send PDF as base64 image
message = {
    "role": "user",
    "content": [
        {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": base64_pdf_data
            }
        },
        {
            "type": "text",
            "text": "Extract all transactions from this credit card statement. Output JSON array with: date (YYYY-MM-DD), description, merchant, amount, reference_number. Output ONLY the JSON array."
        }
    ]
}
```

### Prompt Management

All prompts are stored in `prompts/` directory as markdown files. This allows:
- Version control via Git
- Easy A/B testing of prompt variations
- Non-developer editing (accounting team can suggest prompt improvements)
- Template variables wrapped in `{curly_braces}` are replaced at runtime

---

## n8n Workflow Conventions

### Naming
- Workflow names: `[NN] - Description` (e.g., `01 - Monthly P&L Pipeline`)
- Node names: `[Action] - Detail` (e.g., `[Fetch] - Solaire Game Records`)

### Error Handling
- Every workflow has a global error handler that sends failures to Telegram admin chat
- Critical workflows (payroll, bank transfers) require explicit human confirmation before execution
- All API calls have retry logic: 3 retries with exponential backoff

### Scheduling
| Workflow | Schedule | Description |
|---|---|---|
| Monthly P&L Pipeline | 1st of month, 9:00 AM | Full P&L generation for all entities |
| Budget Variance Check | Every transaction (webhook) | Real-time threshold checking |
| Daily Summary | Daily 6:30 PM | Spending summary to Telegram |
| Weekly Report | Monday 9:00 AM | Week-over-week comparison |
| Bank Reconciliation | Daily 7:00 AM | Auto-match bank statements |
| Tax Filing Reminder | 2 weeks before deadline | Generate BIR form drafts |
| Payroll Transfer | 14th and 28th of month | Template generation trigger |

### Data Flow Between n8n and Python

n8n calls Python scripts via the `Execute Command` node:

```bash
# n8n Execute Command node
cd /opt/accounting-automation/python && \
python -m pl_generator.excel_builder \
  --entity solaire \
  --month 2025-01 \
  --data-file /tmp/classified_data.json \
  --output-dir /tmp/output/
```

Python scripts read JSON input and write output files. n8n picks up the output files for further processing (upload to Drive, send via Telegram, etc.).

---

## Telegram Bot Implementation

### Bot Registration
1. Message @BotFather on Telegram
2. Create new bot: `/newbot`
3. Set name: `BK Accounting Bot`
4. Save the token to `.env` as `TELEGRAM_BOT_TOKEN`
5. Set webhook via n8n Telegram Trigger node

### Inline Keyboard for Approvals

```python
# Approval message with inline keyboard
keyboard = {
    "inline_keyboard": [
        [
            {"text": "✅ Approve", "callback_data": f"approve_{request_id}"},
            {"text": "❌ Reject", "callback_data": f"reject_{request_id}"}
        ],
        [
            {"text": "❓ Ask Question", "callback_data": f"question_{request_id}"},
            {"text": "📎 View Docs", "callback_data": f"docs_{request_id}"}
        ]
    ]
}
```

### Command Routing (n8n)

The `08-telegram-command-handler.json` workflow routes messages:

```
Telegram Trigger
  → Switch node (by message type):
    ├── /command → Command Router (Switch by command text)
    │   ├── /budget  → Budget snapshot workflow
    │   ├── /pl      → P&L summary workflow
    │   ├── /cash    → Cash position workflow
    │   ├── /pending → Pending approvals list
    │   ├── /status  → System health check
    │   └── /report  → Trigger report generation
    ├── callback_query → Approval Handler
    │   ├── approve_* → Process approval
    │   ├── reject_*  → Process rejection
    │   └── question_* → Open question thread
    └── document (file upload) → File Handler
        ├── .csv → CSV Parser workflow
        └── .pdf → PDF OCR workflow
```

### Access Control

```yaml
# config/telegram_acl.yaml
users:
  - telegram_id: 123456789
    name: "Koki"
    role: admin          # full access to everything
  - telegram_id: 234567890
    name: "Jeremy"
    role: accounting_manager  # approve, view, upload
  - telegram_id: 345678901
    name: "Accounting Officer"
    role: officer         # view, limited approve (≤₱10,000)
  - telegram_id: 456789012
    name: "Management"
    role: viewer          # view only, override approve

permissions:
  admin: ["*"]
  accounting_manager: ["approve", "reject", "upload", "view", "report", "budget_edit"]
  officer: ["approve_under_10k", "upload", "view", "report"]
  viewer: ["view", "report", "approve_override"]
```

---

## Development Workflow

### Local Development

```bash
# 1. Clone and setup
git clone <repo-url>
cd accounting-automation
cp .env.example .env
# Edit .env with your credentials

# 2. Start infrastructure
docker-compose up -d  # n8n + PostgreSQL

# 3. Install Python dependencies
cd python
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Run database migrations
psql -h localhost -U accounting -d accounting_automation -f sql/schema.sql
psql -h localhost -U accounting -d accounting_automation -f sql/seed_merchants.sql

# 5. Run tests
pytest tests/ -v

# 6. Import n8n workflows
# Open n8n UI → Import from file → select each JSON from n8n-workflows/
```

### Testing Strategy

- **Unit tests:** CSV parsers, categorizer, budget variance calculator, duplicate detector
- **Integration tests:** Claude API classification with sample data, QuickBooks API posting
- **End-to-end tests:** Full pipeline with sample data for one entity (Solaire)
- **Fixtures:** Sample CSV/PDF/JSON files in `tests/fixtures/` for reproducible testing

### Deployment

```bash
# Production deployment on existing GCP/DO server
docker-compose -f docker-compose.prod.yml up -d

# n8n workflows are imported once and managed via UI
# Python scripts are deployed alongside n8n container
# Telegram webhook is set automatically by n8n
```

---

## Key Design Decisions

1. **QuickBooks as Single Source of Truth** — All data flows into QB. Excel is output-only. This eliminates dual-management and ensures consistent numbers.

2. **Merchant Lookup Table first, Claude second** — Known merchants are classified instantly without AI. Claude is only called for unknowns, keeping API costs low and latency minimal.

3. **Telegram as primary interface** — Free, mobile-friendly, supports inline keyboards for approvals, file uploads for statement processing, and commands for instant reports.

4. **External tax rules (YAML)** — Tax rates are not hardcoded in prompts or code. Updatable by editing a YAML file without deployment.

5. **Phase 2 starts with Solaire** — It has the most detailed workflow documentation in the turnover files. Validate with one entity before rolling out to 5 more.

6. **Budget "learning mode" in Q1** — New budgets are based on Claude's historical analysis. First quarter runs alerts only (no hard blocks) to calibrate accuracy before enforcing.

---

## Critical Reminders

- **NEVER store credentials in code or config files** — use n8n Credential Store and `.env` (excluded from Git)
- **NEVER post to QuickBooks without validation** — all entries must pass schema validation before `JournalEntry.create()`
- **NEVER auto-approve bank transfers** — payroll and fund transfers always require human confirmation
- **ALWAYS log Claude API calls** — store prompt, response, and classification result in `audit_log` for debugging and improvement
- **ALWAYS test with sample data first** — never run a new workflow against production QuickBooks without verifying output with test data


<claude-mem-context>

</claude-mem-context>
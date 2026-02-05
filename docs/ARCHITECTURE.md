# Accounting Workflow Automation Architecture v2.0

> **n8n + Claude API + QuickBooks API + UnionBank/BDO + Telegram Bot**
> Automates ~85% of current manual accounting operations for BK Keyforce / BETRNK Group.

**New in v2.0:** Credit Card & Budget Tracking · Telegram Bot Integration · All Sections Updated

---

## 0. Current State vs. Post-Automation

| Business Area | Current Process | After Automation | Rate |
|---|---|---|---|
| Data Collection & Entry | Manual copy-paste from game records, POS, payroll | API/Webhook auto-fetch → n8n auto-routes | 🟢 95% |
| Monthly P&L (6 entities) | Manual paste into Excel templates → check PL Summary | Claude auto-classifies → auto-generates templates | 🟢 90% |
| Consolidated FS & PPTX | Manual consolidation → manual PowerPoint | n8n pipeline → python-pptx auto-generation | 🟢 95% |
| **Credit Card Processing** 🆕 | Manual download → manual categorization → manual entry | Auto-ingest CSV/PDF → Claude categorizes → QB entry | 🟢 90% |
| **Budget vs. Actual** 🆕 | No tracking exists | Budget master in QB → real-time variance via Telegram | 🟢 85% |
| Bank Transfers (Payroll) | Manual template → manual UB portal upload | Auto-template generation → portal upload (semi-auto) | 🟡 70% |
| Expense Approval *(updated)* | Google Form → manual review → group chat | Form → n8n → Claude check → Telegram one-tap approval | 🟡 75% |
| Bank Reconciliation | No documented procedure | Bank API → QuickBooks auto-match → discrepancy alert | 🟢 85% |
| Tax Filing Documents | Manual calculation & preparation | QuickBooks data → Claude drafts BIR forms | 🟡 60% |
| Approval & Final Review | Manager reviews all items manually | AI flags anomalies → humans handle exceptions only | 🔴 30% |

**Legend:** 🟢 Fully Automated (85%+) · 🟡 Semi-Automated (60–80%) · 🔴 Human-Led (~30%)

---

## 1. System Architecture

### Data Source Layer
- Utak POS API (Midori sales)
- Google Sheets (game records)
- Google Forms (expense requests)
- HR Payroll System / CSV
- UnionBank Portal / API
- BDO Corporate Banking
- GCash Business
- 🆕 Credit Card CSV/PDF Statements

### Processing & Orchestration Layer
- n8n (core workflow engine)
- Claude API (classification, OCR, anomaly detection, reporting)
- Python Scripts (Excel/PPTX generation)
- QuickBooks API (accounting ledger)
- PostgreSQL (transaction DB)
- Google Drive API (file storage)
- 🆕 Budget Engine (variance calculation)

### Output & Notification Layer
- 🆕 Telegram Bot (approvals, alerts, reports, file upload)
- Google Drive (P&L / FS storage)
- Email (monthly PDF delivery)
- Dashboard (real-time monitoring)
- QuickBooks (ledger sync)
- PowerPoint (auto-generated exec reports)
- 🆕 Budget vs. Actual Reports

### Why n8n as the Core Engine?

n8n is a self-hostable workflow automation tool. Unlike Zapier or Make, there's no per-execution cost. It supports complex branching and HTTP requests, handles hundreds to thousands of monthly transactions at a fixed infrastructure cost, and the team already has experience with it.

---

## 2. Credit Card Statement Ingestion 🆕

Automates ingestion from 4 sources (company credit cards, UnionBank cards, BDO cards, GCash) using both CSV and PDF inputs. Claude API handles categorization and OCR for PDF statements.

### Before vs. After

**❌ Before (Manual):**
1. Download CSV or PDF from each bank portal
2. Open each file and manually read transactions
3. Manually categorize each transaction by account
4. Manually assign to the correct entity
5. Manually enter into Excel or QuickBooks
6. Hope nothing was missed or miscategorized

**✅ After (Automated):**
1. Upload CSV/PDF to Telegram or shared folder
2. n8n auto-detects format and source bank
3. Claude AI categorizes every transaction
4. Auto-assigns to correct entity based on rules
5. Auto-enters into QuickBooks with full audit trail
6. Anomalies flagged instantly via Telegram

### Processing Pipeline

```
📎 Upload via Telegram
  → n8n Format Detection
    → CSV Parser / Claude PDF OCR
      → Claude Categorization
        → Entity Assignment
          → QuickBooks Entry
            → 📊 Telegram Summary
```

**CSV Path:** Straightforward parsing — n8n reads column headers, maps to standard schema (Date, Description, Amount, Reference). Different bank formats (UB, BDO, GCash) each have a dedicated parser template.

**PDF Path:** Claude API's vision capability extracts transaction data from PDF statements. Handles varying layouts from different banks. Extracted data is converted to the same standard schema before categorization.

**Categorization:** Claude maps each transaction to the chart of accounts using contextual clues (merchant name, description, amount patterns). Known merchants are cached in a lookup table for instant classification; only unknown merchants trigger AI classification.

### Supported Sources

| Source | Format | Method |
|---|---|---|
| Company Credit Cards | CSV + PDF | Upload or auto-fetch |
| UnionBank Cards | CSV + PDF | UB Portal download → upload |
| BDO Cards | CSV + PDF | BDO Portal download → upload |
| GCash Business | CSV | GCash export → upload |

### Smart Categorization Rules

**Level 1 — Lookup Table:** Known merchants are pre-mapped (e.g., "SHELL" → Fuel / Company Car, "MERALCO" → Utilities). Instant, no AI call needed.

**Level 2 — Claude AI:** Unknown transactions are classified by Claude using merchant name + amount + context. The result is added to the lookup table for next time.

**Level 3 — Human Review:** Low-confidence classifications are sent to Telegram for one-tap confirmation.

> ⚠️ **Duplicate Detection:** Credit card transactions may appear on both bank statements and expense reports (Google Form submissions). The system cross-references all entries by date, amount, and merchant to flag potential duplicates before they reach QuickBooks. Duplicates are sent to Telegram for human confirmation.

**Tech Stack:** `Telegram Bot API` · `Claude API (Vision)` · `n8n CSV Parser` · `QuickBooks API` · `PostgreSQL`

---

## 3. Budget vs. Actual Tracking 🆕

Built from scratch since no budget tracking currently exists. The system establishes budget masters per entity and expense category, then continuously compares actuals as transactions flow in — providing real-time variance alerts via Telegram.

### Before vs. After

**❌ Before:**
- No budget tracking at all
- No visibility into overspending until month-end
- No per-entity or per-category budget limits
- Decisions made without budget context

**✅ After:**
- Annual + monthly budgets per entity & category
- Real-time spending alerts at 70%, 90%, 100% thresholds
- Daily/weekly Telegram budget summary reports
- Every approval shows remaining budget context

### Budget Setup Process (One-Time)

Since budgets don't exist yet, the first step is establishing them:

**Step 1 — Historical Analysis:** Claude analyzes the past 6–12 months of actual spending (already in QuickBooks or Excel P&Ls) and generates suggested budget ranges per entity and category.

**Step 2 — Management Review:** Suggested budgets are presented in a simple spreadsheet for review and adjustment. Management approves or modifies each line item.

**Step 3 — QuickBooks Entry:** Approved budgets are entered into QuickBooks as budget entries using the Budgets API, tagged by Class (entity) and Account (category).

**Step 4 — Threshold Configuration:** Alert thresholds (default: 70%, 90%, 100%) are configured in n8n. Can be customized per entity or category.

### Continuous Variance Monitoring

```
Transaction Enters QB
  → n8n Calculates YTD Actual
    → Compare vs. Budget
      → Check Thresholds
        → 🔔 Telegram Alert (if threshold crossed)
```

Every time a transaction enters QuickBooks (whether from credit cards, expense approvals, or payroll), the system recalculates the year-to-date actual vs. budget for that entity + category combination. If a threshold is crossed, an alert is sent instantly.

### Telegram Budget Alerts

```
⚠️ Budget Alert — Solaire

Category: Travel & Entertainment
Monthly Budget: ₱150,000
Spent This Month: ₱138,500 (92.3%)

Status: 🟡 Approaching Limit

Remaining: ₱11,500
Days Left in Month: 8

[View Details] [Approve Override]
```

### Automated Reports via Telegram

- **Daily (6:30 PM):** Quick summary of the day's spending by entity
- **Weekly (Monday 9 AM):** Week-over-week comparison per entity, highlights categories trending over budget
- **Monthly (1st of month):** Full budget vs. actual report per entity per category, with variance analysis (Telegram message + PDF attachment)
- **On-Demand:** Send `/budget Solaire` to the bot for an instant snapshot

> 💡 **Budget-Aware Expense Approval:** When an expense request comes in via Google Form, the approval notification in Telegram includes budget context: "This ₱25,000 Marketing expense for Solaire would bring the category to 87% of budget (₱217,000 / ₱250,000)." This gives the approver real-time visibility.

**Tech Stack:** `Claude API (Analysis)` · `QuickBooks Budgets API` · `n8n Config Store` · `Telegram Bot API`

---

## 4. Telegram Bot — Command Center 🆕

Telegram replaces Slack/LINE as the single interface for approvals, alerts, reporting, and file uploads. The bot acts as the "remote control" for the entire accounting automation system.

### Capabilities

**📋 Approvals:** Expense requests arrive as interactive messages with inline keyboard buttons: Approve / Reject / Ask Question. One tap to complete. Every approval message includes: amount, category, requestor, supporting documents, and budget remaining.

**📎 File Upload:** Drop a credit card CSV or PDF statement directly into the Telegram chat. The bot auto-detects the source bank, processes it, and replies with a categorized summary. Also accepts payroll files, game record exports, and ad-hoc data files.

**📊 Reports & Commands:**
```
/budget Solaire    → budget snapshot
/pl COD January    → P&L summary
/cash              → cash position
/pending           → pending approvals
/status            → system health
/report weekly     → trigger report
```

### Technical Flow

```
User Message / File
  → n8n Telegram Trigger
    → Intent Router
      → Claude (if needed)
        → Action Execution
          → Telegram Response
```

**Access Control:** Only whitelisted Telegram user IDs can interact with the bot. Permission levels:
- **Accounting Manager** — full access
- **Accounting Officer** — view + limited approve
- **Management** — view only + override approve

### Why Telegram?

Free with no message limits. Supports inline keyboards for interactive approvals. File upload support for CSV/PDF processing. Available on mobile and desktop. Bot API is well-documented and integrates natively with n8n. Group chats for team-wide notifications, DMs for sensitive approvals.

**Tech Stack:** `Telegram Bot API` · `n8n Telegram Trigger` · `Inline Keyboards` · `Webhook Mode`

---

## 5. Monthly P&L Auto-Generation Pipeline

Automates P&L creation for all 6 entities (Solaire, COD, Royce, Manila Junket, Tours, Midori) through a unified pipeline. Now includes credit card data and budget variance in the output.

### Pipeline Flow

```
📊 Data Sources
  → n8n Fetch
    → Claude Classify
      → DB + QuickBooks
        → P&L + Budget Variance
          → Claude Anomaly Check
            → 👤 Review
              → PPTX / PDF
                → 📤 Telegram Delivery
```

### Step 1: Automated Data Retrieval

n8n Cron trigger fires on the 1st of each month. Fetches data in parallel:

```
trigger: Cron "0 9 1 * *"   // 1st of month, 9:00 AM
  → parallel_fetch:
    - Google Sheets → game_records (x5 entities)
    - Utak API     → pos_sales_midori
    - HR System    → payroll_all
    - PostgreSQL   → cc_transactions (month)    ← NEW
    - QuickBooks   → budget_data (month)        ← NEW
```

### Step 2: AI Classification & Aggregation

Claude classifies raw data into account categories. Credit card transactions (already categorized during ingestion) are merged into the same pipeline for a unified view.

**New in v2.0:** The P&L output now includes a "Budget vs. Actual" column alongside each category, showing variance and percentage.

### Step 3: Excel & PowerPoint Generation

Python generates per-entity P&L Excel workbooks replicating the current template structure. A new "Budget vs. Actual" sheet is added to each workbook. The consolidated FS and executive PowerPoint include budget variance charts.

### Step 4: Delivery via Telegram

Completed reports are delivered to the Telegram group chat with a summary message. The Accounting Manager receives a DM with the full package and one-tap approval buttons. Once approved, PDFs are auto-uploaded to Google Drive and emailed to management.

**Tech Stack:** `Claude API` · `openpyxl` · `python-pptx` · `matplotlib` · `Telegram Bot API` · `Google Drive API`

> ⚠️ **Where Humans Stay in the Loop:** Transactions flagged as anomalies by Claude, as well as new vendors or unknown account categories, trigger a Telegram notification for review. Processing resumes after approval. Final P&L numbers are approved via one-click Telegram action.

---

## 6. Banking Operations

### Payroll Bulk Transfer

```
HR Payroll CSV → n8n Validate → UB Template Gen → 👤 Approve (Telegram) → UB Portal Upload → 👤 Bank Approval
```

n8n auto-generates the UB transfer template from payroll data, handling special character constraints (alphanumeric only for names and mobile numbers). Approval notification sent via Telegram with file attached for review.

### Bank Reconciliation

```
UB/BDO/GCash Statements → n8n Daily Fetch → QuickBooks Auto-Match → Claude Gap Analysis → 📋 Telegram Report
```

Daily auto-fetch of bank statements → QuickBooks matching → Claude analyzes discrepancies → Telegram report with unmatched items.

> ⚠️ **UnionBank API Constraints:** UB corporate API supports InstaPay/PESONet but bulk ePay account opening may not be API-enabled. Fallback: Playwright RPA or template auto-gen + manual upload. Confirm with UB relationship manager (Mr. Joe Bien Apaya).

**Tech Stack:** `UnionBank API` · `Playwright (RPA fallback)` · `QuickBooks Bank Feeds` · `Telegram Bot API`

---

## 7. Expense Approval via Telegram *(updated)*

### Flow

```
Google Form Submit
  → n8n Webhook
    → Claude Validation
      → Budget Check
        → 📱 Telegram Approval
          → QuickBooks Entry
```

**Claude validates:** OCR on receipts/invoices, amount consistency (PO vs. Invoice vs. OR), duplicate detection, auto-categorization.

**Budget check:** Before sending for approval, the system checks if this expense would push the budget past a threshold. If so, the Telegram message includes a warning.

**Approval message includes:** Amount, category, requestor, attached documents, budget remaining, Claude's confidence level, and approve/reject buttons.

**₱10,000 rule:** Requests ≤ ₱10,000 with high AI confidence and within budget can be auto-approved (configurable). All others require manager tap.

---

## 8. Tax & Compliance Support

### Flow

```
QuickBooks Monthly Data
  → n8n Scheduler (2 weeks before deadline)
    → Claude Tax Calculation
      → BIR Form PDF Generation
        → 📎 Telegram Delivery
          → 👤 Review & Sign
            → 👤 eFPS Submission
```

**Target forms:** 2550M/Q (VAT), 1601C (Withholding Tax), 1701Q (Quarterly Income Tax), 0619E/0619F (Monthly Withholding).

Drafts auto-generated 2 weeks before deadline and delivered to Telegram for review. Tax rates maintained in external YAML file — updatable without code changes.

> ⚠️ **Tax is "automation-assisted," not fully automated.** Philippine tax law changes frequently. Final responsibility always rests with a human. Claude drafts and calculates; the Accounting Manager reviews, signs, and submits via eFPS.

**Tech Stack:** `Claude API` · `Python reportlab` · `QuickBooks API` · `n8n Scheduler`

---

## 9. QuickBooks — Single Source of Truth

QuickBooks becomes the central accounting ledger. All data flows into it: game records, payroll, credit card transactions, expense approvals, bank transactions. All outputs flow from it: P&L reports, budget vs. actual, cash flow, tax calculations.

**Class Feature:** 6 entities set up as QuickBooks Classes. "Consolidated" vs. "per-entity" reporting becomes a single API parameter — eliminating manual consolidation.

**Budget Feature:** Annual and monthly budgets stored natively in QuickBooks using the Budgets API. The budget vs. actual engine reads directly from QuickBooks, ensuring numbers always match the ledger.

```python
# QuickBooks API flow (simplified)
n8n_workflow:
  1. Classified data → JournalEntry.create()
  2. Budget check   → Budget.query() vs. actuals
  3. P&L report     → Report.ProfitAndLoss(class=entity)
  4. Cash flow      → Report.CashFlow()
  5. Export          → openpyxl formats to current templates
```

---

## 10. Implementation Roadmap

### Phase 1 — Foundation (2–3 weeks)
**n8n + DB + QuickBooks + Telegram Bot Setup**

Self-host n8n on existing GCP/DO infrastructure, set up PostgreSQL, connect QuickBooks OAuth2, register Telegram Bot and configure webhook. Verify all API connectivity. No automation runs yet — establish the pipes.

`n8n Self-Host` · `PostgreSQL` · `Telegram Bot API` · `OAuth2`

### Phase 2 — P&L Automation (3–4 weeks)
**Monthly P&L Pipeline (Solaire first, then rollout)**

Build end-to-end pipeline with Solaire as pilot. Claude prompt tuning, Excel/PPTX generation, Telegram delivery. Validate, then extend to remaining 5 entities.

`Claude API` · `openpyxl` · `python-pptx`

### Phase 3 — Credit Card + Budget (3–4 weeks) 🆕
**Credit Card Ingestion + Budget vs. Actual System**

Build CSV/PDF parsers for all 4 card sources. Train Claude categorization prompts. Set up QuickBooks budgets with management. Build variance monitoring and Telegram alerts. Runs in parallel with Phase 2 validation.

`Claude Vision API` · `CSV Parsers` · `QuickBooks Budgets API` · `Telegram Alerts`

### Phase 4 — Approvals & Notifications (2 weeks)
**Expense Approval via Telegram + Budget-Aware Routing**

Google Form → n8n → Claude validation → budget check → Telegram approval flow. Daily summary auto-generation. Integrates with budget system from Phase 3.

`Google Forms` · `n8n Webhook` · `Telegram Inline Keyboards`

### Phase 5 — Banking (2–3 weeks)
**UB/BDO Transfer Templates + Bank Reconciliation**

Auto-generate payroll templates. Bank reconciliation automation with Telegram discrepancy reports. Confirm UB/BDO API availability; Playwright RPA as fallback.

`UnionBank API` · `Playwright` · `QuickBooks Bank Feeds`

### Phase 6 — Tax + Dashboard (3–4 weeks)
**BIR Filing Support + Executive Dashboard**

Tax auto-calc and BIR form generation. Real-time dashboard showing P&L, budget variance, cash flow, and approval status. Dashboard complements Telegram: Telegram for action, dashboard for overview.

`Next.js` · `Chart.js` · `reportlab`

### Timeline Summary

Phases 1–4 cover the core daily workflow: ~10–13 weeks. Phase 3 (credit card + budget) runs parallel with Phase 2, so no sequential delay. Phases 5–6 add 5–7 weeks. **Total: 4–5 months.**

**First milestone:** Solaire P&L + credit card ingestion working end-to-end by end of Month 2.

---

## 11. Monthly Cost Estimate

| Service | Purpose | Est. Monthly (USD) |
|---|---|---|
| n8n Self-Host | Workflow engine (existing server) | $0 |
| Claude API (Sonnet) | Classification, OCR, anomaly detection, reporting | $40–100 |
| QuickBooks Online | Accounting ledger (existing subscription) | $0 |
| PostgreSQL | Transaction DB (existing server) | $0 |
| Google Workspace | Drive, Sheets, Forms (existing) | $0 |
| Telegram Bot | Approvals, alerts, reports, file upload | $0 (free) |
| **Total** | | **$40–100/month** |

> 💡 **ROI:** Claude API cost increased slightly from v1.0 ($30–80 → $40–100) due to credit card PDF OCR and budget variance calculations. The system saves approximately 70+ hours/month of manual work. Against $40–100/month in tool costs, the labor savings are overwhelmingly favorable.

---

## 12. Security (Critical)

### 🚨 Immediate Action Required

All service credentials are currently stored in plaintext in an Excel file. This must be fixed before any automation work begins.

### Day-1 Actions
1. Deploy password manager (1Password / Bitwarden)
2. Change all passwords (currently reused across services)
3. Enable 2FA on all bank portals, QuickBooks, Gmail
4. Delete the "Log In Credential" sheet from TURN_OVER.xlsx

### Automation Security
1. n8n Credential Store for encrypted key management
2. OAuth2 / Service Accounts (no plaintext passwords)
3. n8n server behind VPN / IP whitelist
4. Telegram Bot restricted to whitelisted user IDs
5. Audit logging on all workflow executions

---

## 13. Risks & Mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| Claude misclassification | 🟡 Medium | Full human review first 3 months. Merchant lookup table reduces AI calls. Few-shot prompts improved continuously. |
| Credit card PDF format changes | 🟡 Medium | Claude Vision is resilient to layout changes. n8n validation detects parsing failures. CSV path as fallback. |
| Budget accuracy (new system) | 🟡 Medium | First quarter is "learning mode" — alerts fire but no hard blocks. Budgets adjusted quarterly. Start broad, refine over time. |
| UnionBank API limitations | 🟡 Medium | Playwright RPA fallback. Template auto-gen + manual upload still provides major gains. |
| n8n server failure | 🔴 High | Docker Compose + daily backups + Git-managed workflows. Manual fallback procedures documented. |
| Telegram bot downtime | 🟢 Low | Telegram has 99.9%+ uptime. Email notifications as fallback. All data persists in DB regardless. |

---

*Accounting Automation Architecture v2.0 — BK Keyforce / BETRNK Group*
*n8n · Claude API · QuickBooks API · UnionBank/BDO · Telegram Bot*

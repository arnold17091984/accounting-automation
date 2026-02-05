# Anomaly Detection Prompt

## System Prompt

```
You are a financial anomaly detection specialist for BK Keyforce / BETRNK Group.
Your task is to identify unusual transactions that may require human review.

## Anomaly Types to Detect

1. **Amount Anomalies**
   - Transactions significantly higher than typical for the category
   - Round number amounts that suggest estimates (e.g., exactly ₱100,000)
   - Unusually small amounts for business transactions

2. **Timing Anomalies**
   - Transactions on weekends/holidays for categories typically weekday-only
   - Multiple similar transactions in short time periods
   - Transactions outside normal business hours

3. **Pattern Anomalies**
   - New merchants not seen before with large amounts
   - Category inconsistent with entity's typical spending
   - Duplicate or near-duplicate transactions

4. **Business Logic Anomalies**
   - Expense categories unusual for the entity type
   - Commission payments to unknown parties
   - Large cash withdrawals

## Historical Context

{historical_summary}

## Entity-Specific Patterns

{entity_patterns}

## Severity Levels

- **HIGH**: Requires immediate review, block from auto-posting
- **MEDIUM**: Flag for review, can proceed with posting
- **LOW**: Informational only, no action needed

## Output Format

Return ONLY a valid JSON array of detected anomalies. No explanations.

```json
[
  {
    "transaction_id": "string",
    "anomaly_type": "amount|timing|pattern|business_logic",
    "severity": "high|medium|low",
    "reason": "Brief explanation",
    "expected_range": "What would be normal (if applicable)",
    "recommendation": "Suggested action"
  }
]
```

Return an empty array `[]` if no anomalies detected.
```

## User Prompt Template

```
Entity: {entity_name}
Period: {period}

Analyze these transactions for anomalies:

{transactions_json}

Historical averages for this entity:
{historical_averages}

Flag any transactions that seem unusual based on:
1. Amount compared to historical average for category (>30% deviation)
2. New/unknown merchants with amounts > ₱10,000
3. Duplicate transaction patterns
4. Category inconsistent with entity type
```

## Example Input

```json
{
  "entity": "solaire",
  "period": "2025-01",
  "transactions": [
    {
      "id": "txn_001",
      "txn_date": "2025-01-15",
      "description": "SHELL BGC",
      "category": "company_car",
      "amount": 25000.00
    },
    {
      "id": "txn_002",
      "txn_date": "2025-01-15",
      "description": "SHELL BGC",
      "category": "company_car",
      "amount": 25000.00
    },
    {
      "id": "txn_003",
      "txn_date": "2025-01-16",
      "description": "UNKNOWN SUPPLIER CO",
      "category": "expense",
      "amount": 500000.00
    }
  ],
  "historical_averages": {
    "company_car": {
      "avg_transaction": 3500,
      "max_transaction": 8000,
      "monthly_total": 45000
    },
    "expense": {
      "avg_transaction": 15000,
      "max_transaction": 100000,
      "monthly_total": 250000
    }
  }
}
```

## Example Output

```json
[
  {
    "transaction_id": "txn_001",
    "anomaly_type": "amount",
    "severity": "high",
    "reason": "Fuel transaction ₱25,000 is 614% higher than average (₱3,500)",
    "expected_range": "₱2,000 - ₱8,000",
    "recommendation": "Verify receipt and confirm if this is a bulk fuel purchase"
  },
  {
    "transaction_id": "txn_002",
    "anomaly_type": "pattern",
    "severity": "high",
    "reason": "Potential duplicate - same merchant, amount, and date as txn_001",
    "expected_range": null,
    "recommendation": "Confirm this is not a duplicate charge"
  },
  {
    "transaction_id": "txn_003",
    "anomaly_type": "business_logic",
    "severity": "high",
    "reason": "Unknown supplier with large amount (₱500,000) - new merchant",
    "expected_range": null,
    "recommendation": "Verify supplier legitimacy and obtain supporting documents"
  }
]
```

## Threshold Configuration

```yaml
# Amount thresholds (configurable)
amount_deviation_warning: 0.30   # 30% above average
amount_deviation_critical: 0.50  # 50% above average

# New merchant thresholds
new_merchant_review_amount: 10000  # ₱10,000
new_merchant_block_amount: 50000   # ₱50,000

# Duplicate detection
duplicate_time_window_hours: 24
duplicate_amount_tolerance: 0.01  # 1% variance allowed

# Round number detection
round_number_threshold: 10000  # Flag round numbers >= ₱10,000
```

## Implementation Notes

1. **Run After Classification**: Anomaly detection runs after transactions are classified.

2. **Historical Data Required**: Needs at least 3 months of historical data for meaningful comparisons.

3. **Entity Context**: Different entities have different spending patterns:
   - Gaming entities: Large commission transactions are normal
   - Tours: Seasonal variation in accommodation bookings
   - Midori: Regular inventory purchases from suppliers

4. **Alert Integration**: High severity anomalies trigger immediate Telegram alerts.

5. **Learning Mode**: During Q1 2025, collect anomaly patterns without blocking transactions.

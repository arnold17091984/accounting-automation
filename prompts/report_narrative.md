# Report Narrative Generation Prompt

## System Prompt

```
You are a financial analyst generating executive summaries for BK Keyforce / BETRNK Group.
Your task is to create clear, concise narratives explaining financial performance.

## Writing Style

- Professional but accessible (avoid jargon where possible)
- Data-driven with specific numbers
- Highlight significant changes (positive and negative)
- Action-oriented recommendations
- Concise (3-5 bullet points per section)

## Report Types

1. **Monthly P&L Summary** - Overview of income and expenses
2. **Budget Variance Report** - Actual vs budget comparison
3. **Daily/Weekly Digest** - Recent transaction summary
4. **Consolidated Report** - Multi-entity comparison

## Currency and Number Formatting

- Use Philippine Peso (₱) symbol
- Format large numbers with commas: ₱1,234,567.89
- Use "M" for millions: ₱1.2M
- Percentages with one decimal: 15.3%

## Output Format

Return the narrative as structured JSON for easy formatting:

```json
{
  "title": "Report title",
  "period": "January 2025",
  "executive_summary": "One paragraph overview",
  "highlights": [
    {"type": "positive|negative|neutral", "text": "Key point"}
  ],
  "sections": [
    {
      "title": "Section name",
      "content": "Section narrative",
      "metrics": [
        {"label": "Metric name", "value": "₱X,XXX", "change": "+X%"}
      ]
    }
  ],
  "recommendations": [
    "Action item 1",
    "Action item 2"
  ],
  "alerts": [
    {"severity": "high|medium|low", "message": "Alert text"}
  ]
}
```
```

## User Prompt Templates

### Monthly P&L Summary

```
Generate a monthly P&L summary for {entity_name}.

Period: {period}
Currency: PHP

Financial Data:
{financial_data_json}

Previous Period Comparison:
{previous_period_json}

Budget Data:
{budget_data_json}

Create an executive summary highlighting:
1. Revenue performance vs last month and budget
2. Major expense categories and changes
3. Net income and margin
4. Notable transactions or anomalies
5. Recommendations for next month
```

### Budget Variance Report

```
Generate a budget variance report for {entity_name}.

Period: {period}
Days Remaining: {days_remaining}

Budget vs Actual:
{variance_data_json}

Categories Over Budget:
{over_budget_json}

Create a report highlighting:
1. Overall budget utilization
2. Categories approaching or exceeding budget
3. Categories significantly under budget
4. Projected month-end position
5. Recommendations for budget management
```

### Daily Digest

```
Generate a daily financial digest for {entity_name}.

Date: {date}

Today's Transactions:
{transactions_json}

Running Month Totals:
{mtd_totals_json}

Create a brief summary including:
1. Total transactions processed
2. Largest transactions
3. Any flagged items requiring attention
4. Month-to-date spending vs budget
```

## Example Output - Monthly P&L

```json
{
  "title": "Solaire Monthly P&L Summary",
  "period": "January 2025",
  "executive_summary": "Solaire achieved strong revenue growth of 12.5% month-over-month, driven by increased VIP gaming activity. Operating expenses remained controlled at 8.2% below budget. Net income of ₱2.4M represents a 15.3% margin, exceeding the target of 12%.",
  "highlights": [
    {"type": "positive", "text": "Revenue up 12.5% vs December 2024"},
    {"type": "positive", "text": "Operating expenses 8.2% under budget"},
    {"type": "negative", "text": "Commission expenses increased 18% due to higher rolling volume"},
    {"type": "neutral", "text": "3 new high-value players onboarded"}
  ],
  "sections": [
    {
      "title": "Revenue",
      "content": "Total revenue of ₱15.7M was driven primarily by gaming operations (₱14.2M) with additional service income of ₱1.5M. The 12.5% increase reflects successful CNY promotional activities.",
      "metrics": [
        {"label": "Total Revenue", "value": "₱15.7M", "change": "+12.5%"},
        {"label": "Gaming Revenue", "value": "₱14.2M", "change": "+14.1%"},
        {"label": "Service Income", "value": "₱1.5M", "change": "+2.3%"}
      ]
    },
    {
      "title": "Operating Expenses",
      "content": "Total operating expenses of ₱11.2M were well-controlled. Major categories include commission expenses (₱6.8M), salaries (₱2.1M), and operational costs (₱2.3M).",
      "metrics": [
        {"label": "Total OpEx", "value": "₱11.2M", "change": "+5.2%"},
        {"label": "Commission Expense", "value": "₱6.8M", "change": "+18.0%"},
        {"label": "Salaries", "value": "₱2.1M", "change": "0%"}
      ]
    },
    {
      "title": "Net Income",
      "content": "Net income of ₱2.4M exceeded expectations, benefiting from revenue growth outpacing expense increases.",
      "metrics": [
        {"label": "Net Income", "value": "₱2.4M", "change": "+22.1%"},
        {"label": "Net Margin", "value": "15.3%", "change": "+1.2pp"}
      ]
    }
  ],
  "recommendations": [
    "Monitor commission rate negotiations with top 3 junket partners",
    "Review Meals & Entertainment spending which is at 78% of budget",
    "Consider increasing marketing budget for Q2 based on CNY success"
  ],
  "alerts": [
    {"severity": "medium", "message": "Fuel expenses at 92% of monthly budget with 5 days remaining"}
  ]
}
```

## Example Output - Budget Variance

```json
{
  "title": "Budget Variance Report - Tours BGC/BSM",
  "period": "January 2025",
  "executive_summary": "Overall budget utilization at 67% with 10 days remaining. Two categories (Accommodation, Transportation) are trending over budget due to peak season bookings. Recommend reallocation from under-utilized Marketing budget.",
  "highlights": [
    {"type": "negative", "text": "Accommodation costs at 95% of budget"},
    {"type": "negative", "text": "Transportation at 88% with 10 days remaining"},
    {"type": "positive", "text": "Marketing only 45% utilized - potential reallocation source"},
    {"type": "neutral", "text": "Overall OpEx tracking to plan"}
  ],
  "sections": [
    {
      "title": "Over Budget Categories",
      "content": "Two cost of sales categories are approaching budget limits due to higher-than-expected booking volume.",
      "metrics": [
        {"label": "Accommodation (5200)", "value": "₱285,000 / ₱300,000", "change": "95%"},
        {"label": "Transportation (5210)", "value": "₱176,000 / ₱200,000", "change": "88%"}
      ]
    },
    {
      "title": "Under Budget Categories",
      "content": "Marketing and professional fees are significantly under budget, providing flexibility.",
      "metrics": [
        {"label": "Marketing", "value": "₱45,000 / ₱100,000", "change": "45%"},
        {"label": "Professional Fees", "value": "₱15,000 / ₱50,000", "change": "30%"}
      ]
    }
  ],
  "recommendations": [
    "Request budget reallocation: ₱50,000 from Marketing to Accommodation",
    "Review transportation vendor contracts for peak season pricing",
    "Pre-approve additional accommodation budget of ₱30,000 for February"
  ],
  "alerts": [
    {"severity": "high", "message": "Accommodation budget will be exceeded by ~₱25,000 at current pace"},
    {"severity": "medium", "message": "Transportation costs trending 15% above monthly average"}
  ]
}
```

## Implementation Notes

1. **Context Window**: Include 3-6 months of historical data for meaningful comparisons.

2. **Language**: Currently English only. Can be extended to Japanese/Filipino if needed.

3. **Formatting for Telegram**: When sending to Telegram, convert JSON to formatted text:
   ```
   📊 *Solaire Monthly P&L - January 2025*

   ✅ Revenue up 12.5% vs December
   ✅ OpEx 8.2% under budget
   ⚠️ Commission +18% (high rolling volume)

   💰 *Net Income: ₱2.4M (+22.1%)*
   ```

4. **PowerPoint Integration**: Use section data to populate PPTX template slides.

5. **Caching**: Cache narratives for 1 hour to avoid regenerating for multiple requests.

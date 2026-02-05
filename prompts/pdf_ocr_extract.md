# PDF OCR Extraction Prompt

## System Prompt

```
You are a document extraction specialist. Your task is to extract structured transaction data from credit card statements and bank documents.

## Document Types

1. **Credit Card Statement** - Monthly statement with transaction list
2. **Bank Statement** - Account activity with deposits and withdrawals
3. **Receipt/Invoice** - Single transaction document

## Extraction Rules

1. **Dates**: Convert all dates to YYYY-MM-DD format
2. **Amounts**: Extract as decimal numbers (no currency symbols)
3. **Descriptions**: Preserve original text, clean up OCR artifacts
4. **Reference Numbers**: Extract if present

## Output Format

Return ONLY a valid JSON object. No explanations, no markdown.

```json
{
  "document_type": "credit_card_statement|bank_statement|receipt",
  "bank_name": "string",
  "account_last_four": "string (last 4 digits)",
  "statement_period": {
    "start": "YYYY-MM-DD",
    "end": "YYYY-MM-DD"
  },
  "transactions": [
    {
      "date": "YYYY-MM-DD",
      "posting_date": "YYYY-MM-DD (if different)",
      "description": "string",
      "merchant": "string (extracted merchant name)",
      "amount": 0.00,
      "reference_number": "string or null"
    }
  ],
  "summary": {
    "previous_balance": 0.00,
    "total_credits": 0.00,
    "total_debits": 0.00,
    "new_balance": 0.00,
    "minimum_due": 0.00,
    "due_date": "YYYY-MM-DD"
  },
  "extraction_confidence": 0.95,
  "notes": ["Any issues or uncertainties"]
}
```
```

## User Prompt for Credit Card Statement

```
Extract all transactions from this credit card statement.

Focus on:
1. Transaction date (posting date if available)
2. Merchant/description
3. Amount (positive = charge, negative = credit/refund)
4. Reference number if shown

Clean up merchant names:
- Remove extra spaces
- Remove reference codes from description
- Standardize common merchants (e.g., "SHELL OIL" → "SHELL")

Output ONLY the JSON object, no other text.
```

## User Prompt for Bank Statement

```
Extract all transactions from this bank statement.

Focus on:
1. Transaction date
2. Description/particulars
3. Debit amount (withdrawal)
4. Credit amount (deposit)
5. Reference number

Separate debits and credits clearly.
Output ONLY the JSON object, no other text.
```

## Example Input Description

For a BDO credit card statement PDF showing:
- Statement period: Dec 16, 2024 - Jan 15, 2025
- Account ending: 1234
- Transactions table with dates, descriptions, amounts

## Example Output

```json
{
  "document_type": "credit_card_statement",
  "bank_name": "BDO",
  "account_last_four": "1234",
  "statement_period": {
    "start": "2024-12-16",
    "end": "2025-01-15"
  },
  "transactions": [
    {
      "date": "2024-12-18",
      "posting_date": "2024-12-19",
      "description": "SHELL TAGUIG BGC",
      "merchant": "SHELL",
      "amount": 2500.00,
      "reference_number": "REF123456"
    },
    {
      "date": "2024-12-20",
      "posting_date": "2024-12-21",
      "description": "GRABCAR 6582315847",
      "merchant": "GRABCAR",
      "amount": 450.00,
      "reference_number": null
    },
    {
      "date": "2024-12-22",
      "posting_date": "2024-12-23",
      "description": "PAYMENT RECEIVED - THANK YOU",
      "merchant": "PAYMENT",
      "amount": -50000.00,
      "reference_number": "PMT789012"
    },
    {
      "date": "2025-01-05",
      "posting_date": "2025-01-06",
      "description": "LAZADA 34521897",
      "merchant": "LAZADA",
      "amount": 1299.00,
      "reference_number": null
    }
  ],
  "summary": {
    "previous_balance": 45000.00,
    "total_credits": 50000.00,
    "total_debits": 4249.00,
    "new_balance": -751.00,
    "minimum_due": 0.00,
    "due_date": "2025-02-05"
  },
  "extraction_confidence": 0.92,
  "notes": [
    "One transaction partially obscured, amount estimated"
  ]
}
```

## Bank-Specific Patterns

### BDO
- Statement format: Table with Posting Date, Transaction Date, Description, Amount
- Date format: MM/DD (year from statement header)
- Amount format: Positive with "CR" suffix for credits

### UnionBank
- Statement format: Date, Description, Ref No, Debit, Credit, Balance
- Date format: MM/DD/YYYY
- Separate debit/credit columns

### GCash
- Export format: Transaction history with Type column
- Date format: "Jan 15, 2025 2:30 PM"
- Type determines if expense or income

### Metrobank
- Statement format: Similar to UnionBank
- Date format: DD/MM/YYYY

## Implementation Notes

1. **Image Quality**: Request re-upload if confidence < 0.7

2. **Multi-page Documents**: Process each page and combine results

3. **Amount Verification**: Sum of transactions should approximately match statement totals

4. **Encoding**: Handle Filipino text and special characters

5. **Error Handling**: Return partial results with notes about issues

## API Call Example

```python
import anthropic
import base64

def extract_from_pdf(pdf_path: str) -> dict:
    client = anthropic.Anthropic()

    with open(pdf_path, "rb") as f:
        pdf_data = base64.standard_b64encode(f.read()).decode("utf-8")

    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_data
                        }
                    },
                    {
                        "type": "text",
                        "text": "Extract all transactions from this credit card statement. Output ONLY valid JSON."
                    }
                ]
            }
        ]
    )

    return json.loads(message.content[0].text)
```

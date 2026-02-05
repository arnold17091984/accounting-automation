"""
UnionBank CSV Parser

Parses UnionBank credit card and bank statement CSV exports.
"""

import re
from datetime import datetime
from decimal import Decimal

from .base import BaseCSVParser, ParsedTransaction, ParseResult


class UnionBankParser(BaseCSVParser):
    """Parser for UnionBank CSV exports."""

    BANK_NAME = "UnionBank of the Philippines"
    BANK_CODE = "unionbank"

    # Expected column names (may vary by export type)
    COLUMN_MAPPINGS = {
        "date": ["Transaction Date", "Date", "TXN DATE"],
        "posting_date": ["Posting Date", "POST DATE"],
        "description": ["Description", "Particulars", "DESCRIPTION"],
        "reference": ["Reference Number", "Reference No.", "REF NO"],
        "debit": ["Debit", "Withdrawal", "DEBIT"],
        "credit": ["Credit", "Deposit", "CREDIT"],
        "balance": ["Running Balance", "Balance", "BALANCE"],
    }

    def __init__(self):
        super().__init__(encoding="utf-8", delimiter=",")

    def _preprocess_content(self, content: str) -> str:
        """Preprocess UnionBank CSV content."""
        content = super()._preprocess_content(content)

        # Skip any header rows before the actual data
        lines = content.split('\n')
        data_start = 0

        for i, line in enumerate(lines):
            # Look for the header row
            if any(col in line for col in ["Transaction Date", "Date", "TXN DATE"]):
                data_start = i
                break

        return '\n'.join(lines[data_start:])

    def _get_column_value(self, row: dict, column_type: str) -> str | None:
        """Get value from row using column mappings."""
        for possible_name in self.COLUMN_MAPPINGS.get(column_type, []):
            if possible_name in row:
                return row[possible_name]
        return None

    def _parse_row(self, row: dict[str, str]) -> ParsedTransaction | None:
        """Parse a UnionBank CSV row."""
        # Get date
        date_str = self._get_column_value(row, "date")
        if not date_str or date_str.strip() == "":
            return None

        try:
            txn_date = self._parse_date(date_str)
        except ValueError:
            return None

        # Get posting date if available
        posting_date = None
        posting_str = self._get_column_value(row, "posting_date")
        if posting_str:
            try:
                posting_date = self._parse_date(posting_str)
            except ValueError:
                pass

        # Get description
        description = self._get_column_value(row, "description") or ""
        description = description.strip()

        # Skip header-like rows
        if description.lower() in ["description", "particulars", ""]:
            return None

        # Get reference
        reference = self._get_column_value(row, "reference")

        # Parse amount (debit/credit columns)
        debit_str = self._get_column_value(row, "debit") or ""
        credit_str = self._get_column_value(row, "credit") or ""

        debit = self._parse_amount(debit_str) if debit_str.strip() else Decimal("0")
        credit = self._parse_amount(credit_str) if credit_str.strip() else Decimal("0")

        # Determine amount (positive = expense, negative = income/credit)
        if debit > 0:
            amount = debit
            txn_type = "debit"
        elif credit > 0:
            amount = -credit  # Credits are negative (refunds, payments received)
            txn_type = "credit"
        else:
            return None  # Skip zero-amount rows

        # Get balance
        balance = None
        balance_str = self._get_column_value(row, "balance")
        if balance_str:
            try:
                balance = self._parse_amount(balance_str)
            except ValueError:
                pass

        # Extract merchant
        merchant = self._extract_merchant(description)

        return ParsedTransaction(
            date=txn_date,
            posting_date=posting_date,
            description=description,
            merchant=merchant,
            amount=amount,
            reference=reference,
            balance=balance,
            transaction_type=txn_type,
            raw_data=dict(row)
        )

    def _extract_metadata(self, content: str, result: ParseResult) -> None:
        """Extract UnionBank-specific metadata."""
        # Try to find account number
        account_match = re.search(r'Account.*?(\d{4})\s*$', content, re.MULTILINE)
        if account_match:
            result.account_last_four = account_match.group(1)

        # Try to find statement period
        period_match = re.search(
            r'Statement Period[:\s]+(\d{1,2}/\d{1,2}/\d{4})\s*(?:to|-)\s*(\d{1,2}/\d{1,2}/\d{4})',
            content,
            re.IGNORECASE
        )
        if period_match:
            try:
                result.statement_period_start = self._parse_date(period_match.group(1))
                result.statement_period_end = self._parse_date(period_match.group(2))
            except ValueError:
                pass

    def _extract_merchant(self, description: str) -> str:
        """Extract merchant from UnionBank description format."""
        # UnionBank format: "POS PURCHASE - MERCHANT NAME - 123456"
        match = re.match(r'^(?:POS PURCHASE|ONLINE TRANSFER|BILLS PAYMENT)\s*-\s*(.+?)\s*-\s*\d+', description, re.IGNORECASE)
        if match:
            return match.group(1).strip().upper()

        # InstaPay format: "INSTAPAY TO MERCHANT 123456"
        match = re.match(r'^INSTAPAY\s+TO\s+(.+?)\s+\d+', description, re.IGNORECASE)
        if match:
            return match.group(1).strip().upper()

        return super()._extract_merchant(description)

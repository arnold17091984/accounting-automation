"""
GCash CSV Parser

Parses GCash transaction history CSV exports.
"""

import re
from datetime import datetime
from decimal import Decimal

from .base import BaseCSVParser, ParsedTransaction, ParseResult


class GCashParser(BaseCSVParser):
    """Parser for GCash CSV exports."""

    BANK_NAME = "GCash"
    BANK_CODE = "gcash"

    # GCash date format: "Jan 15, 2025 2:30 PM"
    DATE_FORMATS = [
        "%b %d, %Y %I:%M %p",
        "%b %d, %Y %I:%M%p",
        "%b %d, %Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]

    # Transaction types that are expenses (money out)
    EXPENSE_TYPES = [
        "PAYMENT",
        "PAY QR",
        "SEND MONEY",
        "CASH OUT",
        "BILLS PAYMENT",
        "BUY LOAD",
        "BANK TRANSFER",
        "GCREDIT PAYMENT",
    ]

    # Transaction types that are income (money in)
    INCOME_TYPES = [
        "RECEIVE MONEY",
        "CASH IN",
        "REFUND",
        "BANK TRANSFER IN",
        "GCASH REWARD",
    ]

    # Column mappings
    COLUMN_MAPPINGS = {
        "date": ["Date & Time", "Date", "Transaction Date"],
        "type": ["Type", "Transaction Type"],
        "description": ["Description", "Details"],
        "reference": ["Reference Number", "Ref No", "Reference"],
        "amount": ["Amount"],
        "status": ["Status"],
        "fee": ["Fee", "Service Fee"],
    }

    def __init__(self):
        super().__init__(encoding="utf-8", delimiter=",")

    def _get_column_value(self, row: dict, column_type: str) -> str | None:
        """Get value from row using column mappings."""
        for possible_name in self.COLUMN_MAPPINGS.get(column_type, []):
            if possible_name in row:
                return row[possible_name]
        return None

    def _parse_row(self, row: dict[str, str]) -> ParsedTransaction | None:
        """Parse a GCash CSV row."""
        # Get date
        date_str = self._get_column_value(row, "date")
        if not date_str or date_str.strip() == "":
            return None

        try:
            txn_date = self._parse_date(date_str)
        except ValueError:
            return None

        # Get transaction type
        txn_type_str = self._get_column_value(row, "type") or ""
        txn_type_str = txn_type_str.strip().upper()

        # Get description
        description = self._get_column_value(row, "description") or ""
        description = description.strip()

        if not description and not txn_type_str:
            return None

        # Combine type and description for full context
        full_description = f"{txn_type_str} - {description}" if description else txn_type_str

        # Get reference
        reference = self._get_column_value(row, "reference")

        # Get status - skip failed/pending transactions
        status = self._get_column_value(row, "status") or ""
        if status.upper() in ["FAILED", "PENDING", "CANCELLED"]:
            return None

        # Parse amount
        amount_str = self._get_column_value(row, "amount") or "0"
        try:
            amount = self._parse_amount(amount_str)
        except ValueError:
            return None

        if amount == 0:
            return None

        # Determine if expense or income based on transaction type
        is_expense = any(exp_type in txn_type_str for exp_type in self.EXPENSE_TYPES)
        is_income = any(inc_type in txn_type_str for inc_type in self.INCOME_TYPES)

        # Ensure sign is correct
        if is_expense and amount < 0:
            amount = abs(amount)
        elif is_income and amount > 0:
            amount = -amount
        elif not is_expense and not is_income:
            # Unknown type - use amount sign as-is
            pass

        # Add fee to amount if present
        fee_str = self._get_column_value(row, "fee")
        if fee_str and fee_str.strip():
            try:
                fee = self._parse_amount(fee_str)
                if is_expense:
                    amount += fee  # Add fee to expense
            except ValueError:
                pass

        # Extract merchant
        merchant = self._extract_merchant(description, txn_type_str)

        return ParsedTransaction(
            date=txn_date,
            description=full_description,
            merchant=merchant,
            amount=amount,
            reference=reference,
            transaction_type="debit" if amount > 0 else "credit",
            raw_data=dict(row)
        )

    def _extract_metadata(self, content: str, result: ParseResult) -> None:
        """Extract GCash-specific metadata."""
        # GCash mobile number (last 4)
        phone_match = re.search(r'(?:Mobile|Phone|Number)[:\s]+.*?(\d{4})\s*$', content, re.MULTILINE)
        if phone_match:
            result.account_last_four = phone_match.group(1)

        # Export date range
        date_match = re.search(
            r'(?:Period|From)[:\s]+(\w+\s+\d{1,2},\s+\d{4}).*?(?:to|-)\s*(\w+\s+\d{1,2},\s+\d{4})',
            content,
            re.IGNORECASE
        )
        if date_match:
            try:
                result.statement_period_start = self._parse_date(date_match.group(1))
                result.statement_period_end = self._parse_date(date_match.group(2))
            except ValueError:
                pass

    def _extract_merchant(self, description: str, txn_type: str) -> str:
        """Extract merchant from GCash description format."""
        # GCash format examples:
        # "Payment to MERCHANT NAME"
        # "Send Money to JOHN DOE"
        # "Bills Payment - MERALCO"

        # Payment to pattern
        match = re.match(r'^Payment\s+to\s+(.+)$', description, re.IGNORECASE)
        if match:
            return match.group(1).strip().upper()

        # Send Money to pattern
        match = re.match(r'^Send\s+Money\s+to\s+(.+)$', description, re.IGNORECASE)
        if match:
            return match.group(1).strip().upper()

        # Bills Payment pattern
        match = re.match(r'^Bills\s+Payment\s*[-:]\s*(.+)$', description, re.IGNORECASE)
        if match:
            return match.group(1).strip().upper()

        # Cash Out pattern
        match = re.match(r'^Cash\s+Out\s*[-:@]\s*(.+)$', description, re.IGNORECASE)
        if match:
            return match.group(1).strip().upper()

        # If no pattern matches, use the full description
        if description:
            return description.upper()
        return txn_type.upper()

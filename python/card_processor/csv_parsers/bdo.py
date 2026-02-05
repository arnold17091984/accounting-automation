"""
BDO CSV Parser

Parses BDO credit card and bank statement CSV exports.
"""

import re
from datetime import datetime
from decimal import Decimal

from .base import BaseCSVParser, ParsedTransaction, ParseResult


class BDOParser(BaseCSVParser):
    """Parser for BDO CSV exports."""

    BANK_NAME = "Banco de Oro"
    BANK_CODE = "bdo"

    # BDO date formats
    DATE_FORMATS = [
        "%d-%b-%Y",   # 15-Jan-2025
        "%d-%b-%y",   # 15-Jan-25
        "%m/%d/%Y",   # 01/15/2025
        "%m/%d",      # 01/15 (year from context)
    ]

    # Column mappings for different BDO export formats
    COLUMN_MAPPINGS = {
        "posting_date": ["Posting Date", "POST DATE", "Date"],
        "transaction_date": ["Transaction Date", "TXN DATE"],
        "description": ["Description", "DESCRIPTION", "Particulars"],
        "reference": ["Reference No.", "REF NO", "Reference"],
        "amount": ["Amount", "AMOUNT"],
        "debit": ["Debit", "DEBIT"],
        "credit": ["Credit", "CREDIT"],
    }

    def __init__(self):
        super().__init__(encoding="utf-8", delimiter=",")
        self._statement_year: int | None = None

    def _preprocess_content(self, content: str) -> str:
        """Preprocess BDO CSV content."""
        content = super()._preprocess_content(content)

        # Extract statement year from header if present
        year_match = re.search(r'Statement.*?(\d{4})', content)
        if year_match:
            self._statement_year = int(year_match.group(1))
        else:
            self._statement_year = datetime.now().year

        # Find and skip to data rows
        lines = content.split('\n')
        data_start = 0

        for i, line in enumerate(lines):
            if any(col in line for col in ["Posting Date", "POST DATE", "Date", "Transaction Date"]):
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
        """Parse a BDO CSV row."""
        # Get posting date
        posting_str = self._get_column_value(row, "posting_date")
        if not posting_str or posting_str.strip() == "":
            return None

        try:
            posting_date = self._parse_date(posting_str, self._statement_year)
        except ValueError:
            return None

        # Get transaction date if available
        txn_date = posting_date
        txn_str = self._get_column_value(row, "transaction_date")
        if txn_str:
            try:
                txn_date = self._parse_date(txn_str, self._statement_year)
            except ValueError:
                pass

        # Get description
        description = self._get_column_value(row, "description") or ""
        description = description.strip()

        if not description or description.lower() in ["description", "particulars"]:
            return None

        # Get reference
        reference = self._get_column_value(row, "reference")

        # Parse amount - BDO may use single column (signed) or separate debit/credit
        amount_str = self._get_column_value(row, "amount")
        debit_str = self._get_column_value(row, "debit")
        credit_str = self._get_column_value(row, "credit")

        amount = Decimal("0")
        txn_type = "debit"

        if amount_str and amount_str.strip():
            # Single column - may be signed or have CR suffix
            amount = self._parse_amount(amount_str)
            if amount < 0:
                txn_type = "credit"
        elif debit_str or credit_str:
            # Separate columns
            debit = self._parse_amount(debit_str) if debit_str and debit_str.strip() else Decimal("0")
            credit = self._parse_amount(credit_str) if credit_str and credit_str.strip() else Decimal("0")

            if debit > 0:
                amount = debit
                txn_type = "debit"
            elif credit > 0:
                amount = -credit
                txn_type = "credit"

        if amount == 0:
            return None

        # Extract merchant
        merchant = self._extract_merchant(description)

        return ParsedTransaction(
            date=txn_date,
            posting_date=posting_date,
            description=description,
            merchant=merchant,
            amount=amount,
            reference=reference,
            transaction_type=txn_type,
            raw_data=dict(row)
        )

    def _extract_metadata(self, content: str, result: ParseResult) -> None:
        """Extract BDO-specific metadata."""
        # Account number (last 4 digits)
        account_match = re.search(r'Card.*?(\d{4})\s*$', content, re.MULTILINE)
        if not account_match:
            account_match = re.search(r'Account.*?(\d{4})\s*$', content, re.MULTILINE)
        if account_match:
            result.account_last_four = account_match.group(1)

        # Statement period
        period_match = re.search(
            r'Statement\s+(?:Period|Date)[:\s]+.*?(\d{1,2}[-/]\w{3}[-/]\d{2,4}).*?(?:to|-)\s*(\d{1,2}[-/]\w{3}[-/]\d{2,4})',
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
        """Extract merchant from BDO description format."""
        # BDO credit card format: "MERCHANT NAME    01/15"
        # Remove trailing date
        cleaned = re.sub(r'\s+\d{2}/\d{2}$', '', description)

        # Remove POS prefix if present
        cleaned = re.sub(r'^POS\s*[-]?\s*', '', cleaned, flags=re.IGNORECASE)

        # Clean up extra spaces
        cleaned = ' '.join(cleaned.split())

        return cleaned.upper() if cleaned else description.upper()

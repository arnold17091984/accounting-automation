"""
Generic CSV Parser

Flexible parser that attempts to auto-detect column mappings for unknown bank formats.
Can also use Claude API for intelligent column detection.
"""

import csv
import re
from datetime import datetime
from decimal import Decimal
from io import StringIO
from typing import Any

from .base import BaseCSVParser, ParsedTransaction, ParseResult


class GenericParser(BaseCSVParser):
    """Generic CSV parser with auto-detection capabilities."""

    BANK_NAME = "Generic"
    BANK_CODE = "generic"

    # Common column name patterns
    DATE_PATTERNS = [
        r'date', r'txn.*date', r'transaction.*date', r'posting.*date',
        r'post.*date', r'value.*date', r'\bdt\b'
    ]
    DESCRIPTION_PATTERNS = [
        r'description', r'particulars', r'details', r'narration',
        r'remarks', r'memo', r'reference.*desc'
    ]
    AMOUNT_PATTERNS = [
        r'\bamount\b', r'value', r'sum', r'total'
    ]
    DEBIT_PATTERNS = [
        r'debit', r'withdrawal', r'dr', r'out', r'expense'
    ]
    CREDIT_PATTERNS = [
        r'credit', r'deposit', r'cr', r'in', r'income'
    ]
    REFERENCE_PATTERNS = [
        r'reference', r'ref.*no', r'ref.*num', r'txn.*id', r'transaction.*id'
    ]
    BALANCE_PATTERNS = [
        r'balance', r'running.*bal', r'available', r'ledger'
    ]

    def __init__(self):
        super().__init__(encoding="utf-8", delimiter=",")
        self._column_mapping: dict[str, str] = {}
        self._detected_format: str = "unknown"

    def _preprocess_content(self, content: str) -> str:
        """Preprocess and detect format."""
        content = super()._preprocess_content(content)

        # Try to detect the bank from content
        self._detected_format = self._detect_bank(content)

        return content

    def _detect_bank(self, content: str) -> str:
        """Attempt to detect bank from content."""
        content_lower = content.lower()

        bank_indicators = {
            "unionbank": ["unionbank", "ubp", "union bank"],
            "bdo": ["banco de oro", "bdo unibank", "bdo"],
            "gcash": ["gcash", "g-xchange", "globe fintech"],
            "metrobank": ["metrobank", "mbtc", "metropolitan bank"],
            "bpi": ["bank of the philippine", "bpi"],
            "landbank": ["landbank", "land bank"],
            "pnb": ["philippine national bank", "pnb"],
        }

        for bank, indicators in bank_indicators.items():
            if any(ind in content_lower for ind in indicators):
                return bank

        return "unknown"

    def _auto_detect_columns(self, headers: list[str]) -> dict[str, str]:
        """Auto-detect column mappings from headers.

        Args:
            headers: List of column headers

        Returns:
            Dictionary mapping field types to column names
        """
        mapping = {}

        for header in headers:
            header_lower = header.lower().strip()

            # Check each pattern type
            for pattern in self.DATE_PATTERNS:
                if re.search(pattern, header_lower):
                    if "date" not in mapping:
                        mapping["date"] = header
                    elif "posting_date" not in mapping:
                        mapping["posting_date"] = header
                    break

            for pattern in self.DESCRIPTION_PATTERNS:
                if re.search(pattern, header_lower):
                    mapping["description"] = header
                    break

            for pattern in self.AMOUNT_PATTERNS:
                if re.search(pattern, header_lower) and "amount" not in mapping:
                    mapping["amount"] = header
                    break

            for pattern in self.DEBIT_PATTERNS:
                if re.search(pattern, header_lower):
                    mapping["debit"] = header
                    break

            for pattern in self.CREDIT_PATTERNS:
                if re.search(pattern, header_lower):
                    mapping["credit"] = header
                    break

            for pattern in self.REFERENCE_PATTERNS:
                if re.search(pattern, header_lower):
                    mapping["reference"] = header
                    break

            for pattern in self.BALANCE_PATTERNS:
                if re.search(pattern, header_lower):
                    mapping["balance"] = header
                    break

        return mapping

    def parse_content(self, content: str) -> ParseResult:
        """Parse CSV content with auto-detection."""
        result = ParseResult(bank=self.BANK_CODE)

        try:
            content = self._preprocess_content(content)

            # Read headers first
            reader = csv.reader(StringIO(content))
            headers = next(reader, [])

            if not headers:
                result.errors.append("No headers found in CSV")
                return result

            # Auto-detect column mappings
            self._column_mapping = self._auto_detect_columns(headers)

            if "date" not in self._column_mapping:
                result.errors.append("Could not detect date column")
                return result

            if "description" not in self._column_mapping:
                result.warnings.append("Could not detect description column")

            # Re-parse with DictReader
            dict_reader = csv.DictReader(StringIO(content))

            for row_num, row in enumerate(dict_reader, start=2):
                try:
                    transaction = self._parse_row(row)
                    if transaction:
                        result.transactions.append(transaction)
                except ValueError as e:
                    result.warnings.append(f"Row {row_num}: {e}")

            # Update bank code if detected
            if self._detected_format != "unknown":
                result.bank = self._detected_format

            # Add detection info to summary
            result.summary["detected_format"] = self._detected_format
            result.summary["column_mapping"] = self._column_mapping

            self._post_process(result)

        except Exception as e:
            result.errors.append(f"Parse error: {e}")

        return result

    def _parse_row(self, row: dict[str, str]) -> ParsedTransaction | None:
        """Parse a row using auto-detected column mapping."""
        # Get date
        date_col = self._column_mapping.get("date")
        if not date_col or date_col not in row:
            return None

        date_str = row[date_col]
        if not date_str or date_str.strip() == "":
            return None

        try:
            txn_date = self._parse_date(date_str)
        except ValueError:
            return None

        # Get posting date
        posting_date = None
        posting_col = self._column_mapping.get("posting_date")
        if posting_col and posting_col in row:
            try:
                posting_date = self._parse_date(row[posting_col])
            except ValueError:
                pass

        # Get description
        description = ""
        desc_col = self._column_mapping.get("description")
        if desc_col and desc_col in row:
            description = row[desc_col].strip()

        # Skip empty descriptions
        if not description:
            return None

        # Get reference
        reference = None
        ref_col = self._column_mapping.get("reference")
        if ref_col and ref_col in row:
            reference = row[ref_col].strip() or None

        # Parse amount
        amount = Decimal("0")
        txn_type = "debit"

        # Try single amount column first
        amount_col = self._column_mapping.get("amount")
        if amount_col and amount_col in row and row[amount_col].strip():
            amount = self._parse_amount(row[amount_col])
            txn_type = "credit" if amount < 0 else "debit"
        else:
            # Try separate debit/credit columns
            debit_col = self._column_mapping.get("debit")
            credit_col = self._column_mapping.get("credit")

            if debit_col and debit_col in row and row[debit_col].strip():
                amount = self._parse_amount(row[debit_col])
                txn_type = "debit"
            elif credit_col and credit_col in row and row[credit_col].strip():
                amount = -self._parse_amount(row[credit_col])
                txn_type = "credit"

        if amount == 0:
            return None

        # Get balance
        balance = None
        bal_col = self._column_mapping.get("balance")
        if bal_col and bal_col in row and row[bal_col].strip():
            try:
                balance = self._parse_amount(row[bal_col])
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


def detect_and_parse(content: str) -> ParseResult:
    """Convenience function to detect bank and parse content.

    Args:
        content: CSV content string

    Returns:
        ParseResult from appropriate parser
    """
    from .unionbank import UnionBankParser
    from .bdo import BDOParser
    from .gcash import GCashParser

    content_lower = content.lower()

    # Try to detect bank and use specific parser
    if any(x in content_lower for x in ["unionbank", "ubp"]):
        return UnionBankParser().parse_content(content)
    elif any(x in content_lower for x in ["bdo", "banco de oro"]):
        return BDOParser().parse_content(content)
    elif any(x in content_lower for x in ["gcash", "g-xchange"]):
        return GCashParser().parse_content(content)
    else:
        # Use generic parser
        return GenericParser().parse_content(content)

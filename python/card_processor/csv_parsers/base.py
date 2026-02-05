"""
Base CSV Parser Module

Abstract base class for bank-specific CSV parsers.
"""

import csv
import hashlib
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from io import StringIO
from pathlib import Path
from typing import Any, Iterator


@dataclass
class ParsedTransaction:
    """Represents a parsed transaction from a bank statement."""

    date: datetime
    posting_date: datetime | None = None
    description: str = ""
    merchant: str = ""
    amount: Decimal = Decimal("0")
    reference: str | None = None
    balance: Decimal | None = None
    transaction_type: str | None = None  # 'debit' or 'credit'
    raw_data: dict = field(default_factory=dict)

    @property
    def is_expense(self) -> bool:
        """Check if this transaction is an expense (debit)."""
        return self.amount > 0

    @property
    def hash(self) -> str:
        """Generate a hash for duplicate detection."""
        data = f"{self.date.isoformat()}|{self.description}|{self.amount}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]


@dataclass
class ParseResult:
    """Result of parsing a bank statement."""

    bank: str
    account_last_four: str | None = None
    statement_period_start: datetime | None = None
    statement_period_end: datetime | None = None
    transactions: list[ParsedTransaction] = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def transaction_count(self) -> int:
        return len(self.transactions)

    @property
    def total_debits(self) -> Decimal:
        return sum(t.amount for t in self.transactions if t.amount > 0)

    @property
    def total_credits(self) -> Decimal:
        return abs(sum(t.amount for t in self.transactions if t.amount < 0))


class BaseCSVParser(ABC):
    """Abstract base class for bank CSV parsers."""

    BANK_NAME: str = "Unknown"
    BANK_CODE: str = "unknown"

    # Date format patterns to try
    DATE_FORMATS = [
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d-%b-%Y",
        "%b %d, %Y",
        "%m/%d",
    ]

    def __init__(self, encoding: str = "utf-8", delimiter: str = ","):
        """Initialize the parser.

        Args:
            encoding: File encoding
            delimiter: CSV delimiter
        """
        self.encoding = encoding
        self.delimiter = delimiter

    def parse_file(self, file_path: Path | str) -> ParseResult:
        """Parse a CSV file.

        Args:
            file_path: Path to the CSV file

        Returns:
            ParseResult object
        """
        file_path = Path(file_path)

        with open(file_path, encoding=self.encoding) as f:
            content = f.read()

        return self.parse_content(content)

    def parse_content(self, content: str) -> ParseResult:
        """Parse CSV content string.

        Args:
            content: CSV content as string

        Returns:
            ParseResult object
        """
        result = ParseResult(bank=self.BANK_CODE)

        try:
            # Preprocess content
            content = self._preprocess_content(content)

            # Parse CSV
            reader = csv.DictReader(
                StringIO(content),
                delimiter=self.delimiter
            )

            for row_num, row in enumerate(reader, start=2):
                try:
                    transaction = self._parse_row(row)
                    if transaction:
                        result.transactions.append(transaction)
                except ValueError as e:
                    result.warnings.append(f"Row {row_num}: {e}")

            # Extract metadata
            self._extract_metadata(content, result)

            # Post-process
            self._post_process(result)

        except Exception as e:
            result.errors.append(f"Parse error: {e}")

        return result

    def _preprocess_content(self, content: str) -> str:
        """Preprocess CSV content before parsing.

        Override in subclasses to handle bank-specific preprocessing.

        Args:
            content: Raw CSV content

        Returns:
            Preprocessed content
        """
        # Remove BOM if present
        if content.startswith('\ufeff'):
            content = content[1:]

        # Normalize line endings
        content = content.replace('\r\n', '\n').replace('\r', '\n')

        return content

    @abstractmethod
    def _parse_row(self, row: dict[str, str]) -> ParsedTransaction | None:
        """Parse a single CSV row into a transaction.

        Args:
            row: Dictionary of column name -> value

        Returns:
            ParsedTransaction or None if row should be skipped
        """
        pass

    def _extract_metadata(self, content: str, result: ParseResult) -> None:
        """Extract metadata from the CSV content.

        Override in subclasses for bank-specific metadata extraction.

        Args:
            content: Full CSV content
            result: ParseResult to update
        """
        pass

    def _post_process(self, result: ParseResult) -> None:
        """Post-process parsed transactions.

        Args:
            result: ParseResult to process
        """
        # Sort by date
        result.transactions.sort(key=lambda t: t.date)

        # Calculate summary
        result.summary = {
            "total_transactions": result.transaction_count,
            "total_debits": float(result.total_debits),
            "total_credits": float(result.total_credits),
            "net_amount": float(result.total_debits - result.total_credits)
        }

    def _parse_date(self, date_str: str, year_hint: int | None = None) -> datetime:
        """Parse a date string using multiple format patterns.

        Args:
            date_str: Date string to parse
            year_hint: Year to use if not present in date string

        Returns:
            Parsed datetime

        Raises:
            ValueError: If date cannot be parsed
        """
        date_str = date_str.strip()

        for fmt in self.DATE_FORMATS:
            try:
                dt = datetime.strptime(date_str, fmt)

                # Handle year-less formats
                if "%Y" not in fmt and "%y" not in fmt:
                    if year_hint:
                        dt = dt.replace(year=year_hint)
                    else:
                        dt = dt.replace(year=datetime.now().year)

                return dt
            except ValueError:
                continue

        raise ValueError(f"Cannot parse date: {date_str}")

    def _parse_amount(self, amount_str: str) -> Decimal:
        """Parse an amount string to Decimal.

        Args:
            amount_str: Amount string (may include currency symbols, commas)

        Returns:
            Parsed Decimal amount
        """
        if not amount_str or amount_str.strip() == "":
            return Decimal("0")

        # Remove currency symbols and whitespace
        cleaned = re.sub(r'[₱PHPP\s]', '', amount_str)

        # Handle negative indicators
        is_negative = False
        if cleaned.startswith('(') and cleaned.endswith(')'):
            cleaned = cleaned[1:-1]
            is_negative = True
        elif cleaned.endswith('CR') or cleaned.endswith('cr'):
            cleaned = cleaned[:-2]
            is_negative = True
        elif cleaned.startswith('-'):
            cleaned = cleaned[1:]
            is_negative = True

        # Remove thousand separators (comma or space)
        cleaned = cleaned.replace(',', '').replace(' ', '')

        try:
            amount = Decimal(cleaned)
            return -amount if is_negative else amount
        except Exception:
            raise ValueError(f"Cannot parse amount: {amount_str}")

    def _extract_merchant(self, description: str) -> str:
        """Extract merchant name from transaction description.

        Args:
            description: Transaction description

        Returns:
            Extracted merchant name
        """
        # Remove common prefixes
        prefixes = [
            r'^POS PURCHASE\s*-?\s*',
            r'^POS\s*-?\s*',
            r'^ONLINE\s*-?\s*',
            r'^BILLS PAYMENT\s*-?\s*',
            r'^PAYMENT\s*-?\s*',
            r'^TRANSFER\s*-?\s*',
        ]

        merchant = description.upper()
        for prefix in prefixes:
            merchant = re.sub(prefix, '', merchant, flags=re.IGNORECASE)

        # Remove trailing reference numbers
        merchant = re.sub(r'\s*-?\s*\d{6,}$', '', merchant)
        merchant = re.sub(r'\s*\d{2}/\d{2}/\d{2,4}$', '', merchant)

        # Clean up
        merchant = merchant.strip(' -')

        return merchant if merchant else description.upper()

"""
Bank Reconciliation Module

Automates matching of bank statement transactions with accounting records.
"""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from enum import Enum

import yaml

logger = logging.getLogger(__name__)


class MatchStatus(Enum):
    """Transaction match status."""
    MATCHED = "matched"
    PARTIAL = "partial"
    UNMATCHED = "unmatched"
    DUPLICATE = "duplicate"
    MANUAL_REVIEW = "manual_review"


class MatchType(Enum):
    """Type of match found."""
    EXACT = "exact"  # Amount and date match exactly
    AMOUNT_ONLY = "amount_only"  # Amount matches, date differs
    FUZZY = "fuzzy"  # Similar amount/date
    REFERENCE = "reference"  # Reference number match
    DESCRIPTION = "description"  # Description pattern match


@dataclass
class BankTransaction:
    """A transaction from bank statement."""

    id: str
    date: date
    description: str
    amount: Decimal
    balance: Decimal | None = None
    reference: str | None = None
    transaction_type: str = ""  # debit, credit
    raw_data: dict = field(default_factory=dict)

    @property
    def hash(self) -> str:
        """Generate unique hash for this transaction."""
        data = f"{self.date}|{self.amount}|{self.description}|{self.reference}"
        return hashlib.md5(data.encode()).hexdigest()[:12]


@dataclass
class BookTransaction:
    """A transaction from accounting books."""

    id: str
    date: date
    description: str
    amount: Decimal
    account_code: str
    account_name: str
    entity: str
    reference: str | None = None
    source: str = ""
    reconciled: bool = False


@dataclass
class MatchedTransaction:
    """A matched pair of transactions."""

    bank_txn: BankTransaction
    book_txn: BookTransaction
    match_type: MatchType
    confidence: float
    date_diff_days: int = 0
    amount_diff: Decimal = Decimal("0")
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "bank_id": self.bank_txn.id,
            "book_id": self.book_txn.id,
            "bank_amount": float(self.bank_txn.amount),
            "book_amount": float(self.book_txn.amount),
            "match_type": self.match_type.value,
            "confidence": self.confidence,
            "date_diff_days": self.date_diff_days,
            "amount_diff": float(self.amount_diff),
            "notes": self.notes
        }


@dataclass
class UnmatchedItem:
    """An unmatched transaction."""

    transaction: BankTransaction | BookTransaction
    source: str  # 'bank' or 'book'
    status: MatchStatus
    possible_matches: list[dict] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.transaction.id,
            "source": self.source,
            "date": self.transaction.date.isoformat(),
            "amount": float(self.transaction.amount),
            "description": self.transaction.description,
            "status": self.status.value,
            "possible_matches": self.possible_matches,
            "notes": self.notes
        }


@dataclass
class ReconciliationResult:
    """Result of reconciliation process."""

    entity: str
    account: str
    period_start: date
    period_end: date
    reconciled_at: datetime = field(default_factory=datetime.now)

    bank_opening_balance: Decimal = Decimal("0")
    bank_closing_balance: Decimal = Decimal("0")
    book_opening_balance: Decimal = Decimal("0")
    book_closing_balance: Decimal = Decimal("0")

    matched: list[MatchedTransaction] = field(default_factory=list)
    unmatched_bank: list[UnmatchedItem] = field(default_factory=list)
    unmatched_book: list[UnmatchedItem] = field(default_factory=list)

    @property
    def match_rate(self) -> float:
        """Calculate match rate percentage."""
        total_bank = len(self.matched) + len(self.unmatched_bank)
        if total_bank == 0:
            return 0.0
        return len(self.matched) / total_bank * 100

    @property
    def total_matched_amount(self) -> Decimal:
        """Sum of matched amounts."""
        return sum(m.bank_txn.amount for m in self.matched)

    @property
    def total_unmatched_bank(self) -> Decimal:
        """Sum of unmatched bank amounts."""
        return sum(u.transaction.amount for u in self.unmatched_bank)

    @property
    def total_unmatched_book(self) -> Decimal:
        """Sum of unmatched book amounts."""
        return sum(u.transaction.amount for u in self.unmatched_book)

    @property
    def difference(self) -> Decimal:
        """Calculate reconciliation difference."""
        return self.bank_closing_balance - self.book_closing_balance

    @property
    def is_reconciled(self) -> bool:
        """Check if fully reconciled."""
        return abs(self.difference) < Decimal("0.01") and len(self.unmatched_bank) == 0

    def to_dict(self) -> dict:
        return {
            "entity": self.entity,
            "account": self.account,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "reconciled_at": self.reconciled_at.isoformat(),
            "bank_opening": float(self.bank_opening_balance),
            "bank_closing": float(self.bank_closing_balance),
            "book_opening": float(self.book_opening_balance),
            "book_closing": float(self.book_closing_balance),
            "match_rate": self.match_rate,
            "matched_count": len(self.matched),
            "matched_amount": float(self.total_matched_amount),
            "unmatched_bank_count": len(self.unmatched_bank),
            "unmatched_bank_amount": float(self.total_unmatched_bank),
            "unmatched_book_count": len(self.unmatched_book),
            "unmatched_book_amount": float(self.total_unmatched_book),
            "difference": float(self.difference),
            "is_reconciled": self.is_reconciled
        }


class BankReconciliation:
    """Performs automated bank reconciliation."""

    # Matching thresholds
    DATE_TOLERANCE_DAYS = 3
    AMOUNT_TOLERANCE_PERCENT = 0.01  # 1%
    MIN_CONFIDENCE_THRESHOLD = 0.7

    def __init__(
        self,
        config_dir: Path | str | None = None,
        db_connection: Any = None
    ):
        """Initialize reconciliation engine.

        Args:
            config_dir: Path to configuration directory
            db_connection: Database connection for fetching book transactions
        """
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent.parent.parent / "config"
        self.db = db_connection
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration."""
        # Load matching rules
        config_file = self.config_dir / "reconciliation_rules.yaml"
        if config_file.exists():
            with open(config_file) as f:
                config = yaml.safe_load(f)
                self.DATE_TOLERANCE_DAYS = config.get("date_tolerance_days", 3)
                self.AMOUNT_TOLERANCE_PERCENT = config.get("amount_tolerance_percent", 0.01)
                self.description_patterns = config.get("description_patterns", {})
        else:
            self.description_patterns = {}

    def reconcile(
        self,
        entity: str,
        account: str,
        bank_transactions: list[BankTransaction],
        book_transactions: list[BookTransaction],
        period_start: date | None = None,
        period_end: date | None = None,
        bank_opening: Decimal = Decimal("0"),
        bank_closing: Decimal = Decimal("0"),
        book_opening: Decimal = Decimal("0"),
        book_closing: Decimal = Decimal("0")
    ) -> ReconciliationResult:
        """Perform reconciliation.

        Args:
            entity: Entity code
            account: Bank account identifier
            bank_transactions: List of bank statement transactions
            book_transactions: List of accounting transactions
            period_start: Start of reconciliation period
            period_end: End of reconciliation period
            bank_opening: Bank opening balance
            bank_closing: Bank closing balance
            book_opening: Book opening balance
            book_closing: Book closing balance

        Returns:
            ReconciliationResult
        """
        # Initialize result
        result = ReconciliationResult(
            entity=entity,
            account=account,
            period_start=period_start or (date.today().replace(day=1) - timedelta(days=1)).replace(day=1),
            period_end=period_end or date.today(),
            bank_opening_balance=bank_opening,
            bank_closing_balance=bank_closing,
            book_opening_balance=book_opening,
            book_closing_balance=book_closing
        )

        # Track which transactions have been matched
        matched_bank_ids = set()
        matched_book_ids = set()

        # Sort transactions by date
        bank_sorted = sorted(bank_transactions, key=lambda x: (x.date, x.amount))
        book_sorted = sorted(book_transactions, key=lambda x: (x.date, x.amount))

        # Phase 1: Exact matches (amount and date)
        for bank_txn in bank_sorted:
            if bank_txn.id in matched_bank_ids:
                continue

            for book_txn in book_sorted:
                if book_txn.id in matched_book_ids:
                    continue

                match = self._try_match(bank_txn, book_txn)
                if match and match.match_type == MatchType.EXACT:
                    result.matched.append(match)
                    matched_bank_ids.add(bank_txn.id)
                    matched_book_ids.add(book_txn.id)
                    break

        # Phase 2: Reference matches
        for bank_txn in bank_sorted:
            if bank_txn.id in matched_bank_ids:
                continue

            if not bank_txn.reference:
                continue

            for book_txn in book_sorted:
                if book_txn.id in matched_book_ids:
                    continue

                if book_txn.reference and bank_txn.reference in book_txn.reference:
                    match = self._create_match(
                        bank_txn, book_txn, MatchType.REFERENCE, 0.9
                    )
                    result.matched.append(match)
                    matched_bank_ids.add(bank_txn.id)
                    matched_book_ids.add(book_txn.id)
                    break

        # Phase 3: Amount-only matches (within date tolerance)
        for bank_txn in bank_sorted:
            if bank_txn.id in matched_bank_ids:
                continue

            candidates = []
            for book_txn in book_sorted:
                if book_txn.id in matched_book_ids:
                    continue

                match = self._try_match(bank_txn, book_txn)
                if match and match.confidence >= self.MIN_CONFIDENCE_THRESHOLD:
                    candidates.append((match, book_txn))

            # Take best match
            if candidates:
                candidates.sort(key=lambda x: x[0].confidence, reverse=True)
                best_match, best_book = candidates[0]
                result.matched.append(best_match)
                matched_bank_ids.add(bank_txn.id)
                matched_book_ids.add(best_book.id)

        # Collect unmatched
        for bank_txn in bank_sorted:
            if bank_txn.id not in matched_bank_ids:
                possible = self._find_possible_matches(bank_txn, book_sorted, matched_book_ids)
                result.unmatched_bank.append(UnmatchedItem(
                    transaction=bank_txn,
                    source="bank",
                    status=MatchStatus.MANUAL_REVIEW if possible else MatchStatus.UNMATCHED,
                    possible_matches=possible
                ))

        for book_txn in book_sorted:
            if book_txn.id not in matched_book_ids:
                result.unmatched_book.append(UnmatchedItem(
                    transaction=book_txn,
                    source="book",
                    status=MatchStatus.UNMATCHED
                ))

        return result

    def _try_match(
        self,
        bank_txn: BankTransaction,
        book_txn: BookTransaction
    ) -> MatchedTransaction | None:
        """Try to match two transactions.

        Args:
            bank_txn: Bank transaction
            book_txn: Book transaction

        Returns:
            MatchedTransaction if match found, None otherwise
        """
        # Check amount match
        amount_match = self._amounts_match(bank_txn.amount, book_txn.amount)
        if not amount_match:
            return None

        # Check date proximity
        date_diff = abs((bank_txn.date - book_txn.date).days)
        if date_diff > self.DATE_TOLERANCE_DAYS:
            return None

        # Determine match type and confidence
        if date_diff == 0 and bank_txn.amount == book_txn.amount:
            match_type = MatchType.EXACT
            confidence = 1.0
        elif date_diff == 0:
            match_type = MatchType.AMOUNT_ONLY
            confidence = 0.95
        else:
            match_type = MatchType.FUZZY
            # Reduce confidence based on date difference
            confidence = max(0.7, 1.0 - (date_diff * 0.1))

        return self._create_match(bank_txn, book_txn, match_type, confidence)

    def _amounts_match(self, amount1: Decimal, amount2: Decimal) -> bool:
        """Check if two amounts match within tolerance.

        Args:
            amount1: First amount
            amount2: Second amount

        Returns:
            True if amounts match
        """
        if amount1 == amount2:
            return True

        # Check within tolerance
        tolerance = abs(amount1) * Decimal(str(self.AMOUNT_TOLERANCE_PERCENT))
        return abs(amount1 - amount2) <= tolerance

    def _create_match(
        self,
        bank_txn: BankTransaction,
        book_txn: BookTransaction,
        match_type: MatchType,
        confidence: float
    ) -> MatchedTransaction:
        """Create a match record.

        Args:
            bank_txn: Bank transaction
            book_txn: Book transaction
            match_type: Type of match
            confidence: Match confidence

        Returns:
            MatchedTransaction
        """
        return MatchedTransaction(
            bank_txn=bank_txn,
            book_txn=book_txn,
            match_type=match_type,
            confidence=confidence,
            date_diff_days=abs((bank_txn.date - book_txn.date).days),
            amount_diff=abs(bank_txn.amount - book_txn.amount)
        )

    def _find_possible_matches(
        self,
        bank_txn: BankTransaction,
        book_transactions: list[BookTransaction],
        matched_ids: set
    ) -> list[dict]:
        """Find possible matches for unmatched bank transaction.

        Args:
            bank_txn: Unmatched bank transaction
            book_transactions: Available book transactions
            matched_ids: Already matched book IDs

        Returns:
            List of possible match dicts
        """
        possible = []

        for book_txn in book_transactions:
            if book_txn.id in matched_ids:
                continue

            # Check if amount is close
            if self._amounts_match(bank_txn.amount, book_txn.amount):
                date_diff = abs((bank_txn.date - book_txn.date).days)
                possible.append({
                    "book_id": book_txn.id,
                    "amount": float(book_txn.amount),
                    "date": book_txn.date.isoformat(),
                    "description": book_txn.description,
                    "date_diff_days": date_diff
                })

        # Sort by date proximity
        possible.sort(key=lambda x: x["date_diff_days"])
        return possible[:5]  # Top 5 possibilities

    def format_report(self, result: ReconciliationResult) -> str:
        """Format reconciliation report for Telegram.

        Args:
            result: Reconciliation result

        Returns:
            Formatted message
        """
        status_emoji = "✅" if result.is_reconciled else "⚠️"

        lines = [
            f"{status_emoji} *Bank Reconciliation Report*",
            "",
            f"*Entity:* {result.entity.upper()}",
            f"*Account:* {result.account}",
            f"*Period:* {result.period_start} to {result.period_end}",
            "",
            "*Balances:*",
            f"• Bank Closing: ₱{result.bank_closing_balance:,.2f}",
            f"• Book Closing: ₱{result.book_closing_balance:,.2f}",
            f"• Difference: ₱{result.difference:,.2f}",
            "",
            "*Matching:*",
            f"• Match Rate: {result.match_rate:.1f}%",
            f"• Matched: {len(result.matched)} (₱{result.total_matched_amount:,.2f})",
            f"• Unmatched Bank: {len(result.unmatched_bank)} (₱{result.total_unmatched_bank:,.2f})",
            f"• Unmatched Book: {len(result.unmatched_book)} (₱{result.total_unmatched_book:,.2f})",
        ]

        if result.unmatched_bank:
            lines.extend([
                "",
                "*Unmatched Bank Items:*"
            ])
            for item in result.unmatched_bank[:5]:
                lines.append(
                    f"• {item.transaction.date}: ₱{item.transaction.amount:,.2f} - "
                    f"{item.transaction.description[:30]}"
                )
            if len(result.unmatched_bank) > 5:
                lines.append(f"_...and {len(result.unmatched_bank) - 5} more_")

        lines.extend([
            "",
            f"_Reconciled: {result.reconciled_at.strftime('%Y-%m-%d %H:%M')}_"
        ])

        return "\n".join(lines)

    def auto_reconcile_from_db(
        self,
        entity: str,
        account: str,
        bank_transactions: list[BankTransaction],
        period_start: date,
        period_end: date
    ) -> ReconciliationResult:
        """Reconcile using book transactions from database.

        Args:
            entity: Entity code
            account: Bank account
            bank_transactions: Bank statement transactions
            period_start: Period start
            period_end: Period end

        Returns:
            ReconciliationResult
        """
        if not self.db:
            raise ValueError("Database connection required for auto-reconciliation")

        # Fetch book transactions from database
        book_transactions = self._fetch_book_transactions(
            entity, period_start, period_end
        )

        # Get balances
        bank_closing = bank_transactions[-1].balance if bank_transactions and bank_transactions[-1].balance else Decimal("0")

        return self.reconcile(
            entity=entity,
            account=account,
            bank_transactions=bank_transactions,
            book_transactions=book_transactions,
            period_start=period_start,
            period_end=period_end,
            bank_closing=bank_closing
        )

    def _fetch_book_transactions(
        self,
        entity: str,
        period_start: date,
        period_end: date
    ) -> list[BookTransaction]:
        """Fetch book transactions from database.

        Args:
            entity: Entity code
            period_start: Period start
            period_end: Period end

        Returns:
            List of BookTransaction
        """
        if not self.db:
            return []

        try:
            from psycopg2.extras import RealDictCursor

            with self.db.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        id::text,
                        txn_date,
                        description,
                        amount,
                        account_code,
                        account_name,
                        entity,
                        source
                    FROM transactions
                    WHERE entity = %s
                      AND txn_date BETWEEN %s AND %s
                      AND category IN ('expense', 'revenue', 'cos')
                    ORDER BY txn_date, amount
                """, (entity, period_start, period_end))

                transactions = []
                for row in cur.fetchall():
                    transactions.append(BookTransaction(
                        id=row["id"],
                        date=row["txn_date"],
                        description=row["description"] or "",
                        amount=Decimal(str(row["amount"])),
                        account_code=row["account_code"],
                        account_name=row["account_name"],
                        entity=row["entity"],
                        source=row["source"]
                    ))

                return transactions

        except Exception as e:
            logger.error(f"Failed to fetch book transactions: {e}")
            return []

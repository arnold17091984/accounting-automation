"""
Duplicate Transaction Detector Module

Detects potential duplicate transactions across multiple sources.
"""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from .csv_parsers.base import ParsedTransaction

logger = logging.getLogger(__name__)


@dataclass
class DuplicateMatch:
    """Represents a potential duplicate match."""

    transaction: ParsedTransaction
    matched_with: ParsedTransaction
    confidence: float
    match_reasons: list[str] = field(default_factory=list)
    is_likely_duplicate: bool = False


@dataclass
class DeduplicationResult:
    """Result of deduplication check."""

    unique_transactions: list[ParsedTransaction] = field(default_factory=list)
    potential_duplicates: list[DuplicateMatch] = field(default_factory=list)
    definite_duplicates: list[DuplicateMatch] = field(default_factory=list)
    stats: dict = field(default_factory=dict)


class DuplicateDetector:
    """Detects duplicate transactions using multiple strategies."""

    # Thresholds
    DATE_TOLERANCE_DAYS = 1  # Transactions within 1 day
    AMOUNT_TOLERANCE_PERCENT = 0.01  # 1% amount tolerance
    HIGH_CONFIDENCE_THRESHOLD = 0.9
    MEDIUM_CONFIDENCE_THRESHOLD = 0.7

    def __init__(
        self,
        date_tolerance_days: int = 1,
        amount_tolerance_percent: float = 0.01
    ):
        """Initialize the duplicate detector.

        Args:
            date_tolerance_days: Days within which transactions may be duplicates
            amount_tolerance_percent: Percentage tolerance for amount matching
        """
        self.date_tolerance = timedelta(days=date_tolerance_days)
        self.amount_tolerance = amount_tolerance_percent
        self._seen_hashes: set[str] = set()
        self._transaction_index: dict[str, list[ParsedTransaction]] = {}

    def check_single(
        self,
        transaction: ParsedTransaction,
        existing_transactions: list[ParsedTransaction]
    ) -> DuplicateMatch | None:
        """Check if a single transaction is a duplicate.

        Args:
            transaction: Transaction to check
            existing_transactions: List of existing transactions to compare against

        Returns:
            DuplicateMatch if potential duplicate found, None otherwise
        """
        for existing in existing_transactions:
            match = self._compare_transactions(transaction, existing)
            if match:
                return match

        return None

    def check_batch(
        self,
        transactions: list[ParsedTransaction],
        existing_transactions: list[ParsedTransaction] | None = None
    ) -> DeduplicationResult:
        """Check a batch of transactions for duplicates.

        Args:
            transactions: New transactions to check
            existing_transactions: Optional list of existing transactions

        Returns:
            DeduplicationResult with unique and duplicate transactions
        """
        result = DeduplicationResult()
        all_to_compare = existing_transactions or []

        # Build index for faster lookup
        self._build_index(all_to_compare)

        for txn in transactions:
            # Check against existing transactions
            match = self._find_duplicate(txn, all_to_compare)

            if match:
                if match.confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
                    result.definite_duplicates.append(match)
                else:
                    result.potential_duplicates.append(match)
            else:
                # Also check within the new batch
                batch_match = self._find_duplicate(txn, result.unique_transactions)
                if batch_match:
                    if batch_match.confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
                        result.definite_duplicates.append(batch_match)
                    else:
                        result.potential_duplicates.append(batch_match)
                else:
                    result.unique_transactions.append(txn)

        # Calculate stats
        total = len(transactions)
        result.stats = {
            "total_checked": total,
            "unique": len(result.unique_transactions),
            "potential_duplicates": len(result.potential_duplicates),
            "definite_duplicates": len(result.definite_duplicates),
            "duplicate_rate": (
                (len(result.potential_duplicates) + len(result.definite_duplicates)) / total
                if total > 0 else 0
            )
        }

        return result

    def _build_index(self, transactions: list[ParsedTransaction]) -> None:
        """Build an index for faster duplicate detection.

        Args:
            transactions: Transactions to index
        """
        self._transaction_index.clear()

        for txn in transactions:
            # Index by amount (rounded to nearest peso)
            amount_key = str(int(abs(txn.amount)))
            if amount_key not in self._transaction_index:
                self._transaction_index[amount_key] = []
            self._transaction_index[amount_key].append(txn)

            # Also index by date
            date_key = txn.date.strftime("%Y-%m-%d")
            if date_key not in self._transaction_index:
                self._transaction_index[date_key] = []
            self._transaction_index[date_key].append(txn)

    def _find_duplicate(
        self,
        transaction: ParsedTransaction,
        candidates: list[ParsedTransaction]
    ) -> DuplicateMatch | None:
        """Find a duplicate for a transaction.

        Args:
            transaction: Transaction to check
            candidates: Candidate transactions to compare

        Returns:
            DuplicateMatch if found, None otherwise
        """
        # Use index for faster lookup
        amount_key = str(int(abs(transaction.amount)))
        date_key = transaction.date.strftime("%Y-%m-%d")

        # Get candidates from index
        indexed_candidates = set()
        if amount_key in self._transaction_index:
            indexed_candidates.update(id(t) for t in self._transaction_index[amount_key])
        if date_key in self._transaction_index:
            indexed_candidates.update(id(t) for t in self._transaction_index[date_key])

        # Filter candidates
        filtered_candidates = [
            c for c in candidates
            if id(c) in indexed_candidates or len(candidates) < 100
        ]

        for candidate in filtered_candidates:
            match = self._compare_transactions(transaction, candidate)
            if match:
                return match

        return None

    def _compare_transactions(
        self,
        txn1: ParsedTransaction,
        txn2: ParsedTransaction
    ) -> DuplicateMatch | None:
        """Compare two transactions for duplicate detection.

        Args:
            txn1: First transaction
            txn2: Second transaction

        Returns:
            DuplicateMatch if potential duplicate, None otherwise
        """
        if txn1 is txn2:
            return None

        confidence = 0.0
        reasons = []

        # 1. Exact hash match (definite duplicate)
        if txn1.hash == txn2.hash:
            return DuplicateMatch(
                transaction=txn1,
                matched_with=txn2,
                confidence=1.0,
                match_reasons=["Exact hash match"],
                is_likely_duplicate=True
            )

        # 2. Check date proximity
        date_diff = abs((txn1.date - txn2.date).days)
        if date_diff > self.date_tolerance.days:
            return None  # Dates too far apart

        if date_diff == 0:
            confidence += 0.3
            reasons.append("Same date")
        else:
            confidence += 0.1
            reasons.append(f"Within {date_diff} day(s)")

        # 3. Check amount match
        amount_diff = abs(txn1.amount - txn2.amount)
        tolerance = abs(txn1.amount) * Decimal(str(self.amount_tolerance))

        if amount_diff == 0:
            confidence += 0.4
            reasons.append("Exact amount match")
        elif amount_diff <= tolerance:
            confidence += 0.2
            reasons.append(f"Amount within {self.amount_tolerance*100}% tolerance")
        else:
            return None  # Amounts too different

        # 4. Check description similarity
        desc_similarity = self._string_similarity(
            txn1.description.lower(),
            txn2.description.lower()
        )
        if desc_similarity > 0.8:
            confidence += 0.3
            reasons.append(f"Description {desc_similarity*100:.0f}% similar")
        elif desc_similarity > 0.5:
            confidence += 0.15
            reasons.append(f"Description {desc_similarity*100:.0f}% similar")

        # 5. Check merchant match
        if txn1.merchant and txn2.merchant:
            merchant_similarity = self._string_similarity(
                txn1.merchant.lower(),
                txn2.merchant.lower()
            )
            if merchant_similarity > 0.8:
                confidence += 0.2
                reasons.append("Same merchant")

        # 6. Check reference number (if both have one)
        if txn1.reference and txn2.reference:
            if txn1.reference == txn2.reference:
                confidence += 0.3
                reasons.append("Same reference number")

        # Determine if this is a likely duplicate
        if confidence >= self.MEDIUM_CONFIDENCE_THRESHOLD:
            return DuplicateMatch(
                transaction=txn1,
                matched_with=txn2,
                confidence=min(confidence, 1.0),
                match_reasons=reasons,
                is_likely_duplicate=confidence >= self.HIGH_CONFIDENCE_THRESHOLD
            )

        return None

    def _string_similarity(self, s1: str, s2: str) -> float:
        """Calculate string similarity using Jaccard index on words.

        Args:
            s1: First string
            s2: Second string

        Returns:
            Similarity score between 0 and 1
        """
        if not s1 or not s2:
            return 0.0

        words1 = set(s1.split())
        words2 = set(s2.split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    def generate_transaction_hash(self, transaction: ParsedTransaction) -> str:
        """Generate a unique hash for a transaction.

        Args:
            transaction: Transaction to hash

        Returns:
            Hash string
        """
        data = (
            f"{transaction.date.isoformat()}|"
            f"{transaction.description}|"
            f"{transaction.amount}|"
            f"{transaction.reference or ''}"
        )
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def reset(self) -> None:
        """Reset the detector state."""
        self._seen_hashes.clear()
        self._transaction_index.clear()

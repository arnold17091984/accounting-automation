"""
Transaction Categorizer Module

Categorizes transactions using merchant lookup first, then Claude API for unknowns.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import anthropic
import yaml

from .csv_parsers.base import ParsedTransaction
from .merchant_lookup import MerchantLookup, MerchantMatch

logger = logging.getLogger(__name__)


@dataclass
class Classification:
    """Transaction classification result."""

    account_code: str
    account_name: str
    category: str
    confidence: float
    method: str  # 'lookup', 'claude', 'human'
    anomaly: bool = False
    anomaly_reason: str | None = None

    def to_dict(self) -> dict:
        return {
            "account_code": self.account_code,
            "account_name": self.account_name,
            "category": self.category,
            "confidence": self.confidence,
            "classification_method": self.method,
            "anomaly_flag": self.anomaly,
            "anomaly_reason": self.anomaly_reason
        }


@dataclass
class ClassifiedTransaction:
    """A transaction with its classification."""

    transaction: ParsedTransaction
    classification: Classification | None


@dataclass
class CategorizationResult:
    """Result of batch categorization."""

    classified: list[ClassifiedTransaction] = field(default_factory=list)
    unclassified: list[ParsedTransaction] = field(default_factory=list)
    stats: dict = field(default_factory=dict)


class TransactionCategorizer:
    """Categorizes transactions using lookup tables and Claude API."""

    DEFAULT_MODEL = "claude-sonnet-4-5-20250929"

    def __init__(
        self,
        config_dir: Path | str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        use_claude: bool = True
    ):
        """Initialize the categorizer.

        Args:
            config_dir: Path to configuration directory
            api_key: Anthropic API key
            model: Claude model to use
            use_claude: Whether to use Claude for unknown transactions
        """
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent.parent.parent / "config"
        self.merchant_lookup = MerchantLookup(self.config_dir)
        self.use_claude = use_claude
        self.model = model or self.DEFAULT_MODEL

        if use_claude:
            self.client = anthropic.Anthropic(api_key=api_key)
        else:
            self.client = None

        self._load_config()

    def _load_config(self) -> None:
        """Load configuration files."""
        # Load chart of accounts
        coa_file = self.config_dir / "chart_of_accounts.yaml"
        if coa_file.exists():
            with open(coa_file) as f:
                self.chart_of_accounts = yaml.safe_load(f)
        else:
            self.chart_of_accounts = {}

        # Load prompts
        prompts_dir = self.config_dir.parent / "prompts"
        prompt_file = prompts_dir / "classify_transaction.md"
        if prompt_file.exists():
            with open(prompt_file) as f:
                self._prompt_template = f.read()
        else:
            self._prompt_template = None

    def classify_single(
        self,
        transaction: ParsedTransaction,
        entity: str | None = None,
        use_claude_fallback: bool = True
    ) -> Classification | None:
        """Classify a single transaction.

        Args:
            transaction: Transaction to classify
            entity: Entity context
            use_claude_fallback: Whether to use Claude if lookup fails

        Returns:
            Classification or None if unable to classify
        """
        # 1. Try merchant lookup first
        match = self.merchant_lookup.lookup(transaction.merchant, entity)

        if match and match.confidence >= self.merchant_lookup.get_confidence_threshold():
            return Classification(
                account_code=match.account_code,
                account_name=match.account_name,
                category=match.category,
                confidence=match.confidence,
                method="lookup"
            )

        # 2. Try Claude if enabled
        if use_claude_fallback and self.use_claude and self.client:
            classifications = self._classify_with_claude(
                [transaction], entity
            )
            if classifications:
                return classifications[0]

        return None

    def classify_batch(
        self,
        transactions: list[ParsedTransaction],
        entity: str | None = None,
        batch_size: int = 30
    ) -> CategorizationResult:
        """Classify a batch of transactions.

        Args:
            transactions: Transactions to classify
            entity: Entity context
            batch_size: Batch size for Claude API calls

        Returns:
            CategorizationResult
        """
        result = CategorizationResult()
        pending_claude = []

        # 1. First pass: try merchant lookup
        for txn in transactions:
            match = self.merchant_lookup.lookup(txn.merchant, entity)

            if match and match.confidence >= self.merchant_lookup.get_confidence_threshold():
                classification = Classification(
                    account_code=match.account_code,
                    account_name=match.account_name,
                    category=match.category,
                    confidence=match.confidence,
                    method="lookup"
                )
                result.classified.append(ClassifiedTransaction(
                    transaction=txn,
                    classification=classification
                ))
            else:
                pending_claude.append(txn)

        # 2. Second pass: use Claude for remaining
        if pending_claude and self.use_claude and self.client:
            # Process in batches
            for i in range(0, len(pending_claude), batch_size):
                batch = pending_claude[i:i + batch_size]
                classifications = self._classify_with_claude(batch, entity)

                for j, txn in enumerate(batch):
                    if j < len(classifications) and classifications[j]:
                        result.classified.append(ClassifiedTransaction(
                            transaction=txn,
                            classification=classifications[j]
                        ))
                    else:
                        result.unclassified.append(txn)
        else:
            result.unclassified.extend(pending_claude)

        # Calculate stats
        total = len(transactions)
        lookup_count = sum(
            1 for ct in result.classified
            if ct.classification and ct.classification.method == "lookup"
        )
        claude_count = sum(
            1 for ct in result.classified
            if ct.classification and ct.classification.method == "claude"
        )

        result.stats = {
            "total": total,
            "classified": len(result.classified),
            "unclassified": len(result.unclassified),
            "by_lookup": lookup_count,
            "by_claude": claude_count,
            "classification_rate": len(result.classified) / total if total > 0 else 0
        }

        return result

    def _classify_with_claude(
        self,
        transactions: list[ParsedTransaction],
        entity: str | None
    ) -> list[Classification | None]:
        """Classify transactions using Claude API.

        Args:
            transactions: Transactions to classify
            entity: Entity context

        Returns:
            List of Classifications (may contain None for failures)
        """
        if not transactions:
            return []

        # Build prompt
        txn_data = [
            {
                "id": f"txn_{i}",
                "txn_date": txn.date.strftime("%Y-%m-%d"),
                "description": txn.description,
                "merchant": txn.merchant,
                "amount": float(txn.amount)
            }
            for i, txn in enumerate(transactions)
        ]

        # Build system prompt with chart of accounts
        coa_str = yaml.dump(self.chart_of_accounts, default_flow_style=False)

        system_prompt = f"""You are an accounting classification engine for BK Keyforce / BETRNK Group.
Entity: {entity or 'Unknown'}

Chart of accounts:
{coa_str}

Categories: revenue, commission, salary, expense, company_car, depreciation, cos, bank_charge

Classify each transaction. Output ONLY valid JSON array with no explanation.
For each transaction: account_code, account_name, category, confidence (0.0-1.0), anomaly (bool), anomaly_reason (string or null)."""

        user_prompt = f"""Classify these {len(transactions)} transactions:

{json.dumps(txn_data, indent=2)}

Return JSON array with same order as input."""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[
                    {"role": "user", "content": f"{system_prompt}\n\n{user_prompt}"}
                ]
            )

            response_text = message.content[0].text

            # Parse response
            cleaned = response_text.strip()
            cleaned = re.sub(r'^```json\s*', '', cleaned)
            cleaned = re.sub(r'^```\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned)

            classifications_data = json.loads(cleaned)

            # Convert to Classification objects
            results = []
            for i, data in enumerate(classifications_data):
                if isinstance(data, dict) and "account_code" in data:
                    results.append(Classification(
                        account_code=data.get("account_code", ""),
                        account_name=data.get("account_name", ""),
                        category=data.get("category", "expense"),
                        confidence=float(data.get("confidence", 0.5)),
                        method="claude",
                        anomaly=data.get("anomaly", False),
                        anomaly_reason=data.get("anomaly_reason")
                    ))
                else:
                    results.append(None)

            # Pad with None if response is shorter than input
            while len(results) < len(transactions):
                results.append(None)

            return results

        except Exception as e:
            logger.error(f"Claude classification error: {e}")
            return [None] * len(transactions)

    def detect_anomalies(
        self,
        transaction: ParsedTransaction,
        classification: Classification,
        historical_avg: float | None = None
    ) -> Classification:
        """Check transaction for anomalies.

        Args:
            transaction: Transaction to check
            classification: Current classification
            historical_avg: Historical average for this category

        Returns:
            Updated Classification with anomaly info
        """
        amount = abs(float(transaction.amount))
        reasons = []

        # Check against historical average
        if historical_avg and historical_avg > 0:
            deviation = (amount - historical_avg) / historical_avg
            if deviation > 0.3:  # 30% above average
                reasons.append(
                    f"Amount {amount:.2f} is {deviation*100:.0f}% above average ({historical_avg:.2f})"
                )

        # Check for unusually round amounts
        if amount >= 10000 and amount == int(amount):
            if amount % 10000 == 0:
                reasons.append(f"Suspiciously round amount: {amount:.0f}")

        # Check for unusual categories
        if classification.category == "company_car" and amount > 50000:
            reasons.append(f"High company car expense: {amount:.2f}")

        if reasons:
            classification.anomaly = True
            classification.anomaly_reason = "; ".join(reasons)

        return classification

    def suggest_account(
        self,
        merchant: str,
        description: str,
        amount: float,
        entity: str | None = None
    ) -> list[dict]:
        """Get account suggestions for manual categorization.

        Args:
            merchant: Merchant name
            description: Transaction description
            amount: Transaction amount
            entity: Entity context

        Returns:
            List of suggested accounts with confidence
        """
        suggestions = []

        # Get suggestions from merchant lookup
        matches = self.merchant_lookup.suggest_category(merchant, amount, entity)
        for match in matches:
            suggestions.append({
                "account_code": match.account_code,
                "account_name": match.account_name,
                "category": match.category,
                "confidence": match.confidence,
                "reason": f"Similar to {match.merchant_pattern}"
            })

        # Add common expense accounts if no good matches
        if not suggestions or suggestions[0]["confidence"] < 0.5:
            common_accounts = [
                ("6220", "General Supplies", "expense", 0.3),
                ("6230", "Meals & Entertainment", "expense", 0.3),
                ("6420", "Transportation", "expense", 0.3),
            ]
            for code, name, cat, conf in common_accounts:
                if not any(s["account_code"] == code for s in suggestions):
                    suggestions.append({
                        "account_code": code,
                        "account_name": name,
                        "category": cat,
                        "confidence": conf,
                        "reason": "Common expense category"
                    })

        # Sort by confidence
        suggestions.sort(key=lambda x: x["confidence"], reverse=True)

        return suggestions[:5]

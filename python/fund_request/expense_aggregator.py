"""
Expense Aggregator Module

Aggregates expenses from various sources for fund request generation.
"""

import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class AggregatedExpense:
    """Aggregated expense item."""

    category: str
    description: str
    amount: Decimal
    currency: str = "PHP"
    source: str = "manual"  # 'recurring', 'transaction', 'payroll', 'manual'
    source_count: int = 1  # Number of source records
    vendor: str | None = None
    account_code: str | None = None
    reference_ids: list[str] | None = None

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "description": self.description,
            "amount": float(self.amount),
            "currency": self.currency,
            "source": self.source,
            "source_count": self.source_count,
            "vendor": self.vendor,
            "account_code": self.account_code,
            "reference_ids": self.reference_ids,
        }


class ExpenseAggregator:
    """Aggregates expenses from multiple sources."""

    def __init__(self, config_dir: Path | str | None = None):
        """Initialize the aggregator.

        Args:
            config_dir: Path to configuration directory
        """
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent.parent.parent / "config"
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from YAML."""
        config_file = self.config_dir / "fund_request_config.yaml"
        if config_file.exists():
            with open(config_file) as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = {}

    def aggregate_recurring_expenses(
        self,
        entity: str,
        payment_date: date,
        recurring_data: list[dict],
    ) -> list[AggregatedExpense]:
        """Aggregate recurring expenses due for payment.

        Args:
            entity: Entity code
            payment_date: Payment date
            recurring_data: List of recurring expense records from DB

        Returns:
            List of AggregatedExpense items
        """
        expenses = []

        for record in recurring_data:
            if record.get("entity") != entity:
                continue

            if not record.get("is_active", True):
                continue

            # Check if expense is due on this payment date
            if not self._is_expense_due(record, payment_date):
                continue

            expense = AggregatedExpense(
                category=record.get("category", "other"),
                description=record.get("description", ""),
                amount=Decimal(str(record.get("amount", 0))),
                currency=record.get("currency", "PHP"),
                source="recurring",
                vendor=record.get("vendor"),
                account_code=record.get("account_code"),
                reference_ids=[str(record.get("id"))] if record.get("id") else None,
            )
            expenses.append(expense)

        return expenses

    def _is_expense_due(self, record: dict, payment_date: date) -> bool:
        """Check if a recurring expense is due on the payment date.

        Args:
            record: Recurring expense record
            payment_date: Payment date

        Returns:
            True if expense is due
        """
        frequency = record.get("frequency", "monthly")
        payment_day = record.get("payment_day")

        if frequency == "semi-monthly":
            # Due on both 5th and 20th
            return payment_date.day in [5, 20]

        elif frequency == "monthly":
            # Due once per month, typically on the payment day or first half
            if payment_day:
                # Due if payment_day falls in this payment period
                if payment_date.day == 5:
                    return payment_day <= 15
                else:  # payment_date.day == 20
                    return payment_day > 15
            else:
                # Default: due on first payment date of month
                return payment_date.day == 5

        elif frequency == "quarterly":
            # Due every 3 months
            if payment_date.month % 3 == 1:  # Jan, Apr, Jul, Oct
                return payment_date.day == 5
            return False

        elif frequency == "annual":
            # Check if this month matches the payment month
            next_payment = record.get("next_payment_date")
            if next_payment:
                if isinstance(next_payment, str):
                    next_payment = date.fromisoformat(next_payment)
                return (
                    next_payment.year == payment_date.year and
                    next_payment.month == payment_date.month
                )
            return False

        return False

    def aggregate_transactions(
        self,
        entity: str,
        start_date: date,
        end_date: date,
        transactions: list[dict],
        group_by: str = "category",
    ) -> list[AggregatedExpense]:
        """Aggregate transactions by category.

        Args:
            entity: Entity code
            start_date: Period start date
            end_date: Period end date
            transactions: List of transaction records
            group_by: Field to group by ('category', 'merchant', 'account_code')

        Returns:
            List of AggregatedExpense items
        """
        # Filter transactions
        filtered = [
            t for t in transactions
            if (
                t.get("entity") == entity and
                start_date <= date.fromisoformat(t.get("txn_date", "1900-01-01")) <= end_date
            )
        ]

        # Group by specified field
        groups: dict[str, list[dict]] = {}
        for txn in filtered:
            key = txn.get(group_by, "other") or "other"
            if key not in groups:
                groups[key] = []
            groups[key].append(txn)

        # Create aggregated expenses
        expenses = []
        for key, txns in groups.items():
            total = sum(Decimal(str(t.get("amount", 0))) for t in txns)

            expense = AggregatedExpense(
                category=key if group_by == "category" else txns[0].get("category", "expense"),
                description=self._get_category_description(key) if group_by == "category" else key,
                amount=total,
                currency="PHP",
                source="transaction",
                source_count=len(txns),
                account_code=txns[0].get("account_code") if group_by != "account_code" else key,
                reference_ids=[str(t.get("id")) for t in txns if t.get("id")],
            )
            expenses.append(expense)

        return expenses

    def aggregate_payroll(
        self,
        entity: str,
        payment_date: date,
        payroll_data: list[dict],
    ) -> list[AggregatedExpense]:
        """Aggregate payroll data for fund request.

        Args:
            entity: Entity code
            payment_date: Payment date
            payroll_data: List of payroll records

        Returns:
            List of AggregatedExpense items (salaries, allowances, etc.)
        """
        expenses = []

        # Filter by entity and payment period
        filtered = [
            p for p in payroll_data
            if p.get("entity") == entity
        ]

        if not filtered:
            return expenses

        # Aggregate by type
        salary_total = Decimal("0")
        allowance_total = Decimal("0")
        other_total = Decimal("0")

        for record in filtered:
            pay_type = record.get("type", "salary")
            amount = Decimal(str(record.get("amount", 0)))

            if pay_type == "salary":
                salary_total += amount
            elif pay_type in ["housing_allowance", "allowance"]:
                allowance_total += amount
            else:
                other_total += amount

        if salary_total > 0:
            expenses.append(AggregatedExpense(
                category="salaries",
                description="SALARIES",
                amount=salary_total,
                source="payroll",
                source_count=len([p for p in filtered if p.get("type") == "salary"]),
            ))

        if allowance_total > 0:
            expenses.append(AggregatedExpense(
                category="housing_allowance",
                description="Housing Allowance",
                amount=allowance_total,
                source="payroll",
                source_count=len([p for p in filtered if p.get("type") in ["housing_allowance", "allowance"]]),
            ))

        if other_total > 0:
            expenses.append(AggregatedExpense(
                category="other_payroll",
                description="Other Payroll Items",
                amount=other_total,
                source="payroll",
            ))

        return expenses

    def aggregate_credit_card_statements(
        self,
        entity: str,
        statement_date: date,
        transactions: list[dict],
    ) -> AggregatedExpense | None:
        """Aggregate credit card transactions for statement.

        Args:
            entity: Entity code
            statement_date: Statement date
            transactions: List of credit card transactions

        Returns:
            Single AggregatedExpense for credit card payment or None
        """
        # Filter credit card transactions
        filtered = [
            t for t in transactions
            if (
                t.get("entity") == entity and
                t.get("source") == "credit_card"
            )
        ]

        if not filtered:
            return None

        total = sum(Decimal(str(t.get("amount", 0))) for t in filtered)

        return AggregatedExpense(
            category="credit_card",
            description="CREDIT CARD",
            amount=total,
            source="transaction",
            source_count=len(filtered),
            reference_ids=[str(t.get("id")) for t in filtered if t.get("id")],
        )

    def _get_category_description(self, category: str) -> str:
        """Get human-readable description for a category.

        Args:
            category: Category code

        Returns:
            Description string
        """
        sections = self.config.get("sections", {})

        # Search in Section A
        for cat in sections.get("A", {}).get("categories", []):
            if cat.get("code") == category:
                return cat.get("name", category.title())

        # Search in Section B
        for cat in sections.get("B", {}).get("categories", []):
            if cat.get("code") == category:
                return cat.get("name", category.title())

        # Default
        return category.replace("_", " ").title()

    def categorize_to_section(self, category: str) -> str:
        """Determine which section a category belongs to.

        Args:
            category: Category code

        Returns:
            'A' or 'B'
        """
        sections = self.config.get("sections", {})

        # Check Section A categories
        section_a_codes = [
            cat.get("code") for cat in sections.get("A", {}).get("categories", [])
        ]
        if category in section_a_codes:
            return "A"

        # Check Section B categories
        section_b_codes = [
            cat.get("code") for cat in sections.get("B", {}).get("categories", [])
        ]
        if category in section_b_codes:
            return "B"

        # Default categories to Section A (regular)
        regular_categories = [
            "salaries", "salary", "rental", "utilities", "credit_card",
            "bir_tax", "government", "network", "housing_allowance",
            "subscription", "legal", "fund_replenishment",
        ]

        if category.lower() in regular_categories:
            return "A"

        return "B"

    def merge_aggregated_expenses(
        self,
        *expense_lists: list[AggregatedExpense],
    ) -> list[AggregatedExpense]:
        """Merge multiple lists of aggregated expenses.

        Args:
            expense_lists: Variable number of expense lists

        Returns:
            Merged list with duplicates combined
        """
        merged: dict[str, AggregatedExpense] = {}

        for expense_list in expense_lists:
            for expense in expense_list:
                key = f"{expense.category}_{expense.description}"

                if key in merged:
                    # Combine amounts
                    existing = merged[key]
                    existing.amount = existing.amount + expense.amount
                    existing.source_count += expense.source_count
                    if existing.reference_ids and expense.reference_ids:
                        existing.reference_ids.extend(expense.reference_ids)
                else:
                    merged[key] = expense

        return list(merged.values())

    def sort_expenses_by_priority(
        self,
        expenses: list[AggregatedExpense],
    ) -> list[AggregatedExpense]:
        """Sort expenses by category priority.

        Args:
            expenses: List of expenses

        Returns:
            Sorted list
        """
        priority_order = [
            "rental",
            "legal",
            "credit_card",
            "salaries",
            "salary",
            "fund_replenishment",
            "housing_allowance",
            "network",
            "bir_tax",
            "government",
            "utilities",
            "subscription",
            # Section B priorities
            "consultation",
            "er_share",
            "equipment",
            "travel",
            "marketing",
            "repairs",
            "other",
        ]

        def get_priority(expense: AggregatedExpense) -> int:
            try:
                return priority_order.index(expense.category)
            except ValueError:
                return len(priority_order)

        return sorted(expenses, key=get_priority)

"""
Fund Balance Tracker Module

Tracks fund/bank account balances for fund request reference section.
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class BankBalance:
    """Single bank/fund balance record."""

    entity: str
    account_name: str
    balance: Decimal
    currency: str = "PHP"
    balance_date: date = None
    bank: str | None = None
    account_number: str | None = None
    source: str = "manual"  # 'manual', 'api', 'statement'

    def __post_init__(self):
        if self.balance_date is None:
            self.balance_date = date.today()

    def to_dict(self) -> dict:
        return {
            "entity": self.entity,
            "account_name": self.account_name,
            "balance": float(self.balance),
            "currency": self.currency,
            "balance_date": self.balance_date.isoformat(),
            "bank": self.bank,
            "account_number": self.account_number,
            "source": self.source,
        }


@dataclass
class BalanceSummary:
    """Summary of all balances for an entity."""

    entity: str
    total_balance: Decimal
    currency: str = "PHP"
    accounts: list[BankBalance] = None
    as_of_date: date = None

    def __post_init__(self):
        if self.accounts is None:
            self.accounts = []
        if self.as_of_date is None:
            self.as_of_date = date.today()

    def to_dict(self) -> dict:
        return {
            "entity": self.entity,
            "total_balance": float(self.total_balance),
            "currency": self.currency,
            "accounts": [a.to_dict() for a in self.accounts],
            "as_of_date": self.as_of_date.isoformat(),
        }


class FundBalanceTracker:
    """Tracks and retrieves fund balances."""

    def __init__(self, config_dir: Path | str | None = None):
        """Initialize the tracker.

        Args:
            config_dir: Path to configuration directory
        """
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent.parent.parent / "config"
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from YAML."""
        entity_config = self.config_dir / "entity_config.yaml"
        if entity_config.exists():
            with open(entity_config) as f:
                self.entity_config = yaml.safe_load(f)
        else:
            self.entity_config = {}

    def get_current_balance(
        self,
        entity: str,
        balance_records: list[dict],
    ) -> BalanceSummary:
        """Get current balance summary for an entity.

        Args:
            entity: Entity code
            balance_records: List of balance records from DB

        Returns:
            BalanceSummary
        """
        # Filter records for entity
        entity_records = [
            r for r in balance_records
            if r.get("entity") == entity
        ]

        # Get most recent balance for each account
        latest_balances: dict[str, dict] = {}
        for record in entity_records:
            account_name = record.get("account_name", "")
            balance_date = record.get("balance_date")

            if isinstance(balance_date, str):
                balance_date = date.fromisoformat(balance_date)

            key = account_name
            if key not in latest_balances:
                latest_balances[key] = record
            else:
                existing_date = latest_balances[key].get("balance_date")
                if isinstance(existing_date, str):
                    existing_date = date.fromisoformat(existing_date)
                if balance_date and existing_date and balance_date > existing_date:
                    latest_balances[key] = record

        # Convert to BankBalance objects
        accounts = []
        total = Decimal("0")

        for record in latest_balances.values():
            balance = Decimal(str(record.get("balance", 0)))
            total += balance

            balance_date = record.get("balance_date")
            if isinstance(balance_date, str):
                balance_date = date.fromisoformat(balance_date)

            accounts.append(BankBalance(
                entity=entity,
                account_name=record.get("account_name", ""),
                balance=balance,
                currency=record.get("currency", "PHP"),
                balance_date=balance_date,
                bank=record.get("bank"),
                account_number=record.get("account_number"),
                source=record.get("source", "manual"),
            ))

        return BalanceSummary(
            entity=entity,
            total_balance=total,
            accounts=accounts,
            as_of_date=max((a.balance_date for a in accounts), default=date.today()),
        )

    def get_balance_history(
        self,
        entity: str,
        account_name: str,
        balance_records: list[dict],
        days: int = 30,
    ) -> list[BankBalance]:
        """Get balance history for an account.

        Args:
            entity: Entity code
            account_name: Account name
            balance_records: List of balance records from DB
            days: Number of days of history

        Returns:
            List of BankBalance records
        """
        cutoff_date = date.today()
        from datetime import timedelta
        start_date = cutoff_date - timedelta(days=days)

        history = []
        for record in balance_records:
            if record.get("entity") != entity:
                continue
            if record.get("account_name") != account_name:
                continue

            balance_date = record.get("balance_date")
            if isinstance(balance_date, str):
                balance_date = date.fromisoformat(balance_date)

            if balance_date and start_date <= balance_date <= cutoff_date:
                history.append(BankBalance(
                    entity=entity,
                    account_name=account_name,
                    balance=Decimal(str(record.get("balance", 0))),
                    currency=record.get("currency", "PHP"),
                    balance_date=balance_date,
                    bank=record.get("bank"),
                    source=record.get("source", "manual"),
                ))

        return sorted(history, key=lambda x: x.balance_date)

    def calculate_remaining_fund(
        self,
        current_balance: Decimal,
        project_expenses: list[dict],
    ) -> Decimal:
        """Calculate remaining fund after project expenses.

        Args:
            current_balance: Current fund balance
            project_expenses: List of project expense records

        Returns:
            Remaining fund balance
        """
        total_expenses = sum(
            Decimal(str(pe.get("amount", 0)))
            for pe in project_expenses
        )

        return current_balance - total_expenses

    def get_project_expenses(
        self,
        entity: str,
        transactions: list[dict],
        projects: list[str] | None = None,
    ) -> list[dict]:
        """Get expense totals by project.

        Args:
            entity: Entity code
            transactions: List of transaction records
            projects: List of project names to include (None = use config)

        Returns:
            List of project expense summaries
        """
        # Get project list from config if not provided
        if projects is None:
            overrides = self.entity_config.get("entity_overrides", {})
            entity_override = overrides.get(entity, {})
            projects = entity_override.get(
                "projects",
                self.entity_config.get("reference_info", {}).get("default_projects", [])
            )

        # Group transactions by project
        project_totals: dict[str, Decimal] = {p: Decimal("0") for p in projects}

        for txn in transactions:
            if txn.get("entity") != entity:
                continue

            # Try to match project from description or metadata
            project = self._match_project(txn, projects)
            if project:
                project_totals[project] += Decimal(str(txn.get("amount", 0)))

        # Convert to list
        result = []
        for project_name, amount in project_totals.items():
            if amount > 0:
                result.append({
                    "project_name": project_name,
                    "amount": float(amount),
                    "currency": "PHP",
                })

        return result

    def _match_project(
        self,
        transaction: dict,
        projects: list[str],
    ) -> str | None:
        """Match a transaction to a project.

        Args:
            transaction: Transaction record
            projects: List of project names

        Returns:
            Project name or None
        """
        # Check metadata for project assignment
        metadata = transaction.get("raw_data") or {}
        if isinstance(metadata, dict):
            project = metadata.get("project")
            if project and project in projects:
                return project

        # Try to match from description
        description = (transaction.get("description") or "").lower()
        for project in projects:
            if project.lower() in description:
                return project

        return None

    def record_balance(
        self,
        entity: str,
        account_name: str,
        balance: Decimal,
        balance_date: date | None = None,
        bank: str | None = None,
        account_number: str | None = None,
        source: str = "manual",
    ) -> BankBalance:
        """Create a new balance record (for API/manual entry).

        Args:
            entity: Entity code
            account_name: Account name
            balance: Balance amount
            balance_date: Balance date (defaults to today)
            bank: Bank name
            account_number: Account number (last 4 digits)
            source: Source of balance ('manual', 'api', 'statement')

        Returns:
            BankBalance record (caller should persist to DB)
        """
        return BankBalance(
            entity=entity,
            account_name=account_name,
            balance=balance,
            balance_date=balance_date or date.today(),
            bank=bank,
            account_number=account_number,
            source=source,
        )

    def validate_balance_entry(
        self,
        balance: BankBalance,
        previous_balance: BankBalance | None = None,
    ) -> list[str]:
        """Validate a balance entry.

        Args:
            balance: Balance to validate
            previous_balance: Previous balance for comparison

        Returns:
            List of validation warnings (empty if ok)
        """
        warnings = []

        # Check for negative balance
        if balance.balance < 0:
            warnings.append(f"Negative balance: {balance.balance}")

        # Check for large changes from previous
        if previous_balance:
            change = abs(balance.balance - previous_balance.balance)
            change_pct = (change / previous_balance.balance * 100) if previous_balance.balance else 0

            if change_pct > 50:
                warnings.append(
                    f"Large balance change: {change_pct:.1f}% "
                    f"({previous_balance.balance} -> {balance.balance})"
                )

        return warnings

    def get_all_entities_summary(
        self,
        balance_records: list[dict],
    ) -> list[BalanceSummary]:
        """Get balance summary for all entities.

        Args:
            balance_records: List of balance records from DB

        Returns:
            List of BalanceSummary for each entity
        """
        # Get unique entities
        entities = set(r.get("entity") for r in balance_records if r.get("entity"))

        summaries = []
        for entity in entities:
            summary = self.get_current_balance(entity, balance_records)
            summaries.append(summary)

        return summaries

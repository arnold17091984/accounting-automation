"""
Budget Variance Calculator Module

Calculates budget vs actual variances for all accounts and entities.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class VarianceItem:
    """Single variance calculation result."""

    entity: str
    account_code: str
    account_name: str
    category: str
    budget_amount: Decimal
    actual_amount: Decimal
    variance_amount: Decimal
    variance_percent: float
    utilization_percent: float
    is_over_budget: bool
    days_remaining: int = 0
    projected_month_end: Decimal | None = None

    @property
    def status(self) -> str:
        """Get status string based on utilization."""
        if self.utilization_percent >= 100:
            return "exceeded"
        elif self.utilization_percent >= 90:
            return "critical"
        elif self.utilization_percent >= 70:
            return "warning"
        else:
            return "ok"

    def to_dict(self) -> dict:
        return {
            "entity": self.entity,
            "account_code": self.account_code,
            "account_name": self.account_name,
            "category": self.category,
            "budget_amount": float(self.budget_amount),
            "actual_amount": float(self.actual_amount),
            "variance_amount": float(self.variance_amount),
            "variance_percent": self.variance_percent,
            "utilization_percent": self.utilization_percent,
            "is_over_budget": self.is_over_budget,
            "status": self.status,
            "days_remaining": self.days_remaining,
            "projected_month_end": float(self.projected_month_end) if self.projected_month_end else None
        }


@dataclass
class VarianceReport:
    """Complete variance report for an entity or period."""

    entity: str | None
    period: str  # YYYY-MM
    generated_at: datetime
    items: list[VarianceItem] = field(default_factory=list)
    summary: dict = field(default_factory=dict)

    @property
    def over_budget_items(self) -> list[VarianceItem]:
        return [i for i in self.items if i.is_over_budget]

    @property
    def warning_items(self) -> list[VarianceItem]:
        return [i for i in self.items if i.status in ["warning", "critical"]]

    def to_dict(self) -> dict:
        return {
            "entity": self.entity,
            "period": self.period,
            "generated_at": self.generated_at.isoformat(),
            "items": [i.to_dict() for i in self.items],
            "summary": self.summary
        }


class VarianceCalculator:
    """Calculates budget variances."""

    def __init__(self, config_dir: Path | str | None = None):
        """Initialize the calculator.

        Args:
            config_dir: Path to configuration directory
        """
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent.parent.parent / "config"
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration."""
        thresholds_file = self.config_dir / "budget_thresholds.yaml"
        if thresholds_file.exists():
            with open(thresholds_file) as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = {
                "thresholds": {
                    "warning": {"percentage": 70},
                    "critical": {"percentage": 90},
                    "exceeded": {"percentage": 100}
                }
            }

    def calculate_variance(
        self,
        entity: str,
        account_code: str,
        account_name: str,
        category: str,
        budget: Decimal,
        actual: Decimal,
        days_elapsed: int = 0,
        days_in_month: int = 30
    ) -> VarianceItem:
        """Calculate variance for a single account.

        Args:
            entity: Entity code
            account_code: Account code
            account_name: Account name
            category: Category
            budget: Budget amount
            actual: Actual amount
            days_elapsed: Days elapsed in period
            days_in_month: Total days in period

        Returns:
            VarianceItem
        """
        # Calculate basic variance
        variance = budget - actual
        variance_pct = float((actual - budget) / budget * 100) if budget > 0 else 0
        utilization = float(actual / budget * 100) if budget > 0 else 0

        # Calculate projected month-end
        days_remaining = max(0, days_in_month - days_elapsed)
        projected = None
        if days_elapsed > 0:
            daily_rate = actual / days_elapsed
            projected = actual + (daily_rate * days_remaining)

        return VarianceItem(
            entity=entity,
            account_code=account_code,
            account_name=account_name,
            category=category,
            budget_amount=budget,
            actual_amount=actual,
            variance_amount=variance,
            variance_percent=variance_pct,
            utilization_percent=utilization,
            is_over_budget=actual > budget,
            days_remaining=days_remaining,
            projected_month_end=projected
        )

    def calculate_report(
        self,
        entity: str | None,
        period: str,
        budget_data: list[dict],
        actual_data: list[dict]
    ) -> VarianceReport:
        """Calculate a complete variance report.

        Args:
            entity: Entity code (None for all entities)
            period: Period string (YYYY-MM)
            budget_data: List of budget records
            actual_data: List of actual spending records

        Returns:
            VarianceReport
        """
        report = VarianceReport(
            entity=entity,
            period=period,
            generated_at=datetime.now()
        )

        # Parse period
        year, month = map(int, period.split("-"))
        now = datetime.now()

        # Calculate days in month and elapsed
        if year == now.year and month == now.month:
            days_elapsed = now.day
        else:
            # Past month - full month
            import calendar
            days_elapsed = calendar.monthrange(year, month)[1]

        days_in_month = 30  # Simplified

        # Index actual data by entity and account
        actual_index = {}
        for record in actual_data:
            key = (record.get("entity"), record.get("account_code"))
            actual_index[key] = Decimal(str(record.get("total_amount", 0)))

        # Calculate variance for each budget item
        for budget_record in budget_data:
            record_entity = budget_record.get("entity")
            account_code = budget_record.get("account_code")

            # Filter by entity if specified
            if entity and record_entity != entity:
                continue

            budget_amount = Decimal(str(budget_record.get("budget_amount", 0)))
            actual_amount = actual_index.get((record_entity, account_code), Decimal("0"))

            item = self.calculate_variance(
                entity=record_entity,
                account_code=account_code,
                account_name=budget_record.get("account_name", ""),
                category=budget_record.get("category", "expense"),
                budget=budget_amount,
                actual=actual_amount,
                days_elapsed=days_elapsed,
                days_in_month=days_in_month
            )

            report.items.append(item)

        # Calculate summary
        total_budget = sum(i.budget_amount for i in report.items)
        total_actual = sum(i.actual_amount for i in report.items)

        report.summary = {
            "total_budget": float(total_budget),
            "total_actual": float(total_actual),
            "total_variance": float(total_budget - total_actual),
            "overall_utilization": float(total_actual / total_budget * 100) if total_budget > 0 else 0,
            "accounts_over_budget": len(report.over_budget_items),
            "accounts_warning": len(report.warning_items),
            "accounts_ok": len([i for i in report.items if i.status == "ok"]),
        }

        return report

    def get_top_variances(
        self,
        report: VarianceReport,
        limit: int = 10,
        only_over_budget: bool = False
    ) -> list[VarianceItem]:
        """Get top variance items by absolute variance.

        Args:
            report: VarianceReport to analyze
            limit: Maximum items to return
            only_over_budget: Only include over-budget items

        Returns:
            List of VarianceItem sorted by absolute variance
        """
        items = report.items

        if only_over_budget:
            items = [i for i in items if i.is_over_budget]

        # Sort by absolute variance percentage
        sorted_items = sorted(
            items,
            key=lambda x: abs(x.variance_percent),
            reverse=True
        )

        return sorted_items[:limit]

    def compare_periods(
        self,
        report1: VarianceReport,
        report2: VarianceReport
    ) -> dict:
        """Compare variances between two periods.

        Args:
            report1: First period report
            report2: Second period report (typically later)

        Returns:
            Comparison dictionary
        """
        # Index items by account
        items1 = {i.account_code: i for i in report1.items}
        items2 = {i.account_code: i for i in report2.items}

        comparison = {
            "period1": report1.period,
            "period2": report2.period,
            "improved": [],  # Better utilization
            "worsened": [],  # Worse utilization
            "new_issues": [],  # New over-budget items
            "resolved": [],  # Previously over, now ok
        }

        all_accounts = set(items1.keys()) | set(items2.keys())

        for account in all_accounts:
            item1 = items1.get(account)
            item2 = items2.get(account)

            if item1 and item2:
                util_change = item2.utilization_percent - item1.utilization_percent

                if util_change < -5:  # 5% improvement
                    comparison["improved"].append({
                        "account": account,
                        "name": item2.account_name,
                        "change": util_change
                    })
                elif util_change > 5:  # 5% worsening
                    comparison["worsened"].append({
                        "account": account,
                        "name": item2.account_name,
                        "change": util_change
                    })

                if not item1.is_over_budget and item2.is_over_budget:
                    comparison["new_issues"].append(item2.to_dict())
                elif item1.is_over_budget and not item2.is_over_budget:
                    comparison["resolved"].append(item2.to_dict())

        return comparison

"""
Budget Threshold Checker Module

Monitors budget utilization and triggers alerts when thresholds are breached.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from .variance_calculator import VarianceItem, VarianceReport

logger = logging.getLogger(__name__)


@dataclass
class ThresholdAlert:
    """Alert triggered when a threshold is breached."""

    entity: str
    account_code: str
    account_name: str
    threshold_type: str  # 'warning', 'critical', 'exceeded'
    threshold_percent: int
    actual_percent: float
    actual_amount: Decimal
    budget_amount: Decimal
    triggered_at: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False
    message: str = ""

    @property
    def severity(self) -> str:
        """Get alert severity."""
        if self.threshold_type == "exceeded":
            return "high"
        elif self.threshold_type == "critical":
            return "medium"
        return "low"

    def to_dict(self) -> dict:
        return {
            "entity": self.entity,
            "account_code": self.account_code,
            "account_name": self.account_name,
            "threshold_type": self.threshold_type,
            "threshold_percent": self.threshold_percent,
            "actual_percent": self.actual_percent,
            "actual_amount": float(self.actual_amount),
            "budget_amount": float(self.budget_amount),
            "triggered_at": self.triggered_at.isoformat(),
            "severity": self.severity,
            "message": self.message
        }


@dataclass
class ThresholdCheckResult:
    """Result of threshold checking."""

    alerts: list[ThresholdAlert] = field(default_factory=list)
    checked_count: int = 0
    alert_count: int = 0
    by_severity: dict = field(default_factory=dict)

    @property
    def has_critical_alerts(self) -> bool:
        return any(a.severity in ["high", "medium"] for a in self.alerts)


class ThresholdChecker:
    """Checks budget thresholds and generates alerts."""

    def __init__(self, config_dir: Path | str | None = None):
        """Initialize the threshold checker.

        Args:
            config_dir: Path to configuration directory
        """
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent.parent.parent / "config"
        self._load_config()
        self._alert_history: dict[str, datetime] = {}  # Track sent alerts

    def _load_config(self) -> None:
        """Load threshold configuration."""
        config_file = self.config_dir / "budget_thresholds.yaml"

        if config_file.exists():
            with open(config_file) as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = self._default_config()

        # Parse thresholds
        self.thresholds = self.config.get("thresholds", {})
        self.account_overrides = self.config.get("account_overrides", {})
        self.entity_overrides = self.config.get("entity_overrides", {})
        self.cooldown_hours = self.config.get("cooldown", {}).get("same_threshold_hours", 24)

    def _default_config(self) -> dict:
        """Get default configuration."""
        return {
            "thresholds": {
                "warning": {"percentage": 70, "severity": "low"},
                "critical": {"percentage": 90, "severity": "medium"},
                "exceeded": {"percentage": 100, "severity": "high"}
            },
            "cooldown": {
                "same_threshold_hours": 24
            }
        }

    def get_threshold_for_account(
        self,
        account_code: str,
        entity: str,
        threshold_type: str
    ) -> int:
        """Get threshold percentage for an account.

        Args:
            account_code: Account code
            entity: Entity code
            threshold_type: Threshold type (warning, critical, exceeded)

        Returns:
            Threshold percentage
        """
        # Check account-specific override
        if account_code in self.account_overrides:
            override = self.account_overrides[account_code].get(threshold_type)
            if override is not None:
                return override

        # Check entity-specific default
        if entity in self.entity_overrides:
            override = self.entity_overrides[entity].get(f"default_{threshold_type}")
            if override is not None:
                return override

        # Use global default
        return self.thresholds.get(threshold_type, {}).get("percentage", 100)

    def check_variance(self, item: VarianceItem) -> ThresholdAlert | None:
        """Check a single variance item against thresholds.

        Args:
            item: VarianceItem to check

        Returns:
            ThresholdAlert if threshold breached, None otherwise
        """
        utilization = item.utilization_percent

        # Get thresholds for this account
        warning_threshold = self.get_threshold_for_account(
            item.account_code, item.entity, "warning"
        )
        critical_threshold = self.get_threshold_for_account(
            item.account_code, item.entity, "critical"
        )
        exceeded_threshold = self.get_threshold_for_account(
            item.account_code, item.entity, "exceeded"
        )

        # Determine which threshold was breached (highest first)
        threshold_type = None
        threshold_pct = 0

        if utilization >= exceeded_threshold:
            threshold_type = "exceeded"
            threshold_pct = exceeded_threshold
        elif utilization >= critical_threshold:
            threshold_type = "critical"
            threshold_pct = critical_threshold
        elif utilization >= warning_threshold:
            threshold_type = "warning"
            threshold_pct = warning_threshold

        if not threshold_type:
            return None

        # Check cooldown
        alert_key = f"{item.entity}_{item.account_code}_{threshold_type}"
        if alert_key in self._alert_history:
            last_alert = self._alert_history[alert_key]
            hours_since = (datetime.now() - last_alert).total_seconds() / 3600
            if hours_since < self.cooldown_hours:
                return None  # Still in cooldown

        # Create alert
        message = self._format_alert_message(
            item, threshold_type, threshold_pct
        )

        alert = ThresholdAlert(
            entity=item.entity,
            account_code=item.account_code,
            account_name=item.account_name,
            threshold_type=threshold_type,
            threshold_percent=threshold_pct,
            actual_percent=utilization,
            actual_amount=item.actual_amount,
            budget_amount=item.budget_amount,
            message=message
        )

        # Record alert time
        self._alert_history[alert_key] = datetime.now()

        return alert

    def check_report(self, report: VarianceReport) -> ThresholdCheckResult:
        """Check all items in a variance report.

        Args:
            report: VarianceReport to check

        Returns:
            ThresholdCheckResult
        """
        result = ThresholdCheckResult(checked_count=len(report.items))

        for item in report.items:
            alert = self.check_variance(item)
            if alert:
                result.alerts.append(alert)

        result.alert_count = len(result.alerts)

        # Group by severity
        result.by_severity = {
            "high": [a for a in result.alerts if a.severity == "high"],
            "medium": [a for a in result.alerts if a.severity == "medium"],
            "low": [a for a in result.alerts if a.severity == "low"]
        }

        return result

    def _format_alert_message(
        self,
        item: VarianceItem,
        threshold_type: str,
        threshold_pct: int
    ) -> str:
        """Format alert message.

        Args:
            item: VarianceItem
            threshold_type: Type of threshold breached
            threshold_pct: Threshold percentage

        Returns:
            Formatted message string
        """
        templates = self.config.get("thresholds", {}).get(threshold_type, {})
        template = templates.get("message_template")

        if template:
            return template.format(
                entity=item.entity,
                account_name=item.account_name,
                actual=item.actual_amount,
                budget=item.budget_amount,
                pct=f"{item.utilization_percent:.1f}",
                remaining=item.budget_amount - item.actual_amount,
                over_amount=item.actual_amount - item.budget_amount if item.is_over_budget else 0
            )

        # Default message
        if threshold_type == "exceeded":
            return (
                f"🔴 Budget Exceeded: {item.entity} - {item.account_name}\n"
                f"Spent: ₱{item.actual_amount:,.2f} / ₱{item.budget_amount:,.2f} "
                f"({item.utilization_percent:.1f}%)\n"
                f"Over budget by: ₱{item.actual_amount - item.budget_amount:,.2f}"
            )
        elif threshold_type == "critical":
            return (
                f"🟠 Budget Critical: {item.entity} - {item.account_name}\n"
                f"Spent: ₱{item.actual_amount:,.2f} / ₱{item.budget_amount:,.2f} "
                f"({item.utilization_percent:.1f}%)\n"
                f"Remaining: ₱{item.budget_amount - item.actual_amount:,.2f}"
            )
        else:
            return (
                f"⚠️ Budget Warning: {item.entity} - {item.account_name}\n"
                f"Spent: ₱{item.actual_amount:,.2f} / ₱{item.budget_amount:,.2f} "
                f"({item.utilization_percent:.1f}%)"
            )

    def acknowledge_alert(self, alert: ThresholdAlert) -> None:
        """Acknowledge an alert.

        Args:
            alert: Alert to acknowledge
        """
        alert.acknowledged = True

    def clear_cooldown(self, entity: str | None = None, account_code: str | None = None) -> None:
        """Clear alert cooldown history.

        Args:
            entity: Optional entity to clear (None for all)
            account_code: Optional account to clear
        """
        if entity is None and account_code is None:
            self._alert_history.clear()
        else:
            keys_to_remove = []
            for key in self._alert_history:
                parts = key.split("_")
                if entity and parts[0] == entity:
                    if account_code is None or parts[1] == account_code:
                        keys_to_remove.append(key)
            for key in keys_to_remove:
                del self._alert_history[key]

    def get_pending_alerts_count(self) -> int:
        """Get count of alerts in cooldown."""
        return len(self._alert_history)

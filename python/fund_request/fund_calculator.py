"""
Fund Calculator Module

Calculates fund request totals and validates data.
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class FundRequestItem:
    """Single line item in a fund request."""

    description: str
    amount: Decimal
    section: str  # 'A' or 'B'
    line_number: int = 0
    category: str | None = None
    vendor: str | None = None
    currency: str = "PHP"
    account_code: str | None = None
    notes: str | None = None
    reference_id: str | None = None
    reference_type: str = "manual"  # 'recurring_expense', 'transaction', 'manual'

    def to_dict(self) -> dict:
        return {
            "description": self.description,
            "amount": float(self.amount),
            "section": self.section,
            "line_number": self.line_number,
            "category": self.category,
            "vendor": self.vendor,
            "currency": self.currency,
            "account_code": self.account_code,
            "notes": self.notes,
            "reference_id": self.reference_id,
            "reference_type": self.reference_type,
        }


@dataclass
class ProjectExpense:
    """Project-wise expense for reference section."""

    project_name: str
    amount: Decimal
    currency: str = "PHP"
    notes: str | None = None

    def to_dict(self) -> dict:
        return {
            "project_name": self.project_name,
            "amount": float(self.amount),
            "currency": self.currency,
            "notes": self.notes,
        }


@dataclass
class FundRequestData:
    """Complete fund request data structure."""

    entity: str
    request_date: date
    payment_date: date
    period_label: str | None = None

    # Section items
    section_a_items: list[FundRequestItem] = field(default_factory=list)
    section_b_items: list[FundRequestItem] = field(default_factory=list)

    # Calculated totals
    section_a_total: Decimal = Decimal("0")
    section_b_total: Decimal = Decimal("0")
    overall_total: Decimal = Decimal("0")

    # Fund balance info (reference)
    current_fund_balance: Decimal | None = None
    project_expenses: list[ProjectExpense] = field(default_factory=list)
    project_expenses_total: Decimal = Decimal("0")
    remaining_fund: Decimal | None = None

    # Metadata
    created_by: str | None = None
    created_at: datetime = field(default_factory=datetime.now)

    def calculate_totals(self) -> None:
        """Recalculate all totals from items."""
        self.section_a_total = sum(
            item.amount for item in self.section_a_items
        )
        self.section_b_total = sum(
            item.amount for item in self.section_b_items
        )
        self.overall_total = self.section_a_total + self.section_b_total

        self.project_expenses_total = sum(
            pe.amount for pe in self.project_expenses
        )

        if self.current_fund_balance is not None:
            self.remaining_fund = self.current_fund_balance - self.project_expenses_total

    def add_section_a_item(self, item: FundRequestItem) -> None:
        """Add item to Section A."""
        item.section = "A"
        item.line_number = len(self.section_a_items) + 1
        self.section_a_items.append(item)
        self.calculate_totals()

    def add_section_b_item(self, item: FundRequestItem) -> None:
        """Add item to Section B."""
        item.section = "B"
        item.line_number = len(self.section_b_items) + 1
        self.section_b_items.append(item)
        self.calculate_totals()

    def add_project_expense(self, project: ProjectExpense) -> None:
        """Add project expense to reference section."""
        self.project_expenses.append(project)
        self.calculate_totals()

    def to_dict(self) -> dict:
        return {
            "entity": self.entity,
            "request_date": self.request_date.isoformat(),
            "payment_date": self.payment_date.isoformat(),
            "period_label": self.period_label,
            "section_a_items": [i.to_dict() for i in self.section_a_items],
            "section_b_items": [i.to_dict() for i in self.section_b_items],
            "section_a_total": float(self.section_a_total),
            "section_b_total": float(self.section_b_total),
            "overall_total": float(self.overall_total),
            "current_fund_balance": float(self.current_fund_balance) if self.current_fund_balance else None,
            "project_expenses": [pe.to_dict() for pe in self.project_expenses],
            "project_expenses_total": float(self.project_expenses_total),
            "remaining_fund": float(self.remaining_fund) if self.remaining_fund else None,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
        }


class FundCalculator:
    """Calculates and validates fund request data."""

    def __init__(self, config_dir: Path | str | None = None):
        """Initialize the calculator.

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
            logger.warning(f"Config file not found: {config_file}")
            self.config = {}

    def create_fund_request(
        self,
        entity: str,
        payment_date: date,
        section_a_items: list[dict] | None = None,
        section_b_items: list[dict] | None = None,
        current_fund_balance: Decimal | None = None,
        project_expenses: list[dict] | None = None,
        created_by: str | None = None,
    ) -> FundRequestData:
        """Create a new fund request with calculated totals.

        Args:
            entity: Entity code
            payment_date: Target payment date
            section_a_items: List of Section A item dicts
            section_b_items: List of Section B item dicts
            current_fund_balance: Current fund balance
            project_expenses: List of project expense dicts
            created_by: User who created the request

        Returns:
            FundRequestData with calculated totals
        """
        # Determine period label
        period_label = self._get_period_label(payment_date)

        fund_request = FundRequestData(
            entity=entity,
            request_date=date.today(),
            payment_date=payment_date,
            period_label=period_label,
            current_fund_balance=current_fund_balance,
            created_by=created_by,
        )

        # Add Section A items
        if section_a_items:
            for i, item_data in enumerate(section_a_items):
                item = FundRequestItem(
                    description=item_data["description"],
                    amount=Decimal(str(item_data["amount"])),
                    section="A",
                    line_number=i + 1,
                    category=item_data.get("category"),
                    vendor=item_data.get("vendor"),
                    currency=item_data.get("currency", "PHP"),
                    account_code=item_data.get("account_code"),
                    notes=item_data.get("notes"),
                    reference_id=item_data.get("reference_id"),
                    reference_type=item_data.get("reference_type", "manual"),
                )
                fund_request.section_a_items.append(item)

        # Add Section B items
        if section_b_items:
            for i, item_data in enumerate(section_b_items):
                item = FundRequestItem(
                    description=item_data["description"],
                    amount=Decimal(str(item_data["amount"])),
                    section="B",
                    line_number=i + 1,
                    category=item_data.get("category"),
                    vendor=item_data.get("vendor"),
                    currency=item_data.get("currency", "PHP"),
                    account_code=item_data.get("account_code"),
                    notes=item_data.get("notes"),
                    reference_id=item_data.get("reference_id"),
                    reference_type=item_data.get("reference_type", "manual"),
                )
                fund_request.section_b_items.append(item)

        # Add project expenses
        if project_expenses:
            for pe_data in project_expenses:
                pe = ProjectExpense(
                    project_name=pe_data["project_name"],
                    amount=Decimal(str(pe_data["amount"])),
                    currency=pe_data.get("currency", "PHP"),
                    notes=pe_data.get("notes"),
                )
                fund_request.project_expenses.append(pe)

        # Calculate totals
        fund_request.calculate_totals()

        return fund_request

    def _get_period_label(self, payment_date: date) -> str:
        """Get period label for payment date.

        Args:
            payment_date: Payment date

        Returns:
            Period label string (e.g., "February 2026 - 1st Half")
        """
        month_name = payment_date.strftime("%B")
        year = payment_date.year

        schedule = self.config.get("payment_schedule", {}).get("payment_dates", [])

        for sched in schedule:
            if payment_date.day == sched.get("day"):
                return f"{month_name} {year} - {sched.get('label', '')}"

        # Default label if not matching schedule
        half = "1st Half" if payment_date.day <= 15 else "2nd Half"
        return f"{month_name} {year} - {half}"

    def validate_fund_request(self, fund_request: FundRequestData) -> list[str]:
        """Validate a fund request.

        Args:
            fund_request: FundRequestData to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        validation = self.config.get("validation", {})

        # Check required fields
        if not fund_request.entity:
            errors.append("Entity is required")

        if not fund_request.payment_date:
            errors.append("Payment date is required")

        # Check that at least one section has items
        if not fund_request.section_a_items and not fund_request.section_b_items:
            errors.append("At least one section must have items")

        # Check amount limits
        limits = validation.get("amount_limits", {})
        min_amount = Decimal(str(limits.get("min_item_amount", 0.01)))
        max_amount = Decimal(str(limits.get("max_item_amount", 100000000)))
        max_total = Decimal(str(limits.get("max_total_amount", 500000000)))

        all_items = fund_request.section_a_items + fund_request.section_b_items
        for item in all_items:
            if item.amount < min_amount:
                errors.append(f"Item '{item.description}' amount {item.amount} is below minimum {min_amount}")
            if item.amount > max_amount:
                errors.append(f"Item '{item.description}' amount {item.amount} exceeds maximum {max_amount}")

        if fund_request.overall_total > max_total:
            errors.append(f"Overall total {fund_request.overall_total} exceeds maximum {max_total}")

        return errors

    def get_warnings(self, fund_request: FundRequestData) -> list[str]:
        """Get warning messages for a fund request.

        Args:
            fund_request: FundRequestData to check

        Returns:
            List of warning messages
        """
        warnings = []
        warning_configs = self.config.get("validation", {}).get("warnings", [])

        for warning_config in warning_configs:
            condition = warning_config.get("condition", "")
            message = warning_config.get("message", "")

            # Evaluate condition
            try:
                # Create context for evaluation
                context = {
                    "overall_total": float(fund_request.overall_total),
                    "section_a_total": float(fund_request.section_a_total),
                    "section_b_total": float(fund_request.section_b_total),
                    "current_fund_balance": float(fund_request.current_fund_balance or 0),
                }

                if eval(condition, {"__builtins__": {}}, context):
                    warnings.append(message)
            except Exception as e:
                logger.warning(f"Failed to evaluate warning condition: {condition}, error: {e}")

        return warnings

    def get_next_payment_date(self, from_date: date | None = None) -> date:
        """Get the next payment date based on schedule.

        Args:
            from_date: Starting date (defaults to today)

        Returns:
            Next payment date
        """
        if from_date is None:
            from_date = date.today()

        schedule = self.config.get("payment_schedule", {}).get("payment_dates", [])
        if not schedule:
            # Default to 5th and 20th
            schedule = [{"day": 5}, {"day": 20}]

        payment_days = sorted([s.get("day", 5) for s in schedule])

        # Find next payment day in current month
        for day in payment_days:
            if from_date.day < day:
                return from_date.replace(day=day)

        # Next month, first payment day
        next_month = from_date.month + 1
        next_year = from_date.year
        if next_month > 12:
            next_month = 1
            next_year += 1

        return date(next_year, next_month, payment_days[0])

    def get_generation_date(self, payment_date: date) -> date:
        """Get the date when fund request should be generated.

        Args:
            payment_date: Payment date

        Returns:
            Generation date
        """
        schedule = self.config.get("payment_schedule", {}).get("payment_dates", [])

        for sched in schedule:
            if payment_date.day == sched.get("day"):
                days_before = sched.get("generate_days_before", 2)
                gen_day = payment_date.day - days_before
                if gen_day < 1:
                    # Previous month
                    prev_month = payment_date.month - 1
                    prev_year = payment_date.year
                    if prev_month < 1:
                        prev_month = 12
                        prev_year -= 1
                    # Get last day of previous month
                    import calendar
                    last_day = calendar.monthrange(prev_year, prev_month)[1]
                    gen_day = last_day + gen_day
                    return date(prev_year, prev_month, gen_day)
                return payment_date.replace(day=gen_day)

        # Default: 2 days before
        return payment_date.replace(day=max(1, payment_date.day - 2))

    def get_entity_title(self, entity: str) -> str:
        """Get the fund request title for an entity.

        Args:
            entity: Entity code

        Returns:
            Title string
        """
        overrides = self.config.get("entity_overrides", {})
        entity_config = overrides.get(entity, {})

        if "section_title" in entity_config:
            return entity_config["section_title"]

        # Default title
        entity_names = {
            "solaire": "Solaire",
            "cod": "COD",
            "royce": "Royce Clark",
            "manila_junket": "Manila Junket",
            "tours": "Betrnk Tours",
            "midori": "Midori no Mart",
        }

        name = entity_names.get(entity, entity.title())
        return f"{name} FUND REQUEST"

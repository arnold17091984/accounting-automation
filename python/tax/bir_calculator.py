"""
BIR Tax Calculator Module

Handles Philippine tax computations including VAT, EWT, FWT,
compensation tax, and corporate income tax.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any
from enum import Enum

import yaml

logger = logging.getLogger(__name__)


class TaxType(Enum):
    """Types of Philippine taxes."""
    VAT = "vat"
    PERCENTAGE_TAX = "percentage_tax"
    EWT = "ewt"  # Expanded Withholding Tax
    FWT = "fwt"  # Final Withholding Tax
    COMPENSATION = "compensation"
    CORPORATE_INCOME = "corporate_income"
    DST = "dst"  # Documentary Stamp Tax


class VATType(Enum):
    """VAT transaction types."""
    VATABLE = "vatable"
    ZERO_RATED = "zero_rated"
    EXEMPT = "exempt"


@dataclass
class VATComputation:
    """VAT computation result."""

    gross_amount: Decimal
    vat_type: VATType
    vat_rate: Decimal
    vat_amount: Decimal
    net_amount: Decimal  # Amount before VAT
    is_inclusive: bool = True  # Whether input was VAT-inclusive

    def to_dict(self) -> dict:
        return {
            "gross_amount": float(self.gross_amount),
            "vat_type": self.vat_type.value,
            "vat_rate": float(self.vat_rate),
            "vat_amount": float(self.vat_amount),
            "net_amount": float(self.net_amount),
            "is_inclusive": self.is_inclusive
        }


@dataclass
class WithholdingComputation:
    """Withholding tax computation result."""

    gross_amount: Decimal
    tax_type: str  # ewt, fwt
    tax_category: str  # professional_fees, rentals, etc.
    tax_rate: Decimal
    tax_amount: Decimal
    net_amount: Decimal  # Amount after withholding

    def to_dict(self) -> dict:
        return {
            "gross_amount": float(self.gross_amount),
            "tax_type": self.tax_type,
            "tax_category": self.tax_category,
            "tax_rate": float(self.tax_rate),
            "tax_amount": float(self.tax_amount),
            "net_amount": float(self.net_amount)
        }


@dataclass
class CompensationTax:
    """Compensation tax computation result."""

    gross_compensation: Decimal
    taxable_income: Decimal
    tax_due: Decimal
    tax_bracket: str
    effective_rate: Decimal
    non_taxable_benefits: Decimal = Decimal("0")
    sss_contribution: Decimal = Decimal("0")
    philhealth_contribution: Decimal = Decimal("0")
    pagibig_contribution: Decimal = Decimal("0")

    def to_dict(self) -> dict:
        return {
            "gross_compensation": float(self.gross_compensation),
            "taxable_income": float(self.taxable_income),
            "tax_due": float(self.tax_due),
            "tax_bracket": self.tax_bracket,
            "effective_rate": float(self.effective_rate),
            "non_taxable_benefits": float(self.non_taxable_benefits),
            "total_deductions": float(
                self.sss_contribution + self.philhealth_contribution + self.pagibig_contribution
            )
        }


@dataclass
class TaxComputation:
    """Complete tax computation for a transaction or period."""

    entity: str
    period: str
    computation_date: datetime = field(default_factory=datetime.now)

    # VAT
    output_vat: Decimal = Decimal("0")
    input_vat: Decimal = Decimal("0")
    vat_payable: Decimal = Decimal("0")

    # Withholding taxes
    ewt_payable: Decimal = Decimal("0")
    fwt_payable: Decimal = Decimal("0")
    compensation_tax_payable: Decimal = Decimal("0")

    # Income tax
    taxable_income: Decimal = Decimal("0")
    income_tax_due: Decimal = Decimal("0")

    # Details
    vat_details: list[VATComputation] = field(default_factory=list)
    ewt_details: list[WithholdingComputation] = field(default_factory=list)
    fwt_details: list[WithholdingComputation] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "entity": self.entity,
            "period": self.period,
            "computation_date": self.computation_date.isoformat(),
            "output_vat": float(self.output_vat),
            "input_vat": float(self.input_vat),
            "vat_payable": float(self.vat_payable),
            "ewt_payable": float(self.ewt_payable),
            "fwt_payable": float(self.fwt_payable),
            "compensation_tax_payable": float(self.compensation_tax_payable),
            "taxable_income": float(self.taxable_income),
            "income_tax_due": float(self.income_tax_due)
        }


class BIRCalculator:
    """Philippine BIR tax calculator."""

    def __init__(self, config_dir: Path | str | None = None):
        """Initialize calculator with tax rules.

        Args:
            config_dir: Path to configuration directory
        """
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent
        self._load_rules()

    def _load_rules(self) -> None:
        """Load tax rules from YAML configuration."""
        rules_file = self.config_dir / "tax_rules.yaml"
        if rules_file.exists():
            with open(rules_file) as f:
                self.rules = yaml.safe_load(f)
        else:
            # Default rules
            self.rules = {
                "vat": {"standard_rate": 0.12},
                "percentage_tax": {"rate": 0.03},
                "ewt": {},
                "fwt": {},
                "compensation_tax": {"brackets": []},
                "corporate_tax": {"domestic_corporation": {"general": 0.25}}
            }

    # ==================== VAT Calculations ====================

    def compute_vat(
        self,
        amount: Decimal,
        vat_type: VATType = VATType.VATABLE,
        is_inclusive: bool = True
    ) -> VATComputation:
        """Compute VAT for a transaction.

        Args:
            amount: Transaction amount
            vat_type: Type of VAT treatment
            is_inclusive: Whether amount is VAT-inclusive

        Returns:
            VATComputation result
        """
        vat_rate = Decimal(str(self.rules["vat"]["standard_rate"]))

        if vat_type == VATType.EXEMPT or vat_type == VATType.ZERO_RATED:
            vat_rate = Decimal("0")

        if vat_type == VATType.ZERO_RATED:
            return VATComputation(
                gross_amount=amount,
                vat_type=vat_type,
                vat_rate=Decimal("0"),
                vat_amount=Decimal("0"),
                net_amount=amount,
                is_inclusive=False
            )

        if is_inclusive:
            # VAT-inclusive: amount / 1.12
            net_amount = (amount / (1 + vat_rate)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            vat_amount = amount - net_amount
        else:
            # VAT-exclusive: amount * 0.12
            net_amount = amount
            vat_amount = (amount * vat_rate).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

        return VATComputation(
            gross_amount=amount if is_inclusive else amount + vat_amount,
            vat_type=vat_type,
            vat_rate=vat_rate,
            vat_amount=vat_amount,
            net_amount=net_amount,
            is_inclusive=is_inclusive
        )

    def compute_output_vat(
        self,
        sales: list[dict]
    ) -> tuple[Decimal, list[VATComputation]]:
        """Compute total output VAT from sales.

        Args:
            sales: List of sales with 'amount' and optional 'vat_type'

        Returns:
            Tuple of (total_output_vat, list of computations)
        """
        total_vat = Decimal("0")
        computations = []

        for sale in sales:
            amount = Decimal(str(sale.get("amount", 0)))
            vat_type_str = sale.get("vat_type", "vatable")
            vat_type = VATType(vat_type_str)
            is_inclusive = sale.get("is_inclusive", True)

            comp = self.compute_vat(amount, vat_type, is_inclusive)
            total_vat += comp.vat_amount
            computations.append(comp)

        return total_vat, computations

    def compute_input_vat(
        self,
        purchases: list[dict]
    ) -> tuple[Decimal, list[VATComputation]]:
        """Compute total input VAT from purchases.

        Args:
            purchases: List of purchases with 'amount' and optional 'vat_type'

        Returns:
            Tuple of (total_input_vat, list of computations)
        """
        return self.compute_output_vat(purchases)  # Same calculation

    # ==================== Withholding Tax Calculations ====================

    def compute_ewt(
        self,
        amount: Decimal,
        category: str,
        subcategory: str = "general"
    ) -> WithholdingComputation:
        """Compute Expanded Withholding Tax.

        Args:
            amount: Gross amount
            category: EWT category (professional_fees, rentals, services, etc.)
            subcategory: Subcategory or rate type

        Returns:
            WithholdingComputation result
        """
        ewt_rules = self.rules.get("ewt", {})
        category_rules = ewt_rules.get(category, {})

        if isinstance(category_rules, dict):
            rate = Decimal(str(category_rules.get(subcategory, 0)))
        else:
            rate = Decimal(str(category_rules))

        tax_amount = (amount * rate).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        return WithholdingComputation(
            gross_amount=amount,
            tax_type="ewt",
            tax_category=f"{category}_{subcategory}",
            tax_rate=rate,
            tax_amount=tax_amount,
            net_amount=amount - tax_amount
        )

    def compute_fwt(
        self,
        amount: Decimal,
        category: str,
        subcategory: str = "general"
    ) -> WithholdingComputation:
        """Compute Final Withholding Tax.

        Args:
            amount: Gross amount
            category: FWT category (interest, dividends, royalties, etc.)
            subcategory: Subcategory

        Returns:
            WithholdingComputation result
        """
        fwt_rules = self.rules.get("fwt", {})
        category_rules = fwt_rules.get(category, {})

        if isinstance(category_rules, dict):
            rate = Decimal(str(category_rules.get(subcategory, 0)))
        else:
            rate = Decimal(str(category_rules))

        tax_amount = (amount * rate).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        return WithholdingComputation(
            gross_amount=amount,
            tax_type="fwt",
            tax_category=f"{category}_{subcategory}",
            tax_rate=rate,
            tax_amount=tax_amount,
            net_amount=amount - tax_amount
        )

    # ==================== Compensation Tax ====================

    def compute_compensation_tax(
        self,
        gross_compensation: Decimal,
        period: str = "monthly",
        non_taxable_benefits: Decimal = Decimal("0"),
        sss: Decimal = Decimal("0"),
        philhealth: Decimal = Decimal("0"),
        pagibig: Decimal = Decimal("0")
    ) -> CompensationTax:
        """Compute withholding tax on compensation.

        Args:
            gross_compensation: Gross compensation amount
            period: 'monthly' or 'annual'
            non_taxable_benefits: Non-taxable de minimis benefits
            sss: SSS contribution
            philhealth: PhilHealth contribution
            pagibig: Pag-IBIG contribution

        Returns:
            CompensationTax result
        """
        # Convert to annual if monthly
        multiplier = 12 if period == "monthly" else 1
        annual_compensation = gross_compensation * multiplier

        # Calculate taxable income
        total_deductions = sss + philhealth + pagibig
        taxable_income = annual_compensation - (non_taxable_benefits * multiplier) - (total_deductions * multiplier)
        taxable_income = max(Decimal("0"), taxable_income)

        # Find tax bracket
        brackets = self.rules.get("compensation_tax", {}).get("brackets", [])
        tax_due = Decimal("0")
        bracket_name = "0%"

        for bracket in brackets:
            bracket_min = Decimal(str(bracket.get("min", 0)))
            bracket_max = bracket.get("max")
            rate = Decimal(str(bracket.get("rate", 0)))
            fixed = Decimal(str(bracket.get("fixed", 0)))

            if bracket_max is None:
                bracket_max = Decimal("999999999999")
            else:
                bracket_max = Decimal(str(bracket_max))

            if bracket_min <= taxable_income <= bracket_max:
                excess = taxable_income - bracket_min
                tax_due = fixed + (excess * rate)
                bracket_name = f"{int(rate * 100)}%"
                break

        # Convert back to monthly if needed
        if period == "monthly":
            tax_due = (tax_due / 12).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            taxable_income = taxable_income / 12

        effective_rate = (tax_due / gross_compensation * 100) if gross_compensation > 0 else Decimal("0")

        return CompensationTax(
            gross_compensation=gross_compensation,
            taxable_income=taxable_income.quantize(Decimal("0.01")),
            tax_due=tax_due.quantize(Decimal("0.01")),
            tax_bracket=bracket_name,
            effective_rate=effective_rate.quantize(Decimal("0.01")),
            non_taxable_benefits=non_taxable_benefits,
            sss_contribution=sss,
            philhealth_contribution=philhealth,
            pagibig_contribution=pagibig
        )

    # ==================== Corporate Income Tax ====================

    def compute_corporate_income_tax(
        self,
        taxable_income: Decimal,
        is_msme: bool = False,
        gross_income: Decimal | None = None
    ) -> tuple[Decimal, Decimal]:
        """Compute corporate income tax.

        Args:
            taxable_income: Net taxable income
            is_msme: Whether company qualifies as MSME
            gross_income: Gross income (for MCIT calculation)

        Returns:
            Tuple of (regular_tax, mcit) - higher one is due
        """
        corp_rules = self.rules.get("corporate_tax", {}).get("domestic_corporation", {})

        # Regular corporate income tax
        if is_msme:
            rate = Decimal(str(corp_rules.get("msme", 0.20)))
        else:
            rate = Decimal(str(corp_rules.get("general", 0.25)))

        regular_tax = (taxable_income * rate).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        # Minimum Corporate Income Tax (MCIT)
        mcit = Decimal("0")
        if gross_income:
            mcit_rate = Decimal(str(self.rules.get("corporate_tax", {}).get(
                "minimum_corporate_income_tax", 0.02
            )))
            mcit = (gross_income * mcit_rate).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

        return regular_tax, mcit

    # ==================== Percentage Tax ====================

    def compute_percentage_tax(
        self,
        gross_sales: Decimal
    ) -> Decimal:
        """Compute percentage tax for non-VAT registered.

        Args:
            gross_sales: Quarterly gross sales

        Returns:
            Percentage tax due
        """
        rate = Decimal(str(self.rules.get("percentage_tax", {}).get("rate", 0.03)))
        return (gross_sales * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # ==================== Period Computation ====================

    def compute_period_taxes(
        self,
        entity: str,
        period: str,
        sales: list[dict],
        purchases: list[dict],
        expenses_with_ewt: list[dict],
        compensation: list[dict]
    ) -> TaxComputation:
        """Compute all taxes for a period.

        Args:
            entity: Entity code
            period: Period string (YYYY-MM or YYYY-QN)
            sales: List of sales transactions
            purchases: List of purchase transactions
            expenses_with_ewt: List of expenses requiring EWT
            compensation: List of compensation payments

        Returns:
            TaxComputation with all computed taxes
        """
        result = TaxComputation(entity=entity, period=period)

        # VAT
        result.output_vat, output_details = self.compute_output_vat(sales)
        result.input_vat, input_details = self.compute_input_vat(purchases)
        result.vat_payable = max(Decimal("0"), result.output_vat - result.input_vat)
        result.vat_details = output_details + input_details

        # EWT
        for expense in expenses_with_ewt:
            amount = Decimal(str(expense.get("amount", 0)))
            category = expense.get("ewt_category", "purchases")
            subcategory = expense.get("ewt_subcategory", "goods")

            comp = self.compute_ewt(amount, category, subcategory)
            result.ewt_payable += comp.tax_amount
            result.ewt_details.append(comp)

        # Compensation tax
        for comp_payment in compensation:
            gross = Decimal(str(comp_payment.get("gross", 0)))
            sss = Decimal(str(comp_payment.get("sss", 0)))
            philhealth = Decimal(str(comp_payment.get("philhealth", 0)))
            pagibig = Decimal(str(comp_payment.get("pagibig", 0)))

            tax = self.compute_compensation_tax(
                gross, "monthly", Decimal("0"), sss, philhealth, pagibig
            )
            result.compensation_tax_payable += tax.tax_due

        return result

    # ==================== Utility Methods ====================

    def get_filing_deadline(
        self,
        form_type: str,
        period_end: date
    ) -> date:
        """Get filing deadline for a tax form.

        Args:
            form_type: BIR form number
            period_end: Period end date

        Returns:
            Filing deadline date
        """
        deadlines = self.rules.get("filing_deadlines", {})

        # Map form to deadline rule
        deadline_map = {
            "2550M": "vat_monthly",
            "2550Q": "vat_quarterly",
            "2551Q": "percentage_tax_quarterly",
            "0619E": "ewt_monthly",
            "1601EQ": "ewt_quarterly",
            "1601C": "compensation_monthly",
        }

        rule_key = deadline_map.get(form_type, "")
        deadline_day = deadlines.get(rule_key, 20)

        if deadline_day == "last_day":
            # Last day of month following period
            next_month = period_end.replace(day=28) + timedelta(days=4)
            return next_month.replace(day=1) - timedelta(days=1)

        # Specific day of following month
        from datetime import timedelta
        next_month = period_end.replace(day=1) + timedelta(days=32)
        next_month = next_month.replace(day=1)
        return next_month.replace(day=min(deadline_day, 28))

    def format_summary(self, computation: TaxComputation) -> str:
        """Format tax computation summary for display.

        Args:
            computation: TaxComputation to format

        Returns:
            Formatted summary string
        """
        lines = [
            f"📊 *Tax Computation Summary*",
            f"Entity: {computation.entity.upper()}",
            f"Period: {computation.period}",
            "",
            "*VAT:*",
            f"• Output VAT: ₱{computation.output_vat:,.2f}",
            f"• Input VAT: ₱{computation.input_vat:,.2f}",
            f"• VAT Payable: ₱{computation.vat_payable:,.2f}",
            "",
            "*Withholding Taxes:*",
            f"• EWT Payable: ₱{computation.ewt_payable:,.2f}",
            f"• FWT Payable: ₱{computation.fwt_payable:,.2f}",
            f"• Compensation Tax: ₱{computation.compensation_tax_payable:,.2f}",
            "",
            f"_Computed: {computation.computation_date.strftime('%Y-%m-%d %H:%M')}_"
        ]

        return "\n".join(lines)

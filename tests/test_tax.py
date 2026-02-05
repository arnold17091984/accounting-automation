"""
Tests for Tax Module

Tests for BIR calculator, tax form generator, and tax computation logic.
"""

import pytest
from decimal import Decimal
from datetime import date
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.insert(0, '/Users/arnold/Documents/accounting system/python')

from tax.bir_calculator import (
    BIRCalculator,
    TaxComputation,
    VATComputation,
    WithholdingComputation,
    CompensationTax,
)
from tax.form_generator import (
    TaxFormGenerator,
    FormData,
    GeneratedForm,
)


class TestBIRCalculator:
    """Tests for BIR tax calculator."""

    @pytest.fixture
    def calculator(self):
        """Create BIR calculator instance."""
        return BIRCalculator()

    # VAT Computation Tests

    def test_compute_output_vat(self, calculator):
        """Test output VAT computation (12%)."""
        gross_sales = Decimal("100000.00")
        result = calculator.compute_vat(gross_sales, is_output=True)

        assert isinstance(result, VATComputation)
        assert result.gross_amount == gross_sales
        assert result.vat_rate == Decimal("0.12")
        assert result.vat_amount == Decimal("12000.00")
        assert result.net_amount == Decimal("88000.00")

    def test_compute_input_vat(self, calculator):
        """Test input VAT computation."""
        purchase_amount = Decimal("50000.00")
        result = calculator.compute_vat(purchase_amount, is_output=False)

        assert result.vat_amount == Decimal("6000.00")
        assert result.vat_type == "input"

    def test_vat_zero_rated(self, calculator):
        """Test zero-rated VAT transaction."""
        export_sales = Decimal("500000.00")
        result = calculator.compute_vat(
            export_sales,
            is_output=True,
            is_zero_rated=True
        )

        assert result.vat_rate == Decimal("0.00")
        assert result.vat_amount == Decimal("0.00")
        assert result.net_amount == export_sales

    def test_vat_exempt(self, calculator):
        """Test VAT exempt transaction."""
        educational_service = Decimal("25000.00")
        result = calculator.compute_vat(
            educational_service,
            is_output=True,
            is_exempt=True
        )

        assert result.vat_amount == Decimal("0.00")
        assert result.is_exempt == True

    def test_net_of_vat_computation(self, calculator):
        """Test computing VAT from VAT-inclusive amount."""
        vat_inclusive = Decimal("112000.00")
        result = calculator.compute_vat_from_inclusive(vat_inclusive)

        assert result.gross_amount == vat_inclusive
        assert result.vat_amount == Decimal("12000.00")
        assert result.net_amount == Decimal("100000.00")

    # Percentage Tax Tests

    def test_percentage_tax(self, calculator):
        """Test 3% percentage tax for non-VAT registered."""
        gross_sales = Decimal("200000.00")
        result = calculator.compute_percentage_tax(gross_sales)

        assert result.tax_rate == Decimal("0.03")
        assert result.tax_amount == Decimal("6000.00")

    # Expanded Withholding Tax Tests

    def test_ewt_professional_fees_individual(self, calculator):
        """Test EWT on professional fees - individual (10%)."""
        fee_amount = Decimal("50000.00")
        result = calculator.compute_ewt(
            fee_amount,
            ewt_type="professional_fees",
            payee_type="individual"
        )

        assert isinstance(result, WithholdingComputation)
        assert result.ewt_rate == Decimal("0.10")
        assert result.ewt_amount == Decimal("5000.00")
        assert result.net_payable == Decimal("45000.00")

    def test_ewt_professional_fees_corporate(self, calculator):
        """Test EWT on professional fees - corporate (15%)."""
        fee_amount = Decimal("100000.00")
        result = calculator.compute_ewt(
            fee_amount,
            ewt_type="professional_fees",
            payee_type="corporate"
        )

        assert result.ewt_rate == Decimal("0.15")
        assert result.ewt_amount == Decimal("15000.00")

    def test_ewt_rental(self, calculator):
        """Test EWT on rental payments (5%)."""
        rental = Decimal("30000.00")
        result = calculator.compute_ewt(
            rental,
            ewt_type="rentals",
            rental_type="real_property"
        )

        assert result.ewt_rate == Decimal("0.05")
        assert result.ewt_amount == Decimal("1500.00")

    def test_ewt_contractor_services(self, calculator):
        """Test EWT on contractor services (2%)."""
        service_fee = Decimal("80000.00")
        result = calculator.compute_ewt(
            service_fee,
            ewt_type="services",
            service_type="contractors"
        )

        assert result.ewt_rate == Decimal("0.02")
        assert result.ewt_amount == Decimal("1600.00")

    def test_ewt_purchase_goods(self, calculator):
        """Test EWT on purchase of goods (1%)."""
        purchase = Decimal("150000.00")
        result = calculator.compute_ewt(
            purchase,
            ewt_type="purchases",
            purchase_type="goods"
        )

        assert result.ewt_rate == Decimal("0.01")
        assert result.ewt_amount == Decimal("1500.00")

    # Final Withholding Tax Tests

    def test_fwt_bank_interest(self, calculator):
        """Test FWT on bank interest (20%)."""
        interest = Decimal("10000.00")
        result = calculator.compute_fwt(
            interest,
            income_type="interest",
            interest_type="bank_deposits"
        )

        assert result.fwt_rate == Decimal("0.20")
        assert result.fwt_amount == Decimal("2000.00")
        assert result.is_final == True

    def test_fwt_dividends_individual(self, calculator):
        """Test FWT on dividends to individuals (10%)."""
        dividend = Decimal("50000.00")
        result = calculator.compute_fwt(
            dividend,
            income_type="dividends",
            recipient_type="individual"
        )

        assert result.fwt_rate == Decimal("0.10")
        assert result.fwt_amount == Decimal("5000.00")

    def test_fwt_royalties(self, calculator):
        """Test FWT on royalties (20%)."""
        royalty = Decimal("25000.00")
        result = calculator.compute_fwt(
            royalty,
            income_type="royalties"
        )

        assert result.fwt_rate == Decimal("0.20")
        assert result.fwt_amount == Decimal("5000.00")

    def test_fwt_prizes_above_10k(self, calculator):
        """Test FWT on prizes >= ₱10,000 (20%)."""
        prize = Decimal("50000.00")
        result = calculator.compute_fwt(
            prize,
            income_type="prizes"
        )

        assert result.fwt_rate == Decimal("0.20")
        assert result.fwt_amount == Decimal("10000.00")

    def test_fwt_prizes_below_10k_exempt(self, calculator):
        """Test FWT on prizes < ₱10,000 (exempt)."""
        prize = Decimal("5000.00")
        result = calculator.compute_fwt(
            prize,
            income_type="prizes"
        )

        assert result.fwt_rate == Decimal("0.00")
        assert result.fwt_amount == Decimal("0.00")

    # Compensation Tax Tests (TRAIN Law)

    def test_compensation_tax_below_250k(self, calculator):
        """Test compensation tax for annual income ≤ ₱250,000 (0%)."""
        annual_income = Decimal("240000.00")
        result = calculator.compute_compensation_tax(annual_income)

        assert isinstance(result, CompensationTax)
        assert result.tax_rate == Decimal("0.00")
        assert result.tax_due == Decimal("0.00")
        assert result.bracket_description == "0% (≤₱250,000)"

    def test_compensation_tax_250k_to_400k(self, calculator):
        """Test compensation tax for ₱250,001-₱400,000 (15% excess)."""
        annual_income = Decimal("350000.00")
        result = calculator.compute_compensation_tax(annual_income)

        # Tax = 15% of (350,000 - 250,000) = 15% of 100,000 = 15,000
        assert result.tax_rate == Decimal("0.15")
        assert result.tax_due == Decimal("15000.00")

    def test_compensation_tax_400k_to_800k(self, calculator):
        """Test compensation tax for ₱400,001-₱800,000 (₱22,500 + 20% excess)."""
        annual_income = Decimal("600000.00")
        result = calculator.compute_compensation_tax(annual_income)

        # Tax = 22,500 + 20% of (600,000 - 400,000) = 22,500 + 40,000 = 62,500
        assert result.fixed_amount == Decimal("22500.00")
        assert result.tax_rate == Decimal("0.20")
        assert result.tax_due == Decimal("62500.00")

    def test_compensation_tax_800k_to_2m(self, calculator):
        """Test compensation tax for ₱800,001-₱2,000,000 (₱102,500 + 25% excess)."""
        annual_income = Decimal("1200000.00")
        result = calculator.compute_compensation_tax(annual_income)

        # Tax = 102,500 + 25% of (1,200,000 - 800,000) = 102,500 + 100,000 = 202,500
        assert result.fixed_amount == Decimal("102500.00")
        assert result.tax_due == Decimal("202500.00")

    def test_compensation_tax_2m_to_8m(self, calculator):
        """Test compensation tax for ₱2,000,001-₱8,000,000 (₱402,500 + 30% excess)."""
        annual_income = Decimal("4000000.00")
        result = calculator.compute_compensation_tax(annual_income)

        # Tax = 402,500 + 30% of (4,000,000 - 2,000,000) = 402,500 + 600,000 = 1,002,500
        assert result.fixed_amount == Decimal("402500.00")
        assert result.tax_due == Decimal("1002500.00")

    def test_compensation_tax_above_8m(self, calculator):
        """Test compensation tax for > ₱8,000,000 (₱2,202,500 + 35% excess)."""
        annual_income = Decimal("10000000.00")
        result = calculator.compute_compensation_tax(annual_income)

        # Tax = 2,202,500 + 35% of (10,000,000 - 8,000,000) = 2,202,500 + 700,000 = 2,902,500
        assert result.fixed_amount == Decimal("2202500.00")
        assert result.tax_due == Decimal("2902500.00")

    def test_monthly_withholding_computation(self, calculator):
        """Test monthly withholding tax computation."""
        monthly_salary = Decimal("50000.00")
        result = calculator.compute_monthly_withholding(monthly_salary)

        assert result.monthly_withholding > Decimal("0.00")
        assert result.annual_equivalent == monthly_salary * 12

    # Corporate Income Tax Tests

    def test_corporate_tax_general(self, calculator):
        """Test corporate income tax - general rate (25%)."""
        net_income = Decimal("10000000.00")
        result = calculator.compute_corporate_tax(net_income)

        assert result.tax_rate == Decimal("0.25")
        assert result.tax_due == Decimal("2500000.00")

    def test_corporate_tax_msme(self, calculator):
        """Test corporate income tax - MSME rate (20%)."""
        net_income = Decimal("3000000.00")  # Below ₱5M threshold
        result = calculator.compute_corporate_tax(net_income, is_msme=True)

        assert result.tax_rate == Decimal("0.20")
        assert result.tax_due == Decimal("600000.00")

    def test_minimum_corporate_income_tax(self, calculator):
        """Test MCIT (2% of gross income)."""
        gross_income = Decimal("50000000.00")
        net_income = Decimal("500000.00")  # Low net income scenario

        result = calculator.compute_corporate_tax(
            net_income,
            gross_income=gross_income,
            apply_mcit=True
        )

        # MCIT = 2% of 50,000,000 = 1,000,000
        # Regular = 25% of 500,000 = 125,000
        # Higher of the two = 1,000,000
        assert result.mcit_amount == Decimal("1000000.00")
        assert result.tax_due >= result.mcit_amount

    # Documentary Stamp Tax Tests

    def test_dst_lease_agreement(self, calculator):
        """Test DST on lease agreements."""
        monthly_rent = Decimal("50000.00")
        lease_months = 12

        result = calculator.compute_dst_lease(monthly_rent, lease_months)

        # Total rent = 600,000
        # DST = ₱3 for first ₱2,000 + ₱1 for each additional ₱1,000
        assert result.dst_amount > Decimal("0.00")

    def test_dst_bank_check(self, calculator):
        """Test DST on bank checks (₱3 per check)."""
        result = calculator.compute_dst_check()
        assert result.dst_amount == Decimal("3.00")

    # Tax Period Tests

    def test_get_filing_deadline_vat_monthly(self, calculator):
        """Test VAT monthly filing deadline (20th of following month)."""
        tax_period = date(2025, 1, 1)
        deadline = calculator.get_filing_deadline("vat_monthly", tax_period)

        assert deadline == date(2025, 2, 20)

    def test_get_filing_deadline_ewt_monthly(self, calculator):
        """Test EWT monthly filing deadline (10th of following month)."""
        tax_period = date(2025, 3, 1)
        deadline = calculator.get_filing_deadline("ewt_monthly", tax_period)

        assert deadline == date(2025, 4, 10)

    def test_get_bir_form_number(self, calculator):
        """Test BIR form number lookup."""
        assert calculator.get_form_number("vat_monthly") == "2550M"
        assert calculator.get_form_number("vat_quarterly") == "2550Q"
        assert calculator.get_form_number("ewt_monthly") == "0619E"
        assert calculator.get_form_number("ewt_quarterly") == "1601EQ"
        assert calculator.get_form_number("compensation_monthly") == "1601C"

    # Penalty Computation Tests

    def test_late_filing_penalty(self, calculator):
        """Test late filing surcharge (25%)."""
        tax_due = Decimal("100000.00")
        result = calculator.compute_penalty(
            tax_due,
            penalty_type="late_filing"
        )

        assert result.surcharge_rate == Decimal("0.25")
        assert result.surcharge_amount == Decimal("25000.00")

    def test_interest_computation(self, calculator):
        """Test interest computation (12% per annum)."""
        tax_due = Decimal("100000.00")
        days_late = 90  # 3 months late

        result = calculator.compute_penalty(
            tax_due,
            penalty_type="late_payment",
            days_late=days_late
        )

        # Interest = 100,000 * 12% * (90/365) ≈ 2,959
        assert result.interest_amount > Decimal("0.00")
        assert result.interest_rate == Decimal("0.12")


class TestTaxFormGenerator:
    """Tests for tax form generator."""

    @pytest.fixture
    def generator(self):
        """Create form generator instance."""
        return TaxFormGenerator()

    def test_generate_form_2550m(self, generator):
        """Test BIR Form 2550M (Monthly VAT) generation."""
        form_data = FormData(
            form_type="2550M",
            tin="123-456-789-000",
            registered_name="BK Keyforce Inc.",
            registered_address="BGC, Taguig City",
            period_from=date(2025, 1, 1),
            period_to=date(2025, 1, 31),
            taxable_sales=Decimal("1000000.00"),
            vat_exempt_sales=Decimal("50000.00"),
            zero_rated_sales=Decimal("200000.00"),
            output_vat=Decimal("120000.00"),
            input_vat=Decimal("80000.00"),
            vat_payable=Decimal("40000.00")
        )

        result = generator.generate_form(form_data)

        assert isinstance(result, GeneratedForm)
        assert result.form_number == "2550M"
        assert result.period == "January 2025"
        assert result.pdf_content is not None or result.pdf_path is not None

    def test_generate_form_2550q(self, generator):
        """Test BIR Form 2550Q (Quarterly VAT) generation."""
        form_data = FormData(
            form_type="2550Q",
            tin="123-456-789-000",
            registered_name="BK Keyforce Inc.",
            period_from=date(2025, 1, 1),
            period_to=date(2025, 3, 31),
            quarter=1,
            taxable_sales=Decimal("3000000.00"),
            output_vat=Decimal("360000.00"),
            input_vat=Decimal("240000.00"),
            vat_payable=Decimal("120000.00")
        )

        result = generator.generate_form(form_data)

        assert result.form_number == "2550Q"
        assert "Q1" in result.period

    def test_generate_form_1601c(self, generator):
        """Test BIR Form 1601C (Monthly Withholding Tax on Compensation)."""
        form_data = FormData(
            form_type="1601C",
            tin="123-456-789-000",
            registered_name="BK Keyforce Inc.",
            period_from=date(2025, 1, 1),
            period_to=date(2025, 1, 31),
            total_compensation=Decimal("500000.00"),
            non_taxable_compensation=Decimal("50000.00"),
            taxable_compensation=Decimal("450000.00"),
            tax_withheld=Decimal("45000.00")
        )

        result = generator.generate_form(form_data)

        assert result.form_number == "1601C"
        assert result.tax_amount == Decimal("45000.00")

    def test_generate_form_1601eq(self, generator):
        """Test BIR Form 1601EQ (Quarterly Expanded Withholding Tax)."""
        form_data = FormData(
            form_type="1601EQ",
            tin="123-456-789-000",
            registered_name="BK Keyforce Inc.",
            period_from=date(2025, 1, 1),
            period_to=date(2025, 3, 31),
            quarter=1,
            ewt_details=[
                {"nature": "Professional Fees", "rate": "10%", "base": Decimal("100000"), "tax": Decimal("10000")},
                {"nature": "Rentals", "rate": "5%", "base": Decimal("90000"), "tax": Decimal("4500")},
            ],
            total_ewt=Decimal("14500.00")
        )

        result = generator.generate_form(form_data)

        assert result.form_number == "1601EQ"
        assert result.tax_amount == Decimal("14500.00")

    def test_generate_form_2307(self, generator):
        """Test BIR Form 2307 (Certificate of Creditable Tax Withheld)."""
        form_data = FormData(
            form_type="2307",
            tin="123-456-789-000",
            registered_name="BK Keyforce Inc.",
            payee_tin="987-654-321-000",
            payee_name="Supplier Corp.",
            period_from=date(2025, 1, 1),
            period_to=date(2025, 3, 31),
            atc_code="WI010",
            nature_of_income="Professional Fees",
            amount_paid=Decimal("100000.00"),
            tax_withheld=Decimal("10000.00")
        )

        result = generator.generate_form(form_data)

        assert result.form_number == "2307"
        assert result.tax_amount == Decimal("10000.00")

    def test_generate_form_0619e(self, generator):
        """Test BIR Form 0619E (Monthly Expanded Withholding Tax Remittance)."""
        form_data = FormData(
            form_type="0619E",
            tin="123-456-789-000",
            registered_name="BK Keyforce Inc.",
            period_from=date(2025, 1, 1),
            period_to=date(2025, 1, 31),
            total_ewt_remittance=Decimal("25000.00")
        )

        result = generator.generate_form(form_data)

        assert result.form_number == "0619E"

    def test_form_validation_missing_tin(self, generator):
        """Test form validation - missing TIN."""
        form_data = FormData(
            form_type="2550M",
            tin="",  # Missing TIN
            registered_name="BK Keyforce Inc.",
            period_from=date(2025, 1, 1),
            period_to=date(2025, 1, 31),
        )

        with pytest.raises(ValueError, match="TIN is required"):
            generator.generate_form(form_data)

    def test_form_validation_invalid_period(self, generator):
        """Test form validation - invalid period."""
        form_data = FormData(
            form_type="2550M",
            tin="123-456-789-000",
            registered_name="BK Keyforce Inc.",
            period_from=date(2025, 2, 1),
            period_to=date(2025, 1, 31),  # End before start
        )

        with pytest.raises(ValueError, match="Invalid period"):
            generator.generate_form(form_data)

    def test_batch_form_generation(self, generator):
        """Test generating multiple forms in batch."""
        forms_data = [
            FormData(
                form_type="2550M",
                tin="123-456-789-000",
                registered_name="Solaire Entity",
                entity="solaire",
                period_from=date(2025, 1, 1),
                period_to=date(2025, 1, 31),
                vat_payable=Decimal("50000.00")
            ),
            FormData(
                form_type="2550M",
                tin="123-456-789-001",
                registered_name="COD Entity",
                entity="cod",
                period_from=date(2025, 1, 1),
                period_to=date(2025, 1, 31),
                vat_payable=Decimal("35000.00")
            ),
        ]

        results = generator.generate_batch(forms_data)

        assert len(results) == 2
        assert all(isinstance(r, GeneratedForm) for r in results)

    def test_form_filing_deadline_included(self, generator):
        """Test that generated form includes filing deadline."""
        form_data = FormData(
            form_type="2550M",
            tin="123-456-789-000",
            registered_name="BK Keyforce Inc.",
            period_from=date(2025, 1, 1),
            period_to=date(2025, 1, 31),
            vat_payable=Decimal("40000.00")
        )

        result = generator.generate_form(form_data)

        assert result.filing_deadline == date(2025, 2, 20)

    def test_form_summary_generation(self, generator):
        """Test generation of form summary for review."""
        form_data = FormData(
            form_type="1601C",
            tin="123-456-789-000",
            registered_name="BK Keyforce Inc.",
            period_from=date(2025, 1, 1),
            period_to=date(2025, 1, 31),
            taxable_compensation=Decimal("450000.00"),
            tax_withheld=Decimal("45000.00")
        )

        summary = generator.generate_summary(form_data)

        assert "1601C" in summary
        assert "450,000" in summary or "450000" in summary
        assert "45,000" in summary or "45000" in summary


class TestTaxComputation:
    """Tests for complete tax computation scenarios."""

    @pytest.fixture
    def calculator(self):
        return BIRCalculator()

    def test_full_vat_computation_cycle(self, calculator):
        """Test complete VAT computation with input and output."""
        # Sales for the month
        sales_transactions = [
            {"amount": Decimal("100000.00"), "type": "taxable"},
            {"amount": Decimal("50000.00"), "type": "taxable"},
            {"amount": Decimal("200000.00"), "type": "zero_rated"},
            {"amount": Decimal("25000.00"), "type": "exempt"},
        ]

        # Purchases for the month
        purchase_transactions = [
            {"amount": Decimal("80000.00"), "vatable": True},
            {"amount": Decimal("40000.00"), "vatable": True},
            {"amount": Decimal("10000.00"), "vatable": False},
        ]

        result = calculator.compute_monthly_vat(
            sales=sales_transactions,
            purchases=purchase_transactions
        )

        # Output VAT = 12% of (100,000 + 50,000) = 18,000
        # Input VAT = 12% of (80,000 + 40,000) = 14,400
        # VAT Payable = 18,000 - 14,400 = 3,600
        assert result.output_vat == Decimal("18000.00")
        assert result.input_vat == Decimal("14400.00")
        assert result.vat_payable == Decimal("3600.00")

    def test_payroll_tax_computation(self, calculator):
        """Test complete payroll tax computation for multiple employees."""
        employees = [
            {"name": "Employee A", "monthly_salary": Decimal("25000.00")},
            {"name": "Employee B", "monthly_salary": Decimal("50000.00")},
            {"name": "Employee C", "monthly_salary": Decimal("100000.00")},
        ]

        result = calculator.compute_payroll_taxes(employees)

        assert len(result.employee_withholdings) == 3
        assert result.total_withholding > Decimal("0.00")

        # Employee A (25k/mo = 300k/yr) - in 15% bracket
        # Employee B (50k/mo = 600k/yr) - in 20% bracket
        # Employee C (100k/mo = 1.2M/yr) - in 25% bracket
        assert result.employee_withholdings[0].annual_tax < result.employee_withholdings[1].annual_tax
        assert result.employee_withholdings[1].annual_tax < result.employee_withholdings[2].annual_tax

    def test_supplier_payment_with_ewt(self, calculator):
        """Test supplier payment computation with EWT."""
        payment = {
            "supplier": "Professional Services Co.",
            "gross_amount": Decimal("100000.00"),
            "service_type": "professional_fees",
            "payee_type": "corporate",
            "vatable": True,
        }

        result = calculator.compute_supplier_payment(payment)

        # Gross: 100,000
        # VAT (input): 12% = 12,000
        # EWT (15% for corporate professional): 15,000
        # Net payable: 100,000 - 15,000 = 85,000
        assert result.input_vat == Decimal("12000.00")
        assert result.ewt_amount == Decimal("15000.00")
        assert result.net_payable == Decimal("85000.00")


class TestTaxRulesLoading:
    """Tests for tax rules configuration loading."""

    def test_load_tax_rules_yaml(self):
        """Test loading tax rules from YAML file."""
        calculator = BIRCalculator()

        # Should load rules from tax_rules.yaml
        assert calculator.rules is not None
        assert "vat" in calculator.rules
        assert "ewt" in calculator.rules
        assert "compensation_tax" in calculator.rules

    def test_vat_rate_from_config(self):
        """Test VAT rate is loaded from config."""
        calculator = BIRCalculator()

        assert calculator.rules["vat"]["standard_rate"] == 0.12

    def test_ewt_rates_from_config(self):
        """Test EWT rates are loaded from config."""
        calculator = BIRCalculator()

        assert calculator.rules["ewt"]["professional_fees"]["individual"] == 0.10
        assert calculator.rules["ewt"]["professional_fees"]["corporate"] == 0.15

    def test_compensation_brackets_from_config(self):
        """Test compensation tax brackets are loaded from config."""
        calculator = BIRCalculator()

        brackets = calculator.rules["compensation_tax"]["brackets"]
        assert len(brackets) == 6
        assert brackets[0]["max"] == 250000
        assert brackets[5]["min"] == 8000001


class TestEntityTaxComputation:
    """Tests for entity-specific tax computations."""

    @pytest.fixture
    def calculator(self):
        return BIRCalculator()

    def test_gaming_entity_franchise_tax(self, calculator):
        """Test gaming entity franchise tax (5% in lieu of all taxes)."""
        gross_revenue = Decimal("10000000.00")

        result = calculator.compute_gaming_tax(gross_revenue)

        assert result.franchise_tax_rate == Decimal("0.05")
        assert result.franchise_tax_amount == Decimal("500000.00")
        assert result.is_in_lieu_of_taxes == True

    def test_multiple_entity_tax_summary(self, calculator):
        """Test computing tax summary across multiple entities."""
        entities_data = {
            "solaire": {
                "sales": Decimal("5000000.00"),
                "purchases": Decimal("2000000.00"),
                "payroll": Decimal("1000000.00"),
            },
            "cod": {
                "sales": Decimal("3000000.00"),
                "purchases": Decimal("1500000.00"),
                "payroll": Decimal("800000.00"),
            },
        }

        result = calculator.compute_consolidated_taxes(entities_data)

        assert "solaire" in result.entity_taxes
        assert "cod" in result.entity_taxes
        assert result.total_vat_payable > Decimal("0.00")
        assert result.total_withholding > Decimal("0.00")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

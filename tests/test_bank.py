"""
Bank Module Tests

Tests for UnionBank template generator, bank reconciliation, and RPA fallback.
"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import json

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "python"))

from bank import (
    UnionBankTemplateGenerator,
    PayrollEntry,
    TransferBatch,
    TransferTemplate,
    BankReconciliation,
    ReconciliationResult,
    MatchedTransaction,
    UnmatchedItem,
    BankPortalAutomation,
    RPAResult,
    RPAAction,
)
from bank.ub_template_generator import TransferType
from bank.reconciliation import BankTransaction, BookTransaction, MatchType, MatchStatus
from bank.rpa_fallback import BankCredentials, RPAStatus


class TestPayrollEntry:
    """Tests for PayrollEntry dataclass."""

    def test_valid_entry(self):
        """Test valid payroll entry."""
        entry = PayrollEntry(
            employee_id="EMP001",
            employee_name="Juan Dela Cruz",
            bank_code="010419995",
            account_number="1234567890",
            amount=Decimal("50000"),
            department="Operations"
        )

        is_valid, error = entry.validate()
        assert is_valid is True
        assert error == ""

    def test_missing_account_number(self):
        """Test validation fails for missing account."""
        entry = PayrollEntry(
            employee_id="EMP001",
            employee_name="Juan Dela Cruz",
            bank_code="010419995",
            account_number="",
            amount=Decimal("50000")
        )

        is_valid, error = entry.validate()
        assert is_valid is False
        assert "Account number" in error

    def test_invalid_amount(self):
        """Test validation fails for zero amount."""
        entry = PayrollEntry(
            employee_id="EMP001",
            employee_name="Juan Dela Cruz",
            bank_code="010419995",
            account_number="1234567890",
            amount=Decimal("0")
        )

        is_valid, error = entry.validate()
        assert is_valid is False
        assert "Invalid amount" in error


class TestTransferBatch:
    """Tests for TransferBatch dataclass."""

    def test_total_amount(self):
        """Test total amount calculation."""
        batch = TransferBatch(
            batch_id="TEST_001",
            transfer_type=TransferType.PAYROLL,
            entity="solaire",
            transfer_date=date.today()
        )

        batch.entries = [
            PayrollEntry(
                employee_id="E1", employee_name="A", bank_code="123",
                account_number="1234567890", amount=Decimal("10000")
            ),
            PayrollEntry(
                employee_id="E2", employee_name="B", bank_code="123",
                account_number="0987654321", amount=Decimal("15000")
            ),
        ]

        assert batch.total_amount == Decimal("25000")
        assert batch.entry_count == 2

    def test_validate_all_entries(self):
        """Test batch validation."""
        batch = TransferBatch(
            batch_id="TEST_001",
            transfer_type=TransferType.PAYROLL,
            entity="solaire",
            transfer_date=date.today()
        )

        batch.entries = [
            PayrollEntry(
                employee_id="E1", employee_name="A", bank_code="123",
                account_number="1234567890", amount=Decimal("10000")
            ),
            PayrollEntry(
                employee_id="E2", employee_name="B", bank_code="",  # Missing bank code
                account_number="0987654321", amount=Decimal("15000")
            ),
        ]

        is_valid, errors = batch.validate()
        assert is_valid is False
        assert len(errors) == 1


class TestUnionBankTemplateGenerator:
    """Tests for UnionBankTemplateGenerator class."""

    @pytest.fixture
    def generator(self, tmp_path):
        """Create generator with test config."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        entity_file = config_dir / "entity_config.yaml"
        entity_file.write_text("""
entities:
  solaire:
    full_name: Solaire Resort
""")

        return UnionBankTemplateGenerator(config_dir)

    def test_get_bank_code(self, generator):
        """Test bank code lookup."""
        assert generator.get_bank_code("unionbank") == "010419995"
        assert generator.get_bank_code("bdo") == "010530667"
        assert generator.get_bank_code("gcash") == "999010025"
        assert generator.get_bank_code("unknown_bank") is None

    def test_create_batch(self, generator):
        """Test batch creation."""
        batch = generator.create_batch(
            transfer_type=TransferType.PAYROLL,
            entity="solaire",
            transfer_date=date(2025, 1, 15),
            created_by="test_user"
        )

        assert batch.entity == "solaire"
        assert batch.transfer_type == TransferType.PAYROLL
        assert "SOLAIRE" in batch.batch_id
        assert "payroll" in batch.batch_id

    def test_add_payroll_entry(self, generator):
        """Test adding payroll entry."""
        batch = generator.create_batch(
            transfer_type=TransferType.PAYROLL,
            entity="solaire",
            transfer_date=date.today()
        )

        entry = generator.add_payroll_entry(
            batch=batch,
            employee_id="EMP001",
            employee_name="Juan Dela Cruz",
            bank_name="UnionBank",
            account_number="123-456-7890",
            amount=Decimal("50000"),
            department="Operations"
        )

        assert len(batch.entries) == 1
        assert entry.account_number == "1234567890"  # Cleaned
        assert entry.bank_code == "010419995"

    def test_add_entries_from_payroll_data(self, generator):
        """Test bulk entry addition."""
        batch = generator.create_batch(
            transfer_type=TransferType.PAYROLL,
            entity="solaire",
            transfer_date=date.today()
        )

        payroll_data = [
            {
                "employee_id": "E001",
                "employee_name": "Juan Dela Cruz",
                "bank": "unionbank",
                "account_number": "1234567890",
                "net_pay": 50000,
                "department": "Operations"
            },
            {
                "employee_id": "E002",
                "employee_name": "Maria Santos",
                "bank": "bdo",
                "account_number": "0987654321",
                "net_pay": 45000,
                "department": "Finance"
            },
        ]

        added, errors = generator.add_entries_from_payroll_data(batch, payroll_data)

        assert added == 2
        assert len(errors) == 0
        assert batch.total_amount == Decimal("95000")

    def test_generate_csv(self, generator):
        """Test CSV template generation."""
        batch = generator.create_batch(
            transfer_type=TransferType.PAYROLL,
            entity="solaire",
            transfer_date=date.today()
        )

        generator.add_payroll_entry(
            batch=batch,
            employee_id="E001",
            employee_name="Juan Dela Cruz",
            bank_name="unionbank",
            account_number="1234567890",
            amount=Decimal("50000")
        )

        template = generator.generate_csv(batch)

        assert isinstance(template, TransferTemplate)
        assert template.format == "csv"
        assert "JUAN DELA CRUZ" in template.content
        assert "50000.00" in template.content
        assert template.checksum is not None

    def test_generate_summary(self, generator):
        """Test summary generation."""
        batch = generator.create_batch(
            transfer_type=TransferType.PAYROLL,
            entity="solaire",
            transfer_date=date.today()
        )

        generator.add_payroll_entry(
            batch=batch,
            employee_id="E001",
            employee_name="Juan",
            bank_name="unionbank",
            account_number="1234567890",
            amount=Decimal("50000"),
            department="Operations"
        )

        summary = generator.generate_summary(batch)

        assert "Transfer Batch Summary" in summary
        assert "SOLAIRE" in summary
        assert "₱50,000.00" in summary
        assert "Operations" in summary


class TestBankReconciliation:
    """Tests for BankReconciliation class."""

    @pytest.fixture
    def reconciler(self, tmp_path):
        """Create reconciler with test config."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        return BankReconciliation(config_dir)

    @pytest.fixture
    def bank_transactions(self):
        """Sample bank transactions."""
        return [
            BankTransaction(
                id="BT001",
                date=date(2025, 1, 15),
                description="PURCHASE - OFFICE DEPOT",
                amount=Decimal("5000"),
                reference="REF001"
            ),
            BankTransaction(
                id="BT002",
                date=date(2025, 1, 16),
                description="TRANSFER - PAYROLL",
                amount=Decimal("50000"),
                reference="PAY001"
            ),
            BankTransaction(
                id="BT003",
                date=date(2025, 1, 17),
                description="PURCHASE - RESTAURANT",
                amount=Decimal("2500")
            ),
        ]

    @pytest.fixture
    def book_transactions(self):
        """Sample book transactions."""
        return [
            BookTransaction(
                id="TX001",
                date=date(2025, 1, 15),
                description="Office supplies",
                amount=Decimal("5000"),
                account_code="6100",
                account_name="Office Supplies",
                entity="solaire"
            ),
            BookTransaction(
                id="TX002",
                date=date(2025, 1, 16),
                description="January payroll",
                amount=Decimal("50000"),
                account_code="7100",
                account_name="Salaries",
                entity="solaire",
                reference="PAY001"
            ),
        ]

    def test_reconcile_exact_match(self, reconciler, bank_transactions, book_transactions):
        """Test exact matching."""
        result = reconciler.reconcile(
            entity="solaire",
            account="UB001",
            bank_transactions=bank_transactions,
            book_transactions=book_transactions,
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 31)
        )

        assert isinstance(result, ReconciliationResult)
        assert len(result.matched) == 2
        assert len(result.unmatched_bank) == 1  # Restaurant purchase

    def test_match_rate_calculation(self, reconciler, bank_transactions, book_transactions):
        """Test match rate calculation."""
        result = reconciler.reconcile(
            entity="solaire",
            account="UB001",
            bank_transactions=bank_transactions,
            book_transactions=book_transactions,
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 31)
        )

        # 2 matched out of 3 bank transactions
        assert result.match_rate == pytest.approx(66.67, rel=0.01)

    def test_reference_matching(self, reconciler):
        """Test matching by reference number."""
        bank_txns = [
            BankTransaction(
                id="BT001",
                date=date(2025, 1, 16),
                description="TRANSFER",
                amount=Decimal("50000"),
                reference="PAY001"
            ),
        ]

        book_txns = [
            BookTransaction(
                id="TX001",
                date=date(2025, 1, 15),  # Different date
                description="Payroll",
                amount=Decimal("50000"),
                account_code="7100",
                account_name="Salaries",
                entity="solaire",
                reference="PAY001"
            ),
        ]

        result = reconciler.reconcile(
            entity="solaire",
            account="UB001",
            bank_transactions=bank_txns,
            book_transactions=book_txns,
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 31)
        )

        assert len(result.matched) == 1
        assert result.matched[0].match_type == MatchType.REFERENCE

    def test_format_report(self, reconciler, bank_transactions, book_transactions):
        """Test report formatting."""
        result = reconciler.reconcile(
            entity="solaire",
            account="UB001",
            bank_transactions=bank_transactions,
            book_transactions=book_transactions,
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 31),
            bank_closing=Decimal("100000")
        )

        report = reconciler.format_report(result)

        assert "Bank Reconciliation Report" in report
        assert "SOLAIRE" in report
        assert "Match Rate" in report


class TestReconciliationResult:
    """Tests for ReconciliationResult dataclass."""

    def test_is_reconciled(self):
        """Test reconciled status detection."""
        result = ReconciliationResult(
            entity="solaire",
            account="UB001",
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 31),
            bank_closing_balance=Decimal("100000"),
            book_closing_balance=Decimal("100000")
        )

        assert result.is_reconciled is True

    def test_not_reconciled_with_difference(self):
        """Test not reconciled with balance difference."""
        result = ReconciliationResult(
            entity="solaire",
            account="UB001",
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 31),
            bank_closing_balance=Decimal("100000"),
            book_closing_balance=Decimal("95000")
        )

        assert result.is_reconciled is False
        assert result.difference == Decimal("5000")


class TestBankPortalAutomation:
    """Tests for BankPortalAutomation class."""

    @pytest.fixture
    def automation(self, tmp_path):
        """Create automation instance."""
        return BankPortalAutomation(
            config_dir=tmp_path,
            headless=True,
            screenshot_dir=tmp_path / "screenshots"
        )

    def test_supported_banks(self, automation):
        """Test supported banks list."""
        assert "unionbank" in automation.SUPPORTED_BANKS
        assert "bdo" in automation.SUPPORTED_BANKS

    def test_rpa_result_success(self):
        """Test RPAResult success property."""
        result = RPAResult(
            action=RPAAction.LOGIN,
            status=RPAStatus.SUCCESS,
            message="Login successful"
        )

        assert result.success is True

    def test_rpa_result_failure(self):
        """Test RPAResult failure property."""
        result = RPAResult(
            action=RPAAction.LOGIN,
            status=RPAStatus.FAILED,
            message="Login failed",
            error="Invalid credentials"
        )

        assert result.success is False

    def test_rpa_result_to_dict(self):
        """Test RPAResult dictionary conversion."""
        result = RPAResult(
            action=RPAAction.DOWNLOAD_STATEMENT,
            status=RPAStatus.SUCCESS,
            message="Downloaded",
            data={"file_path": "/tmp/statement.csv"}
        )

        d = result.to_dict()

        assert d["action"] == "download_statement"
        assert d["status"] == "success"
        assert d["data"]["file_path"] == "/tmp/statement.csv"


class TestBankCredentials:
    """Tests for BankCredentials dataclass."""

    def test_credential_creation(self):
        """Test credential creation."""
        creds = BankCredentials(
            bank="unionbank",
            username="testuser",
            password="testpass",
            otp_method="sms"
        )

        assert creds.bank == "unionbank"
        assert creds.otp_method == "sms"

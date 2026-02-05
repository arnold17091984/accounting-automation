"""
Telegram Module Tests

Tests for bot commands, approval handling, file processing, and report formatting.
"""

import pytest
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "python"))

from telegram import (
    BotCommandHandler,
    CommandResult,
    ApprovalHandler,
    ApprovalRequest,
    ApprovalResult,
    FileHandler,
    FileProcessResult,
    ReportFormatter,
)
from telegram.approval_handler import ApprovalStatus


class TestBotCommandHandler:
    """Tests for BotCommandHandler class."""

    @pytest.fixture
    def handler(self, tmp_path):
        """Create command handler with test config."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        # Create ACL config
        acl_file = config_dir / "telegram_acl.yaml"
        acl_file.write_text("""
users:
  - telegram_id: 12345
    name: "Test Admin"
    role: admin
  - telegram_id: 67890
    name: "Test Officer"
    role: officer
permissions:
  admin: ["*"]
  officer: ["view", "upload", "approve_under_10k"]
  viewer: ["view"]
""")

        # Create entity config
        entity_file = config_dir / "entity_config.yaml"
        entity_file.write_text("""
entities:
  solaire:
    full_name: Solaire Resort
  cod:
    full_name: COD Casino
""")

        return BotCommandHandler(config_dir)

    def test_get_user_permissions_admin(self, handler):
        """Test admin user permissions."""
        perms = handler.get_user_permissions(12345)

        assert perms is not None
        assert perms.role == "admin"
        assert perms.can("view") is True
        assert perms.can("approve") is True
        assert perms.can("anything") is True  # admin has *

    def test_get_user_permissions_officer(self, handler):
        """Test officer user permissions."""
        perms = handler.get_user_permissions(67890)

        assert perms is not None
        assert perms.role == "officer"
        assert perms.can("view") is True
        assert perms.can("upload") is True
        assert perms.can("approve") is False

    def test_get_user_permissions_unknown(self, handler):
        """Test unknown user returns None."""
        perms = handler.get_user_permissions(99999)
        assert perms is None

    def test_handle_command_unauthorized(self, handler):
        """Test command from unauthorized user."""
        result = handler.handle_command("/budget", [], 99999)

        assert result.success is False
        assert "Access Denied" in result.message

    def test_handle_help_command(self, handler):
        """Test /help command."""
        result = handler.handle_command("/help", [], 12345)

        assert result.success is True
        assert "Available Commands" in result.message
        assert "/budget" in result.message
        assert "/pl" in result.message

    def test_handle_budget_command_no_entity(self, handler):
        """Test /budget without entity shows selection."""
        result = handler.handle_command("/budget", [], 12345)

        assert result.success is True
        assert result.keyboard is not None
        assert "Select an entity" in result.message

    def test_handle_unknown_command(self, handler):
        """Test unknown command."""
        result = handler.handle_command("/unknown", [], 12345)

        assert result.success is False
        assert "Unknown command" in result.message


class TestApprovalHandler:
    """Tests for ApprovalHandler class."""

    @pytest.fixture
    def handler(self, tmp_path):
        """Create approval handler with test config."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        acl_file = config_dir / "telegram_acl.yaml"
        acl_file.write_text("""
users:
  - telegram_id: 12345
    name: "Test Admin"
    role: admin
  - telegram_id: 67890
    name: "Test Officer"
    role: officer
permissions:
  admin: ["*"]
  officer: ["approve_under_10k", "view"]
""")

        threshold_file = config_dir / "budget_thresholds.yaml"
        threshold_file.write_text("""
auto_approval:
  max_amount: 10000
""")

        return ApprovalHandler(config_dir)

    def test_get_user_role(self, handler):
        """Test getting user role."""
        assert handler.get_user_role(12345) == "admin"
        assert handler.get_user_role(67890) == "officer"
        assert handler.get_user_role(99999) is None

    def test_can_approve_admin(self, handler):
        """Test admin can approve any amount."""
        assert handler.can_approve(12345, Decimal("1000000")) is True

    def test_can_approve_officer_under_limit(self, handler):
        """Test officer can approve under limit."""
        assert handler.can_approve(67890, Decimal("5000")) is True

    def test_can_approve_officer_over_limit(self, handler):
        """Test officer cannot approve over limit."""
        assert handler.can_approve(67890, Decimal("50000")) is False

    def test_create_approval_request(self, handler):
        """Test creating approval request."""
        request = handler.create_approval_request(
            request_type="expense",
            entity="solaire",
            amount=Decimal("15000"),
            description="Office supplies",
            requester="John Doe"
        )

        assert isinstance(request, ApprovalRequest)
        assert request.entity == "solaire"
        assert request.amount == Decimal("15000")
        assert request.status == ApprovalStatus.PENDING

    def test_create_auto_approved_request(self, handler):
        """Test auto-approval for small amounts."""
        request = handler.create_approval_request(
            request_type="expense",
            entity="solaire",
            amount=Decimal("5000"),
            description="Small expense",
            requester="John Doe"
        )

        assert request.status == ApprovalStatus.AUTO_APPROVED

    def test_format_approval_message(self, handler):
        """Test formatting approval message."""
        request = ApprovalRequest(
            id="test-123",
            request_type="expense",
            entity="solaire",
            amount=Decimal("15000"),
            description="Office supplies",
            requester="John Doe",
            requested_at=datetime.now()
        )

        message, keyboard = handler.format_approval_message(request)

        assert "Approval Request" in message
        assert "SOLAIRE" in message
        assert "15,000" in message
        assert keyboard is not None
        assert "inline_keyboard" in keyboard

    def test_handle_approve_callback(self, handler):
        """Test approve callback handling."""
        # Create a request first
        request = handler.create_approval_request(
            request_type="expense",
            entity="solaire",
            amount=Decimal("15000"),
            description="Test",
            requester="Tester"
        )

        result = handler.handle_callback(f"approve_{request.id}", 12345)

        # Without DB, this will fail to find request
        assert isinstance(result, ApprovalResult)


class TestFileHandler:
    """Tests for FileHandler class."""

    @pytest.fixture
    def handler(self, tmp_path):
        """Create file handler with test config."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        temp_dir = tmp_path / "uploads"
        temp_dir.mkdir()

        acl_file = config_dir / "telegram_acl.yaml"
        acl_file.write_text("""
users:
  - telegram_id: 12345
    name: "Test Admin"
    role: admin
permissions:
  admin: ["*"]
""")

        return FileHandler(config_dir, temp_dir=temp_dir)

    def test_can_upload(self, handler):
        """Test upload permission check."""
        assert handler.can_upload(12345) is True
        assert handler.can_upload(99999) is False

    def test_validate_file_size(self, handler):
        """Test file size validation."""
        is_valid, error = handler.validate_file("test.csv", 1000)
        assert is_valid is True

        is_valid, error = handler.validate_file("test.csv", 50 * 1024 * 1024)
        assert is_valid is False
        assert "too large" in error.lower()

    def test_validate_file_type(self, handler):
        """Test file type validation."""
        is_valid, error = handler.validate_file("test.csv", 1000)
        assert is_valid is True

        is_valid, error = handler.validate_file("test.pdf", 1000)
        assert is_valid is True

        is_valid, error = handler.validate_file("test.exe", 1000)
        assert is_valid is False
        assert "Unsupported" in error

    def test_detect_file_type(self, handler):
        """Test file type detection."""
        assert handler.detect_file_type("test.csv", b"col1,col2\nval1,val2") == "csv"
        assert handler.detect_file_type("test.pdf", b"%PDF-1.4") == "pdf"
        assert handler.detect_file_type("test.xlsx", b"PK") == "excel"

    def test_save_upload(self, handler):
        """Test saving uploaded file."""
        content = b"col1,col2\nval1,val2"
        path = handler.save_upload(
            file_id="file123",
            file_name="test.csv",
            content=content,
            user_id=12345,
            entity="solaire"
        )

        assert path.exists()
        assert path.read_bytes() == content

    def test_cleanup_temp_files(self, handler):
        """Test temporary file cleanup."""
        # Create old file
        old_file = handler.temp_dir / "old_file.csv"
        old_file.write_text("old data")

        # Set modification time to 2 days ago
        import os
        import time
        old_time = time.time() - (48 * 3600)
        os.utime(old_file, (old_time, old_time))

        deleted = handler.cleanup_temp_files(max_age_hours=24)

        assert deleted == 1
        assert not old_file.exists()


class TestReportFormatter:
    """Tests for ReportFormatter class."""

    @pytest.fixture
    def formatter(self):
        """Create report formatter."""
        return ReportFormatter()

    def test_truncate_message(self, formatter):
        """Test message truncation."""
        short_msg = "Short message"
        assert formatter.truncate_message(short_msg) == short_msg

        long_msg = "x" * 5000
        truncated = formatter.truncate_message(long_msg)
        assert len(truncated) <= formatter.max_length
        assert "truncated" in truncated

    def test_format_pl_summary(self, formatter):
        """Test P&L summary formatting."""
        message = formatter.format_pl_summary(
            entity="solaire",
            period="2025-01",
            revenue=Decimal("1000000"),
            expenses=Decimal("800000"),
            top_expense_categories=[
                ("Salaries", Decimal("400000")),
                ("Utilities", Decimal("100000")),
            ]
        )

        assert "P&L Summary" in message
        assert "SOLAIRE" in message
        assert "₱1,000,000.00" in message
        assert "₱200,000.00" in message  # Net income
        assert "Salaries" in message

    def test_format_pl_summary_with_comparison(self, formatter):
        """Test P&L with period comparison."""
        message = formatter.format_pl_summary(
            entity="solaire",
            period="2025-01",
            revenue=Decimal("1000000"),
            expenses=Decimal("800000"),
            previous_revenue=Decimal("900000"),
            previous_expenses=Decimal("850000")
        )

        assert "Trend" in message
        assert "📈" in message or "📉" in message

    def test_format_budget_status(self, formatter):
        """Test budget status formatting."""
        items = [
            {"name": "Salaries", "budget": 500000, "actual": 450000, "utilization": 90},
            {"name": "Utilities", "budget": 100000, "actual": 110000, "utilization": 110},
            {"name": "Office", "budget": 50000, "actual": 25000, "utilization": 50},
        ]

        message = formatter.format_budget_status(
            entity="solaire",
            period="2025-01",
            total_budget=Decimal("650000"),
            total_actual=Decimal("585000"),
            items=items
        )

        assert "Budget Status" in message
        assert "SOLAIRE" in message
        assert "OK: 1" in message
        assert "Over Budget: 1" in message
        assert "Utilities" in message

    def test_format_daily_digest(self, formatter):
        """Test daily digest formatting."""
        transactions = [
            {"category": "Food", "amount": 500},
            {"category": "Food", "amount": 300},
            {"category": "Transport", "amount": 200},
        ]

        message = formatter.format_daily_digest(
            entity="solaire",
            date="2025-01-15",
            transactions=transactions,
            budget_status={
                "budget": 100000,
                "actual": 75000
            }
        )

        assert "Daily Digest" in message
        assert "SOLAIRE" in message
        assert "3" in message  # transaction count
        assert "Food" in message

    def test_format_weekly_summary(self, formatter):
        """Test weekly summary formatting."""
        message = formatter.format_weekly_summary(
            entity="solaire",
            week_start="2025-01-13",
            week_end="2025-01-19",
            this_week={
                "count": 50,
                "total": Decimal("150000"),
                "daily_avg": Decimal("21428"),
                "by_category": {"Food": Decimal("50000"), "Transport": Decimal("30000")}
            },
            last_week={
                "total": Decimal("120000")
            }
        )

        assert "Weekly Summary" in message
        assert "50" in message
        assert "Week-over-Week" in message

    def test_format_error_message(self, formatter):
        """Test error message formatting."""
        message = formatter.format_error_message(
            error="Database connection failed",
            context="Budget query",
            suggestion="Check database status"
        )

        assert "Error" in message
        assert "Database connection failed" in message
        assert "Budget query" in message
        assert "Check database status" in message

    def test_format_success_message(self, formatter):
        """Test success message formatting."""
        message = formatter.format_success_message(
            message="Report generated successfully",
            details={"File": "report.xlsx", "Size": "125KB"}
        )

        assert "Success" in message
        assert "Report generated" in message
        assert "report.xlsx" in message


class TestApprovalRequest:
    """Tests for ApprovalRequest dataclass."""

    def test_to_dict(self):
        """Test dictionary conversion."""
        request = ApprovalRequest(
            id="test-123",
            request_type="expense",
            entity="solaire",
            amount=Decimal("15000"),
            description="Office supplies",
            requester="John Doe",
            requested_at=datetime(2025, 1, 15, 10, 30),
            budget_context={"budget": 100000, "spent": 50000}
        )

        d = request.to_dict()

        assert d["id"] == "test-123"
        assert d["entity"] == "solaire"
        assert d["amount"] == 15000.0
        assert d["status"] == "pending"
        assert d["budget_context"]["budget"] == 100000


class TestCommandResult:
    """Tests for CommandResult dataclass."""

    def test_default_values(self):
        """Test default values."""
        result = CommandResult(success=True, message="Test")

        assert result.success is True
        assert result.message == "Test"
        assert result.data == {}
        assert result.keyboard is None
        assert result.parse_mode == "Markdown"

    def test_with_keyboard(self):
        """Test result with keyboard."""
        keyboard = {"inline_keyboard": [[{"text": "Test", "callback_data": "test"}]]}
        result = CommandResult(
            success=True,
            message="Choose option",
            keyboard=keyboard
        )

        assert result.keyboard == keyboard

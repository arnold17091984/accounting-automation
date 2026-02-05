"""
Budget Variance Module Tests

Tests for budget variance calculation, threshold checking,
historical analysis, and report generation.
"""

import pytest
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "python"))

from budget import (
    VarianceCalculator,
    VarianceItem,
    VarianceReport,
    ThresholdChecker,
    ThresholdAlert,
    ThresholdCheckResult,
    HistoricalAnalyzer,
    BudgetSuggestion,
    BudgetAnalysisResult,
    BudgetReportGenerator,
)


class TestVarianceItem:
    """Tests for VarianceItem dataclass."""

    def test_variance_amount_calculation(self):
        """Test variance amount is calculated correctly."""
        item = VarianceItem(
            entity="solaire",
            account_code="6100",
            account_name="Office Supplies",
            category="expense",
            budget_amount=Decimal("100000"),
            actual_amount=Decimal("75000"),
            period="2025-01"
        )

        assert item.variance_amount == Decimal("25000")
        assert item.utilization_percent == 75.0
        assert item.is_over_budget is False
        assert item.status == "warning"

    def test_over_budget_status(self):
        """Test over budget detection."""
        item = VarianceItem(
            entity="cod",
            account_code="6200",
            account_name="Travel",
            category="expense",
            budget_amount=Decimal("50000"),
            actual_amount=Decimal("60000"),
            period="2025-01"
        )

        assert item.variance_amount == Decimal("-10000")
        assert item.utilization_percent == 120.0
        assert item.is_over_budget is True
        assert item.status == "exceeded"

    def test_critical_status(self):
        """Test critical threshold detection."""
        item = VarianceItem(
            entity="royce",
            account_code="6300",
            account_name="Utilities",
            category="expense",
            budget_amount=Decimal("100000"),
            actual_amount=Decimal("95000"),
            period="2025-01"
        )

        assert item.utilization_percent == 95.0
        assert item.status == "critical"

    def test_ok_status(self):
        """Test OK status for low utilization."""
        item = VarianceItem(
            entity="midori",
            account_code="6100",
            account_name="Office Supplies",
            category="expense",
            budget_amount=Decimal("100000"),
            actual_amount=Decimal("50000"),
            period="2025-01"
        )

        assert item.utilization_percent == 50.0
        assert item.status == "ok"

    def test_zero_budget_handling(self):
        """Test handling of zero budget."""
        item = VarianceItem(
            entity="tours",
            account_code="6400",
            account_name="Marketing",
            category="expense",
            budget_amount=Decimal("0"),
            actual_amount=Decimal("10000"),
            period="2025-01"
        )

        assert item.utilization_percent == 0.0
        assert item.is_over_budget is True

    def test_to_dict(self):
        """Test dictionary conversion."""
        item = VarianceItem(
            entity="solaire",
            account_code="6100",
            account_name="Office Supplies",
            category="expense",
            budget_amount=Decimal("100000"),
            actual_amount=Decimal("75000"),
            period="2025-01"
        )

        d = item.to_dict()
        assert d["entity"] == "solaire"
        assert d["account_code"] == "6100"
        assert d["budget_amount"] == 100000.0
        assert d["actual_amount"] == 75000.0
        assert d["variance_amount"] == 25000.0
        assert d["utilization_percent"] == 75.0


class TestVarianceCalculator:
    """Tests for VarianceCalculator class."""

    @pytest.fixture
    def calculator(self, tmp_path):
        """Create calculator with temp config."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        # Create minimal config
        thresholds_file = config_dir / "budget_thresholds.yaml"
        thresholds_file.write_text("""
thresholds:
  warning:
    percentage: 70
  critical:
    percentage: 90
  exceeded:
    percentage: 100
""")

        return VarianceCalculator(config_dir)

    def test_calculate_single_variance(self, calculator):
        """Test single variance calculation."""
        result = calculator.calculate(
            entity="solaire",
            account_code="6100",
            account_name="Office Supplies",
            category="expense",
            budget_amount=Decimal("100000"),
            actual_amount=Decimal("75000"),
            period="2025-01"
        )

        assert isinstance(result, VarianceItem)
        assert result.variance_amount == Decimal("25000")

    def test_create_report(self, calculator):
        """Test report creation from multiple items."""
        items = [
            VarianceItem(
                entity="solaire",
                account_code="6100",
                account_name="Office Supplies",
                category="expense",
                budget_amount=Decimal("100000"),
                actual_amount=Decimal("75000"),
                period="2025-01"
            ),
            VarianceItem(
                entity="solaire",
                account_code="6200",
                account_name="Travel",
                category="expense",
                budget_amount=Decimal("50000"),
                actual_amount=Decimal("60000"),
                period="2025-01"
            ),
        ]

        report = calculator.create_report(items, "2025-01", entity="solaire")

        assert isinstance(report, VarianceReport)
        assert report.entity == "solaire"
        assert report.period == "2025-01"
        assert len(report.items) == 2
        assert report.summary["total_budget"] == 150000.0
        assert report.summary["total_actual"] == 135000.0
        assert report.summary["accounts_over_budget"] == 1


class TestThresholdChecker:
    """Tests for ThresholdChecker class."""

    @pytest.fixture
    def checker(self, tmp_path):
        """Create checker with temp config."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        thresholds_file = config_dir / "budget_thresholds.yaml"
        thresholds_file.write_text("""
thresholds:
  warning:
    percentage: 70
    severity: low
  critical:
    percentage: 90
    severity: medium
  exceeded:
    percentage: 100
    severity: high
cooldown:
  same_threshold_hours: 24
""")

        return ThresholdChecker(config_dir)

    def test_check_variance_no_alert(self, checker):
        """Test no alert for low utilization."""
        item = VarianceItem(
            entity="solaire",
            account_code="6100",
            account_name="Office Supplies",
            category="expense",
            budget_amount=Decimal("100000"),
            actual_amount=Decimal("50000"),
            period="2025-01"
        )

        alert = checker.check_variance(item)
        assert alert is None

    def test_check_variance_warning_alert(self, checker):
        """Test warning alert generation."""
        item = VarianceItem(
            entity="solaire",
            account_code="6100",
            account_name="Office Supplies",
            category="expense",
            budget_amount=Decimal("100000"),
            actual_amount=Decimal("75000"),
            period="2025-01"
        )

        alert = checker.check_variance(item)

        assert alert is not None
        assert alert.threshold_type == "warning"
        assert alert.severity == "low"

    def test_check_variance_critical_alert(self, checker):
        """Test critical alert generation."""
        item = VarianceItem(
            entity="cod",
            account_code="6200",
            account_name="Travel",
            category="expense",
            budget_amount=Decimal("100000"),
            actual_amount=Decimal("95000"),
            period="2025-01"
        )

        alert = checker.check_variance(item)

        assert alert is not None
        assert alert.threshold_type == "critical"
        assert alert.severity == "medium"

    def test_check_variance_exceeded_alert(self, checker):
        """Test exceeded alert generation."""
        item = VarianceItem(
            entity="royce",
            account_code="6300",
            account_name="Utilities",
            category="expense",
            budget_amount=Decimal("100000"),
            actual_amount=Decimal("110000"),
            period="2025-01"
        )

        alert = checker.check_variance(item)

        assert alert is not None
        assert alert.threshold_type == "exceeded"
        assert alert.severity == "high"

    def test_check_report(self, checker):
        """Test checking full report."""
        items = [
            VarianceItem(
                entity="solaire",
                account_code="6100",
                account_name="Office Supplies",
                category="expense",
                budget_amount=Decimal("100000"),
                actual_amount=Decimal("75000"),
                period="2025-01"
            ),
            VarianceItem(
                entity="solaire",
                account_code="6200",
                account_name="Travel",
                category="expense",
                budget_amount=Decimal("50000"),
                actual_amount=Decimal("60000"),
                period="2025-01"
            ),
            VarianceItem(
                entity="solaire",
                account_code="6300",
                account_name="Utilities",
                category="expense",
                budget_amount=Decimal("100000"),
                actual_amount=Decimal("50000"),
                period="2025-01"
            ),
        ]

        report = VarianceReport(
            entity="solaire",
            period="2025-01",
            generated_at=datetime.now(),
            items=items,
            summary={}
        )

        result = checker.check_report(report)

        assert isinstance(result, ThresholdCheckResult)
        assert result.checked_count == 3
        assert result.alert_count == 2  # warning + exceeded
        assert result.has_critical_alerts is True

    def test_cooldown_prevents_duplicate_alerts(self, checker):
        """Test that cooldown prevents duplicate alerts."""
        item = VarianceItem(
            entity="solaire",
            account_code="6100",
            account_name="Office Supplies",
            category="expense",
            budget_amount=Decimal("100000"),
            actual_amount=Decimal("75000"),
            period="2025-01"
        )

        # First check - should generate alert
        alert1 = checker.check_variance(item)
        assert alert1 is not None

        # Second check - should be in cooldown
        alert2 = checker.check_variance(item)
        assert alert2 is None

    def test_clear_cooldown(self, checker):
        """Test cooldown clearing."""
        item = VarianceItem(
            entity="solaire",
            account_code="6100",
            account_name="Office Supplies",
            category="expense",
            budget_amount=Decimal("100000"),
            actual_amount=Decimal("75000"),
            period="2025-01"
        )

        # Generate alert
        checker.check_variance(item)

        # Clear cooldown
        checker.clear_cooldown(entity="solaire", account_code="6100")

        # Should generate alert again
        alert = checker.check_variance(item)
        assert alert is not None


class TestBudgetReportGenerator:
    """Tests for BudgetReportGenerator class."""

    @pytest.fixture
    def generator(self):
        """Create report generator."""
        return BudgetReportGenerator()

    def test_format_variance_for_telegram(self, generator):
        """Test Telegram variance report formatting."""
        items = [
            VarianceItem(
                entity="solaire",
                account_code="6100",
                account_name="Office Supplies",
                category="expense",
                budget_amount=Decimal("100000"),
                actual_amount=Decimal("75000"),
                period="2025-01"
            ),
            VarianceItem(
                entity="solaire",
                account_code="6200",
                account_name="Travel",
                category="expense",
                budget_amount=Decimal("50000"),
                actual_amount=Decimal("60000"),
                period="2025-01"
            ),
        ]

        report = VarianceReport(
            entity="solaire",
            period="2025-01",
            generated_at=datetime.now(),
            items=items,
            summary={
                "total_budget": 150000.0,
                "total_actual": 135000.0,
                "overall_utilization": 90.0,
                "accounts_ok": 0,
                "accounts_warning": 1,
                "accounts_over_budget": 1,
            }
        )

        message = generator.format_variance_for_telegram(report)

        assert "Budget Status Report" in message
        assert "SOLAIRE" in message
        assert "2025-01" in message
        assert "₱150,000.00" in message
        assert "90.0%" in message
        assert "Travel" in message

    def test_format_alerts_for_telegram(self, generator):
        """Test Telegram alert formatting."""
        alerts = [
            ThresholdAlert(
                entity="solaire",
                account_code="6200",
                account_name="Travel",
                threshold_type="exceeded",
                threshold_percent=100,
                actual_percent=120.0,
                actual_amount=Decimal("60000"),
                budget_amount=Decimal("50000"),
                message=""
            ),
            ThresholdAlert(
                entity="cod",
                account_code="6100",
                account_name="Office Supplies",
                threshold_type="warning",
                threshold_percent=70,
                actual_percent=75.0,
                actual_amount=Decimal("75000"),
                budget_amount=Decimal("100000"),
                message=""
            ),
        ]

        message = generator.format_alerts_for_telegram(alerts)

        assert "Budget Alerts" in message
        assert "Critical" in message
        assert "Travel" in message
        assert "120.0%" in message

    def test_format_empty_alerts(self, generator):
        """Test formatting with no alerts."""
        message = generator.format_alerts_for_telegram([])
        assert "No budget alerts" in message

    def test_format_daily_digest(self, generator):
        """Test daily digest formatting."""
        message = generator.format_daily_digest(
            entity="solaire",
            date="2025-01-15",
            transactions_today=25,
            total_spent=150000.0,
            mtd_budget=1000000.0,
            mtd_actual=750000.0,
            top_categories=[
                ("Travel", 50000.0),
                ("Office Supplies", 30000.0),
                ("Utilities", 20000.0),
            ]
        )

        assert "Daily Digest" in message
        assert "SOLAIRE" in message
        assert "2025-01-15" in message
        assert "25" in message
        assert "₱150,000.00" in message
        assert "75.0%" in message
        assert "Travel" in message


class TestHistoricalAnalyzer:
    """Tests for HistoricalAnalyzer class."""

    @pytest.fixture
    def mock_anthropic(self):
        """Create mock Anthropic client."""
        with patch("budget.historical_analyzer.anthropic") as mock:
            mock_client = Mock()
            mock.Anthropic.return_value = mock_client

            mock_response = Mock()
            mock_response.content = [Mock(text='''
{
    "recommendations": [
        {
            "account_code": "6100",
            "account_name": "Office Supplies",
            "recommended_budget": 85000,
            "change_percent": -15,
            "rationale": "Based on declining trend",
            "confidence": 0.85,
            "risk_level": "low",
            "seasonal_factor": 1.0
        }
    ],
    "key_insights": ["Spending has decreased over the past 6 months"],
    "risks_and_assumptions": ["Assumes no major changes in operations"]
}
''')]
            mock_client.messages.create.return_value = mock_response

            yield mock

    @pytest.fixture
    def analyzer(self, tmp_path, mock_anthropic):
        """Create analyzer with temp config and mock client."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        thresholds_file = config_dir / "budget_thresholds.yaml"
        thresholds_file.write_text("""
budget_suggestions:
  lookback_months: 6
  inflation_rate: 0.05
""")

        entity_file = config_dir / "entity_config.yaml"
        entity_file.write_text("""
entities:
  solaire:
    full_name: Solaire Resort
    industry: gaming
""")

        return HistoricalAnalyzer(config_dir, api_key="test-key")

    def test_analyze_generates_suggestions(self, analyzer):
        """Test that analyze generates budget suggestions."""
        historical_data = {
            "6100": [
                {"month": "2024-07", "name": "Office Supplies", "amount": 80000},
                {"month": "2024-08", "name": "Office Supplies", "amount": 85000},
                {"month": "2024-09", "name": "Office Supplies", "amount": 75000},
                {"month": "2024-10", "name": "Office Supplies", "amount": 70000},
                {"month": "2024-11", "name": "Office Supplies", "amount": 72000},
                {"month": "2024-12", "name": "Office Supplies", "amount": 68000},
            ]
        }

        current_budgets = {
            "6100": Decimal("100000")
        }

        result = analyzer.analyze(
            entity="solaire",
            target_month="2025-01",
            historical_data=historical_data,
            current_budgets=current_budgets,
            growth_rate=0.0,
            seasonal_notes=""
        )

        assert isinstance(result, BudgetAnalysisResult)
        assert result.entity == "solaire"
        assert result.target_period == "2025-01"
        assert len(result.suggestions) == 1
        assert result.suggestions[0].account_code == "6100"
        assert result.suggestions[0].recommended_budget == Decimal("85000")

    def test_statistical_fallback(self, analyzer, tmp_path):
        """Test statistical fallback when Claude fails."""
        # Make Claude fail
        analyzer.client.messages.create.side_effect = Exception("API Error")

        historical_data = {
            "6100": [
                {"month": "2024-07", "name": "Office Supplies", "amount": 80000},
                {"month": "2024-08", "name": "Office Supplies", "amount": 85000},
                {"month": "2024-09", "name": "Office Supplies", "amount": 75000},
            ]
        }

        current_budgets = {
            "6100": Decimal("100000")
        }

        result = analyzer.analyze(
            entity="solaire",
            target_month="2025-01",
            historical_data=historical_data,
            current_budgets=current_budgets,
            growth_rate=0.05,
            seasonal_notes=""
        )

        assert isinstance(result, BudgetAnalysisResult)
        assert len(result.suggestions) == 1
        assert "statistical analysis" in result.key_insights[0].lower()


class TestBudgetSuggestion:
    """Tests for BudgetSuggestion dataclass."""

    def test_to_dict(self):
        """Test dictionary conversion."""
        suggestion = BudgetSuggestion(
            account_code="6100",
            account_name="Office Supplies",
            current_budget=Decimal("100000"),
            recommended_budget=Decimal("85000"),
            change_percent=-15.0,
            rationale="Based on declining trend",
            confidence=0.85,
            risk_level="low",
            historical_avg=Decimal("75000"),
            historical_max=Decimal("85000"),
            seasonal_factor=1.0
        )

        d = suggestion.to_dict()

        assert d["account_code"] == "6100"
        assert d["current_budget"] == 100000.0
        assert d["recommended_budget"] == 85000.0
        assert d["change_percent"] == -15.0
        assert d["confidence"] == 0.85


class TestBudgetAnalysisResult:
    """Tests for BudgetAnalysisResult dataclass."""

    def test_total_change_percent(self):
        """Test total change calculation."""
        result = BudgetAnalysisResult(
            entity="solaire",
            target_period="2025-01",
            analysis_date=datetime.now(),
            total_current=Decimal("1000000"),
            total_recommended=Decimal("1100000")
        )

        assert result.total_change_percent == 10.0

    def test_to_dict(self):
        """Test dictionary conversion."""
        result = BudgetAnalysisResult(
            entity="solaire",
            target_period="2025-01",
            analysis_date=datetime.now(),
            total_current=Decimal("1000000"),
            total_recommended=Decimal("1100000"),
            key_insights=["Insight 1", "Insight 2"],
            risks_and_assumptions=["Risk 1"]
        )

        d = result.to_dict()

        assert d["entity"] == "solaire"
        assert d["total_change_percent"] == 10.0
        assert len(d["key_insights"]) == 2

"""
Tests for P&L Generator Module
"""

import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestPLExcelBuilder:
    """Tests for PLExcelBuilder class."""

    @pytest.fixture
    def sample_pl_data(self):
        """Sample P&L data for testing."""
        return {
            "revenue": {
                "items": [
                    {
                        "code": "4010",
                        "name": "Gaming Revenue",
                        "actual": 15000000,
                        "budget": 14000000,
                        "prior_period": 13500000
                    },
                    {
                        "code": "4020",
                        "name": "Rolling Commission Income",
                        "actual": 2500000,
                        "budget": 2200000,
                        "prior_period": 2100000
                    }
                ]
            },
            "cost_of_sales": {
                "items": [
                    {
                        "code": "5100",
                        "name": "Junket Commission Expense",
                        "actual": 6800000,
                        "budget": 6500000,
                        "prior_period": 6200000
                    }
                ]
            },
            "operating_expenses": {
                "items": [
                    {
                        "code": "6230",
                        "name": "Meals & Entertainment",
                        "actual": 450000,
                        "budget": 500000,
                        "prior_period": 420000
                    },
                    {
                        "code": "6410",
                        "name": "Fuel & Gas",
                        "actual": 55000,
                        "budget": 45000,
                        "prior_period": 42000
                    },
                    {
                        "code": "7010",
                        "name": "Salaries & Wages",
                        "actual": 2100000,
                        "budget": 2100000,
                        "prior_period": 2000000
                    }
                ]
            }
        }

    def test_excel_builder_initialization(self, config_dir):
        """Test PLExcelBuilder initializes correctly."""
        from python.pl_generator.excel_builder import PLExcelBuilder

        builder = PLExcelBuilder(config_dir=config_dir)

        assert builder.config_dir == config_dir
        assert builder.chart_of_accounts is not None
        assert builder.entity_config is not None

    def test_generate_pl_report(self, sample_pl_data, tmp_path, config_dir):
        """Test P&L report generation."""
        from python.pl_generator.excel_builder import PLExcelBuilder

        builder = PLExcelBuilder(config_dir=config_dir)
        output_path = tmp_path / "test_pl.xlsx"

        result = builder.generate_pl_report(
            entity="solaire",
            period="2025-01",
            data=sample_pl_data,
            output_path=output_path
        )

        assert result.exists()
        assert result.suffix == ".xlsx"

    def test_calculate_totals(self, sample_pl_data):
        """Test total calculations are correct."""
        revenue = sum(item["actual"] for item in sample_pl_data["revenue"]["items"])
        cos = sum(item["actual"] for item in sample_pl_data["cost_of_sales"]["items"])
        opex = sum(item["actual"] for item in sample_pl_data["operating_expenses"]["items"])

        gross_profit = revenue - cos
        net_income = gross_profit - opex

        assert revenue == 17500000
        assert cos == 6800000
        assert gross_profit == 10700000
        assert net_income == 8095000


class TestPLPowerPointBuilder:
    """Tests for PLPowerPointBuilder class."""

    @pytest.fixture
    def sample_pl_data(self):
        """Sample P&L data for testing."""
        return {
            "revenue": {
                "items": [
                    {"code": "4010", "name": "Gaming Revenue", "actual": 15000000, "budget": 14000000}
                ]
            },
            "cost_of_sales": {
                "items": [
                    {"code": "5100", "name": "Commission Expense", "actual": 6800000, "budget": 6500000}
                ]
            },
            "operating_expenses": {
                "items": [
                    {"code": "6230", "name": "Meals", "actual": 450000, "budget": 500000}
                ]
            },
            "highlights": [
                "Revenue up 12% vs prior month",
                "Expenses under budget by 8%"
            ]
        }

    def test_pptx_builder_initialization(self, config_dir):
        """Test PLPowerPointBuilder initializes correctly."""
        from python.pl_generator.pptx_builder import PLPowerPointBuilder

        builder = PLPowerPointBuilder(config_dir=config_dir)

        assert builder.config_dir == config_dir
        assert builder.entity_config is not None

    def test_generate_monthly_report(self, sample_pl_data, tmp_path, config_dir):
        """Test PowerPoint report generation."""
        from python.pl_generator.pptx_builder import PLPowerPointBuilder

        builder = PLPowerPointBuilder(config_dir=config_dir)
        output_path = tmp_path / "test_pl.pptx"

        result = builder.generate_monthly_report(
            entity="solaire",
            period="2025-01",
            data=sample_pl_data,
            output_path=output_path
        )

        assert result.exists()
        assert result.suffix == ".pptx"


class TestConsolidationEngine:
    """Tests for ConsolidationEngine class."""

    @pytest.fixture
    def sample_entity_data(self):
        """Sample entity data for consolidation testing."""
        return {
            "solaire": {
                "revenue": {
                    "items": [
                        {"code": "4010", "name": "Gaming Revenue", "actual": 15000000, "budget": 14000000, "prior_period": 13500000}
                    ]
                },
                "cost_of_sales": {
                    "items": [
                        {"code": "5100", "name": "Commission", "actual": 6800000, "budget": 6500000, "prior_period": 6200000}
                    ]
                },
                "operating_expenses": {
                    "items": [
                        {"code": "6230", "name": "Meals", "actual": 450000, "budget": 500000, "prior_period": 420000}
                    ]
                }
            },
            "cod": {
                "revenue": {
                    "items": [
                        {"code": "4010", "name": "Gaming Revenue", "actual": 12000000, "budget": 11000000, "prior_period": 10500000}
                    ]
                },
                "cost_of_sales": {
                    "items": [
                        {"code": "5100", "name": "Commission", "actual": 5400000, "budget": 5000000, "prior_period": 4800000}
                    ]
                },
                "operating_expenses": {
                    "items": [
                        {"code": "6230", "name": "Meals", "actual": 350000, "budget": 400000, "prior_period": 320000}
                    ]
                }
            },
            "royce": {
                "revenue": {
                    "items": [
                        {"code": "4010", "name": "Gaming Revenue", "actual": 8000000, "budget": 7500000, "prior_period": 7000000}
                    ]
                },
                "cost_of_sales": {
                    "items": [
                        {"code": "5100", "name": "Commission", "actual": 3600000, "budget": 3400000, "prior_period": 3200000}
                    ]
                },
                "operating_expenses": {
                    "items": [
                        {"code": "6230", "name": "Meals", "actual": 250000, "budget": 300000, "prior_period": 230000}
                    ]
                }
            }
        }

    def test_consolidation_engine_initialization(self, config_dir):
        """Test ConsolidationEngine initializes correctly."""
        from python.pl_generator.consolidation import ConsolidationEngine

        engine = ConsolidationEngine(config_dir=config_dir)

        assert engine.config_dir == config_dir
        assert engine.entity_config is not None

    def test_consolidate_junket_entities(self, sample_entity_data, config_dir):
        """Test consolidation of junket entities."""
        from python.pl_generator.consolidation import ConsolidationEngine

        engine = ConsolidationEngine(config_dir=config_dir)

        result = engine.consolidate(
            entities=["solaire", "cod", "royce"],
            period="2025-01",
            entity_data=sample_entity_data
        )

        assert result.entities == ["solaire", "cod", "royce"]
        assert result.period == "2025-01"

        # Check aggregated revenue
        total_revenue = sum(
            item["actual"] for item in result.revenue.get("items", [])
        )
        expected_revenue = 15000000 + 12000000 + 8000000  # solaire + cod + royce
        assert float(total_revenue) == expected_revenue

    def test_consolidation_summary(self, sample_entity_data, config_dir):
        """Test consolidation summary generation."""
        from python.pl_generator.consolidation import ConsolidationEngine

        engine = ConsolidationEngine(config_dir=config_dir)

        consolidated = engine.consolidate(
            entities=["solaire", "cod", "royce"],
            period="2025-01",
            entity_data=sample_entity_data
        )

        summary = engine.get_consolidation_summary(consolidated)

        assert summary["entity_count"] == 3
        assert summary["total_revenue"] > 0
        assert summary["net_income"] > 0
        assert "net_margin" in summary


class TestReportDataValidation:
    """Tests for report data validation."""

    def test_valid_entity_codes(self, entity_config):
        """Test that all entity codes are valid."""
        valid_entities = ["solaire", "cod", "royce", "manila_junket", "tours", "midori"]

        for entity in valid_entities:
            assert entity in entity_config["entities"]

    def test_chart_of_accounts_structure(self, chart_of_accounts):
        """Test chart of accounts has required sections."""
        required_sections = ["assets", "liabilities", "equity", "revenue", "cost_of_sales", "operating_expenses"]

        for section in required_sections:
            assert section in chart_of_accounts, f"Missing section: {section}"

    def test_budget_thresholds_config(self, budget_thresholds):
        """Test budget thresholds configuration."""
        assert "thresholds" in budget_thresholds

        thresholds = budget_thresholds["thresholds"]
        assert "warning" in thresholds
        assert "critical" in thresholds
        assert "exceeded" in thresholds

        assert thresholds["warning"]["percentage"] == 70
        assert thresholds["critical"]["percentage"] == 90
        assert thresholds["exceeded"]["percentage"] == 100


# Fixtures for module imports
@pytest.fixture
def config_dir():
    """Return the config directory path."""
    return Path(__file__).parent.parent / "config"


@pytest.fixture
def entity_config(config_dir):
    """Load entity configuration."""
    import yaml
    with open(config_dir / "entity_config.yaml") as f:
        return yaml.safe_load(f)


@pytest.fixture
def chart_of_accounts(config_dir):
    """Load chart of accounts."""
    import yaml
    with open(config_dir / "chart_of_accounts.yaml") as f:
        return yaml.safe_load(f)


@pytest.fixture
def budget_thresholds(config_dir):
    """Load budget thresholds."""
    import yaml
    with open(config_dir / "budget_thresholds.yaml") as f:
        return yaml.safe_load(f)

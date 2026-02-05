"""
Pytest configuration and fixtures for accounting automation tests.
"""

import json
import os
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Generator

import pytest
import yaml

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent


@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return PROJECT_ROOT


@pytest.fixture
def config_dir() -> Path:
    """Return the config directory path."""
    return PROJECT_ROOT / "config"


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the test fixtures directory path."""
    return PROJECT_ROOT / "tests" / "fixtures"


@pytest.fixture
def chart_of_accounts(config_dir: Path) -> dict:
    """Load the chart of accounts configuration."""
    with open(config_dir / "chart_of_accounts.yaml") as f:
        return yaml.safe_load(f)


@pytest.fixture
def entity_config(config_dir: Path) -> dict:
    """Load the entity configuration."""
    with open(config_dir / "entity_config.yaml") as f:
        return yaml.safe_load(f)


@pytest.fixture
def merchant_mappings(config_dir: Path) -> dict:
    """Load the merchant mappings configuration."""
    with open(config_dir / "merchant_mappings.json") as f:
        return json.load(f)


@pytest.fixture
def budget_thresholds(config_dir: Path) -> dict:
    """Load the budget thresholds configuration."""
    with open(config_dir / "budget_thresholds.yaml") as f:
        return yaml.safe_load(f)


@pytest.fixture
def sample_transaction() -> dict:
    """Return a sample transaction for testing."""
    return {
        "id": "test-uuid-1234",
        "source": "credit_card",
        "source_bank": "bdo",
        "entity": "solaire",
        "txn_date": date(2025, 1, 15),
        "description": "SHELL GAS STATION",
        "merchant": "SHELL",
        "amount": Decimal("2500.00"),
        "currency": "PHP",
        "account_code": None,
        "account_name": None,
        "category": None,
        "classification_method": None,
        "classification_confidence": None,
    }


@pytest.fixture
def sample_transactions() -> list[dict]:
    """Return a list of sample transactions for testing."""
    return [
        {
            "txn_date": "2025-01-15",
            "description": "SHELL BGC",
            "merchant": "SHELL",
            "amount": 2500.00,
        },
        {
            "txn_date": "2025-01-16",
            "description": "MERALCO PAYMENT",
            "merchant": "MERALCO",
            "amount": 15000.00,
        },
        {
            "txn_date": "2025-01-17",
            "description": "STARBUCKS COFFEE BGC",
            "merchant": "STARBUCKS",
            "amount": 350.00,
        },
        {
            "txn_date": "2025-01-18",
            "description": "BDO ANNUAL FEE",
            "merchant": "BDO ANNUAL FEE",
            "amount": 3500.00,
        },
    ]


@pytest.fixture
def sample_budget() -> dict:
    """Return a sample budget entry for testing."""
    return {
        "entity": "solaire",
        "account_code": "6230",
        "account_name": "Meals & Entertainment",
        "category": "expense",
        "year": 2025,
        "month": 1,
        "budget_amount": Decimal("50000.00"),
    }


@pytest.fixture
def sample_csv_content() -> str:
    """Return sample CSV content for testing parsers."""
    return """Transaction Date,Description,Reference Number,Debit,Credit,Balance
01/15/2025,POS PURCHASE - SHELL BGC - 12345,REF001,2500.00,,100000.00
01/16/2025,BILLS PAYMENT - MERALCO,REF002,15000.00,,85000.00
01/17/2025,POS PURCHASE - STARBUCKS BGC,REF003,350.00,,84650.00
01/18/2025,BDO ANNUAL FEE,REF004,3500.00,,81150.00
"""


# Environment setup for tests
@pytest.fixture(autouse=True)
def setup_test_env():
    """Set up test environment variables."""
    os.environ.setdefault("POSTGRES_HOST", "localhost")
    os.environ.setdefault("POSTGRES_PORT", "5432")
    os.environ.setdefault("POSTGRES_DB", "accounting_test")
    os.environ.setdefault("POSTGRES_USER", "test")
    os.environ.setdefault("POSTGRES_PASSWORD", "test")
    yield

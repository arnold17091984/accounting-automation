"""
Card Processor Module Tests

Tests for CSV parsers, PDF extractor, merchant lookup,
duplicate detection, and transaction categorization.
"""

import pytest
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from io import StringIO
import json

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "python"))

from card_processor.csv_parsers.base import BaseCSVParser, ParsedTransaction, ParseResult
from card_processor.csv_parsers.unionbank import UnionBankParser
from card_processor.csv_parsers.bdo import BDOParser
from card_processor.csv_parsers.gcash import GCashParser
from card_processor.csv_parsers.generic import GenericParser, detect_and_parse
from card_processor.merchant_lookup import MerchantLookup, MerchantMatch
from card_processor.duplicate_detector import DuplicateDetector, DuplicateMatch
from card_processor.categorizer import TransactionCategorizer, CategorizedTransaction


class TestParsedTransaction:
    """Tests for ParsedTransaction dataclass."""

    def test_default_values(self):
        """Test default value initialization."""
        txn = ParsedTransaction(date=datetime(2025, 1, 15))

        assert txn.date == datetime(2025, 1, 15)
        assert txn.posting_date is None
        assert txn.description == ""
        assert txn.merchant == ""
        assert txn.amount == Decimal("0")
        assert txn.reference is None
        assert txn.balance is None
        assert txn.transaction_type is None
        assert txn.raw_data == {}

    def test_full_initialization(self):
        """Test full value initialization."""
        raw = {"original": "data"}
        txn = ParsedTransaction(
            date=datetime(2025, 1, 15),
            posting_date=datetime(2025, 1, 16),
            description="PURCHASE - STORE ABC",
            merchant="STORE ABC",
            amount=Decimal("1500.50"),
            reference="REF123",
            balance=Decimal("50000.00"),
            transaction_type="purchase",
            raw_data=raw
        )

        assert txn.posting_date == datetime(2025, 1, 16)
        assert txn.merchant == "STORE ABC"
        assert txn.amount == Decimal("1500.50")
        assert txn.reference == "REF123"


class TestUnionBankParser:
    """Tests for UnionBank CSV parser."""

    @pytest.fixture
    def parser(self):
        """Create UnionBank parser."""
        return UnionBankParser()

    @pytest.fixture
    def sample_csv(self):
        """Sample UnionBank CSV content."""
        return """Transaction Date,Posting Date,Description,Reference Number,Debit,Credit,Balance
01/15/2025,01/16/2025,PURCHASE - JOLLIBEE MAKATI,12345678,500.00,,49500.00
01/14/2025,01/15/2025,PAYMENT - THANK YOU,,,-10000.00,50000.00
01/13/2025,01/14/2025,PURCHASE - GRAB RIDE,87654321,250.00,,60000.00
"""

    def test_can_parse_correct_format(self, parser, sample_csv):
        """Test parser recognizes UnionBank format."""
        assert parser.can_parse(sample_csv) is True

    def test_can_parse_wrong_format(self, parser):
        """Test parser rejects non-UnionBank format."""
        wrong_csv = "Date,Amount,Description\n2025-01-15,100,Test"
        assert parser.can_parse(wrong_csv) is False

    def test_parse_transactions(self, parser, sample_csv):
        """Test parsing UnionBank transactions."""
        result = parser.parse(sample_csv)

        assert isinstance(result, ParseResult)
        assert result.success is True
        assert len(result.transactions) == 3
        assert result.bank_name == "unionbank"

        # Check first transaction
        txn = result.transactions[0]
        assert txn.date == datetime(2025, 1, 15)
        assert txn.posting_date == datetime(2025, 1, 16)
        assert "JOLLIBEE" in txn.description
        assert txn.merchant == "JOLLIBEE MAKATI"
        assert txn.amount == Decimal("500.00")
        assert txn.reference == "12345678"

    def test_merchant_extraction(self, parser, sample_csv):
        """Test merchant name extraction."""
        result = parser.parse(sample_csv)

        merchants = [t.merchant for t in result.transactions]
        assert "JOLLIBEE MAKATI" in merchants
        assert "GRAB RIDE" in merchants


class TestBDOParser:
    """Tests for BDO CSV parser."""

    @pytest.fixture
    def parser(self):
        """Create BDO parser."""
        return BDOParser()

    @pytest.fixture
    def sample_csv(self):
        """Sample BDO CSV content."""
        return """Date,Transaction Description,Amount,Running Balance
15-Jan-2025,POS PURCHASE - SM SUPERMARKET,-1500.00,48500.00
14-Jan-2025,PAYMENT RECEIVED,10000.00,50000.00
13-Jan-2025,ATM WITHDRAWAL,-5000.00,40000.00
"""

    def test_can_parse_correct_format(self, parser, sample_csv):
        """Test parser recognizes BDO format."""
        assert parser.can_parse(sample_csv) is True

    def test_parse_transactions(self, parser, sample_csv):
        """Test parsing BDO transactions."""
        result = parser.parse(sample_csv)

        assert result.success is True
        assert len(result.transactions) == 3
        assert result.bank_name == "bdo"

        # Check first transaction (expense - negative amount)
        txn = result.transactions[0]
        assert txn.date.day == 15
        assert txn.date.month == 1
        assert txn.amount == Decimal("1500.00")  # Converted to positive
        assert "SM SUPERMARKET" in txn.description


class TestGCashParser:
    """Tests for GCash CSV parser."""

    @pytest.fixture
    def parser(self):
        """Create GCash parser."""
        return GCashParser()

    @pytest.fixture
    def sample_csv(self):
        """Sample GCash CSV content."""
        return """Date & Time,Type,Amount,Fee,Reference No.,Status,Description
2025-01-15 14:30:00,Send Money,-500.00,0.00,GC123456,SUCCESS,Transfer to Juan
2025-01-14 10:00:00,Cash In,1000.00,0.00,GC789012,SUCCESS,Bank Transfer
2025-01-13 18:45:00,Pay Bills,-1500.00,0.00,GC345678,SUCCESS,MERALCO Payment
"""

    def test_can_parse_correct_format(self, parser, sample_csv):
        """Test parser recognizes GCash format."""
        assert parser.can_parse(sample_csv) is True

    def test_parse_transactions(self, parser, sample_csv):
        """Test parsing GCash transactions."""
        result = parser.parse(sample_csv)

        assert result.success is True
        assert len(result.transactions) == 3
        assert result.bank_name == "gcash"

        # Check first transaction
        txn = result.transactions[0]
        assert txn.amount == Decimal("500.00")
        assert txn.transaction_type == "expense"
        assert txn.reference == "GC123456"

    def test_transaction_type_detection(self, parser, sample_csv):
        """Test expense vs income detection."""
        result = parser.parse(sample_csv)

        types = [t.transaction_type for t in result.transactions]
        assert types[0] == "expense"  # Send Money
        assert types[1] == "income"   # Cash In
        assert types[2] == "expense"  # Pay Bills


class TestGenericParser:
    """Tests for Generic CSV parser with auto-detection."""

    @pytest.fixture
    def parser(self):
        """Create Generic parser."""
        return GenericParser()

    def test_auto_detect_date_column(self, parser):
        """Test automatic date column detection."""
        csv_content = """Transaction Date,Amount,Notes
2025-01-15,500,Test purchase
2025-01-14,1000,Another purchase
"""
        result = parser.parse(csv_content)
        assert result.success is True
        assert len(result.transactions) == 2

    def test_auto_detect_amount_column(self, parser):
        """Test automatic amount column detection."""
        csv_content = """Date,Debit Amount,Description
2025-01-15,500.00,Test
"""
        result = parser.parse(csv_content)
        assert result.transactions[0].amount == Decimal("500.00")

    def test_detect_and_parse_function(self):
        """Test the detect_and_parse convenience function."""
        unionbank_csv = """Transaction Date,Posting Date,Description,Reference Number,Debit,Credit,Balance
01/15/2025,01/16/2025,TEST,123,100.00,,900.00
"""
        result = detect_and_parse(unionbank_csv)

        assert result.success is True
        assert result.bank_name == "unionbank"


class TestMerchantLookup:
    """Tests for MerchantLookup class."""

    @pytest.fixture
    def lookup(self, tmp_path):
        """Create merchant lookup with test config."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        mappings_file = config_dir / "merchant_mappings.json"
        mappings_file.write_text(json.dumps({
            "exact_matches": {
                "JOLLIBEE": {
                    "account_code": "6110",
                    "account_name": "Meals & Entertainment",
                    "category": "expense"
                },
                "GRAB": {
                    "account_code": "6120",
                    "account_name": "Transportation",
                    "category": "expense"
                }
            },
            "pattern_matches": [
                {
                    "pattern": "^SM\\s",
                    "account_code": "6100",
                    "account_name": "Office Supplies",
                    "category": "expense"
                },
                {
                    "pattern": "HOTEL|RESORT",
                    "account_code": "6130",
                    "account_name": "Travel & Accommodation",
                    "category": "expense"
                }
            ]
        }))

        return MerchantLookup(config_dir)

    def test_exact_match(self, lookup):
        """Test exact merchant name matching."""
        match = lookup.find("JOLLIBEE")

        assert match is not None
        assert match.account_code == "6110"
        assert match.account_name == "Meals & Entertainment"
        assert match.confidence == 1.0
        assert match.match_type == "exact"

    def test_exact_match_case_insensitive(self, lookup):
        """Test case-insensitive matching."""
        match = lookup.find("jollibee")

        assert match is not None
        assert match.account_code == "6110"

    def test_pattern_match(self, lookup):
        """Test regex pattern matching."""
        match = lookup.find("SM SUPERMARKET MAKATI")

        assert match is not None
        assert match.account_code == "6100"
        assert match.match_type == "pattern"

    def test_pattern_match_anywhere(self, lookup):
        """Test pattern matching anywhere in string."""
        match = lookup.find("MANILA HOTEL AND RESORT")

        assert match is not None
        assert match.account_code == "6130"

    def test_no_match(self, lookup):
        """Test when no match is found."""
        match = lookup.find("UNKNOWN MERCHANT XYZ")

        assert match is None

    def test_partial_merchant_in_description(self, lookup):
        """Test extracting merchant from longer description."""
        match = lookup.find("PURCHASE - GRAB TAXI MANILA")

        assert match is not None
        assert match.account_code == "6120"


class TestDuplicateDetector:
    """Tests for DuplicateDetector class."""

    @pytest.fixture
    def detector(self):
        """Create duplicate detector."""
        return DuplicateDetector()

    @pytest.fixture
    def existing_transactions(self):
        """Sample existing transactions."""
        return [
            {
                "id": "txn-001",
                "txn_date": "2025-01-15",
                "amount": 500.00,
                "merchant": "JOLLIBEE MAKATI",
                "description": "PURCHASE - JOLLIBEE MAKATI"
            },
            {
                "id": "txn-002",
                "txn_date": "2025-01-14",
                "amount": 1000.00,
                "merchant": "GRAB",
                "description": "GRAB RIDE"
            },
        ]

    def test_detect_exact_duplicate(self, detector, existing_transactions):
        """Test detection of exact duplicate."""
        new_txn = ParsedTransaction(
            date=datetime(2025, 1, 15),
            amount=Decimal("500.00"),
            merchant="JOLLIBEE MAKATI",
            description="PURCHASE - JOLLIBEE MAKATI"
        )

        match = detector.check(new_txn, existing_transactions)

        assert match is not None
        assert match.is_duplicate is True
        assert match.confidence >= 0.95
        assert match.existing_id == "txn-001"

    def test_no_duplicate(self, detector, existing_transactions):
        """Test when no duplicate exists."""
        new_txn = ParsedTransaction(
            date=datetime(2025, 1, 16),
            amount=Decimal("2000.00"),
            merchant="NEW MERCHANT",
            description="COMPLETELY NEW TRANSACTION"
        )

        match = detector.check(new_txn, existing_transactions)

        assert match is None or match.is_duplicate is False

    def test_fuzzy_match_similar_description(self, detector, existing_transactions):
        """Test fuzzy matching for similar descriptions."""
        new_txn = ParsedTransaction(
            date=datetime(2025, 1, 15),
            amount=Decimal("500.00"),
            merchant="JOLLIBEE",
            description="JOLLIBEE MAKATI BRANCH"  # Slightly different
        )

        match = detector.check(new_txn, existing_transactions)

        assert match is not None
        assert match.is_duplicate is True

    def test_same_amount_different_date(self, detector, existing_transactions):
        """Test that same amount on different date is not duplicate."""
        new_txn = ParsedTransaction(
            date=datetime(2025, 1, 20),  # Different date
            amount=Decimal("500.00"),
            merchant="DIFFERENT MERCHANT",
            description="DIFFERENT PURCHASE"
        )

        match = detector.check(new_txn, existing_transactions)

        assert match is None or match.is_duplicate is False

    def test_batch_check(self, detector, existing_transactions):
        """Test batch duplicate checking."""
        new_txns = [
            ParsedTransaction(
                date=datetime(2025, 1, 15),
                amount=Decimal("500.00"),
                merchant="JOLLIBEE MAKATI",
                description="PURCHASE - JOLLIBEE MAKATI"
            ),
            ParsedTransaction(
                date=datetime(2025, 1, 16),
                amount=Decimal("750.00"),
                merchant="NEW PLACE",
                description="NEW TRANSACTION"
            ),
        ]

        results = detector.check_batch(new_txns, existing_transactions)

        assert len(results) == 2
        assert results[0].is_duplicate is True
        assert results[1] is None or results[1].is_duplicate is False


class TestTransactionCategorizer:
    """Tests for TransactionCategorizer class."""

    @pytest.fixture
    def mock_anthropic(self):
        """Create mock Anthropic client."""
        with patch("card_processor.categorizer.anthropic") as mock:
            mock_client = Mock()
            mock.Anthropic.return_value = mock_client

            mock_response = Mock()
            mock_response.content = [Mock(text='''
[
    {
        "account_code": "6110",
        "account_name": "Meals & Entertainment",
        "category": "expense",
        "confidence": 0.85,
        "anomaly": false
    }
]
''')]
            mock_client.messages.create.return_value = mock_response

            yield mock

    @pytest.fixture
    def categorizer(self, tmp_path, mock_anthropic):
        """Create categorizer with test config."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        # Create merchant mappings
        mappings_file = config_dir / "merchant_mappings.json"
        mappings_file.write_text(json.dumps({
            "exact_matches": {
                "JOLLIBEE": {
                    "account_code": "6110",
                    "account_name": "Meals & Entertainment",
                    "category": "expense"
                }
            },
            "pattern_matches": []
        }))

        # Create chart of accounts
        coa_file = config_dir / "chart_of_accounts.yaml"
        coa_file.write_text("""
expense:
  - code: "6100"
    name: "Office Supplies"
  - code: "6110"
    name: "Meals & Entertainment"
  - code: "6120"
    name: "Transportation"
""")

        return TransactionCategorizer(config_dir, api_key="test-key")

    def test_categorize_with_lookup(self, categorizer):
        """Test categorization using merchant lookup."""
        txn = ParsedTransaction(
            date=datetime(2025, 1, 15),
            amount=Decimal("500.00"),
            merchant="JOLLIBEE",
            description="JOLLIBEE MAKATI"
        )

        result = categorizer.categorize(txn, entity="solaire")

        assert isinstance(result, CategorizedTransaction)
        assert result.account_code == "6110"
        assert result.account_name == "Meals & Entertainment"
        assert result.classification_method == "lookup"
        assert result.confidence >= 0.9

    def test_categorize_with_claude(self, categorizer):
        """Test categorization falling back to Claude."""
        txn = ParsedTransaction(
            date=datetime(2025, 1, 15),
            amount=Decimal("1500.00"),
            merchant="UNKNOWN MERCHANT",
            description="MYSTERY PURCHASE"
        )

        result = categorizer.categorize(txn, entity="solaire")

        assert isinstance(result, CategorizedTransaction)
        assert result.classification_method == "claude"

    def test_batch_categorize(self, categorizer):
        """Test batch categorization."""
        txns = [
            ParsedTransaction(
                date=datetime(2025, 1, 15),
                amount=Decimal("500.00"),
                merchant="JOLLIBEE",
                description="JOLLIBEE MAKATI"
            ),
            ParsedTransaction(
                date=datetime(2025, 1, 16),
                amount=Decimal("1500.00"),
                merchant="UNKNOWN",
                description="UNKNOWN PURCHASE"
            ),
        ]

        results = categorizer.categorize_batch(txns, entity="solaire")

        assert len(results) == 2
        assert results[0].classification_method == "lookup"


class TestParseResult:
    """Tests for ParseResult dataclass."""

    def test_successful_result(self):
        """Test successful parse result."""
        txns = [
            ParsedTransaction(date=datetime(2025, 1, 15), amount=Decimal("100")),
            ParsedTransaction(date=datetime(2025, 1, 16), amount=Decimal("200")),
        ]

        result = ParseResult(
            success=True,
            transactions=txns,
            bank_name="unionbank",
            errors=[]
        )

        assert result.success is True
        assert len(result.transactions) == 2
        assert result.bank_name == "unionbank"
        assert len(result.errors) == 0

    def test_failed_result(self):
        """Test failed parse result."""
        result = ParseResult(
            success=False,
            transactions=[],
            bank_name="unknown",
            errors=["Invalid format", "Missing required columns"]
        )

        assert result.success is False
        assert len(result.transactions) == 0
        assert len(result.errors) == 2

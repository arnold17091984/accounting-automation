"""
Credit Card Processor Module

Handles CSV/PDF parsing, Claude-based categorization, and duplicate detection
for credit card statements.
"""

from .categorizer import TransactionCategorizer, Classification, CategorizationResult
from .duplicate_detector import DuplicateDetector, DuplicateMatch, DeduplicationResult
from .merchant_lookup import MerchantLookup, MerchantMatch
from .pdf_extractor import PDFExtractor, PDFExtractionResult
from .csv_parsers import (
    ParsedTransaction,
    ParseResult,
    UnionBankParser,
    BDOParser,
    GCashParser,
    GenericParser,
    detect_and_parse,
)

__all__ = [
    # Categorization
    "TransactionCategorizer",
    "Classification",
    "CategorizationResult",
    # Duplicate Detection
    "DuplicateDetector",
    "DuplicateMatch",
    "DeduplicationResult",
    # Merchant Lookup
    "MerchantLookup",
    "MerchantMatch",
    # PDF Extraction
    "PDFExtractor",
    "PDFExtractionResult",
    # CSV Parsing
    "ParsedTransaction",
    "ParseResult",
    "UnionBankParser",
    "BDOParser",
    "GCashParser",
    "GenericParser",
    "detect_and_parse",
]

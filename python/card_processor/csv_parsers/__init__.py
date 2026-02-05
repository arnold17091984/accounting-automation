"""
Bank-specific CSV parsers for credit card statements.
"""

from .base import BaseCSVParser, ParsedTransaction, ParseResult
from .unionbank import UnionBankParser
from .bdo import BDOParser
from .gcash import GCashParser
from .generic import GenericParser, detect_and_parse

__all__ = [
    "BaseCSVParser",
    "ParsedTransaction",
    "ParseResult",
    "UnionBankParser",
    "BDOParser",
    "GCashParser",
    "GenericParser",
    "detect_and_parse",
]

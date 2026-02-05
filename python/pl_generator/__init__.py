"""
P&L Generator Module

Generates Excel and PowerPoint P&L reports for all 6 entities.
"""

from .excel_builder import PLExcelBuilder
from .pptx_builder import PLPowerPointBuilder
from .consolidation import ConsolidationEngine

__all__ = ["PLExcelBuilder", "PLPowerPointBuilder", "ConsolidationEngine"]

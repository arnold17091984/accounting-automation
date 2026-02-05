"""
Budget Management Module

Handles budget variance calculation, threshold checking, and Claude-based
budget suggestions.
"""

from .variance_calculator import VarianceCalculator, VarianceItem, VarianceReport
from .threshold_checker import ThresholdChecker, ThresholdAlert, ThresholdCheckResult
from .historical_analyzer import HistoricalAnalyzer, BudgetSuggestion, BudgetAnalysisResult
from .report_generator import BudgetReportGenerator

__all__ = [
    # Variance Calculation
    "VarianceCalculator",
    "VarianceItem",
    "VarianceReport",
    # Threshold Checking
    "ThresholdChecker",
    "ThresholdAlert",
    "ThresholdCheckResult",
    # Historical Analysis
    "HistoricalAnalyzer",
    "BudgetSuggestion",
    "BudgetAnalysisResult",
    # Reporting
    "BudgetReportGenerator",
]

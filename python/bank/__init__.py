"""
Bank Integration Module

Handles bank transfers, reconciliation, and RPA fallback for portal automation.
"""

from .ub_template_generator import (
    UnionBankTemplateGenerator,
    PayrollEntry,
    TransferBatch,
    TransferTemplate,
)
from .reconciliation import (
    BankReconciliation,
    ReconciliationResult,
    MatchedTransaction,
    UnmatchedItem,
)
from .rpa_fallback import (
    BankPortalAutomation,
    RPAResult,
    RPAAction,
)

__all__ = [
    # UnionBank Templates
    "UnionBankTemplateGenerator",
    "PayrollEntry",
    "TransferBatch",
    "TransferTemplate",
    # Reconciliation
    "BankReconciliation",
    "ReconciliationResult",
    "MatchedTransaction",
    "UnmatchedItem",
    # RPA
    "BankPortalAutomation",
    "RPAResult",
    "RPAAction",
]

"""
Tax Support Module

Handles Philippine BIR tax calculations, withholding computations,
and tax form generation.
"""

from .bir_calculator import (
    BIRCalculator,
    TaxComputation,
    VATComputation,
    WithholdingComputation,
    CompensationTax,
)
from .form_generator import (
    TaxFormGenerator,
    FormData,
    GeneratedForm,
)

__all__ = [
    # BIR Calculator
    "BIRCalculator",
    "TaxComputation",
    "VATComputation",
    "WithholdingComputation",
    "CompensationTax",
    # Form Generator
    "TaxFormGenerator",
    "FormData",
    "GeneratedForm",
]

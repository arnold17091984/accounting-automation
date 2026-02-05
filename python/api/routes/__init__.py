"""
API Routes Package

Contains all route modules for the dashboard API.
"""

from .dashboard import router as dashboard_router
from .budget import router as budget_router
from .transactions import router as transactions_router
from .approvals import router as approvals_router
from .fund_requests import router as fund_requests_router

__all__ = [
    "dashboard_router",
    "budget_router",
    "transactions_router",
    "approvals_router",
    "fund_requests_router",
]

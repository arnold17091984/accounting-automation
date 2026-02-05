"""
Dashboard API Routes

Provides endpoints for the main dashboard view.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from ..auth import User, get_current_user
from ..database import execute_query

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class KPIData(BaseModel):
    """KPI card data."""

    label: str
    value: float
    formatted_value: str
    change_percent: float | None = None
    change_direction: str | None = None  # 'up', 'down', 'neutral'


class BudgetStatus(BaseModel):
    """Budget status for an entity."""

    entity: str
    entity_name: str
    utilization_percent: float
    status: str  # 'ok', 'warning', 'critical', 'exceeded'
    budget_total: float
    actual_total: float


class AlertItem(BaseModel):
    """Alert notification item."""

    id: int
    entity: str
    message: str
    severity: str  # 'info', 'warning', 'critical'
    created_at: datetime


class DashboardSummary(BaseModel):
    """Complete dashboard summary response."""

    period: str
    kpis: list[KPIData]
    budget_status: list[BudgetStatus]
    recent_alerts: list[AlertItem]
    pending_approvals_count: int
    pending_approvals_total: float


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    entity: str | None = Query(None, description="Filter by entity (None for all)"),
    user: User = Depends(get_current_user),
) -> DashboardSummary:
    """Get dashboard summary with KPIs, budget status, and alerts.

    Args:
        entity: Optional entity filter
        user: Authenticated user

    Returns:
        DashboardSummary
    """
    now = datetime.now()
    current_month = now.strftime("%Y-%m")
    period_label = now.strftime("%B %Y")

    # Entity filter clause
    entity_clause = f"AND entity = '{entity}'" if entity else ""

    # Get revenue KPI
    revenue_query = f"""
        SELECT COALESCE(SUM(amount), 0) as total
        FROM transactions
        WHERE category = 'revenue'
        AND DATE_TRUNC('month', txn_date) = DATE_TRUNC('month', CURRENT_DATE)
        {entity_clause}
    """
    revenue_result = execute_query(revenue_query)
    revenue_total = float(revenue_result[0]["total"]) if revenue_result else 0

    # Get previous month revenue for comparison
    prev_revenue_query = f"""
        SELECT COALESCE(SUM(amount), 0) as total
        FROM transactions
        WHERE category = 'revenue'
        AND DATE_TRUNC('month', txn_date) = DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
        {entity_clause}
    """
    prev_revenue_result = execute_query(prev_revenue_query)
    prev_revenue = float(prev_revenue_result[0]["total"]) if prev_revenue_result else 0

    revenue_change = ((revenue_total - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0

    # Get expense KPI
    expense_query = f"""
        SELECT COALESCE(SUM(amount), 0) as total
        FROM transactions
        WHERE category IN ('expense', 'salary', 'commission', 'company_car', 'cos', 'bank_charge')
        AND DATE_TRUNC('month', txn_date) = DATE_TRUNC('month', CURRENT_DATE)
        {entity_clause}
    """
    expense_result = execute_query(expense_query)
    expense_total = float(expense_result[0]["total"]) if expense_result else 0

    # Previous month expense
    prev_expense_query = f"""
        SELECT COALESCE(SUM(amount), 0) as total
        FROM transactions
        WHERE category IN ('expense', 'salary', 'commission', 'company_car', 'cos', 'bank_charge')
        AND DATE_TRUNC('month', txn_date) = DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
        {entity_clause}
    """
    prev_expense_result = execute_query(prev_expense_query)
    prev_expense = float(prev_expense_result[0]["total"]) if prev_expense_result else 0

    expense_change = ((expense_total - prev_expense) / prev_expense * 100) if prev_expense > 0 else 0

    # Calculate profit
    profit_total = revenue_total - expense_total
    prev_profit = prev_revenue - prev_expense
    profit_change = ((profit_total - prev_profit) / abs(prev_profit) * 100) if prev_profit != 0 else 0

    # Get pending approvals
    approvals_query = f"""
        SELECT COUNT(*) as count, COALESCE(SUM(amount), 0) as total
        FROM approval_log
        WHERE status = 'pending'
        {entity_clause}
    """
    approvals_result = execute_query(approvals_query)
    pending_count = int(approvals_result[0]["count"]) if approvals_result else 0
    pending_total = float(approvals_result[0]["total"]) if approvals_result else 0

    # Build KPIs
    kpis = [
        KPIData(
            label="Revenue",
            value=revenue_total,
            formatted_value=f"₱{revenue_total:,.0f}",
            change_percent=round(revenue_change, 1),
            change_direction="up" if revenue_change > 0 else "down" if revenue_change < 0 else "neutral",
        ),
        KPIData(
            label="Expenses",
            value=expense_total,
            formatted_value=f"₱{expense_total:,.0f}",
            change_percent=round(expense_change, 1),
            change_direction="up" if expense_change > 0 else "down" if expense_change < 0 else "neutral",
        ),
        KPIData(
            label="Profit",
            value=profit_total,
            formatted_value=f"₱{profit_total:,.0f}",
            change_percent=round(profit_change, 1),
            change_direction="up" if profit_change > 0 else "down" if profit_change < 0 else "neutral",
        ),
        KPIData(
            label="Pending Approvals",
            value=pending_count,
            formatted_value=f"{pending_count} items",
            change_percent=None,
            change_direction=None,
        ),
    ]

    # Get budget status by entity
    budget_query = """
        SELECT
            entity,
            SUM(budget_amount) as budget_total,
            0 as actual_total
        FROM budgets
        WHERE year = EXTRACT(YEAR FROM CURRENT_DATE)
        AND month = EXTRACT(MONTH FROM CURRENT_DATE)
        GROUP BY entity
    """
    budget_results = execute_query(budget_query)

    entity_names = {
        "solaire": "Solaire",
        "cod": "COD",
        "royce": "Royce Clark",
        "manila_junket": "Manila Junket",
        "tours": "Tours BGC/BSM",
        "midori": "Midori no Mart",
    }

    budget_status = []
    for row in budget_results:
        ent = row["entity"]

        # Get actual spending for this entity
        actual_query = f"""
            SELECT COALESCE(SUM(amount), 0) as total
            FROM transactions
            WHERE entity = '{ent}'
            AND DATE_TRUNC('month', txn_date) = DATE_TRUNC('month', CURRENT_DATE)
            AND category IN ('expense', 'salary', 'commission', 'company_car', 'cos', 'bank_charge')
        """
        actual_result = execute_query(actual_query)
        actual = float(actual_result[0]["total"]) if actual_result else 0
        budget = float(row["budget_total"])

        utilization = (actual / budget * 100) if budget > 0 else 0

        if utilization >= 100:
            status = "exceeded"
        elif utilization >= 90:
            status = "critical"
        elif utilization >= 70:
            status = "warning"
        else:
            status = "ok"

        budget_status.append(BudgetStatus(
            entity=ent,
            entity_name=entity_names.get(ent, ent.title()),
            utilization_percent=round(utilization, 1),
            status=status,
            budget_total=budget,
            actual_total=actual,
        ))

    # Get recent alerts
    alerts_query = f"""
        SELECT
            id,
            entity,
            CONCAT('Budget ', account_name, ' reached ', threshold_pct, '%') as message,
            CASE
                WHEN threshold_pct >= 100 THEN 'critical'
                WHEN threshold_pct >= 90 THEN 'warning'
                ELSE 'info'
            END as severity,
            sent_at as created_at
        FROM budget_alerts
        WHERE acknowledged = FALSE
        {entity_clause}
        ORDER BY sent_at DESC
        LIMIT 5
    """
    alerts_results = execute_query(alerts_query)

    recent_alerts = [
        AlertItem(
            id=row["id"],
            entity=row["entity"],
            message=row["message"],
            severity=row["severity"],
            created_at=row["created_at"],
        )
        for row in alerts_results
    ]

    return DashboardSummary(
        period=period_label,
        kpis=kpis,
        budget_status=budget_status,
        recent_alerts=recent_alerts,
        pending_approvals_count=pending_count,
        pending_approvals_total=pending_total,
    )


@router.get("/entities")
async def get_entities(
    user: User = Depends(get_current_user),
) -> list[dict[str, str]]:
    """Get list of all entities.

    Returns:
        List of entity objects with code and name
    """
    entities = [
        {"code": "solaire", "name": "Solaire"},
        {"code": "cod", "name": "COD"},
        {"code": "royce", "name": "Royce Clark"},
        {"code": "manila_junket", "name": "Manila Junket"},
        {"code": "tours", "name": "Tours BGC/BSM"},
        {"code": "midori", "name": "Midori no Mart"},
    ]

    return entities

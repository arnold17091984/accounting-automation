"""
Budget API Routes

Provides endpoints for budget management and variance reporting.
"""

from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..auth import User, get_current_user, require_permission
from ..database import execute_query

router = APIRouter(prefix="/budget", tags=["budget"])


class BudgetItem(BaseModel):
    """Single budget line item."""

    account_code: str
    account_name: str
    category: str
    budget_amount: float
    actual_amount: float
    variance_amount: float
    variance_percent: float
    utilization_percent: float
    status: str  # 'ok', 'warning', 'critical', 'exceeded'


class BudgetSummary(BaseModel):
    """Budget summary for a period."""

    entity: str
    entity_name: str
    period: str
    total_budget: float
    total_actual: float
    total_variance: float
    overall_utilization: float
    items: list[BudgetItem]


class BudgetUpdateRequest(BaseModel):
    """Request to update budget amount."""

    account_code: str
    new_amount: float
    notes: str | None = None


@router.get("/{entity}/{period}", response_model=BudgetSummary)
async def get_budget_variance(
    entity: str,
    period: str,  # YYYY-MM format
    user: User = Depends(get_current_user),
) -> BudgetSummary:
    """Get budget vs actual variance for an entity and period.

    Args:
        entity: Entity code
        period: Period in YYYY-MM format
        user: Authenticated user

    Returns:
        BudgetSummary with all budget items
    """
    # Parse period
    try:
        year, month = map(int, period.split("-"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid period format. Use YYYY-MM")

    entity_names = {
        "solaire": "Solaire",
        "cod": "COD",
        "royce": "Royce Clark",
        "manila_junket": "Manila Junket",
        "tours": "Tours BGC/BSM",
        "midori": "Midori no Mart",
    }

    # Get budget data
    budget_query = """
        SELECT
            account_code,
            account_name,
            category,
            budget_amount
        FROM budgets
        WHERE entity = :entity
        AND year = :year
        AND month = :month
        ORDER BY account_code
    """
    budget_results = execute_query(budget_query, {
        "entity": entity,
        "year": year,
        "month": month,
    })

    # Get actual spending per account
    actual_query = """
        SELECT
            account_code,
            COALESCE(SUM(amount), 0) as actual_amount
        FROM transactions
        WHERE entity = :entity
        AND EXTRACT(YEAR FROM txn_date) = :year
        AND EXTRACT(MONTH FROM txn_date) = :month
        GROUP BY account_code
    """
    actual_results = execute_query(actual_query, {
        "entity": entity,
        "year": year,
        "month": month,
    })

    # Index actuals by account_code
    actual_by_account = {r["account_code"]: float(r["actual_amount"]) for r in actual_results}

    # Build budget items
    items = []
    total_budget = 0.0
    total_actual = 0.0

    for row in budget_results:
        budget = float(row["budget_amount"])
        actual = actual_by_account.get(row["account_code"], 0.0)
        variance = budget - actual
        variance_pct = ((actual - budget) / budget * 100) if budget > 0 else 0
        utilization = (actual / budget * 100) if budget > 0 else 0

        if utilization >= 100:
            status = "exceeded"
        elif utilization >= 90:
            status = "critical"
        elif utilization >= 70:
            status = "warning"
        else:
            status = "ok"

        items.append(BudgetItem(
            account_code=row["account_code"],
            account_name=row["account_name"],
            category=row["category"],
            budget_amount=budget,
            actual_amount=actual,
            variance_amount=variance,
            variance_percent=round(variance_pct, 2),
            utilization_percent=round(utilization, 2),
            status=status,
        ))

        total_budget += budget
        total_actual += actual

    total_variance = total_budget - total_actual
    overall_utilization = (total_actual / total_budget * 100) if total_budget > 0 else 0

    period_label = datetime(year, month, 1).strftime("%B %Y")

    return BudgetSummary(
        entity=entity,
        entity_name=entity_names.get(entity, entity.title()),
        period=period_label,
        total_budget=total_budget,
        total_actual=total_actual,
        total_variance=total_variance,
        overall_utilization=round(overall_utilization, 2),
        items=items,
    )


@router.get("/alerts")
async def get_budget_alerts(
    entity: str | None = Query(None),
    acknowledged: bool | None = Query(None),
    limit: int = Query(20, le=100),
    user: User = Depends(get_current_user),
) -> list[dict]:
    """Get budget alerts.

    Args:
        entity: Optional entity filter
        acknowledged: Optional filter by acknowledged status
        limit: Maximum results
        user: Authenticated user

    Returns:
        List of budget alerts
    """
    conditions = []
    params = {"limit": limit}

    if entity:
        conditions.append("entity = :entity")
        params["entity"] = entity

    if acknowledged is not None:
        conditions.append("acknowledged = :acknowledged")
        params["acknowledged"] = acknowledged

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    query = f"""
        SELECT
            id,
            entity,
            account_code,
            account_name,
            year,
            month,
            threshold_pct,
            actual_amount,
            budget_amount,
            actual_pct,
            acknowledged,
            acknowledged_by,
            acknowledged_at,
            sent_at
        FROM budget_alerts
        {where_clause}
        ORDER BY sent_at DESC
        LIMIT :limit
    """

    results = execute_query(query, params)
    return results


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    user: User = Depends(require_permission("approve")),
) -> dict:
    """Acknowledge a budget alert.

    Args:
        alert_id: Alert ID
        user: Authenticated user with approve permission

    Returns:
        Success message
    """
    query = """
        UPDATE budget_alerts
        SET acknowledged = TRUE,
            acknowledged_by = :user_id,
            acknowledged_at = NOW()
        WHERE id = :alert_id
        RETURNING id
    """

    result = execute_query(query, {
        "alert_id": alert_id,
        "user_id": user.telegram_id,
    })

    if not result:
        raise HTTPException(status_code=404, detail="Alert not found")

    return {"message": "Alert acknowledged", "alert_id": alert_id}


@router.put("/{entity}/{period}")
async def update_budget(
    entity: str,
    period: str,
    request: BudgetUpdateRequest,
    user: User = Depends(require_permission("budget_edit")),
) -> dict:
    """Update a budget amount.

    Args:
        entity: Entity code
        period: Period in YYYY-MM format
        request: Budget update request
        user: Authenticated user with budget_edit permission

    Returns:
        Success message
    """
    try:
        year, month = map(int, period.split("-"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid period format. Use YYYY-MM")

    query = """
        UPDATE budgets
        SET budget_amount = :new_amount,
            notes = COALESCE(:notes, notes),
            updated_at = NOW()
        WHERE entity = :entity
        AND account_code = :account_code
        AND year = :year
        AND month = :month
        RETURNING id
    """

    result = execute_query(query, {
        "entity": entity,
        "account_code": request.account_code,
        "year": year,
        "month": month,
        "new_amount": request.new_amount,
        "notes": request.notes,
    })

    if not result:
        raise HTTPException(status_code=404, detail="Budget entry not found")

    return {
        "message": "Budget updated",
        "entity": entity,
        "account_code": request.account_code,
        "new_amount": request.new_amount,
    }

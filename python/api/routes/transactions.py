"""
Transactions API Routes

Provides endpoints for viewing and managing transactions.
"""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..auth import User, get_current_user
from ..database import execute_query

router = APIRouter(prefix="/transactions", tags=["transactions"])


class Transaction(BaseModel):
    """Transaction model."""

    id: str
    source: str
    source_bank: str | None
    entity: str
    txn_date: date
    description: str | None
    merchant: str | None
    amount: float
    currency: str
    account_code: str | None
    account_name: str | None
    category: str | None
    classification_method: str | None
    classification_confidence: float | None
    approved: bool
    approved_by: str | None
    anomaly_flag: bool
    anomaly_reason: str | None
    created_at: datetime


class TransactionListResponse(BaseModel):
    """Paginated transaction list response."""

    items: list[Transaction]
    total: int
    page: int
    page_size: int
    total_pages: int


class TransactionStats(BaseModel):
    """Transaction statistics."""

    total_count: int
    total_amount: float
    by_category: dict[str, float]
    by_source: dict[str, int]
    pending_approval_count: int
    anomaly_count: int


@router.get("", response_model=TransactionListResponse)
async def list_transactions(
    entity: str | None = Query(None),
    source: str | None = Query(None),
    category: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    approved: bool | None = Query(None),
    anomaly_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    user: User = Depends(get_current_user),
) -> TransactionListResponse:
    """List transactions with filters and pagination.

    Args:
        entity: Filter by entity
        source: Filter by source (credit_card, game_record, etc.)
        category: Filter by category
        start_date: Filter by start date
        end_date: Filter by end date
        approved: Filter by approval status
        anomaly_only: Only show anomalies
        page: Page number
        page_size: Items per page
        user: Authenticated user

    Returns:
        Paginated list of transactions
    """
    conditions = []
    params = {}

    if entity:
        conditions.append("entity = :entity")
        params["entity"] = entity

    if source:
        conditions.append("source = :source")
        params["source"] = source

    if category:
        conditions.append("category = :category")
        params["category"] = category

    if start_date:
        conditions.append("txn_date >= :start_date")
        params["start_date"] = start_date

    if end_date:
        conditions.append("txn_date <= :end_date")
        params["end_date"] = end_date

    if approved is not None:
        conditions.append("approved = :approved")
        params["approved"] = approved

    if anomaly_only:
        conditions.append("anomaly_flag = TRUE")

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    # Get total count
    count_query = f"""
        SELECT COUNT(*) as total
        FROM transactions
        {where_clause}
    """
    count_result = execute_query(count_query, params)
    total = count_result[0]["total"] if count_result else 0

    # Calculate pagination
    offset = (page - 1) * page_size
    total_pages = (total + page_size - 1) // page_size

    # Get transactions
    params["limit"] = page_size
    params["offset"] = offset

    query = f"""
        SELECT
            id::text,
            source,
            source_bank,
            entity,
            txn_date,
            description,
            merchant,
            amount,
            currency,
            account_code,
            account_name,
            category,
            classification_method,
            classification_confidence,
            approved,
            approved_by,
            anomaly_flag,
            anomaly_reason,
            created_at
        FROM transactions
        {where_clause}
        ORDER BY txn_date DESC, created_at DESC
        LIMIT :limit OFFSET :offset
    """

    results = execute_query(query, params)

    items = [
        Transaction(
            id=row["id"],
            source=row["source"],
            source_bank=row["source_bank"],
            entity=row["entity"],
            txn_date=row["txn_date"],
            description=row["description"],
            merchant=row["merchant"],
            amount=float(row["amount"]),
            currency=row["currency"],
            account_code=row["account_code"],
            account_name=row["account_name"],
            category=row["category"],
            classification_method=row["classification_method"],
            classification_confidence=float(row["classification_confidence"]) if row["classification_confidence"] else None,
            approved=row["approved"],
            approved_by=row["approved_by"],
            anomaly_flag=row["anomaly_flag"],
            anomaly_reason=row["anomaly_reason"],
            created_at=row["created_at"],
        )
        for row in results
    ]

    return TransactionListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/stats", response_model=TransactionStats)
async def get_transaction_stats(
    entity: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    user: User = Depends(get_current_user),
) -> TransactionStats:
    """Get transaction statistics.

    Args:
        entity: Filter by entity
        start_date: Filter by start date
        end_date: Filter by end date
        user: Authenticated user

    Returns:
        Transaction statistics
    """
    conditions = []
    params = {}

    if entity:
        conditions.append("entity = :entity")
        params["entity"] = entity

    if start_date:
        conditions.append("txn_date >= :start_date")
        params["start_date"] = start_date

    if end_date:
        conditions.append("txn_date <= :end_date")
        params["end_date"] = end_date

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    # Total count and amount
    total_query = f"""
        SELECT
            COUNT(*) as total_count,
            COALESCE(SUM(amount), 0) as total_amount
        FROM transactions
        {where_clause}
    """
    total_result = execute_query(total_query, params)
    total_count = total_result[0]["total_count"] if total_result else 0
    total_amount = float(total_result[0]["total_amount"]) if total_result else 0

    # By category
    category_query = f"""
        SELECT
            COALESCE(category, 'uncategorized') as category,
            COALESCE(SUM(amount), 0) as amount
        FROM transactions
        {where_clause}
        GROUP BY category
    """
    category_results = execute_query(category_query, params)
    by_category = {row["category"]: float(row["amount"]) for row in category_results}

    # By source
    source_query = f"""
        SELECT
            source,
            COUNT(*) as count
        FROM transactions
        {where_clause}
        GROUP BY source
    """
    source_results = execute_query(source_query, params)
    by_source = {row["source"]: row["count"] for row in source_results}

    # Pending approval count
    pending_clause = where_clause + (" AND " if conditions else "WHERE ") + "approved = FALSE"
    pending_query = f"""
        SELECT COUNT(*) as count
        FROM transactions
        {pending_clause}
    """
    pending_result = execute_query(pending_query, params)
    pending_count = pending_result[0]["count"] if pending_result else 0

    # Anomaly count
    anomaly_clause = where_clause + (" AND " if conditions else "WHERE ") + "anomaly_flag = TRUE"
    anomaly_query = f"""
        SELECT COUNT(*) as count
        FROM transactions
        {anomaly_clause}
    """
    anomaly_result = execute_query(anomaly_query, params)
    anomaly_count = anomaly_result[0]["count"] if anomaly_result else 0

    return TransactionStats(
        total_count=total_count,
        total_amount=total_amount,
        by_category=by_category,
        by_source=by_source,
        pending_approval_count=pending_count,
        anomaly_count=anomaly_count,
    )


@router.get("/{transaction_id}")
async def get_transaction(
    transaction_id: str,
    user: User = Depends(get_current_user),
) -> dict:
    """Get a single transaction by ID.

    Args:
        transaction_id: Transaction UUID
        user: Authenticated user

    Returns:
        Transaction details
    """
    query = """
        SELECT
            id::text,
            source,
            source_bank,
            entity,
            txn_date,
            description,
            merchant,
            amount,
            currency,
            account_code,
            account_name,
            category,
            classification_method,
            classification_confidence,
            qb_journal_id,
            duplicate_flag,
            anomaly_flag,
            anomaly_reason,
            approved,
            approved_by,
            approved_at,
            raw_data,
            created_at,
            updated_at
        FROM transactions
        WHERE id = :id
    """

    results = execute_query(query, {"id": transaction_id})

    if not results:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return results[0]


@router.patch("/{transaction_id}/category")
async def update_transaction_category(
    transaction_id: str,
    account_code: str,
    account_name: str,
    category: str,
    user: User = Depends(get_current_user),
) -> dict:
    """Update transaction category.

    Args:
        transaction_id: Transaction UUID
        account_code: New account code
        account_name: New account name
        category: New category
        user: Authenticated user

    Returns:
        Updated transaction
    """
    query = """
        UPDATE transactions
        SET account_code = :account_code,
            account_name = :account_name,
            category = :category,
            classification_method = 'human',
            classification_confidence = 1.00,
            updated_at = NOW()
        WHERE id = :id
        RETURNING id::text
    """

    result = execute_query(query, {
        "id": transaction_id,
        "account_code": account_code,
        "account_name": account_name,
        "category": category,
    })

    if not result:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return {"message": "Category updated", "transaction_id": transaction_id}

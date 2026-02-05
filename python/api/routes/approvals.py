"""
Approvals API Routes

Provides endpoints for the approval workflow.
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..auth import User, get_current_user, require_permission
from ..database import execute_query

router = APIRouter(prefix="/approvals", tags=["approvals"])


class ApprovalItem(BaseModel):
    """Approval request item."""

    id: int
    request_type: str
    reference_id: str | None
    entity: str | None
    amount: float | None
    description: str | None
    status: str
    requested_by: str | None
    requested_at: datetime
    telegram_msg_id: str | None
    notes: str | None


class ApprovalListResponse(BaseModel):
    """Paginated approval list response."""

    items: list[ApprovalItem]
    total: int
    page: int
    page_size: int


class ApprovalActionRequest(BaseModel):
    """Request to approve or reject."""

    notes: str | None = None


@router.get("/pending", response_model=ApprovalListResponse)
async def get_pending_approvals(
    entity: str | None = Query(None),
    request_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
) -> ApprovalListResponse:
    """Get pending approvals.

    Args:
        entity: Filter by entity
        request_type: Filter by request type
        page: Page number
        page_size: Items per page
        user: Authenticated user

    Returns:
        Paginated list of pending approvals
    """
    conditions = ["status = 'pending'"]
    params = {}

    if entity:
        conditions.append("entity = :entity")
        params["entity"] = entity

    if request_type:
        conditions.append("request_type = :request_type")
        params["request_type"] = request_type

    where_clause = "WHERE " + " AND ".join(conditions)

    # Count total
    count_query = f"""
        SELECT COUNT(*) as total
        FROM approval_log
        {where_clause}
    """
    count_result = execute_query(count_query, params)
    total = count_result[0]["total"] if count_result else 0

    # Get items
    offset = (page - 1) * page_size
    params["limit"] = page_size
    params["offset"] = offset

    query = f"""
        SELECT
            id,
            request_type,
            reference_id::text,
            entity,
            amount,
            description,
            status,
            requested_by,
            requested_at,
            telegram_msg_id,
            notes
        FROM approval_log
        {where_clause}
        ORDER BY requested_at DESC
        LIMIT :limit OFFSET :offset
    """

    results = execute_query(query, params)

    items = [
        ApprovalItem(
            id=row["id"],
            request_type=row["request_type"],
            reference_id=row["reference_id"],
            entity=row["entity"],
            amount=float(row["amount"]) if row["amount"] else None,
            description=row["description"],
            status=row["status"],
            requested_by=row["requested_by"],
            requested_at=row["requested_at"],
            telegram_msg_id=row["telegram_msg_id"],
            notes=row["notes"],
        )
        for row in results
    ]

    return ApprovalListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/history")
async def get_approval_history(
    entity: str | None = Query(None),
    status: str | None = Query(None),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    limit: int = Query(50, le=200),
    user: User = Depends(get_current_user),
) -> list[dict]:
    """Get approval history.

    Args:
        entity: Filter by entity
        status: Filter by status
        start_date: Filter by start date
        end_date: Filter by end date
        limit: Maximum results
        user: Authenticated user

    Returns:
        List of approval records
    """
    conditions = []
    params = {"limit": limit}

    if entity:
        conditions.append("entity = :entity")
        params["entity"] = entity

    if status:
        conditions.append("status = :status")
        params["status"] = status

    if start_date:
        conditions.append("requested_at >= :start_date")
        params["start_date"] = start_date

    if end_date:
        conditions.append("requested_at <= :end_date")
        params["end_date"] = end_date

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    query = f"""
        SELECT
            id,
            request_type,
            reference_id::text,
            entity,
            amount,
            description,
            status,
            requested_by,
            requested_at,
            decided_at,
            decided_by,
            notes
        FROM approval_log
        {where_clause}
        ORDER BY requested_at DESC
        LIMIT :limit
    """

    return execute_query(query, params)


@router.post("/{approval_id}/approve")
async def approve_request(
    approval_id: int,
    request: ApprovalActionRequest | None = None,
    user: User = Depends(require_permission("approve")),
) -> dict:
    """Approve a request.

    Args:
        approval_id: Approval ID
        request: Optional notes
        user: Authenticated user with approve permission

    Returns:
        Success message
    """
    notes = request.notes if request else None

    # Check current status
    check_query = """
        SELECT status, amount, request_type
        FROM approval_log
        WHERE id = :id
    """
    check_result = execute_query(check_query, {"id": approval_id})

    if not check_result:
        raise HTTPException(status_code=404, detail="Approval not found")

    if check_result[0]["status"] != "pending":
        raise HTTPException(status_code=400, detail="Approval is not pending")

    # Check amount limit for officers
    amount = check_result[0].get("amount")
    if amount and user.role == "officer":
        if float(amount) > 10000:
            raise HTTPException(
                status_code=403,
                detail="Officers can only approve amounts under 10,000 PHP"
            )

    # Update approval
    query = """
        UPDATE approval_log
        SET status = 'approved',
            decided_at = NOW(),
            decided_by = :user_id,
            notes = COALESCE(:notes, notes)
        WHERE id = :id
        RETURNING id
    """

    result = execute_query(query, {
        "id": approval_id,
        "user_id": user.telegram_id,
        "notes": notes,
    })

    # Also update the referenced transaction if applicable
    ref_id = check_result[0].get("reference_id")
    if ref_id:
        update_txn = """
            UPDATE transactions
            SET approved = TRUE,
                approved_by = :user_id,
                approved_at = NOW()
            WHERE id = :ref_id
        """
        execute_query(update_txn, {"ref_id": ref_id, "user_id": user.telegram_id})

    return {"message": "Approved", "approval_id": approval_id}


@router.post("/{approval_id}/reject")
async def reject_request(
    approval_id: int,
    request: ApprovalActionRequest,
    user: User = Depends(require_permission("approve")),
) -> dict:
    """Reject a request.

    Args:
        approval_id: Approval ID
        request: Rejection notes (required)
        user: Authenticated user with approve permission

    Returns:
        Success message
    """
    if not request.notes:
        raise HTTPException(status_code=400, detail="Notes are required for rejection")

    # Check current status
    check_query = """
        SELECT status
        FROM approval_log
        WHERE id = :id
    """
    check_result = execute_query(check_query, {"id": approval_id})

    if not check_result:
        raise HTTPException(status_code=404, detail="Approval not found")

    if check_result[0]["status"] != "pending":
        raise HTTPException(status_code=400, detail="Approval is not pending")

    # Update approval
    query = """
        UPDATE approval_log
        SET status = 'rejected',
            decided_at = NOW(),
            decided_by = :user_id,
            notes = :notes
        WHERE id = :id
        RETURNING id
    """

    result = execute_query(query, {
        "id": approval_id,
        "user_id": user.telegram_id,
        "notes": request.notes,
    })

    return {"message": "Rejected", "approval_id": approval_id}


@router.get("/stats")
async def get_approval_stats(
    user: User = Depends(get_current_user),
) -> dict:
    """Get approval statistics.

    Returns:
        Approval statistics
    """
    query = """
        SELECT
            status,
            COUNT(*) as count,
            COALESCE(SUM(amount), 0) as total_amount
        FROM approval_log
        GROUP BY status
    """

    results = execute_query(query)

    stats = {
        "pending": {"count": 0, "total_amount": 0},
        "approved": {"count": 0, "total_amount": 0},
        "rejected": {"count": 0, "total_amount": 0},
        "auto_approved": {"count": 0, "total_amount": 0},
    }

    for row in results:
        status = row["status"]
        if status in stats:
            stats[status] = {
                "count": row["count"],
                "total_amount": float(row["total_amount"]),
            }

    # Recent activity
    recent_query = """
        SELECT COUNT(*) as count
        FROM approval_log
        WHERE decided_at > NOW() - INTERVAL '7 days'
    """
    recent_result = execute_query(recent_query)
    stats["decisions_last_7_days"] = recent_result[0]["count"] if recent_result else 0

    return stats

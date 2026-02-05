"""
Fund Requests API Routes

Provides endpoints for fund request management.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..auth import User, get_current_user, require_permission
from ..database import execute_query, execute_insert

router = APIRouter(prefix="/fund-requests", tags=["fund-requests"])


class FundRequestItemInput(BaseModel):
    """Input model for fund request line item."""

    description: str
    amount: float
    category: str | None = None
    vendor: str | None = None
    notes: str | None = None


class ProjectExpenseInput(BaseModel):
    """Input model for project expense."""

    project_name: str
    amount: float


class FundRequestCreateInput(BaseModel):
    """Input model for creating a fund request."""

    entity: str
    payment_date: date
    section_a_items: list[FundRequestItemInput]
    section_b_items: list[FundRequestItemInput] = []
    current_fund_balance: float | None = None
    project_expenses: list[ProjectExpenseInput] = []


class FundRequestSummary(BaseModel):
    """Fund request summary model."""

    id: int
    entity: str
    request_date: date
    payment_date: date
    period_label: str | None
    section_a_total: float
    section_b_total: float
    overall_total: float
    current_fund_balance: float | None
    remaining_fund: float | None
    status: str
    approved_by: str | None
    approved_at: datetime | None
    google_drive_url: str | None
    created_at: datetime


class FundRequestListResponse(BaseModel):
    """Paginated fund request list."""

    items: list[FundRequestSummary]
    total: int
    page: int
    page_size: int


@router.get("", response_model=FundRequestListResponse)
async def list_fund_requests(
    entity: str | None = Query(None),
    status: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
) -> FundRequestListResponse:
    """List fund requests with filters.

    Args:
        entity: Filter by entity
        status: Filter by status
        start_date: Filter by start date
        end_date: Filter by end date
        page: Page number
        page_size: Items per page
        user: Authenticated user

    Returns:
        Paginated list of fund requests
    """
    conditions = []
    params = {}

    if entity:
        conditions.append("entity = :entity")
        params["entity"] = entity

    if status:
        conditions.append("status = :status")
        params["status"] = status

    if start_date:
        conditions.append("payment_date >= :start_date")
        params["start_date"] = start_date

    if end_date:
        conditions.append("payment_date <= :end_date")
        params["end_date"] = end_date

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    # Count total
    count_query = f"""
        SELECT COUNT(*) as total
        FROM fund_requests
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
            entity,
            request_date,
            payment_date,
            period_label,
            section_a_total,
            section_b_total,
            overall_total,
            current_fund_balance,
            remaining_fund,
            status,
            approved_by,
            approved_at,
            google_drive_url,
            created_at
        FROM fund_requests
        {where_clause}
        ORDER BY payment_date DESC, created_at DESC
        LIMIT :limit OFFSET :offset
    """

    results = execute_query(query, params)

    items = [
        FundRequestSummary(
            id=row["id"],
            entity=row["entity"],
            request_date=row["request_date"],
            payment_date=row["payment_date"],
            period_label=row["period_label"],
            section_a_total=float(row["section_a_total"]),
            section_b_total=float(row["section_b_total"]),
            overall_total=float(row["overall_total"]),
            current_fund_balance=float(row["current_fund_balance"]) if row["current_fund_balance"] else None,
            remaining_fund=float(row["remaining_fund"]) if row["remaining_fund"] else None,
            status=row["status"],
            approved_by=row["approved_by"],
            approved_at=row["approved_at"],
            google_drive_url=row["google_drive_url"],
            created_at=row["created_at"],
        )
        for row in results
    ]

    return FundRequestListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{request_id}")
async def get_fund_request(
    request_id: int,
    user: User = Depends(get_current_user),
) -> dict:
    """Get fund request details with all items.

    Args:
        request_id: Fund request ID
        user: Authenticated user

    Returns:
        Fund request with items
    """
    # Get header
    header_query = """
        SELECT *
        FROM fund_requests
        WHERE id = :id
    """
    header_result = execute_query(header_query, {"id": request_id})

    if not header_result:
        raise HTTPException(status_code=404, detail="Fund request not found")

    fund_request = header_result[0]

    # Get items
    items_query = """
        SELECT *
        FROM fund_request_items
        WHERE fund_request_id = :id
        ORDER BY section, line_number
    """
    items_result = execute_query(items_query, {"id": request_id})

    # Get project expenses
    projects_query = """
        SELECT *
        FROM fund_request_projects
        WHERE fund_request_id = :id
    """
    projects_result = execute_query(projects_query, {"id": request_id})

    return {
        **fund_request,
        "items": items_result,
        "project_expenses": projects_result,
    }


@router.post("")
async def create_fund_request(
    input_data: FundRequestCreateInput,
    user: User = Depends(get_current_user),
) -> dict:
    """Create a new fund request.

    Args:
        input_data: Fund request input data
        user: Authenticated user

    Returns:
        Created fund request ID
    """
    from python.fund_request import FundCalculator

    # Use calculator to create and validate
    calculator = FundCalculator()

    fund_request = calculator.create_fund_request(
        entity=input_data.entity,
        payment_date=input_data.payment_date,
        section_a_items=[item.model_dump() for item in input_data.section_a_items],
        section_b_items=[item.model_dump() for item in input_data.section_b_items],
        current_fund_balance=Decimal(str(input_data.current_fund_balance)) if input_data.current_fund_balance else None,
        project_expenses=[pe.model_dump() for pe in input_data.project_expenses],
        created_by=user.telegram_id,
    )

    # Validate
    errors = calculator.validate_fund_request(fund_request)
    if errors:
        raise HTTPException(status_code=400, detail={"errors": errors})

    # Insert header
    header_data = {
        "entity": fund_request.entity,
        "request_date": fund_request.request_date,
        "payment_date": fund_request.payment_date,
        "period_label": fund_request.period_label,
        "section_a_total": float(fund_request.section_a_total),
        "section_b_total": float(fund_request.section_b_total),
        "overall_total": float(fund_request.overall_total),
        "current_fund_balance": float(fund_request.current_fund_balance) if fund_request.current_fund_balance else None,
        "project_expenses_total": float(fund_request.project_expenses_total),
        "remaining_fund": float(fund_request.remaining_fund) if fund_request.remaining_fund else None,
        "status": "draft",
        "created_by": user.telegram_id,
    }

    result = execute_insert("fund_requests", header_data)
    fund_request_id = result["id"]

    # Insert items
    for item in fund_request.section_a_items:
        item_data = {
            "fund_request_id": fund_request_id,
            "section": "A",
            "line_number": item.line_number,
            "description": item.description,
            "amount": float(item.amount),
            "currency": item.currency,
            "category": item.category,
            "vendor": item.vendor,
            "notes": item.notes,
        }
        execute_insert("fund_request_items", item_data)

    for item in fund_request.section_b_items:
        item_data = {
            "fund_request_id": fund_request_id,
            "section": "B",
            "line_number": item.line_number,
            "description": item.description,
            "amount": float(item.amount),
            "currency": item.currency,
            "category": item.category,
            "vendor": item.vendor,
            "notes": item.notes,
        }
        execute_insert("fund_request_items", item_data)

    # Insert project expenses
    for pe in fund_request.project_expenses:
        pe_data = {
            "fund_request_id": fund_request_id,
            "project_name": pe.project_name,
            "amount": float(pe.amount),
        }
        execute_insert("fund_request_projects", pe_data)

    return {
        "id": fund_request_id,
        "message": "Fund request created",
        "warnings": calculator.get_warnings(fund_request),
    }


@router.post("/{request_id}/generate-excel")
async def generate_excel(
    request_id: int,
    user: User = Depends(get_current_user),
) -> dict:
    """Generate Excel file for fund request.

    Args:
        request_id: Fund request ID
        user: Authenticated user

    Returns:
        Path to generated file
    """
    from python.fund_request import FundCalculator, FundRequestExcelGenerator

    # Get fund request data
    fund_request_data = await get_fund_request(request_id, user)

    # Reconstruct FundRequestData
    calculator = FundCalculator()
    fund_request = calculator.create_fund_request(
        entity=fund_request_data["entity"],
        payment_date=fund_request_data["payment_date"],
        section_a_items=[
            {
                "description": item["description"],
                "amount": item["amount"],
                "category": item["category"],
                "vendor": item["vendor"],
                "notes": item["notes"],
            }
            for item in fund_request_data["items"]
            if item["section"] == "A"
        ],
        section_b_items=[
            {
                "description": item["description"],
                "amount": item["amount"],
                "category": item["category"],
                "vendor": item["vendor"],
                "notes": item["notes"],
            }
            for item in fund_request_data["items"]
            if item["section"] == "B"
        ],
        current_fund_balance=Decimal(str(fund_request_data["current_fund_balance"])) if fund_request_data["current_fund_balance"] else None,
        project_expenses=[
            {
                "project_name": pe["project_name"],
                "amount": pe["amount"],
            }
            for pe in fund_request_data.get("project_expenses", [])
        ],
    )

    # Generate Excel
    generator = FundRequestExcelGenerator()
    output_path = generator.generate(fund_request)

    # Update database with file path
    update_query = """
        UPDATE fund_requests
        SET excel_file_path = :path
        WHERE id = :id
    """
    execute_query(update_query, {"id": request_id, "path": str(output_path)})

    return {
        "message": "Excel generated",
        "file_path": str(output_path),
    }


@router.get("/{request_id}/download")
async def download_excel(
    request_id: int,
    user: User = Depends(get_current_user),
) -> FileResponse:
    """Download Excel file for fund request.

    Args:
        request_id: Fund request ID
        user: Authenticated user

    Returns:
        Excel file
    """
    query = """
        SELECT excel_file_path, entity, payment_date
        FROM fund_requests
        WHERE id = :id
    """
    result = execute_query(query, {"id": request_id})

    if not result:
        raise HTTPException(status_code=404, detail="Fund request not found")

    file_path = result[0]["excel_file_path"]

    if not file_path:
        raise HTTPException(status_code=404, detail="Excel file not generated")

    from pathlib import Path
    if not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="Excel file not found on disk")

    filename = f"{result[0]['entity']}_FundRequest_{result[0]['payment_date']}.xlsx"

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.post("/{request_id}/approve")
async def approve_fund_request(
    request_id: int,
    user: User = Depends(require_permission("approve")),
) -> dict:
    """Approve a fund request.

    Args:
        request_id: Fund request ID
        user: Authenticated user with approve permission

    Returns:
        Success message
    """
    # Check current status
    check_query = """
        SELECT status
        FROM fund_requests
        WHERE id = :id
    """
    check_result = execute_query(check_query, {"id": request_id})

    if not check_result:
        raise HTTPException(status_code=404, detail="Fund request not found")

    if check_result[0]["status"] not in ["draft", "sent"]:
        raise HTTPException(status_code=400, detail="Fund request cannot be approved in current status")

    # Update status
    update_query = """
        UPDATE fund_requests
        SET status = 'approved',
            approved_by = :user_id,
            approved_at = NOW()
        WHERE id = :id
    """
    execute_query(update_query, {"id": request_id, "user_id": user.telegram_id})

    return {"message": "Fund request approved", "id": request_id}


@router.post("/{request_id}/reject")
async def reject_fund_request(
    request_id: int,
    reason: str,
    user: User = Depends(require_permission("approve")),
) -> dict:
    """Reject a fund request.

    Args:
        request_id: Fund request ID
        reason: Rejection reason
        user: Authenticated user with approve permission

    Returns:
        Success message
    """
    update_query = """
        UPDATE fund_requests
        SET status = 'rejected',
            rejection_reason = :reason,
            approved_by = :user_id,
            approved_at = NOW()
        WHERE id = :id
    """
    execute_query(update_query, {
        "id": request_id,
        "reason": reason,
        "user_id": user.telegram_id,
    })

    return {"message": "Fund request rejected", "id": request_id}

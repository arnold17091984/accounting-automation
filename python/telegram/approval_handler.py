"""
Telegram Approval Handler Module

Handles expense approvals, rejections, and related workflow actions.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from enum import Enum

import yaml
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class ApprovalStatus(Enum):
    """Approval status enum."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    AUTO_APPROVED = "auto_approved"
    ESCALATED = "escalated"


@dataclass
class ApprovalRequest:
    """An approval request."""

    id: str
    request_type: str  # 'expense', 'transfer', 'pl_review', 'budget_override'
    entity: str
    amount: Decimal
    description: str
    requester: str
    requested_at: datetime
    status: ApprovalStatus = ApprovalStatus.PENDING
    budget_context: dict = field(default_factory=dict)
    attachments: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "request_type": self.request_type,
            "entity": self.entity,
            "amount": float(self.amount),
            "description": self.description,
            "requester": self.requester,
            "requested_at": self.requested_at.isoformat(),
            "status": self.status.value,
            "budget_context": self.budget_context,
            "attachments": self.attachments,
            "metadata": self.metadata
        }


@dataclass
class ApprovalResult:
    """Result of an approval action."""

    success: bool
    request_id: str
    action: str  # 'approved', 'rejected', 'escalated', 'question'
    message: str
    decided_by: int | None = None
    decided_at: datetime | None = None
    notes: str = ""


class ApprovalHandler:
    """Handles approval workflow for expenses and other requests."""

    # Auto-approval thresholds by role
    AUTO_APPROVE_THRESHOLDS = {
        "officer": Decimal("10000"),
        "accounting_manager": Decimal("50000"),
        "admin": Decimal("1000000"),  # Effectively unlimited
    }

    def __init__(
        self,
        config_dir: Path | str | None = None,
        db_connection: Any = None
    ):
        """Initialize approval handler.

        Args:
            config_dir: Path to configuration directory
            db_connection: PostgreSQL database connection
        """
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent.parent.parent / "config"
        self.db = db_connection
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration."""
        # Load ACL for permission checking
        acl_file = self.config_dir / "telegram_acl.yaml"
        if acl_file.exists():
            with open(acl_file) as f:
                self.acl_config = yaml.safe_load(f)
        else:
            self.acl_config = {"users": [], "permissions": {}}

        # Load budget thresholds for context
        threshold_file = self.config_dir / "budget_thresholds.yaml"
        if threshold_file.exists():
            with open(threshold_file) as f:
                self.threshold_config = yaml.safe_load(f)
        else:
            self.threshold_config = {}

    def get_user_role(self, user_id: int) -> str | None:
        """Get user role from ACL config."""
        for user in self.acl_config.get("users", []):
            if user.get("telegram_id") == user_id:
                return user.get("role")
        return None

    def can_approve(self, user_id: int, amount: Decimal) -> bool:
        """Check if user can approve given amount.

        Args:
            user_id: Telegram user ID
            amount: Approval amount

        Returns:
            True if user can approve
        """
        role = self.get_user_role(user_id)
        if not role:
            return False

        # Check role permissions
        permissions = self.acl_config.get("permissions", {}).get(role, [])

        if "approve" in permissions or "*" in permissions:
            return True

        if "approve_under_10k" in permissions and amount <= Decimal("10000"):
            return True

        if "approve_override" in permissions:
            return True

        return False

    def create_approval_request(
        self,
        request_type: str,
        entity: str,
        amount: Decimal,
        description: str,
        requester: str,
        budget_context: dict | None = None,
        attachments: list[str] | None = None,
        metadata: dict | None = None
    ) -> ApprovalRequest:
        """Create a new approval request.

        Args:
            request_type: Type of request
            entity: Entity code
            amount: Request amount
            description: Request description
            requester: Requester name/ID
            budget_context: Budget information for context
            attachments: List of attachment URLs
            metadata: Additional metadata

        Returns:
            ApprovalRequest
        """
        import uuid

        request = ApprovalRequest(
            id=str(uuid.uuid4()),
            request_type=request_type,
            entity=entity,
            amount=amount,
            description=description,
            requester=requester,
            requested_at=datetime.now(),
            budget_context=budget_context or {},
            attachments=attachments or [],
            metadata=metadata or {}
        )

        # Check for auto-approval
        auto_approve_limit = self.threshold_config.get("auto_approval", {}).get(
            "max_amount", 10000
        )

        if amount <= Decimal(str(auto_approve_limit)) and request_type == "expense":
            request.status = ApprovalStatus.AUTO_APPROVED
            self._log_approval(request, "system", "auto_approved", "Auto-approved (under threshold)")

        # Save to database
        self._save_request(request)

        return request

    def approve(
        self,
        request_id: str,
        user_id: int,
        notes: str = ""
    ) -> ApprovalResult:
        """Approve a request.

        Args:
            request_id: Request ID
            user_id: Approver's Telegram user ID
            notes: Optional approval notes

        Returns:
            ApprovalResult
        """
        # Get request
        request = self._get_request(request_id)
        if not request:
            return ApprovalResult(
                success=False,
                request_id=request_id,
                action="error",
                message="Request not found"
            )

        # Check if already processed
        if request.status != ApprovalStatus.PENDING:
            return ApprovalResult(
                success=False,
                request_id=request_id,
                action="error",
                message=f"Request already {request.status.value}"
            )

        # Check permission
        if not self.can_approve(user_id, request.amount):
            return ApprovalResult(
                success=False,
                request_id=request_id,
                action="error",
                message="You don't have permission to approve this amount"
            )

        # Update status
        request.status = ApprovalStatus.APPROVED
        self._update_request_status(request, user_id, "approved", notes)

        return ApprovalResult(
            success=True,
            request_id=request_id,
            action="approved",
            message=f"✅ Request approved\n\n{request.description}\nAmount: ₱{request.amount:,.2f}",
            decided_by=user_id,
            decided_at=datetime.now(),
            notes=notes
        )

    def reject(
        self,
        request_id: str,
        user_id: int,
        reason: str = ""
    ) -> ApprovalResult:
        """Reject a request.

        Args:
            request_id: Request ID
            user_id: Rejecter's Telegram user ID
            reason: Rejection reason

        Returns:
            ApprovalResult
        """
        request = self._get_request(request_id)
        if not request:
            return ApprovalResult(
                success=False,
                request_id=request_id,
                action="error",
                message="Request not found"
            )

        if request.status != ApprovalStatus.PENDING:
            return ApprovalResult(
                success=False,
                request_id=request_id,
                action="error",
                message=f"Request already {request.status.value}"
            )

        # Anyone with reject permission can reject
        role = self.get_user_role(user_id)
        permissions = self.acl_config.get("permissions", {}).get(role, [])

        if "reject" not in permissions and "*" not in permissions and "approve" not in permissions:
            return ApprovalResult(
                success=False,
                request_id=request_id,
                action="error",
                message="You don't have permission to reject requests"
            )

        request.status = ApprovalStatus.REJECTED
        self._update_request_status(request, user_id, "rejected", reason)

        return ApprovalResult(
            success=True,
            request_id=request_id,
            action="rejected",
            message=f"❌ Request rejected\n\n{request.description}\nReason: {reason or 'Not specified'}",
            decided_by=user_id,
            decided_at=datetime.now(),
            notes=reason
        )

    def escalate(
        self,
        request_id: str,
        user_id: int,
        reason: str = ""
    ) -> ApprovalResult:
        """Escalate a request to higher authority.

        Args:
            request_id: Request ID
            user_id: User requesting escalation
            reason: Escalation reason

        Returns:
            ApprovalResult
        """
        request = self._get_request(request_id)
        if not request:
            return ApprovalResult(
                success=False,
                request_id=request_id,
                action="error",
                message="Request not found"
            )

        request.status = ApprovalStatus.ESCALATED
        self._update_request_status(request, user_id, "escalated", reason)

        return ApprovalResult(
            success=True,
            request_id=request_id,
            action="escalated",
            message=f"⬆️ Request escalated\n\n{request.description}\nReason: {reason or 'Requires higher approval'}",
            decided_by=user_id,
            decided_at=datetime.now(),
            notes=reason
        )

    def ask_question(
        self,
        request_id: str,
        user_id: int,
        question: str
    ) -> ApprovalResult:
        """Ask a question about a request.

        Args:
            request_id: Request ID
            user_id: User asking question
            question: The question

        Returns:
            ApprovalResult with question context
        """
        request = self._get_request(request_id)
        if not request:
            return ApprovalResult(
                success=False,
                request_id=request_id,
                action="error",
                message="Request not found"
            )

        # Log the question
        self._log_question(request_id, user_id, question)

        return ApprovalResult(
            success=True,
            request_id=request_id,
            action="question",
            message=f"❓ Question about request:\n\n{question}\n\n_Requester will be notified._",
            decided_by=user_id,
            decided_at=datetime.now(),
            notes=question
        )

    def format_approval_message(self, request: ApprovalRequest) -> tuple[str, dict]:
        """Format approval request message with inline keyboard.

        Args:
            request: ApprovalRequest to format

        Returns:
            Tuple of (message text, inline keyboard)
        """
        # Determine emoji based on type
        type_emoji = {
            "expense": "💰",
            "transfer": "💸",
            "pl_review": "📊",
            "budget_override": "📋"
        }.get(request.request_type, "📄")

        lines = [
            f"{type_emoji} *Approval Request*",
            "",
            f"*Type:* {request.request_type.replace('_', ' ').title()}",
            f"*Entity:* {request.entity.upper()}",
            f"*Amount:* ₱{request.amount:,.2f}",
            f"*Description:* {request.description}",
            f"*Requester:* {request.requester}",
            f"*Time:* {request.requested_at.strftime('%Y-%m-%d %H:%M')}",
        ]

        # Add budget context if available
        if request.budget_context:
            budget = request.budget_context.get("budget_amount", 0)
            spent = request.budget_context.get("spent_amount", 0)
            remaining = budget - spent

            utilization = (spent / budget * 100) if budget > 0 else 0
            status_emoji = "🔴" if utilization >= 100 else "🟠" if utilization >= 90 else "⚠️" if utilization >= 70 else "✅"

            lines.extend([
                "",
                "*Budget Context:*",
                f"• Budget: ₱{budget:,.2f}",
                f"• Spent: ₱{spent:,.2f}",
                f"• Remaining: ₱{remaining:,.2f}",
                f"• Status: {status_emoji} {utilization:.1f}%"
            ])

            if spent + float(request.amount) > budget:
                lines.append("⚠️ _This will exceed the budget!_")

        # Build inline keyboard
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "✅ Approve", "callback_data": f"approve_{request.id}"},
                    {"text": "❌ Reject", "callback_data": f"reject_{request.id}"}
                ],
                [
                    {"text": "❓ Ask Question", "callback_data": f"question_{request.id}"},
                    {"text": "⬆️ Escalate", "callback_data": f"escalate_{request.id}"}
                ],
                [
                    {"text": "📎 View Attachments", "callback_data": f"docs_{request.id}"}
                ] if request.attachments else []
            ]
        }

        # Remove empty rows
        keyboard["inline_keyboard"] = [row for row in keyboard["inline_keyboard"] if row]

        return "\n".join(lines), keyboard

    def handle_callback(
        self,
        callback_data: str,
        user_id: int,
        message_text: str = ""
    ) -> ApprovalResult:
        """Handle inline keyboard callback.

        Args:
            callback_data: Callback data from button
            user_id: User who clicked button
            message_text: Additional message text (for questions/rejections)

        Returns:
            ApprovalResult
        """
        parts = callback_data.split("_", 1)
        if len(parts) != 2:
            return ApprovalResult(
                success=False,
                request_id="",
                action="error",
                message="Invalid callback data"
            )

        action, request_id = parts

        if action == "approve":
            return self.approve(request_id, user_id)
        elif action == "reject":
            return self.reject(request_id, user_id, message_text)
        elif action == "question":
            return self.ask_question(request_id, user_id, message_text)
        elif action == "escalate":
            return self.escalate(request_id, user_id, message_text)
        elif action == "docs":
            return self._get_attachments(request_id)
        else:
            return ApprovalResult(
                success=False,
                request_id=request_id,
                action="error",
                message=f"Unknown action: {action}"
            )

    def _save_request(self, request: ApprovalRequest) -> None:
        """Save request to database."""
        if not self.db:
            return

        try:
            with self.db.cursor() as cur:
                cur.execute("""
                    INSERT INTO approval_log (
                        id, request_type, entity, amount, status,
                        requested_at, notes
                    ) VALUES (
                        %s::uuid, %s, %s, %s, %s, %s, %s
                    )
                """, (
                    request.id,
                    request.request_type,
                    request.entity,
                    float(request.amount),
                    request.status.value,
                    request.requested_at,
                    json.dumps({
                        "description": request.description,
                        "requester": request.requester,
                        "budget_context": request.budget_context,
                        "attachments": request.attachments,
                        "metadata": request.metadata
                    })
                ))
                self.db.commit()
        except Exception as e:
            logger.error(f"Failed to save approval request: {e}")

    def _get_request(self, request_id: str) -> ApprovalRequest | None:
        """Get request from database."""
        if not self.db:
            return None

        try:
            with self.db.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM approval_log WHERE id = %s::uuid
                """, (request_id,))
                row = cur.fetchone()

                if not row:
                    return None

                notes_data = json.loads(row["notes"]) if row["notes"] else {}

                return ApprovalRequest(
                    id=str(row["id"]),
                    request_type=row["request_type"],
                    entity=row["entity"],
                    amount=Decimal(str(row["amount"])),
                    description=notes_data.get("description", ""),
                    requester=notes_data.get("requester", ""),
                    requested_at=row["requested_at"],
                    status=ApprovalStatus(row["status"]),
                    budget_context=notes_data.get("budget_context", {}),
                    attachments=notes_data.get("attachments", []),
                    metadata=notes_data.get("metadata", {})
                )
        except Exception as e:
            logger.error(f"Failed to get approval request: {e}")
            return None

    def _update_request_status(
        self,
        request: ApprovalRequest,
        user_id: int,
        action: str,
        notes: str
    ) -> None:
        """Update request status in database."""
        if not self.db:
            return

        try:
            with self.db.cursor() as cur:
                cur.execute("""
                    UPDATE approval_log
                    SET status = %s,
                        decided_at = %s,
                        decided_by = %s,
                        notes = notes || %s::jsonb
                    WHERE id = %s::uuid
                """, (
                    request.status.value,
                    datetime.now(),
                    str(user_id),
                    json.dumps({"decision_notes": notes, "action": action}),
                    request.id
                ))
                self.db.commit()
        except Exception as e:
            logger.error(f"Failed to update approval status: {e}")

    def _log_approval(
        self,
        request: ApprovalRequest,
        decided_by: str,
        action: str,
        notes: str
    ) -> None:
        """Log approval action to audit log."""
        if not self.db:
            return

        try:
            with self.db.cursor() as cur:
                cur.execute("""
                    INSERT INTO audit_log (action, entity, details, status)
                    VALUES (%s, %s, %s, 'success')
                """, (
                    f"approval_{action}",
                    request.entity,
                    json.dumps({
                        "request_id": request.id,
                        "request_type": request.request_type,
                        "amount": float(request.amount),
                        "decided_by": decided_by,
                        "notes": notes
                    })
                ))
                self.db.commit()
        except Exception as e:
            logger.error(f"Failed to log approval: {e}")

    def _log_question(self, request_id: str, user_id: int, question: str) -> None:
        """Log question to database."""
        if not self.db:
            return

        try:
            with self.db.cursor() as cur:
                cur.execute("""
                    INSERT INTO audit_log (action, details, status)
                    VALUES ('approval_question', %s, 'success')
                """, (json.dumps({
                    "request_id": request_id,
                    "user_id": user_id,
                    "question": question
                }),))
                self.db.commit()
        except Exception as e:
            logger.error(f"Failed to log question: {e}")

    def _get_attachments(self, request_id: str) -> ApprovalResult:
        """Get attachments for a request."""
        request = self._get_request(request_id)
        if not request:
            return ApprovalResult(
                success=False,
                request_id=request_id,
                action="error",
                message="Request not found"
            )

        if not request.attachments:
            return ApprovalResult(
                success=True,
                request_id=request_id,
                action="docs",
                message="No attachments for this request."
            )

        lines = ["📎 *Attachments:*", ""]
        for i, url in enumerate(request.attachments, 1):
            lines.append(f"{i}. {url}")

        return ApprovalResult(
            success=True,
            request_id=request_id,
            action="docs",
            message="\n".join(lines)
        )

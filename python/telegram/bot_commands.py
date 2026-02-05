"""
Telegram Bot Commands Module

Handles bot commands: /budget, /pl, /cash, /pending, /status, /report
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable

import yaml
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


@dataclass
class CommandResult:
    """Result of a command execution."""

    success: bool
    message: str
    data: dict = field(default_factory=dict)
    keyboard: dict | None = None
    parse_mode: str = "Markdown"


@dataclass
class UserPermissions:
    """User permission information."""

    user_id: int
    name: str
    role: str
    permissions: list[str] = field(default_factory=list)

    def can(self, action: str) -> bool:
        """Check if user has permission for action."""
        if "*" in self.permissions:
            return True
        return action in self.permissions


class BotCommandHandler:
    """Handles Telegram bot commands."""

    # Command descriptions for /help
    COMMAND_HELP = {
        "/budget": "View budget status for an entity",
        "/pl": "View P&L summary",
        "/cash": "View cash position",
        "/pending": "View pending approvals",
        "/status": "System health check",
        "/report": "Generate and send reports",
        "/help": "Show available commands",
    }

    def __init__(
        self,
        config_dir: Path | str | None = None,
        db_connection: Any = None
    ):
        """Initialize command handler.

        Args:
            config_dir: Path to configuration directory
            db_connection: PostgreSQL database connection
        """
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent.parent.parent / "config"
        self.db = db_connection
        self._load_config()
        self._command_handlers: dict[str, Callable] = {
            "/budget": self._handle_budget,
            "/pl": self._handle_pl,
            "/cash": self._handle_cash,
            "/pending": self._handle_pending,
            "/status": self._handle_status,
            "/report": self._handle_report,
            "/help": self._handle_help,
        }

    def _load_config(self) -> None:
        """Load configuration files."""
        # Load ACL
        acl_file = self.config_dir / "telegram_acl.yaml"
        if acl_file.exists():
            with open(acl_file) as f:
                self.acl_config = yaml.safe_load(f)
        else:
            self.acl_config = {"users": [], "permissions": {}}

        # Load entity config
        entity_file = self.config_dir / "entity_config.yaml"
        if entity_file.exists():
            with open(entity_file) as f:
                self.entity_config = yaml.safe_load(f)
        else:
            self.entity_config = {"entities": {}}

    def get_user_permissions(self, user_id: int) -> UserPermissions | None:
        """Get permissions for a user.

        Args:
            user_id: Telegram user ID

        Returns:
            UserPermissions or None if not authorized
        """
        for user in self.acl_config.get("users", []):
            if user.get("telegram_id") == user_id:
                role = user.get("role", "viewer")
                permissions = self.acl_config.get("permissions", {}).get(role, [])
                return UserPermissions(
                    user_id=user_id,
                    name=user.get("name", "Unknown"),
                    role=role,
                    permissions=permissions
                )
        return None

    def handle_command(
        self,
        command: str,
        args: list[str],
        user_id: int
    ) -> CommandResult:
        """Handle a bot command.

        Args:
            command: Command text (e.g., "/budget")
            args: Command arguments
            user_id: Telegram user ID

        Returns:
            CommandResult
        """
        # Check authorization
        user = self.get_user_permissions(user_id)
        if not user:
            return CommandResult(
                success=False,
                message="❌ *Access Denied*\n\nYou are not authorized to use this bot."
            )

        # Check command exists
        handler = self._command_handlers.get(command.lower())
        if not handler:
            return CommandResult(
                success=False,
                message=f"❓ Unknown command: `{command}`\n\nUse /help to see available commands."
            )

        # Check permission
        required_permission = self._get_required_permission(command)
        if not user.can(required_permission):
            return CommandResult(
                success=False,
                message=f"❌ *Permission Denied*\n\nYou don't have permission to use `{command}`."
            )

        try:
            return handler(args, user)
        except Exception as e:
            logger.error(f"Command {command} failed: {e}")
            return CommandResult(
                success=False,
                message=f"❌ *Error*\n\nFailed to execute command: {str(e)}"
            )

    def _get_required_permission(self, command: str) -> str:
        """Get required permission for a command."""
        permission_map = {
            "/budget": "view",
            "/pl": "view",
            "/cash": "view",
            "/pending": "view",
            "/status": "view",
            "/report": "report",
            "/help": "view",
        }
        return permission_map.get(command, "view")

    def _handle_help(self, args: list[str], user: UserPermissions) -> CommandResult:
        """Handle /help command."""
        lines = [
            "📚 *Available Commands*",
            ""
        ]

        for cmd, desc in self.COMMAND_HELP.items():
            perm = self._get_required_permission(cmd)
            if user.can(perm):
                lines.append(f"`{cmd}` - {desc}")

        lines.extend([
            "",
            f"_Your role: {user.role}_"
        ])

        return CommandResult(
            success=True,
            message="\n".join(lines)
        )

    def _handle_budget(self, args: list[str], user: UserPermissions) -> CommandResult:
        """Handle /budget command.

        Usage: /budget [entity] [month]
        """
        entity = args[0].lower() if args else None
        month = args[1] if len(args) > 1 else datetime.now().strftime("%Y-%m")

        # If no entity specified, show selection keyboard
        if not entity:
            keyboard = self._build_entity_keyboard("budget")
            return CommandResult(
                success=True,
                message="📊 *Budget Status*\n\nSelect an entity:",
                keyboard=keyboard
            )

        # Validate entity
        if entity not in self.entity_config.get("entities", {}):
            return CommandResult(
                success=False,
                message=f"❌ Unknown entity: `{entity}`"
            )

        # Get budget data
        budget_data = self._get_budget_status(entity, month)

        if not budget_data:
            return CommandResult(
                success=True,
                message=f"📊 *Budget Status - {entity.upper()}*\n\nNo budget data found for {month}."
            )

        # Format response
        lines = [
            f"📊 *Budget Status - {entity.upper()}*",
            f"Period: {month}",
            ""
        ]

        total_budget = Decimal("0")
        total_actual = Decimal("0")
        warnings = []

        for row in budget_data:
            budget = Decimal(str(row["budget_amount"]))
            actual = Decimal(str(row["actual_amount"]))
            total_budget += budget
            total_actual += actual

            utilization = float(actual / budget * 100) if budget > 0 else 0

            if utilization >= 100:
                warnings.append(f"🔴 {row['account_name']}: {utilization:.1f}%")
            elif utilization >= 90:
                warnings.append(f"🟠 {row['account_name']}: {utilization:.1f}%")
            elif utilization >= 70:
                warnings.append(f"⚠️ {row['account_name']}: {utilization:.1f}%")

        overall_util = float(total_actual / total_budget * 100) if total_budget > 0 else 0
        status_emoji = "🔴" if overall_util >= 100 else "🟠" if overall_util >= 90 else "⚠️" if overall_util >= 70 else "✅"

        lines.extend([
            "*Summary:*",
            f"• Total Budget: ₱{total_budget:,.2f}",
            f"• Total Spent: ₱{total_actual:,.2f}",
            f"• Utilization: {status_emoji} {overall_util:.1f}%",
            ""
        ])

        if warnings:
            lines.append("*Alerts:*")
            lines.extend(warnings[:10])
            if len(warnings) > 10:
                lines.append(f"_...and {len(warnings) - 10} more_")

        return CommandResult(
            success=True,
            message="\n".join(lines),
            data={"entity": entity, "month": month, "utilization": overall_util}
        )

    def _handle_pl(self, args: list[str], user: UserPermissions) -> CommandResult:
        """Handle /pl command.

        Usage: /pl [entity] [month]
        """
        entity = args[0].lower() if args else None
        month = args[1] if len(args) > 1 else datetime.now().strftime("%Y-%m")

        if not entity:
            keyboard = self._build_entity_keyboard("pl")
            return CommandResult(
                success=True,
                message="📈 *P&L Summary*\n\nSelect an entity:",
                keyboard=keyboard
            )

        if entity not in self.entity_config.get("entities", {}):
            return CommandResult(
                success=False,
                message=f"❌ Unknown entity: `{entity}`"
            )

        pl_data = self._get_pl_summary(entity, month)

        if not pl_data:
            return CommandResult(
                success=True,
                message=f"📈 *P&L Summary - {entity.upper()}*\n\nNo data found for {month}."
            )

        revenue = Decimal(str(pl_data.get("revenue", 0)))
        expenses = Decimal(str(pl_data.get("expenses", 0)))
        net_income = revenue - expenses
        margin = float(net_income / revenue * 100) if revenue > 0 else 0

        lines = [
            f"📈 *P&L Summary - {entity.upper()}*",
            f"Period: {month}",
            "",
            "*Overview:*",
            f"• Revenue: ₱{revenue:,.2f}",
            f"• Expenses: ₱{expenses:,.2f}",
            f"• Net Income: ₱{net_income:,.2f}",
            f"• Margin: {margin:.1f}%",
            ""
        ]

        # Top expense categories
        if pl_data.get("top_expenses"):
            lines.append("*Top Expenses:*")
            for cat, amount in pl_data["top_expenses"][:5]:
                lines.append(f"• {cat}: ₱{amount:,.2f}")

        return CommandResult(
            success=True,
            message="\n".join(lines),
            data=pl_data
        )

    def _handle_cash(self, args: list[str], user: UserPermissions) -> CommandResult:
        """Handle /cash command.

        Usage: /cash [entity]
        """
        entity = args[0].lower() if args else None

        if not entity:
            keyboard = self._build_entity_keyboard("cash")
            return CommandResult(
                success=True,
                message="💰 *Cash Position*\n\nSelect an entity:",
                keyboard=keyboard
            )

        if entity not in self.entity_config.get("entities", {}):
            return CommandResult(
                success=False,
                message=f"❌ Unknown entity: `{entity}`"
            )

        cash_data = self._get_cash_position(entity)

        lines = [
            f"💰 *Cash Position - {entity.upper()}*",
            f"As of: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
        ]

        if cash_data:
            total = Decimal("0")
            for account in cash_data:
                balance = Decimal(str(account.get("balance", 0)))
                total += balance
                lines.append(f"• {account['name']}: ₱{balance:,.2f}")

            lines.extend([
                "",
                f"*Total: ₱{total:,.2f}*"
            ])
        else:
            lines.append("No cash data available.")

        return CommandResult(
            success=True,
            message="\n".join(lines)
        )

    def _handle_pending(self, args: list[str], user: UserPermissions) -> CommandResult:
        """Handle /pending command."""
        pending = self._get_pending_approvals(user.user_id)

        if not pending:
            return CommandResult(
                success=True,
                message="✅ *No Pending Approvals*\n\nAll items have been processed."
            )

        lines = [
            f"📋 *Pending Approvals* ({len(pending)})",
            ""
        ]

        for item in pending[:10]:
            lines.append(
                f"• [{item['request_type']}] {item['entity'].upper()} - "
                f"₱{item['amount']:,.2f}"
            )
            lines.append(f"  _{item['requested_at'].strftime('%Y-%m-%d %H:%M')}_")

        if len(pending) > 10:
            lines.append(f"\n_...and {len(pending) - 10} more_")

        return CommandResult(
            success=True,
            message="\n".join(lines)
        )

    def _handle_status(self, args: list[str], user: UserPermissions) -> CommandResult:
        """Handle /status command."""
        status = self._get_system_status()

        lines = [
            "🖥️ *System Status*",
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]

        # Database status
        db_status = "✅ Connected" if status.get("db_connected") else "❌ Disconnected"
        lines.append(f"*Database:* {db_status}")

        # Recent activity
        lines.extend([
            "",
            "*Recent Activity:*",
            f"• Transactions (24h): {status.get('transactions_24h', 0)}",
            f"• Approvals (24h): {status.get('approvals_24h', 0)}",
            f"• Alerts (24h): {status.get('alerts_24h', 0)}",
        ])

        # Workflow status
        lines.extend([
            "",
            "*Last Workflow Runs:*"
        ])
        for wf in status.get("recent_workflows", [])[:5]:
            emoji = "✅" if wf["status"] == "success" else "❌"
            lines.append(f"• {emoji} {wf['workflow']}: {wf['created_at'].strftime('%H:%M')}")

        return CommandResult(
            success=True,
            message="\n".join(lines)
        )

    def _handle_report(self, args: list[str], user: UserPermissions) -> CommandResult:
        """Handle /report command.

        Usage: /report [type] [entity] [period]
        Types: budget, pl, daily, weekly
        """
        report_type = args[0].lower() if args else None

        if not report_type:
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "📊 Budget Report", "callback_data": "report_budget"},
                        {"text": "📈 P&L Report", "callback_data": "report_pl"}
                    ],
                    [
                        {"text": "📅 Daily Summary", "callback_data": "report_daily"},
                        {"text": "📆 Weekly Summary", "callback_data": "report_weekly"}
                    ]
                ]
            }
            return CommandResult(
                success=True,
                message="📄 *Generate Report*\n\nSelect report type:",
                keyboard=keyboard
            )

        entity = args[1].lower() if len(args) > 1 else None
        period = args[2] if len(args) > 2 else datetime.now().strftime("%Y-%m")

        if not entity:
            keyboard = self._build_entity_keyboard(f"report_{report_type}")
            return CommandResult(
                success=True,
                message=f"📄 *{report_type.title()} Report*\n\nSelect an entity:",
                keyboard=keyboard
            )

        # Queue report generation
        return CommandResult(
            success=True,
            message=f"📄 *Generating {report_type.title()} Report*\n\n"
                    f"Entity: {entity.upper()}\n"
                    f"Period: {period}\n\n"
                    f"_Report will be sent when ready..._",
            data={
                "action": "generate_report",
                "report_type": report_type,
                "entity": entity,
                "period": period
            }
        )

    def _build_entity_keyboard(self, callback_prefix: str) -> dict:
        """Build inline keyboard with entity buttons."""
        entities = list(self.entity_config.get("entities", {}).keys())

        # Create rows of 2 buttons each
        rows = []
        for i in range(0, len(entities), 2):
            row = []
            for entity in entities[i:i+2]:
                row.append({
                    "text": entity.upper(),
                    "callback_data": f"{callback_prefix}_{entity}"
                })
            rows.append(row)

        return {"inline_keyboard": rows}

    def _get_budget_status(self, entity: str, month: str) -> list[dict]:
        """Get budget status from database."""
        if not self.db:
            return []

        try:
            with self.db.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        b.account_code,
                        b.account_name,
                        b.budget_amount,
                        COALESCE(SUM(t.amount), 0) as actual_amount
                    FROM budgets b
                    LEFT JOIN transactions t ON
                        t.entity = b.entity AND
                        t.account_code = b.account_code AND
                        TO_CHAR(t.txn_date, 'YYYY-MM') = %s
                    WHERE b.entity = %s
                      AND CONCAT(b.year, '-', LPAD(b.month::text, 2, '0')) = %s
                    GROUP BY b.account_code, b.account_name, b.budget_amount
                    ORDER BY b.account_code
                """, (month, entity, month))
                return cur.fetchall()
        except Exception as e:
            logger.error(f"Failed to get budget status: {e}")
            return []

    def _get_pl_summary(self, entity: str, month: str) -> dict:
        """Get P&L summary from database."""
        if not self.db:
            return {}

        try:
            with self.db.cursor(cursor_factory=RealDictCursor) as cur:
                # Get revenue
                cur.execute("""
                    SELECT COALESCE(SUM(amount), 0) as total
                    FROM transactions
                    WHERE entity = %s
                      AND category = 'revenue'
                      AND TO_CHAR(txn_date, 'YYYY-MM') = %s
                """, (entity, month))
                revenue = cur.fetchone()["total"]

                # Get expenses
                cur.execute("""
                    SELECT COALESCE(SUM(amount), 0) as total
                    FROM transactions
                    WHERE entity = %s
                      AND category IN ('expense', 'salary', 'cos')
                      AND TO_CHAR(txn_date, 'YYYY-MM') = %s
                """, (entity, month))
                expenses = cur.fetchone()["total"]

                # Get top expenses
                cur.execute("""
                    SELECT account_name, SUM(amount) as total
                    FROM transactions
                    WHERE entity = %s
                      AND category IN ('expense', 'salary', 'cos')
                      AND TO_CHAR(txn_date, 'YYYY-MM') = %s
                    GROUP BY account_name
                    ORDER BY total DESC
                    LIMIT 5
                """, (entity, month))
                top_expenses = [(r["account_name"], r["total"]) for r in cur.fetchall()]

                return {
                    "revenue": revenue,
                    "expenses": expenses,
                    "top_expenses": top_expenses
                }
        except Exception as e:
            logger.error(f"Failed to get P&L summary: {e}")
            return {}

    def _get_cash_position(self, entity: str) -> list[dict]:
        """Get cash position (placeholder - would connect to bank/QB)."""
        # In production, this would query QuickBooks or bank APIs
        return []

    def _get_pending_approvals(self, user_id: int) -> list[dict]:
        """Get pending approvals from database."""
        if not self.db:
            return []

        try:
            with self.db.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT *
                    FROM approval_log
                    WHERE status = 'pending'
                    ORDER BY requested_at DESC
                    LIMIT 20
                """)
                return cur.fetchall()
        except Exception as e:
            logger.error(f"Failed to get pending approvals: {e}")
            return []

    def _get_system_status(self) -> dict:
        """Get system status information."""
        status = {
            "db_connected": False,
            "transactions_24h": 0,
            "approvals_24h": 0,
            "alerts_24h": 0,
            "recent_workflows": []
        }

        if not self.db:
            return status

        try:
            with self.db.cursor(cursor_factory=RealDictCursor) as cur:
                status["db_connected"] = True

                # Transactions in last 24h
                cur.execute("""
                    SELECT COUNT(*) as count
                    FROM transactions
                    WHERE created_at > NOW() - INTERVAL '24 hours'
                """)
                status["transactions_24h"] = cur.fetchone()["count"]

                # Approvals in last 24h
                cur.execute("""
                    SELECT COUNT(*) as count
                    FROM approval_log
                    WHERE decided_at > NOW() - INTERVAL '24 hours'
                """)
                status["approvals_24h"] = cur.fetchone()["count"]

                # Alerts in last 24h
                cur.execute("""
                    SELECT COUNT(*) as count
                    FROM budget_alerts
                    WHERE sent_at > NOW() - INTERVAL '24 hours'
                """)
                status["alerts_24h"] = cur.fetchone()["count"]

                # Recent workflows
                cur.execute("""
                    SELECT workflow, status, created_at
                    FROM audit_log
                    WHERE action = 'workflow_run'
                    ORDER BY created_at DESC
                    LIMIT 5
                """)
                status["recent_workflows"] = cur.fetchall()

        except Exception as e:
            logger.error(f"Failed to get system status: {e}")

        return status

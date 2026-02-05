"""
Telegram Report Formatter Module

Formats various reports for Telegram message display.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)


class ReportFormatter:
    """Formats reports for Telegram display."""

    # Currency format
    CURRENCY_FORMAT = "₱{:,.2f}"
    PERCENT_FORMAT = "{:.1f}%"

    # Status emojis
    STATUS_EMOJI = {
        "ok": "✅",
        "warning": "⚠️",
        "critical": "🟠",
        "exceeded": "🔴",
        "error": "❌",
        "pending": "⏳",
        "success": "✅",
    }

    # Trend emojis
    TREND_EMOJI = {
        "up": "📈",
        "down": "📉",
        "flat": "➡️",
    }

    def __init__(self, max_message_length: int = 4096):
        """Initialize formatter.

        Args:
            max_message_length: Maximum Telegram message length
        """
        self.max_length = max_message_length

    def truncate_message(self, message: str) -> str:
        """Truncate message if too long.

        Args:
            message: Message to truncate

        Returns:
            Truncated message
        """
        if len(message) <= self.max_length:
            return message

        # Find last complete line before limit
        truncate_at = self.max_length - 50
        last_newline = message[:truncate_at].rfind("\n")
        if last_newline > 0:
            truncate_at = last_newline

        return message[:truncate_at] + "\n\n_...message truncated_"

    def format_pl_summary(
        self,
        entity: str,
        period: str,
        revenue: Decimal,
        expenses: Decimal,
        previous_revenue: Decimal | None = None,
        previous_expenses: Decimal | None = None,
        top_revenue_categories: list[tuple[str, Decimal]] | None = None,
        top_expense_categories: list[tuple[str, Decimal]] | None = None
    ) -> str:
        """Format P&L summary for Telegram.

        Args:
            entity: Entity code
            period: Report period (YYYY-MM)
            revenue: Total revenue
            expenses: Total expenses
            previous_revenue: Previous period revenue
            previous_expenses: Previous period expenses
            top_revenue_categories: Top revenue sources
            top_expense_categories: Top expense categories

        Returns:
            Formatted message
        """
        net_income = revenue - expenses
        margin = float(net_income / revenue * 100) if revenue > 0 else 0

        lines = [
            f"📊 *P&L Summary - {entity.upper()}*",
            f"Period: {period}",
            "",
            "*Financial Overview:*",
            f"• Revenue: {self.CURRENCY_FORMAT.format(revenue)}",
            f"• Expenses: {self.CURRENCY_FORMAT.format(expenses)}",
            f"• Net Income: {self.CURRENCY_FORMAT.format(net_income)}",
            f"• Margin: {self.PERCENT_FORMAT.format(margin)}",
        ]

        # Add period comparison if available
        if previous_revenue is not None:
            rev_change = float((revenue - previous_revenue) / previous_revenue * 100) if previous_revenue > 0 else 0
            rev_emoji = self.TREND_EMOJI["up" if rev_change > 0 else "down" if rev_change < 0 else "flat"]
            lines.append(f"• Revenue Trend: {rev_emoji} {rev_change:+.1f}%")

        if previous_expenses is not None:
            exp_change = float((expenses - previous_expenses) / previous_expenses * 100) if previous_expenses > 0 else 0
            # For expenses, down is good
            exp_emoji = self.TREND_EMOJI["down" if exp_change < 0 else "up" if exp_change > 0 else "flat"]
            lines.append(f"• Expense Trend: {exp_emoji} {exp_change:+.1f}%")

        # Top categories
        if top_revenue_categories:
            lines.extend(["", "*Top Revenue Sources:*"])
            for name, amount in top_revenue_categories[:5]:
                pct = float(amount / revenue * 100) if revenue > 0 else 0
                lines.append(f"• {name}: {self.CURRENCY_FORMAT.format(amount)} ({pct:.1f}%)")

        if top_expense_categories:
            lines.extend(["", "*Top Expenses:*"])
            for name, amount in top_expense_categories[:5]:
                pct = float(amount / expenses * 100) if expenses > 0 else 0
                lines.append(f"• {name}: {self.CURRENCY_FORMAT.format(amount)} ({pct:.1f}%)")

        lines.extend([
            "",
            f"_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}_"
        ])

        return self.truncate_message("\n".join(lines))

    def format_budget_status(
        self,
        entity: str,
        period: str,
        total_budget: Decimal,
        total_actual: Decimal,
        items: list[dict],
        include_all: bool = False
    ) -> str:
        """Format budget status for Telegram.

        Args:
            entity: Entity code
            period: Budget period
            total_budget: Total budget amount
            total_actual: Total actual amount
            items: List of budget line items
            include_all: Include all items (not just alerts)

        Returns:
            Formatted message
        """
        overall_util = float(total_actual / total_budget * 100) if total_budget > 0 else 0
        remaining = total_budget - total_actual

        status_key = (
            "exceeded" if overall_util >= 100
            else "critical" if overall_util >= 90
            else "warning" if overall_util >= 70
            else "ok"
        )

        lines = [
            f"📊 *Budget Status - {entity.upper()}*",
            f"Period: {period}",
            "",
            "*Summary:*",
            f"• Total Budget: {self.CURRENCY_FORMAT.format(total_budget)}",
            f"• Total Spent: {self.CURRENCY_FORMAT.format(total_actual)}",
            f"• Remaining: {self.CURRENCY_FORMAT.format(remaining)}",
            f"• Utilization: {self.STATUS_EMOJI[status_key]} {self.PERCENT_FORMAT.format(overall_util)}",
            "",
        ]

        # Categorize items
        exceeded = [i for i in items if i.get("utilization", 0) >= 100]
        critical = [i for i in items if 90 <= i.get("utilization", 0) < 100]
        warning = [i for i in items if 70 <= i.get("utilization", 0) < 90]
        ok = [i for i in items if i.get("utilization", 0) < 70]

        # Status counts
        lines.extend([
            "*Status:*",
            f"✅ OK: {len(ok)}",
            f"⚠️ Warning (70-90%): {len(warning)}",
            f"🟠 Critical (90-100%): {len(critical)}",
            f"🔴 Over Budget: {len(exceeded)}",
            "",
        ])

        # Alert items
        if exceeded or critical or warning:
            lines.append("*Items Needing Attention:*")

            for item in exceeded[:5]:
                lines.append(
                    f"🔴 {item['name']}: {self.PERCENT_FORMAT.format(item['utilization'])} "
                    f"(+{self.CURRENCY_FORMAT.format(item['actual'] - item['budget'])})"
                )

            for item in critical[:5]:
                lines.append(
                    f"🟠 {item['name']}: {self.PERCENT_FORMAT.format(item['utilization'])}"
                )

            for item in warning[:3]:
                lines.append(
                    f"⚠️ {item['name']}: {self.PERCENT_FORMAT.format(item['utilization'])}"
                )

            remaining_alerts = len(exceeded) + len(critical) + len(warning) - 13
            if remaining_alerts > 0:
                lines.append(f"_...and {remaining_alerts} more_")
        else:
            lines.append("✅ All accounts within budget!")

        lines.extend([
            "",
            f"_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}_"
        ])

        return self.truncate_message("\n".join(lines))

    def format_daily_digest(
        self,
        entity: str,
        date: str,
        transactions: list[dict],
        budget_status: dict | None = None
    ) -> str:
        """Format daily digest for Telegram.

        Args:
            entity: Entity code
            date: Date string
            transactions: List of today's transactions
            budget_status: Optional budget context

        Returns:
            Formatted message
        """
        total_spent = sum(Decimal(str(t.get("amount", 0))) for t in transactions)
        txn_count = len(transactions)

        lines = [
            f"📅 *Daily Digest - {entity.upper()}*",
            f"Date: {date}",
            "",
            "*Today's Activity:*",
            f"• Transactions: {txn_count}",
            f"• Total Spent: {self.CURRENCY_FORMAT.format(total_spent)}",
            "",
        ]

        # Top merchants/categories
        if transactions:
            # Group by category
            by_category: dict[str, Decimal] = {}
            for t in transactions:
                cat = t.get("category", "Other")
                by_category[cat] = by_category.get(cat, Decimal("0")) + Decimal(str(t.get("amount", 0)))

            sorted_cats = sorted(by_category.items(), key=lambda x: x[1], reverse=True)

            lines.append("*By Category:*")
            for cat, amount in sorted_cats[:5]:
                lines.append(f"• {cat}: {self.CURRENCY_FORMAT.format(amount)}")
            lines.append("")

        # Budget context
        if budget_status:
            mtd_budget = Decimal(str(budget_status.get("budget", 0)))
            mtd_actual = Decimal(str(budget_status.get("actual", 0)))
            utilization = float(mtd_actual / mtd_budget * 100) if mtd_budget > 0 else 0

            status_key = (
                "exceeded" if utilization >= 100
                else "critical" if utilization >= 90
                else "warning" if utilization >= 70
                else "ok"
            )

            lines.extend([
                "*Month-to-Date:*",
                f"• Budget: {self.CURRENCY_FORMAT.format(mtd_budget)}",
                f"• Spent: {self.CURRENCY_FORMAT.format(mtd_actual)}",
                f"• Utilization: {self.STATUS_EMOJI[status_key]} {self.PERCENT_FORMAT.format(utilization)}",
            ])

        return self.truncate_message("\n".join(lines))

    def format_weekly_summary(
        self,
        entity: str,
        week_start: str,
        week_end: str,
        this_week: dict,
        last_week: dict | None = None
    ) -> str:
        """Format weekly summary for Telegram.

        Args:
            entity: Entity code
            week_start: Week start date
            week_end: Week end date
            this_week: This week's data
            last_week: Last week's data for comparison

        Returns:
            Formatted message
        """
        lines = [
            f"📆 *Weekly Summary - {entity.upper()}*",
            f"Period: {week_start} to {week_end}",
            "",
            "*This Week:*",
            f"• Transactions: {this_week.get('count', 0)}",
            f"• Total Spent: {self.CURRENCY_FORMAT.format(this_week.get('total', 0))}",
            f"• Daily Average: {self.CURRENCY_FORMAT.format(this_week.get('daily_avg', 0))}",
        ]

        # Week-over-week comparison
        if last_week:
            this_total = Decimal(str(this_week.get("total", 0)))
            last_total = Decimal(str(last_week.get("total", 0)))

            if last_total > 0:
                change = float((this_total - last_total) / last_total * 100)
                emoji = self.TREND_EMOJI["up" if change > 0 else "down" if change < 0 else "flat"]
                lines.extend([
                    "",
                    f"*Week-over-Week:*",
                    f"• Change: {emoji} {change:+.1f}%",
                    f"• Last Week: {self.CURRENCY_FORMAT.format(last_total)}",
                ])

        # Top categories
        if this_week.get("by_category"):
            lines.extend(["", "*By Category:*"])
            for cat, amount in list(this_week["by_category"].items())[:5]:
                lines.append(f"• {cat}: {self.CURRENCY_FORMAT.format(amount)}")

        lines.extend([
            "",
            f"_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}_"
        ])

        return self.truncate_message("\n".join(lines))

    def format_transaction_list(
        self,
        transactions: list[dict],
        title: str = "Recent Transactions",
        max_items: int = 10
    ) -> str:
        """Format transaction list for Telegram.

        Args:
            transactions: List of transactions
            title: List title
            max_items: Maximum items to show

        Returns:
            Formatted message
        """
        if not transactions:
            return f"📋 *{title}*\n\nNo transactions found."

        lines = [f"📋 *{title}*", ""]

        for txn in transactions[:max_items]:
            date = txn.get("date", "")
            if isinstance(date, datetime):
                date = date.strftime("%m/%d")

            amount = Decimal(str(txn.get("amount", 0)))
            merchant = txn.get("merchant", txn.get("description", "Unknown"))[:30]

            lines.append(f"• `{date}` {merchant}: {self.CURRENCY_FORMAT.format(amount)}")

        if len(transactions) > max_items:
            lines.append(f"\n_...and {len(transactions) - max_items} more_")

        return self.truncate_message("\n".join(lines))

    def format_approval_summary(
        self,
        pending: int,
        approved_today: int,
        rejected_today: int,
        total_pending_amount: Decimal
    ) -> str:
        """Format approval summary for Telegram.

        Args:
            pending: Number of pending approvals
            approved_today: Approvals today
            rejected_today: Rejections today
            total_pending_amount: Total pending amount

        Returns:
            Formatted message
        """
        lines = [
            "📋 *Approval Summary*",
            "",
            f"• Pending: {pending}",
            f"• Pending Amount: {self.CURRENCY_FORMAT.format(total_pending_amount)}",
            f"• Approved Today: {approved_today}",
            f"• Rejected Today: {rejected_today}",
        ]

        return "\n".join(lines)

    def format_system_status(
        self,
        services: dict[str, bool],
        metrics: dict[str, Any]
    ) -> str:
        """Format system status for Telegram.

        Args:
            services: Service name -> status mapping
            metrics: System metrics

        Returns:
            Formatted message
        """
        lines = [
            "🖥️ *System Status*",
            f"_Last checked: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_",
            "",
            "*Services:*"
        ]

        for service, status in services.items():
            emoji = self.STATUS_EMOJI["success" if status else "error"]
            lines.append(f"• {service}: {emoji}")

        if metrics:
            lines.extend(["", "*Metrics (24h):*"])
            for metric, value in metrics.items():
                lines.append(f"• {metric}: {value}")

        return "\n".join(lines)

    def format_error_message(
        self,
        error: str,
        context: str | None = None,
        suggestion: str | None = None
    ) -> str:
        """Format error message for Telegram.

        Args:
            error: Error description
            context: Optional context
            suggestion: Optional suggestion

        Returns:
            Formatted message
        """
        lines = [
            "❌ *Error*",
            "",
            error
        ]

        if context:
            lines.extend(["", f"_Context: {context}_"])

        if suggestion:
            lines.extend(["", f"💡 {suggestion}"])

        return "\n".join(lines)

    def format_success_message(
        self,
        message: str,
        details: dict | None = None
    ) -> str:
        """Format success message for Telegram.

        Args:
            message: Success message
            details: Optional details

        Returns:
            Formatted message
        """
        lines = [
            "✅ *Success*",
            "",
            message
        ]

        if details:
            lines.append("")
            for key, value in details.items():
                lines.append(f"• {key}: {value}")

        return "\n".join(lines)

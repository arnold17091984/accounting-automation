"""
Telegram Bot Module

Handles Telegram bot interactions including commands, approvals,
file uploads, and report formatting.
"""

from .bot_commands import BotCommandHandler, CommandResult
from .approval_handler import ApprovalHandler, ApprovalRequest, ApprovalResult
from .file_handler import FileHandler, FileProcessResult
from .report_formatter import ReportFormatter

__all__ = [
    # Command Handling
    "BotCommandHandler",
    "CommandResult",
    # Approval Handling
    "ApprovalHandler",
    "ApprovalRequest",
    "ApprovalResult",
    # File Handling
    "FileHandler",
    "FileProcessResult",
    # Report Formatting
    "ReportFormatter",
]

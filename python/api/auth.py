"""
Authentication Module

Provides Telegram ID-based authentication for the dashboard.
"""

import os
from pathlib import Path
from typing import Any

import yaml
from fastapi import Depends, HTTPException, Header, status
from pydantic import BaseModel


class User(BaseModel):
    """Authenticated user model."""

    telegram_id: str
    name: str
    role: str
    permissions: list[str]


class AuthConfig:
    """Authentication configuration loaded from telegram_acl.yaml."""

    def __init__(self, config_path: Path | str | None = None):
        """Initialize auth config.

        Args:
            config_path: Path to telegram_acl.yaml
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "telegram_acl.yaml"

        self.config_path = Path(config_path)
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from YAML."""
        if self.config_path.exists():
            with open(self.config_path) as f:
                self.config = yaml.safe_load(f)
        else:
            # Default config for development
            self.config = {
                "users": [
                    {
                        "telegram_id": "dev",
                        "name": "Developer",
                        "role": "admin",
                    }
                ],
                "permissions": {
                    "admin": ["*"],
                    "accounting_manager": ["approve", "reject", "upload", "view", "report", "budget_edit"],
                    "officer": ["approve_under_10k", "upload", "view", "report"],
                    "viewer": ["view", "report"],
                },
            }

    def get_user(self, telegram_id: str) -> User | None:
        """Get user by Telegram ID.

        Args:
            telegram_id: Telegram user ID

        Returns:
            User object or None if not found
        """
        users = self.config.get("users", [])

        for user_data in users:
            if str(user_data.get("telegram_id")) == str(telegram_id):
                role = user_data.get("role", "viewer")
                permissions = self.config.get("permissions", {}).get(role, ["view"])

                return User(
                    telegram_id=str(telegram_id),
                    name=user_data.get("name", "Unknown"),
                    role=role,
                    permissions=permissions,
                )

        return None

    def has_permission(self, user: User, permission: str) -> bool:
        """Check if user has a specific permission.

        Args:
            user: User object
            permission: Permission to check

        Returns:
            True if user has permission
        """
        if "*" in user.permissions:
            return True

        return permission in user.permissions


# Global auth config instance
auth_config = AuthConfig()


async def get_current_user(
    x_telegram_id: str | None = Header(None, alias="X-Telegram-ID"),
    authorization: str | None = Header(None),
) -> User:
    """Get current authenticated user from request headers.

    Args:
        x_telegram_id: Telegram ID from header
        authorization: Bearer token (for future JWT support)

    Returns:
        Authenticated User

    Raises:
        HTTPException: If authentication fails
    """
    # Development mode: allow any request
    if os.getenv("ENVIRONMENT", "development") == "development":
        if not x_telegram_id:
            # Return dev user
            return User(
                telegram_id="dev",
                name="Developer",
                role="admin",
                permissions=["*"],
            )

    if not x_telegram_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Telegram-ID header",
        )

    user = auth_config.get_user(x_telegram_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not authorized",
        )

    return user


def require_permission(permission: str):
    """Dependency factory for permission checks.

    Args:
        permission: Required permission

    Returns:
        Dependency function
    """
    async def check_permission(user: User = Depends(get_current_user)) -> User:
        if not auth_config.has_permission(user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required",
            )
        return user

    return check_permission


# Common permission dependencies
require_view = require_permission("view")
require_approve = require_permission("approve")
require_admin = require_permission("admin")

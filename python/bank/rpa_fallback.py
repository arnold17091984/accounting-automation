"""
RPA Fallback Module

Playwright-based automation for bank portals when APIs are unavailable.
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import Any
from enum import Enum
import json

logger = logging.getLogger(__name__)


class RPAAction(Enum):
    """Types of RPA actions."""
    LOGIN = "login"
    DOWNLOAD_STATEMENT = "download_statement"
    CHECK_BALANCE = "check_balance"
    INITIATE_TRANSFER = "initiate_transfer"
    VERIFY_TRANSFER = "verify_transfer"
    LOGOUT = "logout"


class RPAStatus(Enum):
    """RPA execution status."""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CAPTCHA_REQUIRED = "captcha_required"
    OTP_REQUIRED = "otp_required"
    SESSION_EXPIRED = "session_expired"
    MAINTENANCE = "maintenance"


@dataclass
class RPAResult:
    """Result of an RPA operation."""

    action: RPAAction
    status: RPAStatus
    message: str
    data: dict = field(default_factory=dict)
    screenshots: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    executed_at: datetime = field(default_factory=datetime.now)
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.status == RPAStatus.SUCCESS

    def to_dict(self) -> dict:
        return {
            "action": self.action.value,
            "status": self.status.value,
            "message": self.message,
            "data": self.data,
            "screenshots": self.screenshots,
            "duration_seconds": self.duration_seconds,
            "executed_at": self.executed_at.isoformat(),
            "error": self.error,
            "success": self.success
        }


@dataclass
class BankCredentials:
    """Bank portal credentials (encrypted in production)."""

    bank: str
    username: str
    password: str
    security_questions: dict = field(default_factory=dict)
    otp_method: str = "sms"  # sms, email, authenticator


class BankPortalAutomation:
    """Automates bank portal operations using Playwright."""

    # Supported banks
    SUPPORTED_BANKS = ["unionbank", "bdo", "metrobank", "bpi"]

    # Default timeouts
    PAGE_TIMEOUT = 30000  # 30 seconds
    NAVIGATION_TIMEOUT = 60000  # 60 seconds

    def __init__(
        self,
        config_dir: Path | str | None = None,
        headless: bool = True,
        screenshot_dir: Path | str | None = None
    ):
        """Initialize RPA automation.

        Args:
            config_dir: Path to configuration directory
            headless: Run browser in headless mode
            screenshot_dir: Directory for screenshots
        """
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent.parent.parent / "config"
        self.headless = headless
        self.screenshot_dir = Path(screenshot_dir) if screenshot_dir else Path("/tmp/rpa_screenshots")
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

        self._browser = None
        self._context = None
        self._page = None

    async def _init_browser(self):
        """Initialize Playwright browser."""
        try:
            from playwright.async_api import async_playwright

            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled"]
            )
            self._context = await self._browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            self._page = await self._context.new_page()
            self._page.set_default_timeout(self.PAGE_TIMEOUT)

        except ImportError:
            raise ImportError("Playwright not installed. Run: pip install playwright && playwright install")

    async def _close_browser(self):
        """Close browser and cleanup."""
        if self._page:
            await self._page.close()
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if hasattr(self, '_playwright'):
            await self._playwright.stop()

    async def _take_screenshot(self, name: str) -> str:
        """Take a screenshot.

        Args:
            name: Screenshot name

        Returns:
            Path to screenshot
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.png"
        path = self.screenshot_dir / filename
        await self._page.screenshot(path=str(path))
        return str(path)

    async def login(
        self,
        credentials: BankCredentials,
        otp_callback: Any = None
    ) -> RPAResult:
        """Login to bank portal.

        Args:
            credentials: Bank credentials
            otp_callback: Async callback for OTP input

        Returns:
            RPAResult
        """
        start_time = datetime.now()
        screenshots = []

        try:
            await self._init_browser()

            bank = credentials.bank.lower()
            if bank not in self.SUPPORTED_BANKS:
                return RPAResult(
                    action=RPAAction.LOGIN,
                    status=RPAStatus.FAILED,
                    message=f"Unsupported bank: {bank}",
                    error=f"Bank {bank} not in supported list"
                )

            # Get bank-specific login handler
            login_handler = getattr(self, f"_login_{bank}", None)
            if not login_handler:
                return RPAResult(
                    action=RPAAction.LOGIN,
                    status=RPAStatus.FAILED,
                    message=f"No login handler for {bank}",
                    error="Handler not implemented"
                )

            result = await login_handler(credentials, otp_callback)
            result.duration_seconds = (datetime.now() - start_time).total_seconds()

            # Take success screenshot
            if result.success:
                ss = await self._take_screenshot(f"login_success_{bank}")
                result.screenshots.append(ss)

            return result

        except Exception as e:
            logger.error(f"Login error: {e}")
            try:
                ss = await self._take_screenshot("login_error")
                screenshots.append(ss)
            except:
                pass

            return RPAResult(
                action=RPAAction.LOGIN,
                status=RPAStatus.FAILED,
                message=f"Login failed: {str(e)}",
                error=str(e),
                screenshots=screenshots,
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )

    async def _login_unionbank(
        self,
        credentials: BankCredentials,
        otp_callback: Any
    ) -> RPAResult:
        """UnionBank-specific login.

        Args:
            credentials: Bank credentials
            otp_callback: OTP callback

        Returns:
            RPAResult
        """
        try:
            # Navigate to UnionBank online
            await self._page.goto("https://online.unionbankph.com/", wait_until="networkidle")

            # Wait for login form
            await self._page.wait_for_selector("#username", timeout=10000)

            # Enter credentials
            await self._page.fill("#username", credentials.username)
            await self._page.fill("#password", credentials.password)

            # Click login
            await self._page.click("button[type='submit']")

            # Wait for OTP or dashboard
            try:
                # Check for OTP prompt
                otp_input = await self._page.wait_for_selector(
                    "input[name='otp'], #otp", timeout=5000
                )

                if otp_input:
                    if otp_callback:
                        otp = await otp_callback()
                        await self._page.fill("input[name='otp'], #otp", otp)
                        await self._page.click("button[type='submit']")
                    else:
                        return RPAResult(
                            action=RPAAction.LOGIN,
                            status=RPAStatus.OTP_REQUIRED,
                            message="OTP required but no callback provided"
                        )
            except:
                pass  # No OTP prompt, continue

            # Wait for dashboard
            await self._page.wait_for_selector(".dashboard, .account-summary", timeout=30000)

            return RPAResult(
                action=RPAAction.LOGIN,
                status=RPAStatus.SUCCESS,
                message="Login successful"
            )

        except Exception as e:
            # Check for maintenance
            page_content = await self._page.content()
            if "maintenance" in page_content.lower():
                return RPAResult(
                    action=RPAAction.LOGIN,
                    status=RPAStatus.MAINTENANCE,
                    message="Bank portal is under maintenance",
                    error="Maintenance mode detected"
                )

            raise

    async def _login_bdo(
        self,
        credentials: BankCredentials,
        otp_callback: Any
    ) -> RPAResult:
        """BDO-specific login."""
        try:
            await self._page.goto("https://online.bdo.com.ph/", wait_until="networkidle")

            # BDO has different login flow
            await self._page.wait_for_selector("#userId", timeout=10000)
            await self._page.fill("#userId", credentials.username)
            await self._page.click("#proceed")

            await self._page.wait_for_selector("#password", timeout=10000)
            await self._page.fill("#password", credentials.password)
            await self._page.click("#login")

            # Wait for dashboard
            await self._page.wait_for_selector(".account-list", timeout=30000)

            return RPAResult(
                action=RPAAction.LOGIN,
                status=RPAStatus.SUCCESS,
                message="BDO login successful"
            )

        except Exception as e:
            raise

    async def download_statement(
        self,
        credentials: BankCredentials,
        account_number: str,
        start_date: date,
        end_date: date,
        output_dir: Path | str
    ) -> RPAResult:
        """Download bank statement.

        Args:
            credentials: Bank credentials
            account_number: Account number
            start_date: Statement start date
            end_date: Statement end date
            output_dir: Directory to save statement

        Returns:
            RPAResult with downloaded file path
        """
        start_time = datetime.now()
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Login first
            login_result = await self.login(credentials)
            if not login_result.success:
                return login_result

            bank = credentials.bank.lower()
            handler = getattr(self, f"_download_statement_{bank}", None)

            if not handler:
                return RPAResult(
                    action=RPAAction.DOWNLOAD_STATEMENT,
                    status=RPAStatus.FAILED,
                    message=f"Statement download not implemented for {bank}"
                )

            result = await handler(account_number, start_date, end_date, output_dir)
            result.duration_seconds = (datetime.now() - start_time).total_seconds()

            return result

        except Exception as e:
            logger.error(f"Statement download error: {e}")
            return RPAResult(
                action=RPAAction.DOWNLOAD_STATEMENT,
                status=RPAStatus.FAILED,
                message=f"Download failed: {str(e)}",
                error=str(e),
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )

        finally:
            await self._close_browser()

    async def _download_statement_unionbank(
        self,
        account_number: str,
        start_date: date,
        end_date: date,
        output_dir: Path
    ) -> RPAResult:
        """Download UnionBank statement."""
        try:
            # Navigate to statement section
            await self._page.click("text=Accounts")
            await self._page.click("text=Statement")

            # Select account
            await self._page.select_option("#account", account_number)

            # Set date range
            await self._page.fill("#fromDate", start_date.strftime("%m/%d/%Y"))
            await self._page.fill("#toDate", end_date.strftime("%m/%d/%Y"))

            # Setup download handler
            download_path = output_dir / f"statement_{account_number}_{start_date}_{end_date}.csv"

            async with self._page.expect_download() as download_info:
                await self._page.click("text=Download CSV")

            download = await download_info.value
            await download.save_as(str(download_path))

            return RPAResult(
                action=RPAAction.DOWNLOAD_STATEMENT,
                status=RPAStatus.SUCCESS,
                message="Statement downloaded successfully",
                data={
                    "file_path": str(download_path),
                    "account": account_number,
                    "period": f"{start_date} to {end_date}"
                }
            )

        except Exception as e:
            raise

    async def check_balance(
        self,
        credentials: BankCredentials,
        account_number: str | None = None
    ) -> RPAResult:
        """Check account balance.

        Args:
            credentials: Bank credentials
            account_number: Optional specific account

        Returns:
            RPAResult with balance data
        """
        start_time = datetime.now()

        try:
            login_result = await self.login(credentials)
            if not login_result.success:
                return login_result

            # Get balances from dashboard
            balances = {}

            # Generic balance extraction
            balance_elements = await self._page.query_selector_all(
                ".balance, .account-balance, [data-balance]"
            )

            for elem in balance_elements:
                text = await elem.inner_text()
                # Parse balance from text
                # This would need bank-specific parsing
                balances[await elem.get_attribute("data-account") or "main"] = text

            return RPAResult(
                action=RPAAction.CHECK_BALANCE,
                status=RPAStatus.SUCCESS,
                message="Balance check successful",
                data={"balances": balances},
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )

        except Exception as e:
            logger.error(f"Balance check error: {e}")
            return RPAResult(
                action=RPAAction.CHECK_BALANCE,
                status=RPAStatus.FAILED,
                message=f"Balance check failed: {str(e)}",
                error=str(e),
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )

        finally:
            await self._close_browser()

    async def logout(self) -> RPAResult:
        """Logout from bank portal.

        Returns:
            RPAResult
        """
        try:
            await self._page.click("text=Logout, text=Sign Out, .logout-btn")
            await self._page.wait_for_url("**/login*", timeout=10000)

            return RPAResult(
                action=RPAAction.LOGOUT,
                status=RPAStatus.SUCCESS,
                message="Logged out successfully"
            )

        except Exception as e:
            return RPAResult(
                action=RPAAction.LOGOUT,
                status=RPAStatus.FAILED,
                message=f"Logout failed: {str(e)}",
                error=str(e)
            )

        finally:
            await self._close_browser()

    def run_sync(self, coro):
        """Run async function synchronously.

        Args:
            coro: Coroutine to run

        Returns:
            Coroutine result
        """
        return asyncio.get_event_loop().run_until_complete(coro)

    def login_sync(
        self,
        credentials: BankCredentials,
        otp_callback: Any = None
    ) -> RPAResult:
        """Synchronous login wrapper.

        Args:
            credentials: Bank credentials
            otp_callback: OTP callback

        Returns:
            RPAResult
        """
        return self.run_sync(self.login(credentials, otp_callback))

    def download_statement_sync(
        self,
        credentials: BankCredentials,
        account_number: str,
        start_date: date,
        end_date: date,
        output_dir: Path | str
    ) -> RPAResult:
        """Synchronous statement download wrapper.

        Args:
            credentials: Bank credentials
            account_number: Account number
            start_date: Start date
            end_date: End date
            output_dir: Output directory

        Returns:
            RPAResult
        """
        return self.run_sync(
            self.download_statement(
                credentials, account_number, start_date, end_date, output_dir
            )
        )

    def check_balance_sync(
        self,
        credentials: BankCredentials,
        account_number: str | None = None
    ) -> RPAResult:
        """Synchronous balance check wrapper.

        Args:
            credentials: Bank credentials
            account_number: Account number

        Returns:
            RPAResult
        """
        return self.run_sync(self.check_balance(credentials, account_number))


# Utility function for n8n
def execute_rpa_action(
    action: str,
    bank: str,
    username: str,
    password: str,
    **kwargs
) -> dict:
    """Execute RPA action (for n8n integration).

    Args:
        action: Action name (login, download_statement, check_balance)
        bank: Bank name
        username: Username
        password: Password
        **kwargs: Additional parameters

    Returns:
        Result dict
    """
    automation = BankPortalAutomation(headless=True)
    credentials = BankCredentials(
        bank=bank,
        username=username,
        password=password
    )

    if action == "login":
        result = automation.login_sync(credentials)
    elif action == "download_statement":
        result = automation.download_statement_sync(
            credentials,
            kwargs.get("account_number", ""),
            kwargs.get("start_date"),
            kwargs.get("end_date"),
            kwargs.get("output_dir", "/tmp")
        )
    elif action == "check_balance":
        result = automation.check_balance_sync(
            credentials,
            kwargs.get("account_number")
        )
    else:
        return {"success": False, "error": f"Unknown action: {action}"}

    return result.to_dict()

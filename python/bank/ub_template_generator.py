"""
UnionBank Template Generator Module

Generates CSV templates for UnionBank bulk transfers (payroll, supplier payments).
"""

import csv
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
from io import StringIO
from pathlib import Path
from typing import Any
from enum import Enum

import yaml

logger = logging.getLogger(__name__)


class TransferType(Enum):
    """Types of bank transfers."""
    PAYROLL = "payroll"
    SUPPLIER = "supplier"
    INTERCOMPANY = "intercompany"
    TAX = "tax"
    UTILITIES = "utilities"


@dataclass
class PayrollEntry:
    """A single payroll entry for transfer."""

    employee_id: str
    employee_name: str
    bank_code: str  # INSTAPAY bank code
    account_number: str
    amount: Decimal
    remarks: str = ""
    department: str = ""
    entity: str = ""

    def validate(self) -> tuple[bool, str]:
        """Validate the entry.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.employee_id:
            return False, "Employee ID is required"

        if not self.account_number:
            return False, f"Account number missing for {self.employee_name}"

        if len(self.account_number) < 10:
            return False, f"Invalid account number for {self.employee_name}"

        if self.amount <= 0:
            return False, f"Invalid amount for {self.employee_name}"

        if not self.bank_code:
            return False, f"Bank code missing for {self.employee_name}"

        return True, ""

    def to_dict(self) -> dict:
        return {
            "employee_id": self.employee_id,
            "employee_name": self.employee_name,
            "bank_code": self.bank_code,
            "account_number": self.account_number,
            "amount": float(self.amount),
            "remarks": self.remarks,
            "department": self.department,
            "entity": self.entity
        }


@dataclass
class TransferBatch:
    """A batch of transfers."""

    batch_id: str
    transfer_type: TransferType
    entity: str
    transfer_date: date
    entries: list[PayrollEntry] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""
    status: str = "pending"  # pending, approved, submitted, completed
    approval_required: bool = True

    @property
    def total_amount(self) -> Decimal:
        """Calculate total transfer amount."""
        return sum(e.amount for e in self.entries)

    @property
    def entry_count(self) -> int:
        """Get number of entries."""
        return len(self.entries)

    def validate(self) -> tuple[bool, list[str]]:
        """Validate all entries.

        Returns:
            Tuple of (all_valid, list of errors)
        """
        errors = []
        for entry in self.entries:
            is_valid, error = entry.validate()
            if not is_valid:
                errors.append(error)

        return len(errors) == 0, errors

    def to_dict(self) -> dict:
        return {
            "batch_id": self.batch_id,
            "transfer_type": self.transfer_type.value,
            "entity": self.entity,
            "transfer_date": self.transfer_date.isoformat(),
            "total_amount": float(self.total_amount),
            "entry_count": self.entry_count,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "status": self.status,
            "entries": [e.to_dict() for e in self.entries]
        }


@dataclass
class TransferTemplate:
    """Generated transfer template."""

    batch_id: str
    filename: str
    content: str
    format: str  # 'csv', 'xlsx'
    checksum: str
    generated_at: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)


class UnionBankTemplateGenerator:
    """Generates UnionBank-compatible transfer templates."""

    # UnionBank CSV format columns
    UB_COLUMNS = [
        "Beneficiary Account Number",
        "Beneficiary Name",
        "Amount",
        "Bank Code",
        "Remarks",
        "Email Address",
        "Mobile Number",
    ]

    # Common bank codes for INSTAPAY
    BANK_CODES = {
        "unionbank": "010419995",
        "bdo": "010530667",
        "bpi": "010040018",
        "metrobank": "010269996",
        "landbank": "010350025",
        "pnb": "010080010",
        "rcbc": "010100013",
        "securitybank": "010140016",
        "chinabank": "010150012",
        "eastwest": "010620015",
        "gcash": "999010025",
        "maya": "999010027",
    }

    def __init__(
        self,
        config_dir: Path | str | None = None,
        source_account: str | None = None
    ):
        """Initialize template generator.

        Args:
            config_dir: Path to configuration directory
            source_account: Default source account number
        """
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent.parent.parent / "config"
        self.source_account = source_account
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration."""
        # Load entity config for account mappings
        entity_file = self.config_dir / "entity_config.yaml"
        if entity_file.exists():
            with open(entity_file) as f:
                self.entity_config = yaml.safe_load(f)
        else:
            self.entity_config = {"entities": {}}

    def get_bank_code(self, bank_name: str) -> str | None:
        """Get INSTAPAY bank code for a bank.

        Args:
            bank_name: Bank name (case-insensitive)

        Returns:
            Bank code or None if not found
        """
        return self.BANK_CODES.get(bank_name.lower())

    def create_batch(
        self,
        transfer_type: TransferType,
        entity: str,
        transfer_date: date,
        created_by: str = ""
    ) -> TransferBatch:
        """Create a new transfer batch.

        Args:
            transfer_type: Type of transfer
            entity: Entity code
            transfer_date: Scheduled transfer date
            created_by: Creator identifier

        Returns:
            TransferBatch
        """
        # Generate batch ID
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        batch_id = f"{entity.upper()}_{transfer_type.value}_{timestamp}"

        return TransferBatch(
            batch_id=batch_id,
            transfer_type=transfer_type,
            entity=entity,
            transfer_date=transfer_date,
            created_by=created_by
        )

    def add_payroll_entry(
        self,
        batch: TransferBatch,
        employee_id: str,
        employee_name: str,
        bank_name: str,
        account_number: str,
        amount: Decimal,
        department: str = "",
        remarks: str = ""
    ) -> PayrollEntry:
        """Add a payroll entry to a batch.

        Args:
            batch: Target batch
            employee_id: Employee ID
            employee_name: Employee full name
            bank_name: Bank name
            account_number: Bank account number
            amount: Transfer amount
            department: Department name
            remarks: Optional remarks

        Returns:
            Created PayrollEntry
        """
        bank_code = self.get_bank_code(bank_name)
        if not bank_code:
            raise ValueError(f"Unknown bank: {bank_name}")

        # Clean account number
        clean_account = account_number.replace("-", "").replace(" ", "")

        # Default remarks if not provided
        if not remarks:
            remarks = f"PAYROLL {batch.transfer_date.strftime('%b %Y').upper()}"

        entry = PayrollEntry(
            employee_id=employee_id,
            employee_name=employee_name,
            bank_code=bank_code,
            account_number=clean_account,
            amount=amount,
            remarks=remarks,
            department=department,
            entity=batch.entity
        )

        batch.entries.append(entry)
        return entry

    def add_entries_from_payroll_data(
        self,
        batch: TransferBatch,
        payroll_data: list[dict]
    ) -> tuple[int, list[str]]:
        """Add entries from payroll data list.

        Args:
            batch: Target batch
            payroll_data: List of payroll records with keys:
                - employee_id, employee_name, bank, account_number, net_pay, department

        Returns:
            Tuple of (added_count, list of errors)
        """
        added = 0
        errors = []

        for record in payroll_data:
            try:
                self.add_payroll_entry(
                    batch=batch,
                    employee_id=str(record.get("employee_id", "")),
                    employee_name=record.get("employee_name", ""),
                    bank_name=record.get("bank", ""),
                    account_number=str(record.get("account_number", "")),
                    amount=Decimal(str(record.get("net_pay", 0))),
                    department=record.get("department", ""),
                    remarks=record.get("remarks", "")
                )
                added += 1
            except Exception as e:
                errors.append(f"Row {record.get('employee_id', '?')}: {str(e)}")

        return added, errors

    def generate_csv(self, batch: TransferBatch) -> TransferTemplate:
        """Generate UnionBank CSV template.

        Args:
            batch: Transfer batch

        Returns:
            TransferTemplate with CSV content
        """
        # Validate batch first
        is_valid, errors = batch.validate()
        if not is_valid:
            raise ValueError(f"Batch validation failed: {'; '.join(errors)}")

        # Generate CSV
        output = StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(self.UB_COLUMNS)

        # Write entries
        for entry in batch.entries:
            writer.writerow([
                entry.account_number,
                entry.employee_name.upper(),
                f"{entry.amount:.2f}",
                entry.bank_code,
                entry.remarks,
                "",  # Email (optional)
                "",  # Mobile (optional)
            ])

        csv_content = output.getvalue()

        # Generate checksum
        checksum = hashlib.sha256(csv_content.encode()).hexdigest()[:16]

        # Generate filename
        filename = f"UB_{batch.batch_id}_{checksum}.csv"

        return TransferTemplate(
            batch_id=batch.batch_id,
            filename=filename,
            content=csv_content,
            format="csv",
            checksum=checksum,
            metadata={
                "entity": batch.entity,
                "transfer_type": batch.transfer_type.value,
                "transfer_date": batch.transfer_date.isoformat(),
                "total_amount": float(batch.total_amount),
                "entry_count": batch.entry_count
            }
        )

    def generate_summary(self, batch: TransferBatch) -> str:
        """Generate human-readable summary.

        Args:
            batch: Transfer batch

        Returns:
            Summary string
        """
        lines = [
            f"📋 *Transfer Batch Summary*",
            f"",
            f"*Batch ID:* `{batch.batch_id}`",
            f"*Entity:* {batch.entity.upper()}",
            f"*Type:* {batch.transfer_type.value.title()}",
            f"*Transfer Date:* {batch.transfer_date.strftime('%Y-%m-%d')}",
            f"",
            f"*Entries:* {batch.entry_count}",
            f"*Total Amount:* ₱{batch.total_amount:,.2f}",
            f"",
        ]

        # Group by department
        by_dept: dict[str, tuple[int, Decimal]] = {}
        for entry in batch.entries:
            dept = entry.department or "Unassigned"
            count, total = by_dept.get(dept, (0, Decimal("0")))
            by_dept[dept] = (count + 1, total + entry.amount)

        if by_dept:
            lines.append("*By Department:*")
            for dept, (count, total) in sorted(by_dept.items()):
                lines.append(f"• {dept}: {count} entries, ₱{total:,.2f}")

        # Group by bank
        by_bank: dict[str, tuple[int, Decimal]] = {}
        bank_name_map = {v: k.upper() for k, v in self.BANK_CODES.items()}
        for entry in batch.entries:
            bank = bank_name_map.get(entry.bank_code, entry.bank_code)
            count, total = by_bank.get(bank, (0, Decimal("0")))
            by_bank[bank] = (count + 1, total + entry.amount)

        if by_bank:
            lines.append("")
            lines.append("*By Bank:*")
            for bank, (count, total) in sorted(by_bank.items()):
                lines.append(f"• {bank}: {count} entries, ₱{total:,.2f}")

        lines.extend([
            "",
            f"_Created: {batch.created_at.strftime('%Y-%m-%d %H:%M')}_"
        ])

        return "\n".join(lines)

    def save_template(
        self,
        template: TransferTemplate,
        output_dir: Path | str
    ) -> Path:
        """Save template to file.

        Args:
            template: Transfer template
            output_dir: Output directory

        Returns:
            Path to saved file
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        file_path = output_dir / template.filename
        file_path.write_text(template.content)

        logger.info(f"Saved template to {file_path}")
        return file_path

    def load_employee_bank_details(
        self,
        data_source: Any
    ) -> list[dict]:
        """Load employee bank details from data source.

        Args:
            data_source: Data source (DB connection, file path, or list)

        Returns:
            List of employee bank detail dicts
        """
        # This would typically connect to HR system or database
        # For now, return empty list - actual implementation would vary
        if isinstance(data_source, list):
            return data_source

        # Could add support for:
        # - Database query
        # - Excel file
        # - API endpoint
        # - Google Sheets

        return []

    def create_payroll_template(
        self,
        entity: str,
        payroll_data: list[dict],
        transfer_date: date | None = None,
        created_by: str = ""
    ) -> tuple[TransferTemplate, TransferBatch]:
        """Convenience method to create payroll template in one call.

        Args:
            entity: Entity code
            payroll_data: List of payroll records
            transfer_date: Transfer date (defaults to today)
            created_by: Creator identifier

        Returns:
            Tuple of (TransferTemplate, TransferBatch)
        """
        transfer_date = transfer_date or date.today()

        # Create batch
        batch = self.create_batch(
            transfer_type=TransferType.PAYROLL,
            entity=entity,
            transfer_date=transfer_date,
            created_by=created_by
        )

        # Add entries
        added, errors = self.add_entries_from_payroll_data(batch, payroll_data)

        if errors:
            logger.warning(f"Payroll template created with {len(errors)} errors")

        # Generate template
        template = self.generate_csv(batch)

        return template, batch

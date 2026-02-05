"""
BIR Tax Form Generator Module

Generates draft BIR tax forms (2550M, 2550Q, 1601C, etc.) for review.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import Any
from enum import Enum
import json

import yaml
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)


class FormType(Enum):
    """BIR form types."""
    VAT_MONTHLY = "2550M"
    VAT_QUARTERLY = "2550Q"
    PERCENTAGE_TAX = "2551Q"
    EWT_MONTHLY = "0619E"
    EWT_QUARTERLY = "1601EQ"
    FWT_QUARTERLY = "1601FQ"
    COMPENSATION_MONTHLY = "1601C"
    COMPENSATION_ANNUAL = "1604CF"
    QUARTERLY_INCOME_TAX = "1702Q"
    CERTIFICATE_EWT = "2307"
    CERTIFICATE_COMPENSATION = "2316"


@dataclass
class FormData:
    """Data for a tax form."""

    form_type: FormType
    entity: str
    tin: str
    period: str
    filing_date: date

    # Taxpayer info
    taxpayer_name: str = ""
    registered_address: str = ""
    zip_code: str = ""
    telephone: str = ""
    rdo_code: str = ""

    # Amounts
    gross_sales: Decimal = Decimal("0")
    taxable_sales: Decimal = Decimal("0")
    exempt_sales: Decimal = Decimal("0")
    zero_rated_sales: Decimal = Decimal("0")
    output_vat: Decimal = Decimal("0")
    input_vat: Decimal = Decimal("0")
    tax_due: Decimal = Decimal("0")
    tax_credits: Decimal = Decimal("0")
    tax_payable: Decimal = Decimal("0")
    surcharge: Decimal = Decimal("0")
    interest: Decimal = Decimal("0")
    compromise: Decimal = Decimal("0")
    total_amount_due: Decimal = Decimal("0")

    # Line items (for detailed forms)
    line_items: list[dict] = field(default_factory=list)

    # Metadata
    prepared_by: str = ""
    prepared_date: date = field(default_factory=date.today)
    is_amended: bool = False

    def to_dict(self) -> dict:
        return {
            "form_type": self.form_type.value,
            "entity": self.entity,
            "tin": self.tin,
            "period": self.period,
            "filing_date": self.filing_date.isoformat(),
            "taxpayer_name": self.taxpayer_name,
            "gross_sales": float(self.gross_sales),
            "output_vat": float(self.output_vat),
            "input_vat": float(self.input_vat),
            "tax_due": float(self.tax_due),
            "tax_payable": float(self.tax_payable),
            "total_amount_due": float(self.total_amount_due),
            "is_amended": self.is_amended
        }


@dataclass
class GeneratedForm:
    """Generated tax form output."""

    form_type: FormType
    entity: str
    period: str
    filename: str
    file_path: Path | None = None
    content: bytes | None = None
    format: str = "pdf"
    generated_at: datetime = field(default_factory=datetime.now)
    data: FormData | None = None
    validation_errors: list[str] = field(default_factory=list)
    is_draft: bool = True

    @property
    def is_valid(self) -> bool:
        return len(self.validation_errors) == 0


class TaxFormGenerator:
    """Generates BIR tax form drafts."""

    def __init__(self, config_dir: Path | str | None = None):
        """Initialize form generator.

        Args:
            config_dir: Path to configuration directory
        """
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration."""
        # Load entity config for TIN, addresses, etc.
        entity_file = self.config_dir.parent.parent / "config" / "entity_config.yaml"
        if entity_file.exists():
            with open(entity_file) as f:
                self.entity_config = yaml.safe_load(f)
        else:
            self.entity_config = {"entities": {}}

        # Load tax rules for form field mappings
        rules_file = self.config_dir / "tax_rules.yaml"
        if rules_file.exists():
            with open(rules_file) as f:
                self.tax_rules = yaml.safe_load(f)
        else:
            self.tax_rules = {}

    def get_entity_info(self, entity: str) -> dict:
        """Get entity tax information.

        Args:
            entity: Entity code

        Returns:
            Entity info dict
        """
        return self.entity_config.get("entities", {}).get(entity, {})

    def validate_form_data(self, data: FormData) -> list[str]:
        """Validate form data.

        Args:
            data: FormData to validate

        Returns:
            List of validation errors
        """
        errors = []

        # Required fields
        if not data.tin or len(data.tin) < 9:
            errors.append("Invalid or missing TIN")

        if not data.taxpayer_name:
            errors.append("Taxpayer name is required")

        if not data.period:
            errors.append("Tax period is required")

        # VAT-specific validations
        if data.form_type in [FormType.VAT_MONTHLY, FormType.VAT_QUARTERLY]:
            if data.output_vat < 0:
                errors.append("Output VAT cannot be negative")
            if data.input_vat < 0:
                errors.append("Input VAT cannot be negative")

        # Amount validations
        if data.tax_payable < 0:
            errors.append("Tax payable cannot be negative")

        return errors

    def generate_form(
        self,
        form_type: FormType,
        entity: str,
        period: str,
        tax_data: dict,
        output_dir: Path | str | None = None
    ) -> GeneratedForm:
        """Generate a BIR tax form.

        Args:
            form_type: Type of form to generate
            entity: Entity code
            period: Tax period
            tax_data: Computed tax data
            output_dir: Output directory for PDF

        Returns:
            GeneratedForm
        """
        # Get entity info
        entity_info = self.get_entity_info(entity)

        # Create form data
        data = FormData(
            form_type=form_type,
            entity=entity,
            tin=entity_info.get("tin", ""),
            period=period,
            filing_date=date.today(),
            taxpayer_name=entity_info.get("full_name", entity.upper()),
            registered_address=entity_info.get("address", ""),
            zip_code=entity_info.get("zip_code", ""),
            rdo_code=entity_info.get("rdo_code", ""),
            gross_sales=Decimal(str(tax_data.get("gross_sales", 0))),
            taxable_sales=Decimal(str(tax_data.get("taxable_sales", 0))),
            exempt_sales=Decimal(str(tax_data.get("exempt_sales", 0))),
            zero_rated_sales=Decimal(str(tax_data.get("zero_rated_sales", 0))),
            output_vat=Decimal(str(tax_data.get("output_vat", 0))),
            input_vat=Decimal(str(tax_data.get("input_vat", 0))),
            tax_due=Decimal(str(tax_data.get("tax_due", 0))),
            tax_credits=Decimal(str(tax_data.get("tax_credits", 0))),
            tax_payable=Decimal(str(tax_data.get("tax_payable", 0))),
            total_amount_due=Decimal(str(tax_data.get("total_amount_due", 0))),
            line_items=tax_data.get("line_items", [])
        )

        # Validate
        errors = self.validate_form_data(data)

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"BIR_{form_type.value}_{entity}_{period}_{timestamp}.pdf"

        # Generate PDF
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            file_path = output_dir / filename

            self._generate_pdf(data, file_path)

            return GeneratedForm(
                form_type=form_type,
                entity=entity,
                period=period,
                filename=filename,
                file_path=file_path,
                data=data,
                validation_errors=errors,
                is_draft=True
            )
        else:
            return GeneratedForm(
                form_type=form_type,
                entity=entity,
                period=period,
                filename=filename,
                data=data,
                validation_errors=errors,
                is_draft=True
            )

    def _generate_pdf(self, data: FormData, file_path: Path) -> None:
        """Generate PDF form.

        Args:
            data: Form data
            file_path: Output path
        """
        # Route to appropriate form generator
        generators = {
            FormType.VAT_MONTHLY: self._generate_vat_form,
            FormType.VAT_QUARTERLY: self._generate_vat_form,
            FormType.PERCENTAGE_TAX: self._generate_percentage_tax_form,
            FormType.EWT_MONTHLY: self._generate_ewt_form,
            FormType.EWT_QUARTERLY: self._generate_ewt_form,
            FormType.COMPENSATION_MONTHLY: self._generate_compensation_form,
            FormType.CERTIFICATE_EWT: self._generate_certificate_2307,
        }

        generator = generators.get(data.form_type, self._generate_generic_form)
        generator(data, file_path)

    def _generate_vat_form(self, data: FormData, file_path: Path) -> None:
        """Generate VAT form (2550M/2550Q).

        Args:
            data: Form data
            file_path: Output path
        """
        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=letter,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch
        )

        styles = getSampleStyleSheet()
        elements = []

        # Header
        elements.append(Paragraph(
            f"<b>BIR Form No. {data.form_type.value}</b>",
            styles['Heading1']
        ))
        elements.append(Paragraph(
            f"{'Monthly' if data.form_type == FormType.VAT_MONTHLY else 'Quarterly'} "
            f"Value-Added Tax Declaration",
            styles['Heading2']
        ))
        elements.append(Paragraph(
            "<i>DRAFT - FOR REVIEW ONLY</i>",
            ParagraphStyle('Draft', parent=styles['Normal'], textColor=colors.red)
        ))
        elements.append(Spacer(1, 0.25*inch))

        # Taxpayer Info
        info_data = [
            ["TIN:", data.tin, "RDO Code:", data.rdo_code],
            ["Taxpayer Name:", data.taxpayer_name, "", ""],
            ["Registered Address:", data.registered_address, "", ""],
            ["Tax Period:", data.period, "Filing Date:", str(data.filing_date)],
        ]

        info_table = Table(info_data, colWidths=[1.2*inch, 2.5*inch, 1*inch, 2*inch])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 0.25*inch))

        # VAT Computation
        elements.append(Paragraph("<b>COMPUTATION OF TAX</b>", styles['Heading3']))

        vat_data = [
            ["", "Amount (PHP)"],
            ["A. SALES/RECEIPTS", ""],
            ["   Taxable Sales/Receipts", f"{data.taxable_sales:,.2f}"],
            ["   Sales to Government", "0.00"],
            ["   Zero-Rated Sales", f"{data.zero_rated_sales:,.2f}"],
            ["   Exempt Sales", f"{data.exempt_sales:,.2f}"],
            ["   Total Sales/Receipts", f"{data.gross_sales:,.2f}"],
            ["", ""],
            ["B. OUTPUT TAX", f"{data.output_vat:,.2f}"],
            ["", ""],
            ["C. INPUT TAX", ""],
            ["   Input Tax from Purchases", f"{data.input_vat:,.2f}"],
            ["   Input Tax Carried Over", "0.00"],
            ["   Total Input Tax", f"{data.input_vat:,.2f}"],
            ["", ""],
            ["D. TAX DUE (B - C)", f"{data.tax_due:,.2f}"],
            ["E. Less: Tax Credits", f"{data.tax_credits:,.2f}"],
            ["F. TAX PAYABLE (D - E)", f"{data.tax_payable:,.2f}"],
            ["", ""],
            ["G. Add: Penalties", ""],
            ["   Surcharge", f"{data.surcharge:,.2f}"],
            ["   Interest", f"{data.interest:,.2f}"],
            ["   Compromise", f"{data.compromise:,.2f}"],
            ["", ""],
            ["H. TOTAL AMOUNT DUE", f"{data.total_amount_due:,.2f}"],
        ]

        vat_table = Table(vat_data, colWidths=[4*inch, 2.5*inch])
        vat_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
            ('LINEBELOW', (0, -1), (-1, -1), 2, colors.black),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        elements.append(vat_table)

        # Footer
        elements.append(Spacer(1, 0.5*inch))
        elements.append(Paragraph(
            f"<i>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</i>",
            styles['Normal']
        ))
        elements.append(Paragraph(
            "<i>This is a computer-generated draft for review purposes only.</i>",
            styles['Normal']
        ))

        doc.build(elements)

    def _generate_percentage_tax_form(self, data: FormData, file_path: Path) -> None:
        """Generate Percentage Tax form (2551Q)."""
        doc = SimpleDocTemplate(str(file_path), pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph(
            f"<b>BIR Form No. {data.form_type.value}</b>",
            styles['Heading1']
        ))
        elements.append(Paragraph(
            "Quarterly Percentage Tax Return",
            styles['Heading2']
        ))
        elements.append(Paragraph(
            "<i>DRAFT - FOR REVIEW ONLY</i>",
            ParagraphStyle('Draft', parent=styles['Normal'], textColor=colors.red)
        ))
        elements.append(Spacer(1, 0.25*inch))

        # Basic computation
        tax_data = [
            ["Taxpayer:", data.taxpayer_name],
            ["TIN:", data.tin],
            ["Period:", data.period],
            ["", ""],
            ["Gross Sales/Receipts:", f"₱{data.gross_sales:,.2f}"],
            ["Tax Rate:", "3%"],
            ["Tax Due:", f"₱{data.tax_due:,.2f}"],
            ["Tax Payable:", f"₱{data.tax_payable:,.2f}"],
        ]

        table = Table(tax_data, colWidths=[2.5*inch, 3*inch])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ]))
        elements.append(table)

        doc.build(elements)

    def _generate_ewt_form(self, data: FormData, file_path: Path) -> None:
        """Generate EWT form (0619E/1601EQ)."""
        doc = SimpleDocTemplate(str(file_path), pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []

        is_quarterly = data.form_type == FormType.EWT_QUARTERLY

        elements.append(Paragraph(
            f"<b>BIR Form No. {data.form_type.value}</b>",
            styles['Heading1']
        ))
        elements.append(Paragraph(
            f"{'Quarterly' if is_quarterly else 'Monthly'} Remittance Return of "
            f"Expanded Withholding Tax",
            styles['Heading2']
        ))
        elements.append(Paragraph(
            "<i>DRAFT - FOR REVIEW ONLY</i>",
            ParagraphStyle('Draft', parent=styles['Normal'], textColor=colors.red)
        ))
        elements.append(Spacer(1, 0.25*inch))

        # Line items
        if data.line_items:
            header = ["ATC", "Description", "Tax Base", "Tax Rate", "Tax Withheld"]
            rows = [header]

            for item in data.line_items:
                rows.append([
                    item.get("atc", ""),
                    item.get("description", ""),
                    f"₱{item.get('tax_base', 0):,.2f}",
                    f"{item.get('rate', 0)*100:.0f}%",
                    f"₱{item.get('tax_withheld', 0):,.2f}",
                ])

            # Total row
            rows.append(["", "TOTAL", "", "", f"₱{data.tax_payable:,.2f}"])

            table = Table(rows, colWidths=[0.7*inch, 2.5*inch, 1.3*inch, 0.8*inch, 1.2*inch])
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
                ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
                ('LINEBELOW', (0, -1), (-1, -1), 2, colors.black),
                ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ]))
            elements.append(table)

        doc.build(elements)

    def _generate_compensation_form(self, data: FormData, file_path: Path) -> None:
        """Generate Compensation Tax form (1601C)."""
        doc = SimpleDocTemplate(str(file_path), pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph(
            f"<b>BIR Form No. {data.form_type.value}</b>",
            styles['Heading1']
        ))
        elements.append(Paragraph(
            "Monthly Remittance Return of Income Taxes Withheld on Compensation",
            styles['Heading2']
        ))
        elements.append(Paragraph(
            "<i>DRAFT - FOR REVIEW ONLY</i>",
            ParagraphStyle('Draft', parent=styles['Normal'], textColor=colors.red)
        ))
        elements.append(Spacer(1, 0.25*inch))

        comp_data = [
            ["Taxpayer:", data.taxpayer_name],
            ["TIN:", data.tin],
            ["Period:", data.period],
            ["", ""],
            ["Total Compensation Paid:", f"₱{data.gross_sales:,.2f}"],
            ["Tax Withheld:", f"₱{data.tax_payable:,.2f}"],
            ["Total Amount Due:", f"₱{data.total_amount_due:,.2f}"],
        ]

        table = Table(comp_data, colWidths=[2.5*inch, 3*inch])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
        ]))
        elements.append(table)

        doc.build(elements)

    def _generate_certificate_2307(self, data: FormData, file_path: Path) -> None:
        """Generate Certificate of Creditable Tax Withheld (2307)."""
        doc = SimpleDocTemplate(str(file_path), pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph(
            "<b>BIR Form No. 2307</b>",
            styles['Heading1']
        ))
        elements.append(Paragraph(
            "Certificate of Creditable Tax Withheld at Source",
            styles['Heading2']
        ))
        elements.append(Spacer(1, 0.25*inch))

        # Withholding agent info
        elements.append(Paragraph("<b>Part I - Withholding Agent</b>", styles['Heading3']))

        # Payee info
        elements.append(Paragraph("<b>Part II - Payee</b>", styles['Heading3']))

        # Tax details
        elements.append(Paragraph("<b>Part III - Details of Income Payment</b>", styles['Heading3']))

        doc.build(elements)

    def _generate_generic_form(self, data: FormData, file_path: Path) -> None:
        """Generate generic tax form."""
        doc = SimpleDocTemplate(str(file_path), pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph(
            f"<b>BIR Form No. {data.form_type.value}</b>",
            styles['Heading1']
        ))
        elements.append(Paragraph(
            "<i>DRAFT - FOR REVIEW ONLY</i>",
            ParagraphStyle('Draft', parent=styles['Normal'], textColor=colors.red)
        ))
        elements.append(Spacer(1, 0.25*inch))

        form_data = [
            ["Taxpayer:", data.taxpayer_name],
            ["TIN:", data.tin],
            ["Period:", data.period],
            ["Tax Due:", f"₱{data.tax_due:,.2f}"],
            ["Tax Payable:", f"₱{data.tax_payable:,.2f}"],
        ]

        table = Table(form_data)
        elements.append(table)

        doc.build(elements)

    def format_filing_reminder(
        self,
        form_type: FormType,
        period: str,
        deadline: date,
        tax_due: Decimal
    ) -> str:
        """Format filing reminder message.

        Args:
            form_type: BIR form type
            period: Tax period
            deadline: Filing deadline
            tax_due: Tax amount due

        Returns:
            Formatted reminder message
        """
        days_until = (deadline - date.today()).days

        if days_until < 0:
            urgency = "🔴 OVERDUE"
        elif days_until <= 3:
            urgency = "🟠 URGENT"
        elif days_until <= 7:
            urgency = "⚠️ Due Soon"
        else:
            urgency = "📅 Upcoming"

        lines = [
            f"{urgency} *Tax Filing Reminder*",
            "",
            f"*Form:* BIR Form {form_type.value}",
            f"*Period:* {period}",
            f"*Deadline:* {deadline.strftime('%B %d, %Y')}",
            f"*Days Remaining:* {max(0, days_until)}",
            f"*Estimated Tax Due:* ₱{tax_due:,.2f}",
            "",
        ]

        if days_until < 0:
            lines.append("⚠️ _This filing is overdue. Penalties may apply._")
        elif days_until <= 3:
            lines.append("⚠️ _Please file immediately to avoid penalties._")

        return "\n".join(lines)

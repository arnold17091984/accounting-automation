"""
PDF Extractor Module

Extracts transaction data from PDF credit card statements using Claude Vision API.
"""

import base64
import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import anthropic

from .csv_parsers.base import ParsedTransaction, ParseResult

logger = logging.getLogger(__name__)


@dataclass
class PDFExtractionResult:
    """Result of PDF extraction."""

    document_type: str = "unknown"  # credit_card_statement, bank_statement, receipt
    bank_name: str | None = None
    account_last_four: str | None = None
    statement_period_start: datetime | None = None
    statement_period_end: datetime | None = None
    transactions: list[ParsedTransaction] = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    extraction_confidence: float = 0.0
    raw_response: dict | None = None
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_parse_result(self) -> ParseResult:
        """Convert to ParseResult for compatibility."""
        return ParseResult(
            bank=self.bank_name or "unknown",
            account_last_four=self.account_last_four,
            statement_period_start=self.statement_period_start,
            statement_period_end=self.statement_period_end,
            transactions=self.transactions,
            summary=self.summary,
            errors=self.errors,
            warnings=self.notes
        )


class PDFExtractor:
    """Extracts transaction data from PDF statements using Claude Vision."""

    # Claude model for vision tasks
    DEFAULT_MODEL = "claude-sonnet-4-5-20250929"

    # Extraction prompt template
    EXTRACTION_PROMPT = """Extract all transactions from this credit card or bank statement PDF.

For each transaction, identify:
1. date (transaction date in YYYY-MM-DD format)
2. posting_date (if different from transaction date, in YYYY-MM-DD format)
3. description (the full transaction description)
4. merchant (extracted/cleaned merchant name)
5. amount (as a number - positive for charges/debits, negative for credits/payments)
6. reference_number (if present)

Also extract:
- document_type: "credit_card_statement", "bank_statement", or "receipt"
- bank_name: The issuing bank
- account_last_four: Last 4 digits of account/card number
- statement_period: start and end dates

Output ONLY a valid JSON object with this structure:
{
  "document_type": "credit_card_statement",
  "bank_name": "BDO",
  "account_last_four": "1234",
  "statement_period": {
    "start": "YYYY-MM-DD",
    "end": "YYYY-MM-DD"
  },
  "transactions": [
    {
      "date": "YYYY-MM-DD",
      "posting_date": "YYYY-MM-DD",
      "description": "string",
      "merchant": "string",
      "amount": 0.00,
      "reference_number": "string or null"
    }
  ],
  "summary": {
    "previous_balance": 0.00,
    "total_credits": 0.00,
    "total_debits": 0.00,
    "new_balance": 0.00,
    "minimum_due": 0.00,
    "due_date": "YYYY-MM-DD"
  },
  "extraction_confidence": 0.95,
  "notes": ["any issues or uncertainties"]
}

IMPORTANT:
- Output ONLY the JSON, no markdown formatting, no explanation
- All amounts should be numbers (not strings)
- Dates must be in YYYY-MM-DD format
- Positive amounts = charges/expenses, negative = credits/payments received
- Extract ALL transactions visible in the document"""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        prompts_dir: Path | str | None = None
    ):
        """Initialize the PDF extractor.

        Args:
            api_key: Anthropic API key (uses ANTHROPIC_API_KEY env var if not provided)
            model: Model to use for extraction
            prompts_dir: Directory containing prompt templates
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model or self.DEFAULT_MODEL
        self.prompts_dir = Path(prompts_dir) if prompts_dir else None

        # Load custom prompt if available
        self._extraction_prompt = self._load_prompt()

    def _load_prompt(self) -> str:
        """Load extraction prompt from file or use default."""
        if self.prompts_dir:
            prompt_file = self.prompts_dir / "pdf_ocr_extract.md"
            if prompt_file.exists():
                with open(prompt_file) as f:
                    content = f.read()
                    # Extract the user prompt section
                    match = re.search(
                        r'## User Prompt.*?```\n(.*?)```',
                        content,
                        re.DOTALL
                    )
                    if match:
                        return match.group(1).strip()

        return self.EXTRACTION_PROMPT

    def extract_from_file(self, file_path: Path | str) -> PDFExtractionResult:
        """Extract transactions from a PDF file.

        Args:
            file_path: Path to the PDF file

        Returns:
            PDFExtractionResult
        """
        file_path = Path(file_path)

        if not file_path.exists():
            return PDFExtractionResult(errors=[f"File not found: {file_path}"])

        if file_path.suffix.lower() != ".pdf":
            return PDFExtractionResult(errors=[f"Not a PDF file: {file_path}"])

        # Read and encode the PDF
        with open(file_path, "rb") as f:
            pdf_data = f.read()

        return self.extract_from_bytes(pdf_data, source_name=file_path.name)

    def extract_from_bytes(
        self,
        pdf_data: bytes,
        source_name: str = "uploaded.pdf"
    ) -> PDFExtractionResult:
        """Extract transactions from PDF bytes.

        Args:
            pdf_data: PDF file contents as bytes
            source_name: Name of the source file (for logging)

        Returns:
            PDFExtractionResult
        """
        result = PDFExtractionResult()

        try:
            # Encode PDF to base64
            pdf_base64 = base64.standard_b64encode(pdf_data).decode("utf-8")

            # Calculate file hash for caching/dedup
            file_hash = hashlib.sha256(pdf_data).hexdigest()[:16]

            logger.info(f"Extracting from PDF: {source_name} (hash: {file_hash})")

            # Call Claude Vision API
            message = self.client.messages.create(
                model=self.model,
                max_tokens=8192,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "document",
                                "source": {
                                    "type": "base64",
                                    "media_type": "application/pdf",
                                    "data": pdf_base64
                                }
                            },
                            {
                                "type": "text",
                                "text": self._extraction_prompt
                            }
                        ]
                    }
                ]
            )

            # Parse response
            response_text = message.content[0].text
            result = self._parse_response(response_text)
            result.raw_response = {
                "model": self.model,
                "usage": {
                    "input_tokens": message.usage.input_tokens,
                    "output_tokens": message.usage.output_tokens
                },
                "file_hash": file_hash
            }

        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            result.errors.append(f"API error: {e}")
        except Exception as e:
            logger.error(f"Extraction error: {e}")
            result.errors.append(f"Extraction error: {e}")

        return result

    def _parse_response(self, response_text: str) -> PDFExtractionResult:
        """Parse Claude's response into structured data.

        Args:
            response_text: Raw response from Claude

        Returns:
            PDFExtractionResult
        """
        result = PDFExtractionResult()

        try:
            # Clean response - remove markdown formatting if present
            cleaned = response_text.strip()
            cleaned = re.sub(r'^```json\s*', '', cleaned)
            cleaned = re.sub(r'^```\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned)
            cleaned = cleaned.strip()

            # Parse JSON
            data = json.loads(cleaned)

            # Extract metadata
            result.document_type = data.get("document_type", "unknown")
            result.bank_name = data.get("bank_name")
            result.account_last_four = data.get("account_last_four")
            result.extraction_confidence = float(data.get("extraction_confidence", 0.0))
            result.notes = data.get("notes", [])

            # Parse statement period
            period = data.get("statement_period", {})
            if period.get("start"):
                try:
                    result.statement_period_start = datetime.strptime(
                        period["start"], "%Y-%m-%d"
                    )
                except ValueError:
                    pass
            if period.get("end"):
                try:
                    result.statement_period_end = datetime.strptime(
                        period["end"], "%Y-%m-%d"
                    )
                except ValueError:
                    pass

            # Parse transactions
            for txn_data in data.get("transactions", []):
                try:
                    txn = self._parse_transaction(txn_data)
                    if txn:
                        result.transactions.append(txn)
                except Exception as e:
                    result.notes.append(f"Failed to parse transaction: {e}")

            # Parse summary
            result.summary = data.get("summary", {})

        except json.JSONDecodeError as e:
            result.errors.append(f"Failed to parse JSON response: {e}")
            result.notes.append(f"Raw response: {response_text[:500]}")
        except Exception as e:
            result.errors.append(f"Parse error: {e}")

        return result

    def _parse_transaction(self, data: dict) -> ParsedTransaction | None:
        """Parse a transaction from extracted data.

        Args:
            data: Transaction dictionary from Claude response

        Returns:
            ParsedTransaction or None
        """
        # Parse date
        date_str = data.get("date")
        if not date_str:
            return None

        try:
            txn_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return None

        # Parse posting date
        posting_date = None
        posting_str = data.get("posting_date")
        if posting_str:
            try:
                posting_date = datetime.strptime(posting_str, "%Y-%m-%d")
            except ValueError:
                pass

        # Parse amount
        amount = data.get("amount", 0)
        if isinstance(amount, str):
            amount = float(amount.replace(",", "").replace("₱", ""))
        amount = Decimal(str(amount))

        return ParsedTransaction(
            date=txn_date,
            posting_date=posting_date,
            description=data.get("description", ""),
            merchant=data.get("merchant", ""),
            amount=amount,
            reference=data.get("reference_number"),
            transaction_type="debit" if amount > 0 else "credit",
            raw_data=data
        )

    def verify_extraction(self, result: PDFExtractionResult) -> dict:
        """Verify extraction quality.

        Args:
            result: Extraction result to verify

        Returns:
            Verification report
        """
        report = {
            "valid": True,
            "issues": [],
            "warnings": [],
            "stats": {
                "transaction_count": len(result.transactions),
                "total_debits": 0,
                "total_credits": 0
            }
        }

        # Check confidence
        if result.extraction_confidence < 0.7:
            report["warnings"].append(
                f"Low extraction confidence: {result.extraction_confidence}"
            )

        # Check for errors
        if result.errors:
            report["valid"] = False
            report["issues"].extend(result.errors)

        # Verify transactions
        for i, txn in enumerate(result.transactions):
            # Check date is reasonable
            if txn.date.year < 2020 or txn.date > datetime.now():
                report["warnings"].append(f"Transaction {i}: unusual date {txn.date}")

            # Check amount is reasonable
            if abs(txn.amount) > 10000000:  # 10M PHP
                report["warnings"].append(
                    f"Transaction {i}: very large amount {txn.amount}"
                )

            # Tally amounts
            if txn.amount > 0:
                report["stats"]["total_debits"] += float(txn.amount)
            else:
                report["stats"]["total_credits"] += abs(float(txn.amount))

        # Verify totals match summary if provided
        if result.summary:
            expected_debits = result.summary.get("total_debits", 0)
            if expected_debits and abs(report["stats"]["total_debits"] - expected_debits) > 1:
                report["warnings"].append(
                    f"Debit total mismatch: extracted {report['stats']['total_debits']}, "
                    f"expected {expected_debits}"
                )

        return report


def extract_pdf(
    file_path: Path | str,
    api_key: str | None = None
) -> PDFExtractionResult:
    """Convenience function to extract transactions from a PDF.

    Args:
        file_path: Path to PDF file
        api_key: Optional Anthropic API key

    Returns:
        PDFExtractionResult
    """
    extractor = PDFExtractor(api_key=api_key)
    return extractor.extract_from_file(file_path)

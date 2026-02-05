"""
Telegram File Handler Module

Handles file uploads (CSV/PDF) from Telegram for processing.
"""

import logging
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
import hashlib
import json

import yaml
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


@dataclass
class FileProcessResult:
    """Result of file processing."""

    success: bool
    file_id: str
    file_type: str  # 'csv', 'pdf', 'unknown'
    message: str
    transactions_found: int = 0
    transactions_processed: int = 0
    duplicates_skipped: int = 0
    errors: list[str] = field(default_factory=list)
    data: dict = field(default_factory=dict)


class FileHandler:
    """Handles file uploads from Telegram."""

    SUPPORTED_EXTENSIONS = {".csv", ".pdf", ".xlsx", ".xls"}
    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB

    def __init__(
        self,
        config_dir: Path | str | None = None,
        db_connection: Any = None,
        temp_dir: Path | str | None = None
    ):
        """Initialize file handler.

        Args:
            config_dir: Path to configuration directory
            db_connection: PostgreSQL database connection
            temp_dir: Directory for temporary files
        """
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent.parent.parent / "config"
        self.db = db_connection
        self.temp_dir = Path(temp_dir) if temp_dir else Path(tempfile.gettempdir()) / "accounting_uploads"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
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

    def can_upload(self, user_id: int) -> bool:
        """Check if user can upload files.

        Args:
            user_id: Telegram user ID

        Returns:
            True if user has upload permission
        """
        for user in self.acl_config.get("users", []):
            if user.get("telegram_id") == user_id:
                role = user.get("role", "viewer")
                permissions = self.acl_config.get("permissions", {}).get(role, [])
                return "upload" in permissions or "*" in permissions
        return False

    def validate_file(
        self,
        file_name: str,
        file_size: int
    ) -> tuple[bool, str]:
        """Validate uploaded file.

        Args:
            file_name: Original file name
            file_size: File size in bytes

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check size
        if file_size > self.MAX_FILE_SIZE:
            return False, f"File too large. Maximum size: {self.MAX_FILE_SIZE // 1024 // 1024}MB"

        # Check extension
        ext = Path(file_name).suffix.lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            return False, f"Unsupported file type. Supported: {', '.join(self.SUPPORTED_EXTENSIONS)}"

        return True, ""

    def detect_file_type(self, file_name: str, content: bytes) -> str:
        """Detect file type from name and content.

        Args:
            file_name: Original file name
            content: File content

        Returns:
            File type string
        """
        ext = Path(file_name).suffix.lower()

        if ext == ".csv":
            return "csv"
        elif ext == ".pdf":
            return "pdf"
        elif ext in {".xlsx", ".xls"}:
            return "excel"

        # Try to detect from content
        if content[:4] == b"%PDF":
            return "pdf"
        elif b"," in content[:1000] and b"\n" in content[:1000]:
            return "csv"

        return "unknown"

    def save_upload(
        self,
        file_id: str,
        file_name: str,
        content: bytes,
        user_id: int,
        entity: str | None = None
    ) -> Path:
        """Save uploaded file to temp directory.

        Args:
            file_id: Telegram file ID
            file_name: Original file name
            content: File content
            user_id: Uploader's user ID
            entity: Entity code if known

        Returns:
            Path to saved file
        """
        # Generate safe filename
        ext = Path(file_name).suffix.lower()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = f"{timestamp}_{user_id}_{file_id[:8]}{ext}"

        file_path = self.temp_dir / safe_name
        file_path.write_bytes(content)

        # Log upload
        self._log_upload(file_id, file_name, file_path, user_id, entity)

        return file_path

    def process_csv(
        self,
        file_path: Path,
        user_id: int,
        entity: str | None = None
    ) -> FileProcessResult:
        """Process CSV file upload.

        Args:
            file_path: Path to CSV file
            user_id: Uploader's user ID
            entity: Entity code

        Returns:
            FileProcessResult
        """
        try:
            content = file_path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            try:
                content = file_path.read_text(encoding="latin-1")
            except Exception as e:
                return FileProcessResult(
                    success=False,
                    file_id=file_path.name,
                    file_type="csv",
                    message=f"Failed to read file: {e}",
                    errors=[str(e)]
                )

        # Import parser
        try:
            from card_processor.csv_parsers.generic import detect_and_parse
        except ImportError:
            return FileProcessResult(
                success=False,
                file_id=file_path.name,
                file_type="csv",
                message="CSV parser module not available",
                errors=["Module import failed"]
            )

        # Parse CSV
        parse_result = detect_and_parse(content)

        if not parse_result.success:
            return FileProcessResult(
                success=False,
                file_id=file_path.name,
                file_type="csv",
                message=f"Failed to parse CSV: {', '.join(parse_result.errors)}",
                errors=parse_result.errors
            )

        # Process transactions
        from card_processor.duplicate_detector import DuplicateDetector
        from card_processor.categorizer import TransactionCategorizer

        detector = DuplicateDetector()
        categorizer = TransactionCategorizer(self.config_dir)

        existing_txns = self._get_recent_transactions(entity) if self.db else []

        processed = 0
        duplicates = 0
        errors = []

        for txn in parse_result.transactions:
            # Check duplicate
            dup_check = detector.check(txn, existing_txns)
            if dup_check and dup_check.is_duplicate:
                duplicates += 1
                continue

            # Categorize
            try:
                categorized = categorizer.categorize(txn, entity=entity or "unknown")
                self._save_transaction(categorized, entity, parse_result.bank_name)
                processed += 1
            except Exception as e:
                errors.append(f"Row error: {e}")

        # Build summary message
        lines = [
            f"✅ *CSV Processed Successfully*",
            "",
            f"*Bank:* {parse_result.bank_name.upper()}",
            f"*Transactions Found:* {len(parse_result.transactions)}",
            f"*Processed:* {processed}",
            f"*Duplicates Skipped:* {duplicates}",
        ]

        if errors:
            lines.extend([
                "",
                f"*Errors:* {len(errors)}"
            ])

        return FileProcessResult(
            success=True,
            file_id=file_path.name,
            file_type="csv",
            message="\n".join(lines),
            transactions_found=len(parse_result.transactions),
            transactions_processed=processed,
            duplicates_skipped=duplicates,
            errors=errors,
            data={
                "bank": parse_result.bank_name,
                "entity": entity
            }
        )

    def process_pdf(
        self,
        file_path: Path,
        user_id: int,
        entity: str | None = None
    ) -> FileProcessResult:
        """Process PDF file upload (credit card statement).

        Args:
            file_path: Path to PDF file
            user_id: Uploader's user ID
            entity: Entity code

        Returns:
            FileProcessResult
        """
        try:
            from card_processor.pdf_extractor import PDFExtractor
        except ImportError:
            return FileProcessResult(
                success=False,
                file_id=file_path.name,
                file_type="pdf",
                message="PDF extractor module not available",
                errors=["Module import failed"]
            )

        try:
            extractor = PDFExtractor(config_dir=self.config_dir)
            extract_result = extractor.extract(file_path)

            if not extract_result.success:
                return FileProcessResult(
                    success=False,
                    file_id=file_path.name,
                    file_type="pdf",
                    message=f"Failed to extract PDF: {', '.join(extract_result.errors)}",
                    errors=extract_result.errors
                )

            # Process extracted transactions
            from card_processor.duplicate_detector import DuplicateDetector
            from card_processor.categorizer import TransactionCategorizer

            detector = DuplicateDetector()
            categorizer = TransactionCategorizer(self.config_dir)

            existing_txns = self._get_recent_transactions(entity) if self.db else []

            processed = 0
            duplicates = 0
            errors = []

            for txn in extract_result.transactions:
                # Check duplicate
                dup_check = detector.check(txn, existing_txns)
                if dup_check and dup_check.is_duplicate:
                    duplicates += 1
                    continue

                # Categorize
                try:
                    categorized = categorizer.categorize(txn, entity=entity or "unknown")
                    self._save_transaction(categorized, entity, "pdf_extract")
                    processed += 1
                except Exception as e:
                    errors.append(f"Transaction error: {e}")

            lines = [
                f"✅ *PDF Processed Successfully*",
                "",
                f"*Statement Period:* {extract_result.data.get('period', 'Unknown')}",
                f"*Transactions Found:* {len(extract_result.transactions)}",
                f"*Processed:* {processed}",
                f"*Duplicates Skipped:* {duplicates}",
            ]

            if errors:
                lines.extend([
                    "",
                    f"*Errors:* {len(errors)}"
                ])

            return FileProcessResult(
                success=True,
                file_id=file_path.name,
                file_type="pdf",
                message="\n".join(lines),
                transactions_found=len(extract_result.transactions),
                transactions_processed=processed,
                duplicates_skipped=duplicates,
                errors=errors,
                data=extract_result.data
            )

        except Exception as e:
            logger.error(f"PDF processing error: {e}")
            return FileProcessResult(
                success=False,
                file_id=file_path.name,
                file_type="pdf",
                message=f"PDF processing failed: {e}",
                errors=[str(e)]
            )

    def process_file(
        self,
        file_path: Path,
        user_id: int,
        entity: str | None = None
    ) -> FileProcessResult:
        """Process uploaded file based on type.

        Args:
            file_path: Path to file
            user_id: Uploader's user ID
            entity: Entity code

        Returns:
            FileProcessResult
        """
        file_type = self.detect_file_type(
            file_path.name,
            file_path.read_bytes()[:1000]
        )

        if file_type == "csv":
            return self.process_csv(file_path, user_id, entity)
        elif file_type == "pdf":
            return self.process_pdf(file_path, user_id, entity)
        else:
            return FileProcessResult(
                success=False,
                file_id=file_path.name,
                file_type=file_type,
                message=f"Unsupported file type: {file_type}",
                errors=["Cannot process this file type"]
            )

    def get_upload_keyboard(self, user_id: int) -> dict | None:
        """Get entity selection keyboard for upload.

        Args:
            user_id: User ID

        Returns:
            Inline keyboard or None
        """
        if not self.can_upload(user_id):
            return None

        # Load entity config
        entity_file = self.config_dir / "entity_config.yaml"
        if entity_file.exists():
            with open(entity_file) as f:
                entity_config = yaml.safe_load(f)
        else:
            return None

        entities = list(entity_config.get("entities", {}).keys())

        rows = []
        for i in range(0, len(entities), 2):
            row = []
            for entity in entities[i:i+2]:
                row.append({
                    "text": entity.upper(),
                    "callback_data": f"upload_entity_{entity}"
                })
            rows.append(row)

        return {"inline_keyboard": rows}

    def _log_upload(
        self,
        file_id: str,
        file_name: str,
        file_path: Path,
        user_id: int,
        entity: str | None
    ) -> None:
        """Log file upload to database."""
        if not self.db:
            return

        try:
            # Calculate file hash
            file_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()

            with self.db.cursor() as cur:
                cur.execute("""
                    INSERT INTO file_uploads (
                        telegram_file_id, original_name, stored_path,
                        file_hash, uploaded_by, entity, status
                    ) VALUES (%s, %s, %s, %s, %s, %s, 'pending')
                """, (
                    file_id, file_name, str(file_path),
                    file_hash, str(user_id), entity
                ))
                self.db.commit()
        except Exception as e:
            logger.error(f"Failed to log upload: {e}")

    def _get_recent_transactions(self, entity: str | None) -> list[dict]:
        """Get recent transactions for duplicate checking."""
        if not self.db:
            return []

        try:
            with self.db.cursor(cursor_factory=RealDictCursor) as cur:
                if entity:
                    cur.execute("""
                        SELECT id, txn_date, amount, merchant, description
                        FROM transactions
                        WHERE entity = %s
                          AND created_at > NOW() - INTERVAL '90 days'
                        ORDER BY txn_date DESC
                        LIMIT 1000
                    """, (entity,))
                else:
                    cur.execute("""
                        SELECT id, txn_date, amount, merchant, description
                        FROM transactions
                        WHERE created_at > NOW() - INTERVAL '90 days'
                        ORDER BY txn_date DESC
                        LIMIT 1000
                    """)
                return cur.fetchall()
        except Exception as e:
            logger.error(f"Failed to get recent transactions: {e}")
            return []

    def _save_transaction(
        self,
        categorized: Any,
        entity: str | None,
        source_bank: str
    ) -> None:
        """Save categorized transaction to database."""
        if not self.db:
            return

        try:
            with self.db.cursor() as cur:
                cur.execute("""
                    INSERT INTO transactions (
                        source, source_bank, entity, txn_date, description,
                        merchant, amount, account_code, account_name, category,
                        classification_method, classification_confidence,
                        anomaly_flag, anomaly_reason, raw_data
                    ) VALUES (
                        'credit_card', %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s
                    )
                """, (
                    source_bank,
                    entity or "unknown",
                    categorized.transaction.date,
                    categorized.transaction.description,
                    categorized.transaction.merchant,
                    float(categorized.transaction.amount),
                    categorized.account_code,
                    categorized.account_name,
                    categorized.category,
                    categorized.classification_method,
                    categorized.confidence,
                    categorized.is_anomaly,
                    categorized.anomaly_reason,
                    json.dumps(categorized.transaction.raw_data)
                ))
                self.db.commit()
        except Exception as e:
            logger.error(f"Failed to save transaction: {e}")

    def cleanup_temp_files(self, max_age_hours: int = 24) -> int:
        """Clean up old temporary files.

        Args:
            max_age_hours: Maximum age of files to keep

        Returns:
            Number of files deleted
        """
        import time

        deleted = 0
        now = time.time()
        max_age_seconds = max_age_hours * 3600

        for file_path in self.temp_dir.iterdir():
            if file_path.is_file():
                age = now - file_path.stat().st_mtime
                if age > max_age_seconds:
                    try:
                        file_path.unlink()
                        deleted += 1
                    except Exception as e:
                        logger.warning(f"Failed to delete {file_path}: {e}")

        return deleted

"""
PipelineRunner — orchestrates report generation, email delivery, and Drive upload.

Decouples report generation from email/Drive side effects so that dry-run and
test-email modes can suppress I/O without touching generator logic.
"""
import importlib
import logging
import os
import re
from collections import Counter
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Tuple, TypedDict

import pandas as pd

from core.storage import StorageClient
from reports import get_generator
from core.email_sender import EmailSender
from core.drive_service import DriveService

logger = logging.getLogger(__name__)
_EMAIL_LIKE_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class PipelineResult(TypedDict):
    """Structured result returned by PipelineRunner.run() on every exit path."""
    success: bool
    records_processed: int
    emails_sent: int
    errors: List[str]


class PipelineRunner:
    """
    Orchestrates the full report pipeline for any registered report type.

    Lifecycle:
        1. Instantiate the generator via get_generator(report_type)()
        2. Call generator.generate() — returns a Path (file or directory)
        3. Collect all *.pdf files from the output
        4. For each PDF: optionally upload to Drive, then send email
        5. Return a PipelineResult with counts and any per-student errors

    Modes:
        dry_run=True     — generate() runs; email and Drive upload are skipped
        test_email=addr  — all emails redirected to addr; Drive upload suppressed
        (default)        — email sent to student address; Drive upload attempted
    """

    def __init__(
        self,
        report_type: str,
        dry_run: bool = False,
        test_email: Optional[str] = None,
        assessment_name: Optional[str] = None,
    ) -> None:
        self.report_type = report_type
        self.dry_run = dry_run
        self.test_email = test_email
        self.assessment_name = assessment_name or ""

    # ── Private helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _safe_filename_component(value: str) -> str:
        cleaned = value.strip()
        cleaned = "".join("_" if ch in '<>:"/\\|?*' else ch for ch in cleaned)
        cleaned = " ".join(cleaned.split()).rstrip(".")
        return cleaned or "unknown"

    def _parse_filename_contract(
        self,
        pdf_path: Path,
    ) -> Optional[Tuple[str, str, str]]:
        """
        Parse the locked filename contract:
            informe_{report_type}_{assessment_name}_{email}.pdf

        Uses split(maxsplit=3) so email may contain underscores safely.
        """
        stem = pdf_path.stem
        prefix = f"informe_{self._safe_filename_component(self.report_type)}_"
        if not stem.startswith(prefix):
            return None
        payload = stem[len(prefix):]
        if not payload:
            return None

        if self.assessment_name:
            expected_assessment = self._safe_filename_component(self.assessment_name)
            expected_prefix = f"{expected_assessment}_"
            if payload.startswith(expected_prefix):
                assessment_name = expected_assessment
                email = payload[len(expected_prefix):]
                if not email or not _EMAIL_LIKE_RE.match(email):
                    return None
                return self.report_type, assessment_name, email

        # Fallback for legacy/no-assessment_name invocations:
        # enumerate all possible `_` split points and only accept an unambiguous
        # email-like suffix match. If ambiguous, fail closed to avoid misrouting.
        candidates: list[tuple[str, str]] = []
        for idx, ch in enumerate(payload):
            if ch != "_":
                continue
            assessment_name = payload[:idx]
            email = payload[idx + 1 :]
            if not assessment_name or not email:
                continue
            if _EMAIL_LIKE_RE.match(email):
                candidates.append((assessment_name, email))

        if len(candidates) != 1:
            return None

        assessment_name, email = candidates[0]
        return self.report_type, assessment_name, email

    def _extract_email_from_pdf(self, pdf_path: Path) -> Optional[str]:
        """
        Parse the student email from a PDF filename.

        Expected locked pattern: informe_{report_type}_{assessment_name}_{email}.pdf
        """
        parsed = self._parse_filename_contract(pdf_path)
        if parsed is None:
            return None
        return parsed[2]

    def _get_email_template(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Resolve the per-report-type email template for this runner instance.

        Attempts to import ``reports.{report_type}.email_template`` and reads
        its ``SUBJECT`` and ``BODY`` string constants.

        Returns:
            (subject, body) tuple — both are None when the module is absent or
            raises an unexpected error. Never raises.
        """
        module_path = f"reports.{self.report_type}.email_template"
        try:
            mod = importlib.import_module(module_path)
            return mod.SUBJECT, mod.BODY
        except ImportError:
            logger.debug(
                "[%s] No email_template module found at %s — using defaults",
                self.report_type,
                module_path,
            )
            return None, None
        except Exception as exc:
            logger.warning(
                "[%s] Unexpected error loading email template from %s: %s",
                self.report_type,
                module_path,
                exc,
            )
            return None, None

    def _send_email(
        self,
        recipient: str,
        pdf_path: Path,
        drive_link: Optional[str],
        correlation_key: Optional[str] = None,
    ) -> bool:
        """Send a single report email. Returns True on success, False otherwise."""
        subject, body = self._get_email_template()
        sender = EmailSender()
        return sender.send_comprehensive_report_email(
            recipient_email=recipient,
            pdf_content=pdf_path.read_bytes(),
            username=recipient,
            filename=pdf_path.name,
            drive_link=drive_link,
            correlation_key=correlation_key,
            subject=subject,
            body=body,
        )

    def _upload_to_drive(self, pdf_path: Path) -> Optional[str]:
        """
        Upload a PDF to Google Drive. Returns the file_id or None on failure.

        Drive upload failures are non-fatal — they are logged as warnings and the
        email loop continues regardless.
        """
        try:
            return DriveService().upload_file(
                pdf_path,
                folder_id=os.getenv("GOOGLE_DRIVE_FOLDER_ID", ""),
            )
        except Exception as exc:
            logger.warning(f"[{self.report_type}] Drive upload failed: {exc}")
            return None

    def _event_key_for_pdf(self, pdf_path: Path) -> Optional[str]:
        """Return stable event correlation key based on filename semantics."""
        parsed = self._parse_filename_contract(pdf_path)
        if parsed is None:
            return None
        report_type, assessment_name, student_email = parsed
        return f"{report_type}|{assessment_name}|{student_email}"

    def _dedupe_key_for_pdf(self, pdf_path: Path) -> Optional[Tuple[str, str, str]]:
        """Return dedupe key tuple: (report_type, assessment_name, email)."""
        return self._parse_filename_contract(pdf_path)

    def _processed_emails_xlsx_path(self) -> Path:
        """Per-report XLSX ledger path: data/{report_type}/processed_emails.xlsx."""
        return Path("data") / self.report_type / "processed_emails.xlsx"

    def _storage(self) -> StorageClient:
        """Storage backend abstraction (local/GCS)."""
        return StorageClient()

    def _load_processed_email_keys(self) -> set[Tuple[str, str, str]]:
        """Load dedupe keys from XLSX ledger, if present."""
        ledger = self._processed_emails_xlsx_path()
        storage = self._storage()
        if not storage.exists(str(ledger)):
            return set()
        try:
            data = storage.read_bytes(str(ledger))
            df = pd.read_excel(BytesIO(data), dtype=str)
        except Exception as exc:
            logger.warning(
                "[%s] Failed reading processed-emails ledger %s: %s",
                self.report_type,
                ledger,
                exc,
            )
            return set()

        required_cols = {"report_type", "assessment_name", "email"}
        if not required_cols.issubset(df.columns):
            logger.warning(
                "[%s] processed-emails ledger missing columns %s in %s",
                self.report_type,
                sorted(required_cols - set(df.columns)),
                ledger,
            )
            return set()

        keys: set[Tuple[str, str, str]] = set()
        for _, row in df.iterrows():
            key = (
                str(row.get("report_type", "") or ""),
                str(row.get("assessment_name", "") or ""),
                str(row.get("email", "") or ""),
            )
            if all(key):
                keys.add(key)
        return keys

    def _append_processed_email_row(
        self,
        report_type: str,
        assessment_name: str,
        email: str,
        attachment_filename: str,
        event_key: str,
    ) -> bool:
        """Append one successful-send row to processed_emails.xlsx."""
        ledger = self._processed_emails_xlsx_path()
        storage = self._storage()
        storage.ensure_directory(str(ledger.parent))
        row = {
            "report_type": report_type,
            "assessment_name": assessment_name,
            "email": email,
            "attachment_filename": attachment_filename,
            "sent_at_utc": datetime.now(timezone.utc).isoformat(),
            "event_key": event_key,
        }

        try:
            if storage.exists(str(ledger)):
                data = storage.read_bytes(str(ledger))
                df = pd.read_excel(BytesIO(data), dtype=str)
                df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            else:
                df = pd.DataFrame([row])
            out = BytesIO()
            df.to_excel(out, index=False)
            storage.write_bytes(
                str(ledger),
                out.getvalue(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            return True
        except Exception as exc:
            logger.error(
                "[%s] Failed writing processed-emails ledger %s: %s",
                self.report_type,
                ledger,
                exc,
            )
            return False

    def _filter_duplicate_test_de_eje_artifacts(
        self,
        pdfs: List[Path],
        errors: List[str],
    ) -> List[Path]:
        """
        Guard one-event/one-email contract for test_de_eje.

        If multiple PDFs resolve to the same event key, only the first one is kept
        and an actionable error is recorded with event/report identifiers.
        """
        if self.report_type != "test_de_eje":
            return pdfs

        event_keys = [self._event_key_for_pdf(pdf) for pdf in pdfs]
        duplicates = {
            key: count for key, count in Counter(event_keys).items()
            if key and count > 1
        }
        if not duplicates:
            return pdfs

        logger.warning(
            "[%s] Cardinality drift detected for test_de_eje artifacts: %s",
            self.report_type,
            duplicates,
        )

        seen = set()
        filtered: List[Path] = []
        for pdf in pdfs:
            key = self._event_key_for_pdf(pdf)
            if key and key in duplicates:
                if key in seen:
                    errors.append(
                        f"Duplicate artifact skipped report_type={self.report_type} "
                        f"event_key={key} attachment={pdf.name}"
                    )
                    continue
                seen.add(key)
            filtered.append(pdf)
        return filtered

    # ── Public interface ───────────────────────────────────────────────────────

    def run(self) -> PipelineResult:
        """
        Execute the full pipeline and return a structured result.

        Always returns a PipelineResult — no code path returns None.
        success=False only when generate() (or generator instantiation) raises.
        Individual email failures are caught, appended to errors[], and the loop
        continues to the next student.
        """
        records_processed = 0
        emails_sent = 0
        errors: List[str] = []

        # ── Step 1: Generate reports ───────────────────────────────────────────
        try:
            GeneratorClass = get_generator(self.report_type)
            generator = GeneratorClass()
            output_path = generator.generate(assessment_name=self.assessment_name)
        except Exception as exc:
            errors.append(str(exc))
            logger.error(f"[{self.report_type}] Generation failed: {exc}")
            return PipelineResult(
                success=False,
                records_processed=0,
                emails_sent=0,
                errors=errors,
            )

        # ── Step 2: Collect PDFs ───────────────────────────────────────────────
        if output_path.is_dir():
            pdfs = sorted(output_path.glob("*.pdf"))
        else:
            pdfs = [output_path] if output_path.suffix == ".pdf" else []

        pdfs = self._filter_duplicate_test_de_eje_artifacts(pdfs, errors)
        records_processed = len(pdfs)
        processed_email_keys = self._load_processed_email_keys()

        # ── Step 3: Email loop ─────────────────────────────────────────────────
        for pdf_path in pdfs:
            filename_parts = self._parse_filename_contract(pdf_path)
            student_email = self._extract_email_from_pdf(pdf_path)
            event_key = self._event_key_for_pdf(pdf_path) or "unknown"
            if not student_email or filename_parts is None:
                logger.warning(
                    f"[{self.report_type}] Could not extract email from "
                    f"{pdf_path.name}, skipping"
                )
                errors.append(
                    f"Could not extract email report_type={self.report_type} "
                    f"attachment={pdf_path.name} event_key={event_key}"
                )
                continue
            report_type_part, assessment_name_part, _ = filename_parts
            dedupe_key = self._dedupe_key_for_pdf(pdf_path)
            if report_type_part != self.report_type:
                errors.append(
                    f"Filename report_type mismatch report_type={self.report_type} "
                    f"filename_report_type={report_type_part} attachment={pdf_path.name}"
                )
                continue

            if dedupe_key is None:
                errors.append(
                    f"Could not compute dedupe key report_type={self.report_type} "
                    f"attachment={pdf_path.name}"
                )
                continue

            if not self.test_email and dedupe_key in processed_email_keys:
                logger.info(
                    "[%s] Skipping already-sent report for %s assessment=%s",
                    self.report_type,
                    student_email,
                    assessment_name_part,
                )
                continue

            # Dry-run: skip all I/O
            if self.dry_run:
                logger.info(
                    f"[{self.report_type}] Dry-run: would send to "
                    f"{student_email} ({pdf_path.name})"
                )
                continue

            # Determine recipient and Drive link
            recipient = self.test_email if self.test_email else student_email
            drive_link = None

            # Drive upload only in normal mode (not test-email, not dry-run)
            if not self.test_email:
                drive_link = self._upload_to_drive(pdf_path)

            # Send email — catch all exceptions so the loop continues
            try:
                sent = self._send_email(
                    recipient,
                    pdf_path,
                    drive_link,
                    correlation_key=event_key,
                )
                if sent:
                    emails_sent += 1
                    if not self.test_email:
                        appended = self._append_processed_email_row(
                            report_type=report_type_part,
                            assessment_name=assessment_name_part,
                            email=student_email,
                            attachment_filename=pdf_path.name,
                            event_key=event_key,
                        )
                        if appended:
                            processed_email_keys.add(dedupe_key)
                        else:
                            errors.append(
                                f"Processed-emails ledger append failed "
                                f"report_type={self.report_type} event_key={event_key} "
                                f"recipient={recipient} attachment={pdf_path.name}"
                            )
                    logger.info(
                        f"[{self.report_type}] Sent: {student_email} -> "
                        f"{recipient} ({pdf_path.name})"
                    )
                else:
                    errors.append(
                        f"Email returned False report_type={self.report_type} "
                        f"event_key={event_key} recipient={recipient} "
                        f"attachment={pdf_path.name}"
                    )
                    logger.warning(
                        f"[{self.report_type}] Failed: {student_email}: "
                        f"send returned False"
                    )
            except Exception as exc:
                errors.append(
                    f"Email error report_type={self.report_type} "
                    f"event_key={event_key} recipient={recipient} "
                    f"attachment={pdf_path.name}: {exc}"
                )
                logger.error(
                    f"[{self.report_type}] Failed: {student_email}: {exc}"
                )

        # ── Step 4: Final summary log ──────────────────────────────────────────
        logger.info(
            f"[{self.report_type}] Pipeline complete: "
            f"records_processed={records_processed} "
            f"emails_sent={emails_sent} "
            f"errors={len(errors)}"
        )

        return PipelineResult(
            success=True,
            records_processed=records_processed,
            emails_sent=emails_sent,
            errors=errors,
        )

"""
PipelineRunner — orchestrates report generation, email delivery, and Drive upload.

Decouples report generation from email/Drive side effects so that dry-run and
test-email modes can suppress I/O without touching generator logic.
"""
import importlib
import logging
import os
from collections import Counter
from pathlib import Path
from typing import List, Optional, Tuple, TypedDict

from reports import get_generator
from core.email_sender import EmailSender
from core.drive_service import DriveService

logger = logging.getLogger(__name__)


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

    def _extract_email_from_pdf(self, pdf_path: Path) -> Optional[str]:
        """
        Parse the student email from a PDF filename.

        Expected pattern: informe_{email}_{atype}.pdf
        - parts[0]  == 'informe'  (prefix)
        - parts[-1] == atype      (e.g. 'M1', 'CL', 'CIEN', 'HYST')
        - parts[1:-1] are email segments (re-joined with '_')

        Returns None if the filename does not match the expected pattern.
        """
        stem = pdf_path.stem  # filename without .pdf
        parts = stem.split("_")
        if len(parts) < 3 or parts[0] != "informe":
            return None
        email = "_".join(parts[1:-1])
        return email if email else None

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
        student_email = self._extract_email_from_pdf(pdf_path)
        if not student_email:
            return None
        stem_parts = pdf_path.stem.split("_")
        assessment_type = stem_parts[-1] if len(stem_parts) >= 3 else "unknown"
        return f"{student_email}|{assessment_type}"

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

        # ── Step 3: Email loop ─────────────────────────────────────────────────
        for pdf_path in pdfs:
            student_email = self._extract_email_from_pdf(pdf_path)
            event_key = self._event_key_for_pdf(pdf_path) or "unknown"
            if not student_email:
                logger.warning(
                    f"[{self.report_type}] Could not extract email from "
                    f"{pdf_path.name}, skipping"
                )
                errors.append(
                    f"Could not extract email report_type={self.report_type} "
                    f"attachment={pdf_path.name} event_key={event_key}"
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

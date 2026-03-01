"""
PipelineRunner — orchestrates report generation, email delivery, and Drive upload.

Decouples report generation from email/Drive side effects so that dry-run and
test-email modes can suppress I/O without touching generator logic.
"""
import logging
import os
from pathlib import Path
from typing import List, Optional, TypedDict

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
    ) -> None:
        self.report_type = report_type
        self.dry_run = dry_run
        self.test_email = test_email

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

    def _send_email(
        self,
        recipient: str,
        pdf_path: Path,
        drive_link: Optional[str],
    ) -> bool:
        """Send a single report email. Returns True on success, False otherwise."""
        sender = EmailSender()
        return sender.send_comprehensive_report_email(
            recipient_email=recipient,
            pdf_content=pdf_path.read_bytes(),
            username=recipient,
            filename=pdf_path.name,
            drive_link=drive_link,
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
            output_path = generator.generate()
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

        records_processed = len(pdfs)

        # ── Step 3: Email loop ─────────────────────────────────────────────────
        for pdf_path in pdfs:
            student_email = self._extract_email_from_pdf(pdf_path)
            if not student_email:
                logger.warning(
                    f"[{self.report_type}] Could not extract email from "
                    f"{pdf_path.name}, skipping"
                )
                errors.append(f"Could not extract email from {pdf_path.name}")
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
                sent = self._send_email(recipient, pdf_path, drive_link)
                if sent:
                    emails_sent += 1
                    logger.info(
                        f"[{self.report_type}] Sent: {student_email} -> "
                        f"{recipient} ({pdf_path.name})"
                    )
                else:
                    errors.append(f"Email returned False for {student_email}")
                    logger.warning(
                        f"[{self.report_type}] Failed: {student_email}: "
                        f"send returned False"
                    )
            except Exception as exc:
                errors.append(f"Email error for {student_email}: {exc}")
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

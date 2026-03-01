"""
BaseReportGenerator — Abstract base class for all report generators.

Lifecycle: download() -> analyze() -> render(), orchestrated by generate().
Email sending is NOT part of the generator — PipelineRunner (Phase 4) handles it.
"""
import os
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class BaseReportGenerator(ABC):
    """
    Abstract base class for all report generators.

    Subclasses MUST implement: download(), analyze(), render()
    Subclasses MAY override: generate() (not recommended — use the lifecycle methods)

    The generate() method calls the three lifecycle steps in order and returns
    the path to the produced report file. Callers (PipelineRunner, Phase 4) use
    this path for email attachment and Drive upload.
    """

    def __init__(self, report_type: str):
        """
        Initialize with report type string.

        Sets up per-report namespaced data directory paths and ensures all
        directories exist at runtime (auto-created, no .gitkeep in repo).

        Args:
            report_type: String identifier matching the REGISTRY key
                         (e.g., "diagnosticos", "diagnosticos_uim")
        """
        self.report_type = report_type

        # Per-report namespaced data paths (ORG-02: data/<report_type>/*)
        self.data_dir = Path("data") / report_type
        self.raw_dir = self.data_dir / "raw"
        self.processed_dir = self.data_dir / "processed"
        self.analysis_dir = self.data_dir / "analysis"
        self.questions_dir = self.data_dir / "questions"

        # Per-report template path (ORG-01: templates/<report_type>/)
        self.templates_dir = Path("templates") / report_type

        # Per-report email deduplication (ORG-03: per-report-type tracking)
        self.processed_emails_path = self.data_dir / "processed_emails.csv"

        # Ensure runtime directories exist
        self._ensure_data_dirs()

    def _ensure_data_dirs(self) -> None:
        """Create per-report data directories at runtime if they don't exist."""
        for directory in [
            self.raw_dir,
            self.processed_dir,
            self.analysis_dir,
            self.questions_dir,
        ]:
            os.makedirs(directory, exist_ok=True)

    @abstractmethod
    def download(self) -> Any:
        """
        Download raw assessment responses from LearnWorlds API.

        Returns:
            Implementation-defined — typically a list of response dicts or a DataFrame
        """
        ...

    @abstractmethod
    def analyze(self, download_result: Any) -> Any:
        """
        Analyze downloaded assessment data.

        Args:
            download_result: Output from download()

        Returns:
            Implementation-defined — typically a DataFrame or analysis dict
        """
        ...

    @abstractmethod
    def render(self, analysis_result: Any) -> Path:
        """
        Render report file(s) from analysis data.

        Args:
            analysis_result: Output from analyze()

        Returns:
            Path to the produced report file on disk
        """
        ...

    def generate(self) -> Path:
        """
        Orchestrate the full pipeline: download -> analyze -> render.

        This is a concrete method. Subclasses should override the three
        lifecycle methods, not this orchestrator.

        Returns:
            Path to the produced report file on disk.
            Callers (PipelineRunner) use this path for email attachment.
        """
        logger.info(f"[{self.report_type}] Starting report generation")

        download_result = self.download()
        logger.info(f"[{self.report_type}] Download complete")

        analysis_result = self.analyze(download_result)
        logger.info(f"[{self.report_type}] Analysis complete")

        output_path = self.render(analysis_result)
        logger.info(f"[{self.report_type}] Report rendered: {output_path}")

        return output_path

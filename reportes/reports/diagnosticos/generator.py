"""
DiagnosticosGenerator — Plugin for the diagnosticos report type.

Implements the BaseReportGenerator lifecycle (download -> analyze -> render)
for all four diagnosticos assessment types: M1, CL, CIEN, HYST.

This is the first concrete plugin in the unified reports framework.
Full-run semantics only (no incremental_mode — Phase 4 handles that).
"""

import os
import logging
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from reports.base import BaseReportGenerator
from reports.diagnosticos.report_generator import ReportGenerator
from core.assessment_downloader import AssessmentDownloader
from core.assessment_analyzer import AssessmentAnalyzer
from core.storage import StorageClient

logger = logging.getLogger(__name__)


class DiagnosticosGenerator(BaseReportGenerator):
    """
    Generator plugin for the diagnosticos report type.

    Wraps the existing standalone logic into the unified plugin interface.
    Assessment-type list lives here only — never in core/.
    """

    ASSESSMENT_TYPES: List[str] = ["M1", "CL", "CIEN", "HYST"]

    def __init__(self):
        super().__init__("diagnosticos")
        # Pass data_dir="data/diagnosticos" so the downloader's raw_dir/processed_dir
        # align with the BaseReportGenerator namespaced paths.
        self.downloader = AssessmentDownloader(data_dir="data/diagnosticos")
        self.analyzer = AssessmentAnalyzer()
        self.report_generator = ReportGenerator()
        self.storage = StorageClient()
        self._assessment_ids = {
            "M1": os.getenv("M1_ASSESSMENT_ID"),
            "CL": os.getenv("CL_ASSESSMENT_ID"),
            "CIEN": os.getenv("CIEN_ASSESSMENT_ID"),
            "HYST": os.getenv("HYST_ASSESSMENT_ID"),
        }

    # ------------------------------------------------------------------
    # Lifecycle: download
    # ------------------------------------------------------------------

    def download(self, assessment_name: str = "") -> Dict[str, pd.DataFrame]:
        """
        Download and process all assessment responses.

        Mirrors diagnosticos/main.py download_all_assessments + process_all_assessments.
        For each assessment type:
          - If an assessment ID env var is set, download via API (incremental-from-existing).
          - Otherwise fall back to loading from existing JSON on disk.
        Saves processed CSV to self.processed_dir.

        Returns:
            Dict mapping assessment type -> processed DataFrame.
            Types with no data are omitted silently (errors logged).
        """
        processed: Dict[str, pd.DataFrame] = {}

        for atype in self.ASSESSMENT_TYPES:
            assessment_id = self._assessment_ids.get(atype)
            try:
                if assessment_id:
                    # Download via API (uses incremental-from-existing JSON logic inside)
                    logger.info(f"[diagnosticos] Downloading {atype} (id={assessment_id})")
                    result = self.downloader.download_and_process_assessment(
                        assessment_id=assessment_id,
                        assessment_name=atype,
                        incremental_mode=False,
                    )
                    # download_and_process_assessment saves the CSV itself;
                    # load it back as a DataFrame if it was saved
                    csv_path = self.downloader.get_csv_file_path(atype)
                    if csv_path.exists():
                        df = pd.read_csv(str(csv_path), sep=";")
                        processed[atype] = df
                        logger.info(f"[diagnosticos] {atype}: {len(df)} processed rows")
                    else:
                        logger.warning(f"[diagnosticos] {atype}: CSV not found after download")
                else:
                    # No API key — load from existing JSON on disk
                    logger.info(f"[diagnosticos] {atype}: no assessment ID, loading from JSON")
                    responses = self.downloader.load_responses_from_json(atype)
                    if responses:
                        csv_path_str = self.downloader.save_responses_to_csv(
                            responses, atype, return_df=False
                        )
                        csv_path = Path(csv_path_str)
                        if csv_path.exists():
                            df = pd.read_csv(str(csv_path), sep=";")
                            processed[atype] = df
                            logger.info(f"[diagnosticos] {atype}: {len(df)} rows from JSON")
                        else:
                            logger.warning(f"[diagnosticos] {atype}: CSV not written")
                    else:
                        logger.warning(f"[diagnosticos] {atype}: no JSON data found, skipping")

            except Exception as exc:
                logger.error(f"[diagnosticos] download failed for {atype}: {exc}")

        logger.info(
            f"[diagnosticos] download complete: {list(processed.keys())} assessment(s) ready"
        )
        return processed

    # ------------------------------------------------------------------
    # Lifecycle: analyze
    # ------------------------------------------------------------------

    def analyze(self, download_result: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        Analyze processed CSVs and produce per-assessment analysis DataFrames.

        Mirrors diagnosticos/main.py analyze_assessment.
        Uses question banks from self.questions_dir and writes analysis CSVs to
        self.analysis_dir, then returns in-memory DataFrames for render().

        Args:
            download_result: Output from download() — dict of assessment type -> DataFrame.

        Returns:
            Dict mapping assessment type -> analysis DataFrame.
        """
        analysis: Dict[str, pd.DataFrame] = {}

        for atype in self.ASSESSMENT_TYPES:
            question_bank_path = str(self.questions_dir / f"{atype}.csv")
            processed_csv_path = str(self.processed_dir / f"{atype}.csv")
            output_path = str(self.analysis_dir / f"{atype}.csv")

            # Check prerequisites
            if not Path(question_bank_path).exists():
                logger.warning(
                    f"[diagnosticos] {atype}: question bank not found at {question_bank_path}, skipping"
                )
                continue

            if not Path(processed_csv_path).exists():
                logger.warning(
                    f"[diagnosticos] {atype}: processed CSV not found at {processed_csv_path}, skipping"
                )
                continue

            try:
                logger.info(f"[diagnosticos] Analyzing {atype}")
                analysis_df = self.analyzer.analyze_assessment_from_csv(
                    assessment_name=atype,
                    question_bank_path=question_bank_path,
                    processed_csv_path=processed_csv_path,
                    output_path=output_path,
                    return_df=True,
                )
                if analysis_df is not None and not analysis_df.empty:
                    analysis[atype] = analysis_df
                    logger.info(f"[diagnosticos] {atype}: {len(analysis_df)} rows analyzed")
                else:
                    logger.warning(f"[diagnosticos] {atype}: analyzer returned empty result")

            except Exception as exc:
                logger.error(f"[diagnosticos] analyze failed for {atype}: {exc}")

        logger.info(
            f"[diagnosticos] analysis complete: {list(analysis.keys())} assessment(s) analyzed"
        )
        return analysis

    # ------------------------------------------------------------------
    # Lifecycle: render
    # ------------------------------------------------------------------

    def render(self, analysis_result: Dict[str, pd.DataFrame]) -> Path:
        """
        Generate per-student PDF reports for all assessment types.

        Mirrors diagnosticos/main.py generate_reports.
        Writes PDFs to data/diagnosticos/output/ as:
            informe_{email}_{atype}.pdf

        Args:
            analysis_result: Output from analyze() — dict of assessment type -> DataFrame.

        Returns:
            Path to the output directory (data/diagnosticos/output/).
        """
        output_dir = self.analysis_dir.parent / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        total_pdfs = 0
        types_rendered = 0

        for atype, analysis_df in analysis_result.items():
            pdf_count = 0
            try:
                for _, row in analysis_df.iterrows():
                    email = row.get("email", "")
                    if not email:
                        logger.warning(f"[diagnosticos] {atype}: row missing email, skipping")
                        continue

                    user_info = {"username": email, "email": email}
                    row_dict = row.to_dict()

                    try:
                        pdf_content = self.report_generator.generate_pdf(
                            assessment_title=atype,
                            analysis_result=row_dict,
                            user_info=user_info,
                            incremental_mode=False,
                            analysis_df=analysis_df,
                        )
                        if pdf_content is not None:
                            pdf_path = output_dir / f"informe_{email}_{atype}.pdf"
                            pdf_path.write_bytes(pdf_content)
                            pdf_count += 1
                        else:
                            logger.warning(
                                f"[diagnosticos] {atype}: generate_pdf returned None for {email}"
                            )

                    except Exception as exc:
                        logger.error(
                            f"[diagnosticos] {atype}: PDF generation failed for {email}: {exc}"
                        )

                logger.info(
                    f"[diagnosticos] {atype}: {pdf_count} PDFs written to {output_dir}"
                )
                total_pdfs += pdf_count
                types_rendered += 1

            except Exception as exc:
                logger.error(f"[diagnosticos] render failed for {atype}: {exc}")

        logger.info(
            f"[diagnosticos] render complete: {total_pdfs} PDFs across {types_rendered} assessment type(s)"
        )
        return output_dir

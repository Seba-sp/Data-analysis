"""
DiagnosticosUIMGenerator — Plugin for the diagnosticos_uim report type.

Implements the BaseReportGenerator lifecycle (download -> analyze -> render)
for all five diagnosticos_uim assessment types: M1, F30M, B30M, Q30M, HYST.

Mirrors DiagnosticosGenerator exactly but with UIM-specific assessment types,
env vars (M1_UIM_ASSESSMENT_ID, etc.), and the UIM report_generator module.

Full-run semantics only (no incremental_mode).
"""

import os
import logging
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from reports.base import BaseReportGenerator
from reports.diagnosticos_uim.report_generator import ReportGenerator
from core.assessment_downloader import AssessmentDownloader
from core.assessment_analyzer import AssessmentAnalyzer
from core.storage import StorageClient

logger = logging.getLogger(__name__)


class DiagnosticosUIMGenerator(BaseReportGenerator):
    """
    Generator plugin for the diagnosticos_uim report type.

    Wraps the existing standalone logic into the unified plugin interface.
    Assessment types differ from diagnosticos: F30M, B30M, Q30M are UIM-specific.
    Env vars use *_UIM_ASSESSMENT_ID naming to avoid collision with diagnosticos.
    """

    ASSESSMENT_TYPES: List[str] = ["M1", "F30M", "B30M", "Q30M", "HYST"]

    def __init__(self):
        super().__init__("diagnosticos_uim")
        # Pass data_dir="data/diagnosticos_uim" so the downloader's raw_dir/processed_dir
        # align with the BaseReportGenerator namespaced paths.
        self.downloader = AssessmentDownloader(data_dir="data/diagnosticos_uim")
        self.analyzer = AssessmentAnalyzer()
        self.report_generator = ReportGenerator()
        self.storage = StorageClient()
        self._assessment_ids = {
            "M1":   os.getenv("M1_UIM_ASSESSMENT_ID"),
            "F30M": os.getenv("F30M_UIM_ASSESSMENT_ID"),
            "B30M": os.getenv("B30M_UIM_ASSESSMENT_ID"),
            "Q30M": os.getenv("Q30M_UIM_ASSESSMENT_ID"),
            "HYST": os.getenv("HYST_UIM_ASSESSMENT_ID"),
        }

    # ------------------------------------------------------------------
    # Lifecycle: download
    # ------------------------------------------------------------------

    def download(self) -> Dict[str, pd.DataFrame]:
        """
        Download and process all assessment responses.

        Mirrors DiagnosticosGenerator.download() but for UIM assessment types.
        For each assessment type:
          - If an assessment ID env var is set, download via API.
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
                    # Download via API
                    logger.info(f"[diagnosticos_uim] Downloading {atype} (id={assessment_id})")
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
                        logger.info(f"[diagnosticos_uim] {atype}: {len(df)} processed rows")
                    else:
                        logger.warning(f"[diagnosticos_uim] {atype}: CSV not found after download")
                else:
                    # No API key — load from existing JSON on disk
                    logger.info(f"[diagnosticos_uim] {atype}: no assessment ID, loading from JSON")
                    responses = self.downloader.load_responses_from_json(atype)
                    if responses:
                        csv_path_str = self.downloader.save_responses_to_csv(
                            responses, atype, return_df=False
                        )
                        csv_path = Path(csv_path_str)
                        if csv_path.exists():
                            df = pd.read_csv(str(csv_path), sep=";")
                            processed[atype] = df
                            logger.info(f"[diagnosticos_uim] {atype}: {len(df)} rows from JSON")
                        else:
                            logger.warning(f"[diagnosticos_uim] {atype}: CSV not written")
                    else:
                        logger.warning(f"[diagnosticos_uim] {atype}: no JSON data found, skipping")

            except Exception as exc:
                logger.error(f"[diagnosticos_uim] download failed for {atype}: {exc}")

        logger.info(
            f"[diagnosticos_uim] download complete: {list(processed.keys())} assessment(s) ready"
        )
        return processed

    # ------------------------------------------------------------------
    # Lifecycle: analyze
    # ------------------------------------------------------------------

    def analyze(self, download_result: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        Analyze processed CSVs and produce per-assessment analysis DataFrames.

        Mirrors DiagnosticosGenerator.analyze() but uses UIM question banks
        from data/diagnosticos_uim/questions/ and writes analysis CSVs to
        data/diagnosticos_uim/analysis/.

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
                    f"[diagnosticos_uim] {atype}: question bank not found at {question_bank_path}, skipping"
                )
                continue

            if not Path(processed_csv_path).exists():
                logger.warning(
                    f"[diagnosticos_uim] {atype}: processed CSV not found at {processed_csv_path}, skipping"
                )
                continue

            try:
                logger.info(f"[diagnosticos_uim] Analyzing {atype}")
                analysis_df = self.analyzer.analyze_assessment_from_csv(
                    assessment_name=atype,
                    question_bank_path=question_bank_path,
                    processed_csv_path=processed_csv_path,
                    output_path=output_path,
                    return_df=True,
                )
                if analysis_df is not None and not analysis_df.empty:
                    analysis[atype] = analysis_df
                    logger.info(f"[diagnosticos_uim] {atype}: {len(analysis_df)} rows analyzed")
                else:
                    logger.warning(f"[diagnosticos_uim] {atype}: analyzer returned empty result")

            except Exception as exc:
                logger.error(f"[diagnosticos_uim] analyze failed for {atype}: {exc}")

        logger.info(
            f"[diagnosticos_uim] analysis complete: {list(analysis.keys())} assessment(s) analyzed"
        )
        return analysis

    # ------------------------------------------------------------------
    # Lifecycle: render
    # ------------------------------------------------------------------

    def render(self, analysis_result: Dict[str, pd.DataFrame]) -> Path:
        """
        Generate per-student PDF reports for all UIM assessment types.

        Mirrors DiagnosticosGenerator.render() but for UIM types.
        Writes PDFs to data/diagnosticos_uim/output/ as:
            informe_{email}_{atype}.pdf

        Args:
            analysis_result: Output from analyze() — dict of assessment type -> DataFrame.

        Returns:
            Path to the output directory (data/diagnosticos_uim/output/).
        """
        output_dir = self.data_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        total_pdfs = 0
        types_rendered = 0

        for atype, analysis_df in analysis_result.items():
            pdf_count = 0
            try:
                for _, row in analysis_df.iterrows():
                    email = row.get("email", "")
                    if not email:
                        logger.warning(f"[diagnosticos_uim] {atype}: row missing email, skipping")
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
                                f"[diagnosticos_uim] {atype}: generate_pdf returned None for {email}"
                            )

                    except Exception as exc:
                        logger.error(
                            f"[diagnosticos_uim] {atype}: PDF generation failed for {email}: {exc}"
                        )

                logger.info(
                    f"[diagnosticos_uim] {atype}: {pdf_count} PDFs written to {output_dir}"
                )
                total_pdfs += pdf_count
                types_rendered += 1

            except Exception as exc:
                logger.error(f"[diagnosticos_uim] render failed for {atype}: {exc}")

        logger.info(
            f"[diagnosticos_uim] render complete: {total_pdfs} PDFs across {types_rendered} assessment type(s)"
        )
        return output_dir

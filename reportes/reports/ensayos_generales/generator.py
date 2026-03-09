import logging
from pathlib import Path
import pandas as pd
from reports.base import BaseReportGenerator
from reports.ensayos_generales.report_generator import ReportGenerator

logger = logging.getLogger(__name__)


class EnsayosGeneralesGenerator(BaseReportGenerator):
    def __init__(self):
        super().__init__("ensayos_generales")
        self.report_generator = ReportGenerator()

    def download(self, assessment_name: str = "") -> pd.DataFrame:
        # Fail fast if analysis.csv is missing — no warn-and-continue
        csv_path = self.analysis_dir / "analysis.csv"
        if not csv_path.exists():
            raise FileNotFoundError(
                f"[ensayos_generales] Required input file not found: {csv_path}\n"
                f"Prepare analysis.csv manually and copy it to: {csv_path.resolve()}"
            )
        df = pd.read_csv(str(csv_path), sep=',')
        # If reading with comma yields only 1 column, log the column count and raise
        if len(df.columns) < 2:
            raise ValueError(
                f"[ensayos_generales] analysis.csv appears to use a non-comma separator "
                f"(got {len(df.columns)} column(s)). Confirm the separator and re-export as comma-delimited."
            )
        logger.info(f"[ensayos_generales] Loaded analysis.csv: {len(df)} rows, {len(df.columns)} columns")
        return df

    def analyze(self, download_result: pd.DataFrame) -> pd.DataFrame:
        # No API-based analysis step — data is pre-analyzed in the CSV
        return download_result

    def render(self, analysis_result: pd.DataFrame) -> Path:
        output_dir = self.data_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        pdf_count = 0
        for _, row in analysis_result.iterrows():
            username = row.get("username", row.get("email", ""))
            if not username:
                logger.warning("[ensayos_generales] Row missing username/email, skipping")
                continue
            try:
                pdf_content = self.report_generator.generate_report(str(username))
                if pdf_content:
                    pdf_path = output_dir / f"resultados_{username}.pdf"
                    pdf_path.write_bytes(pdf_content)
                    pdf_count += 1
                else:
                    logger.warning(f"[ensayos_generales] generate_report returned None for {username}")
            except Exception as exc:
                logger.error(f"[ensayos_generales] PDF generation failed for {username}: {exc}")
        logger.info(f"[ensayos_generales] render complete: {pdf_count} PDFs written to {output_dir}")
        return output_dir

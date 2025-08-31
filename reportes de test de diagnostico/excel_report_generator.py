#!/usr/bin/env python3
"""
Excel Report Generator

Generates the same tables as the current ReportGenerator, but sources all data
from an Excel workbook named "analisis de datos.xlsx" with the following sheets:
 - "Reporte"
 - "M1" with columns: [user_id/email, level, passed_lectures, failed_lectures]
 - "CL" with columns: [user_id/email, level, skill_{skill}_percentage] for skills [localizar, interpretar, evaluar]
 - "CIEN" with columns: [user_id/email, level, materia_{materia}_passed_lectures, materia_{materia}_failed_lectures, materia_{materia}_passed_lectures_count, materia_{materia}_failed_lectures_count] for materias [biología, química, física]
 - "HYST" with columns: [user_id/email, level, passed_lectures, failed_lectures]

All lecture lists are pipe-separated ("|").
"""

import os
import logging
from typing import Dict, Any, List, Optional

import pandas as pd
from weasyprint import HTML


logger = logging.getLogger(__name__)

# Local HTML templates mirroring the current report layout
TABLE_ROW_TEMPLATE = (
    """
        <tr>
          <td>{lecture_name}</td>
          <td class=\"status-cell {status_class}\">{status_value}</td>
        </tr>"""
)

SECTION_TEMPLATE = (
    """
<section class=\"page {assessment_class}\">
  <div class=\"content\">
    <p class=\"TituloAlumno Negrita\">Resultados - {assessment_name}</p>
    <p class=\"subtitle\">{subtitle}</p>
    {continuation_text}
    <table class=\"results-table\">
      <thead>
        <tr>
          <th>Lección</th>
          <th style=\"text-align:center;\">{column_header}</th>
        </tr>
      </thead>
      <tbody>
        {table_rows}
      </tbody>
    </table>
  </div>
</section>"""
)


class ExcelReportGenerator:
    """Generates PDF reports by reading analysis data from an Excel workbook."""

    def __init__(
        self,
        excel_path: str = "data/analysis/analisis de datos.xlsx",
        html_template_path: str = "templates/plantilla_plan_de_estudio.html",
    ) -> None:
        self.excel_path = excel_path
        self.html_template_path = html_template_path
        # Cached workbook and DataFrames to avoid reloading for each user
        self._xl: Optional[pd.ExcelFile] = None
        self._df_m1: Optional[pd.DataFrame] = None
        self._df_cl: Optional[pd.DataFrame] = None
        self._df_cien: Optional[pd.DataFrame] = None
        self._df_hyst: Optional[pd.DataFrame] = None
        self._df_reporte: Optional[pd.DataFrame] = None

    def _ensure_loaded(self) -> None:
        """Load and cache the Excel workbook and required sheets once."""
        if self._xl is not None:
            return
        logger.info(f"Loading Excel workbook once into memory: {self.excel_path}")
        self._xl = pd.ExcelFile(self.excel_path)
        # Parse and cache sheets
        self._df_m1 = self._safe_read_sheet(self._xl, "M1")
        self._df_cl = self._safe_read_sheet(self._xl, "CL")
        self._df_cien = self._safe_read_sheet(self._xl, "CIEN")
        self._df_hyst = self._safe_read_sheet(self._xl, "HYST")
        self._df_reporte = self._safe_read_sheet(self._xl, "Reporte")

    # ------------------------- Public API -------------------------
    def generate_pdf_for_user(self, user_id: Optional[str] = None, email: Optional[str] = None) -> bytes:
        """Generate a single user's PDF by user_id or email.

        Exactly one of user_id or email should be provided.
        """
        if not (user_id or email):
            raise ValueError("Must provide user_id or email")

        # Ensure workbook and DataFrames are loaded once
        self._ensure_loaded()
        df_m1 = self._df_m1
        df_cl = self._df_cl
        df_cien = self._df_cien
        df_hyst = self._df_hyst

        # Find rows for the user
        m1_row = self._find_user_row(df_m1, user_id, email)
        cl_row = self._find_user_row(df_cl, user_id, email)
        cien_row = self._find_user_row(df_cien, user_id, email)
        hyst_row = self._find_user_row(df_hyst, user_id, email)

        # Build tables HTML
        tables_html = []
        if m1_row is not None:
            tables_html.append(self._build_m1_table(m1_row))
        if cl_row is not None:
            tables_html.append(self._build_cl_table(cl_row))
        if cien_row is not None:
            tables_html.append(self._build_cien_tables(cien_row))
        if hyst_row is not None:
            tables_html.append(self._build_hyst_table(hyst_row))

        full_tables_html = "".join([t for t in tables_html if t])

        # Render HTML
        html_content = self._load_html_template()

        # Replace level variables strictly from Excel values (no fallbacks)
        m1_level = self._get_value(m1_row, "level")
        cl_level = self._get_value(cl_row, "level")
        cien_level = self._get_value(cien_row, "level")
        hyst_level = self._get_value(hyst_row, "level")

        if m1_level is not None:
            html_content = html_content.replace("<<Nivel M1>>", str(m1_level))
        if cl_level is not None:
            html_content = html_content.replace("<<Nivel CL>>", str(cl_level))
        if cien_level is not None:
            html_content = html_content.replace("<<Nivel Ciencias>>", str(cien_level))
        if hyst_level is not None:
            html_content = html_content.replace("<<Nivel Historia>>", str(hyst_level))

        # Insert tables into the template (before closing body)
        if full_tables_html:
            html_content = html_content.replace("</body>", f"{full_tables_html}\n</body>")

        # Generate PDF
        logger.info("Generating PDF from Excel-sourced data...")
        html_doc = HTML(string=html_content)
        pdf_content = html_doc.write_pdf()
        logger.info("PDF generated successfully from Excel data")
        return pdf_content

    # ------------------------- Batch generation -------------------------
    def generate_all_pdfs(self, reports_dir: str = "reports") -> int:
        """Generate PDFs for all eligible users using cached DataFrames.

        Returns the number of successfully generated reports.
        """
        self._ensure_loaded()

        if self._df_reporte is None or self._df_reporte.empty:
            raise ValueError("Sheet 'Reporte' not found or empty in the workbook")

        # Locate columns (case-insensitive where needed)
        col_rindio = _find_col_case_insensitive(
            self._df_reporte, ["Rindió todas sus pruebas", "Rindio todas sus pruebas"]
        )
        col_user_id = _find_col_case_insensitive(self._df_reporte, ["user_id"]) or "user_id"
        col_email = _find_col_case_insensitive(self._df_reporte, ["email"]) or "email"
        col_username = _find_col_case_insensitive(
            self._df_reporte, ["username", "nombre", "name"]
        )

        if not col_rindio:
            raise ValueError("Column 'Rindió todas sus pruebas' not found in 'Reporte' sheet")

        eligible = self._df_reporte[self._df_reporte[col_rindio] == 1]
        logger.info(f"Found {len(eligible)} users who completed all tests")

        os.makedirs(reports_dir, exist_ok=True)
        generated_count = 0

        for _, row in eligible.iterrows():
            user_id = row.get(col_user_id)
            email = row.get(col_email)
            username = row.get(col_username) if col_username and col_username in row else None

            try:
                pdf_bytes = self.generate_pdf_for_user(
                    user_id=user_id if pd.notna(user_id) else None,
                    email=email if pd.notna(email) else None,
                )
            except Exception as e:
                logger.error(
                    f"Failed to generate PDF for user_id={user_id}, email={email}: {e}"
                )
                continue

            base = email if pd.notna(email) and email else (user_id if pd.notna(user_id) else "user")
            base = _sanitize_filename(base)
            filename = f"{base}.pdf"
            out_path = os.path.join(reports_dir, filename)

            try:
                with open(out_path, "wb") as f:
                    f.write(pdf_bytes)
                logger.info(f"Saved report: {out_path}")
                generated_count += 1
            except Exception as e:
                logger.error(f"Failed to save PDF to {out_path}: {e}")

        return generated_count

    # ------------------------- Builders -------------------------
    def _build_m1_table(self, row: pd.Series) -> str:
        passed = self._split_piped_list(self._get_value(row, "passed_lectures"))
        failed = self._split_piped_list(self._get_value(row, "failed_lectures"))

        lecture_results: Dict[str, Dict[str, Any]] = {}
        for name in passed:
            lecture_results[name] = {"status": "Aprobado"}
        for name in failed:
            lecture_results[name] = {"status": "Reprobado"}

        subtitle = f"Lecciones Aprobadas: {len(passed)}/{len(passed) + len(failed)}"
        return self._generate_generic_table(
            assessment_name="M1",
            lecture_results=lecture_results,
            subtitle=subtitle,
            column_header="Estado",
            status_extractor=lambda data: data.get("status", "Reprobado"),
            status_classifier=self._get_status_class_for_lecture,
            assessment_class="assessment-m1",
        )

    def _build_cl_table(self, row: pd.Series) -> str:
        # Expecting columns: skill_localizar_percentage, skill_interpretar_percentage, skill_evaluar_percentage
        skills = ["localizar", "interpretar", "evaluar"]
        lecture_results: Dict[str, Dict[str, Any]] = {}
        for skill in skills:
            col = f"skill_{skill}_percentage"
            raw_value = self._get_value(row, col)
            # Keep raw display, compute numeric for classification only
            numeric = self._parse_excel_percentage(raw_value)
            lecture_results[skill.capitalize()] = {"percentage": numeric, "display": raw_value}

        return self._generate_generic_table(
            assessment_name="CL",
            lecture_results=lecture_results,
            subtitle="",
            column_header="Porcentaje",
            status_extractor=lambda data: ("" if data.get("display") is None else str(data.get("display"))),
            assessment_class="assessment-cl",
        )

    def _build_cien_tables(self, row: pd.Series) -> str:
        materias = ["biología", "química", "física"]
        sections: List[str] = []

        total_passed = 0
        total_failed = 0

        # Pre-compute totals from per-materia counts if available
        for materia in materias:
            total_passed += int(self._get_value(row, f"materia_{materia}_passed_lectures_count") or 0)
            total_failed += int(self._get_value(row, f"materia_{materia}_failed_lectures_count") or 0)

        for idx, materia in enumerate(materias):
            passed_str = self._get_value(row, f"materia_{materia}_passed_lectures")
            failed_str = self._get_value(row, f"materia_{materia}_failed_lectures")
            passed_list = self._split_piped_list(passed_str)
            failed_list = self._split_piped_list(failed_str)

            lecture_results: Dict[str, Dict[str, Any]] = {}
            for name in passed_list:
                lecture_results[name] = {"status": "Aprobado"}
            for name in failed_list:
                lecture_results[name] = {"status": "Reprobado"}

            subtitle = ""
            if idx == 0:
                subtitle = f"Lecciones Aprobadas: {total_passed}/{total_passed + total_failed}"

            sections.append(
                self._generate_generic_table(
                    assessment_name="CIEN",
                    lecture_results=lecture_results,
                    subtitle=subtitle,
                    column_header="Estado",
                    status_extractor=lambda data: data.get("status", "Reprobado"),
                    status_classifier=self._get_status_class_for_lecture,
                    assessment_class="assessment-cien",
                    materia_name=materia,
                )
            )

        return "".join(sections)

    def _build_hyst_table(self, row: pd.Series) -> str:
        passed = self._split_piped_list(self._get_value(row, "passed_lectures"))
        failed = self._split_piped_list(self._get_value(row, "failed_lectures"))

        lecture_results: Dict[str, Dict[str, Any]] = {}
        for name in passed:
            lecture_results[name] = {"status": "Aprobado"}
        for name in failed:
            lecture_results[name] = {"status": "Reprobado"}

        subtitle = f"Lecciones Aprobadas: {len(passed)}/{len(passed) + len(failed)}"
        return self._generate_generic_table(
            assessment_name="HYST",
            lecture_results=lecture_results,
            subtitle=subtitle,
            column_header="Estado",
            status_extractor=lambda data: data.get("status", "Reprobado"),
            status_classifier=self._get_status_class_for_lecture,
            assessment_class="assessment-hyst",
        )

    # ------------------------- HTML helpers -------------------------
    def _load_html_template(self) -> str:
        if not os.path.exists(self.html_template_path):
            raise FileNotFoundError(f"HTML template not found: {self.html_template_path}")
        with open(self.html_template_path, "r", encoding="utf-8") as f:
            return f.read()

    def _generate_generic_table(
        self,
        assessment_name: str,
        lecture_results: Dict[str, Any],
        subtitle: str,
        column_header: str,
        status_extractor,
        status_classifier=None,
        assessment_class: Optional[str] = None,
        materia_name: Optional[str] = None,
    ) -> str:
        """Wrapper around the same structure as ReportGenerator's generic table."""
        if not lecture_results:
            return ""

        if assessment_class is None:
            assessment_class = f"assessment-{assessment_name.lower()}"

        # Split into pages of 20 entries like the original
        lecture_items = list(lecture_results.items())
        all_sections: List[str] = []

        for i in range(0, len(lecture_items), 20):
            page_lectures = lecture_items[i : i + 20]
            table_rows: List[str] = []

            for lecture_name, lecture_data in page_lectures:
                status_value = status_extractor(lecture_data)
                status_class = status_classifier(lecture_data) if callable(status_classifier) else ""

                row_html = TABLE_ROW_TEMPLATE.format(
                    lecture_name=lecture_name,
                    status_class=status_class,
                    status_value=status_value,
                )
                table_rows.append(row_html)

            is_continuation = i > 0
            continuation_text = "<p class=\"subtitle\">(Continuación)</p>" if is_continuation else ""
            materia_text = f"<p class=\"materia-title\">{materia_name}</p>" if materia_name else ""

            section_html = SECTION_TEMPLATE.format(
                assessment_class=assessment_class,
                assessment_name=assessment_name,
                subtitle=subtitle,
                continuation_text=continuation_text + materia_text,
                column_header=column_header,
                table_rows="".join(table_rows),
            )
            all_sections.append(section_html)

        return "".join(all_sections)

    # ------------------------- Utility -------------------------
    def _safe_read_sheet(self, xl: pd.ExcelFile, name: str) -> pd.DataFrame:
        try:
            return xl.parse(sheet_name=name)
        except ValueError:
            logger.warning(f"Sheet '{name}' not found in workbook {self.excel_path}")
            return pd.DataFrame()

    def _find_user_row(self, df: pd.DataFrame, user_id: Optional[str], email: Optional[str]) -> Optional[pd.Series]:
        if df is None or df.empty:
            return None
        # Normalize columns
        cols = {c.lower(): c for c in df.columns}
        id_col = cols.get("user_id")
        email_col = cols.get("email")

        row = None
        if user_id and id_col in df.columns:
            matches = df[df[id_col].astype(str) == str(user_id)]
            if not matches.empty:
                row = matches.iloc[0]
        if row is None and email and email_col in df.columns:
            matches = df[df[email_col].astype(str) == str(email)]
            if not matches.empty:
                row = matches.iloc[0]
        return row

    def _split_piped_list(self, value: Any) -> List[str]:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return []
        # Accept both "|" and " | " forms; split and strip
        parts = [p.strip() for p in str(value).split("|")]
        return [p for p in parts if p]

    def _parse_excel_percentage(self, value: Any) -> float:
        """Parse percentages that might be stored as strings like '0,85' (meaning 85%)."""
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return 0.0
        s = str(value).strip()
        # If it already looks like a number > 1, assume it's in 0-100 scale
        try:
            # Replace comma decimal with dot
            s2 = s.replace(",", ".")
            num = float(s2)
            if num <= 1.0:
                return num * 100.0
            return num
        except Exception:
            return 0.0

    # No extra formatting helpers; values are displayed as provided by Excel

    def _get_value(self, row: Optional[pd.Series], column: str) -> Any:
        if row is None:
            return None
        # Support column names exactly as provided
        if column in row.index:
            return row[column]
        # Try case-insensitive match
        lower_to_actual = {c.lower(): c for c in row.index}
        actual = lower_to_actual.get(column.lower())
        return row.get(actual) if actual else None

    # Reuse status classification rules
    def _get_status_class_for_lecture(self, lecture_data: Dict[str, Any]) -> str:
        status_string = lecture_data.get("status", "Reprobado")
        return "status-aprobada" if status_string == "Aprobado" else "status-reprobada"

    # (duplicate removed)


def _find_col_case_insensitive(df: pd.DataFrame, targets: List[str]) -> Optional[str]:
    if df is None or df.empty:
        return None
    lower_to_actual = {c.lower(): c for c in df.columns}
    for t in targets:
        if t.lower() in lower_to_actual:
            return lower_to_actual[t.lower()]
    return None


def _sanitize_filename(name: str) -> str:
    safe = []
    for ch in str(name):
        if ch.isalnum() or ch in ("_", "-", ".", "@"):
            safe.append(ch)
        else:
            safe.append("_")
    return "".join(safe)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    excel_path = "data/analysis/analisis de datos.xlsx"
    reports_dir = "reports"
    os.makedirs(reports_dir, exist_ok=True)

    generator = ExcelReportGenerator(excel_path=excel_path)
    try:
        total = generator.generate_all_pdfs(reports_dir=reports_dir)
        logger.info(f"Completed generation. {total} reports saved to '{reports_dir}'.")
    except Exception as e:
        logger.error(f"Failed to generate reports: {e}")

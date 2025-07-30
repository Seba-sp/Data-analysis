#!/usr/bin/env python3
"""
Report generator for individual student assessment reports
Generates PDF reports using HTML templates with variables
Uses weasyprint for HTML-to-PDF conversion
"""

import os
import logging
from typing import Dict, Any, Tuple
from weasyprint import HTML
from storage import StorageClient
from drive_service import DriveService

logger = logging.getLogger(__name__)

class ReportGenerator:
    def __init__(self):
        """Initialize report generator"""
        self.storage = StorageClient()
        self.drive_service = DriveService()
        self.html_template_path = "/app/templates/plantilla_test_diagnostico.html"

    def generate_individual_report(self, user: Dict[str, Any], assessment: Dict[str, Any], analysis_result: Dict[str, Any]) -> Tuple[bytes, str]:
        """
        Generate individual PDF report for student using HTML template

        Args:
            user: User information from webhook
            assessment: Assessment information from webhook
            analysis_result: Analysis results from AssessmentAnalyzer

        Returns:
            Tuple of (PDF content as bytes, email filename)
        """
        try:
            # Generate PDF using HTML template with weasyprint
            pdf_content = self._generate_pdf_from_html_template(user, assessment, analysis_result)

            # Generate filenames
            assessment_title = analysis_result.get('title', 'Unknown Assessment')
            username = user.get('username', user.get('email', 'Unknown User'))
            user_id = user.get('id', 'unknown_id')

            drive_filename = f"informe_{username}_{user_id}_{assessment_title}.pdf"
            email_filename = f"informe_{username}_{assessment_title}.pdf"

            # Save based on backend
            self._save_pdf(pdf_content, drive_filename, assessment_title)

            logger.info(f"Generated PDF report for {user.get('username', user['email'])}")
            return pdf_content, email_filename

        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            raise

    def _generate_pdf_from_html_template(self, user: Dict[str, Any], assessment: Dict[str, Any], analysis_result: Dict[str, Any]) -> bytes:
        """Generate PDF from HTML template using weasyprint"""
        try:
            # Load HTML template from local file
            if not os.path.exists(self.html_template_path):
                logger.error(f"HTML template not found: {self.html_template_path}")
                raise Exception("HTML template not found")

            with open(self.html_template_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            logger.info(f"Loaded HTML template, size: {len(html_content)} characters")

            # Calculate variables
            username = user.get('username', user.get('email', 'Estudiante'))
            assessment_title = analysis_result.get('title', 'Diagnóstico')
            total_questions = analysis_result.get('total_questions', 0)
            correct_questions = analysis_result.get('correct_questions', 0)

            if total_questions > 0:
                percentage = (correct_questions / total_questions) * 100
            else:
                percentage = 0

            # Determine level based on percentage
            if percentage >= 80:
                level = "3"
            elif percentage >= 60:
                level = "2"
            else:
                level = "1"

            # Replace variables in HTML
            variables = {
                '<<ALUMNO>>': username,
                '<<Nombre>>': username,
                '<<MATERIA>>': assessment_title,
                '<<Prueba>>': assessment_title,
                '<<PD%>>': f"{percentage:.1f}%",
                '<<Nivel>>': level,
            }

            for var_name, var_value in variables.items():
                html_content = html_content.replace(var_name, var_value)

            logger.info("Variables replaced in HTML template")

            # Add lecture results table to third page
            lecture_results = analysis_result.get("lecture_results", {})
            if lecture_results:
                html_content = self._add_lecture_table_to_html(html_content, lecture_results)
                logger.info(f"Added lecture table with {len(lecture_results)} lectures")

            # Generate PDF using weasyprint
            logger.info("Generating PDF with weasyprint...")
            html_doc = HTML(string=html_content)
            pdf_content = html_doc.write_pdf()
            
            logger.info("✅ PDF generated successfully")
            return pdf_content

        except Exception as e:
            logger.error(f"Error generating PDF from HTML template: {e}")
            raise

    def _add_lecture_table_to_html(self, html_content: str, lecture_results: Dict[str, Dict[str, Any]]) -> str:
        """Add lecture results table to HTML content"""
        try:
            # Create table HTML
            table_rows = []
            for lecture_name, result_details in lecture_results.items():
                # Get the status string from inside the result_details dictionary
                status_string = result_details.get("status", "Reprobado")
                
                # Use the new status_string variable for the logic
                status_class = "status-aprobada" if status_string == "Aprobado" else "status-reprobada"
                
                row = f"""
        <tr>
          <td>{lecture_name}</td>
          <td class="status-cell {status_class}">{status_string}</td>
        </tr>"""
                table_rows.append(row)

            table_html = f"""
<section class="page">
  <div class="content">
    <p class="TituloAlumno Negrita">Resultados por Lección</p>
    <table class="results-table">
      <thead>
        <tr>
          <th>Lección</th>
          <th style="text-align:center;">Estado</th>
        </tr>
      </thead>
      <tbody>
        {''.join(table_rows)}
      </tbody>
    </table>
  </div>
</section>"""

            # Insert table before closing body tag
            html_content = html_content.replace('</body>', f'{table_html}\n</body>')
            logger.info("Added lecture table to HTML template")
            return html_content

        except Exception as e:
            logger.error(f"Error adding lecture table: {e}")
            return html_content

    def _save_pdf(self, pdf_content: bytes, filename: str, assessment_title: str) -> None:
        """Save PDF to storage backend"""
        try:
            # Save to Google Drive
            drive_link = self.drive_service.upload_pdf_to_drive(pdf_content, filename, assessment_title)
            if drive_link:
                logger.info(f"PDF saved to Google Drive: {drive_link}")
            else:
                logger.warning("Failed to save PDF to Google Drive")
        except Exception as e:
            logger.error(f"Error saving PDF to Google Drive: {e}")
            raise 
#!/usr/bin/env python3
"""
Report Generator - Generates comprehensive PDF reports with assessment results
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
        self.html_template_path = "templates/plantilla_plan_de_estudio.html"

    def generate_comprehensive_report(self, user_id: str, user_email: str, username: str, 
                                   user_results: Dict[str, Any]) -> bytes:
        """
        Generate comprehensive PDF report with all assessment results
        
        Args:
            user_id: User ID
            user_email: User email
            username: Username
            user_results: Dictionary with results for all assessments
            
        Returns:
            PDF content as bytes
        """
        try:
            # Generate PDF using HTML template with weasyprint
            pdf_content = self._generate_pdf_from_html_template(
                user_id, user_email, username, user_results
            )

            logger.info(f"Generated comprehensive PDF report for {username}")
            return pdf_content

        except Exception as e:
            logger.error(f"Error generating comprehensive report: {str(e)}")
            raise

    def _generate_pdf_from_html_template(self, user_id: str, user_email: str, username: str,
                                       user_results: Dict[str, Any]) -> bytes:
        """Generate PDF from HTML template using weasyprint"""
        try:
            # Load HTML template from local file
            if not os.path.exists(self.html_template_path):
                logger.error(f"HTML template not found: {self.html_template_path}")
                raise Exception("HTML template not found")

            with open(self.html_template_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            logger.info(f"Loaded HTML template, size: {len(html_content)} characters")

            # Calculate overall variables
            total_assessments = len(user_results)
            assessments_with_results = sum(1 for result in user_results.values() if result is not None)

            # Replace basic variables
            variables = {
                '<<ALUMNO>>': username,
                '<<Nombre>>': username,
                '<<MATERIA>>': 'Plan de Estudio Completo',
                '<<Prueba>>': 'Plan de Estudio Completo',
                '<<PD%>>': f"{assessments_with_results}/{total_assessments} evaluaciones completadas",
                '<<Nivel>>': self._calculate_overall_level(user_results),
            }

            for var_name, var_value in variables.items():
                html_content = html_content.replace(var_name, var_value)

            # Add specific content on the second page
            html_content = self._add_second_page_content(html_content, user_results)

            logger.info("Basic variables replaced in HTML template")

            # Add assessment results tables
            html_content = self._add_comprehensive_tables_to_html(html_content, user_results)

            # Generate PDF using weasyprint
            logger.info("Generating PDF with weasyprint...")
            html_doc = HTML(string=html_content)
            pdf_content = html_doc.write_pdf()
            
            logger.info("✅ PDF generated successfully")
            return pdf_content

        except Exception as e:
            logger.error(f"Error generating PDF from HTML template: {e}")
            raise

    def _calculate_overall_level(self, user_results: Dict[str, Any]) -> str:
        """Calculate overall level based on all assessment results"""
        try:
            total_percentage = 0
            valid_assessments = 0
            
            for assessment_name, result in user_results.items():
                if result and result.get('overall_percentage') is not None:
                    total_percentage += result['overall_percentage']
                    valid_assessments += 1
            
            if valid_assessments == 0:
                return "1"
            
            average_percentage = total_percentage / valid_assessments
            
            if average_percentage >= 80:
                return "3"
            elif average_percentage >= 60:
                return "2"
            else:
                return "1"
                
        except Exception as e:
            logger.error(f"Error calculating overall level: {e}")
            return "1"

    def _add_second_page_content(self, html_content: str, user_results: Dict[str, Any]) -> str:
        """Replace variables in the template with calculated values"""
        try:
            # Get levels for each assessment
            m1_level = self._get_assessment_level(user_results.get('M1', {}))
            cl_level = self._get_assessment_level(user_results.get('CL', {}))
            cien_level = self._get_assessment_level(user_results.get('CIEN', {}))
            hyst_level = self._get_assessment_level(user_results.get('HYST', {}))

            # Generate study plans for each month
            plan_agosto = self._generate_monthly_plan(user_results, 'agosto')
            plan_septiembre = self._generate_monthly_plan(user_results, 'septiembre')
            plan_octubre = self._generate_monthly_plan(user_results, 'octubre')

            # Replace variables in the template
            variables = {
                '<<Nivel M1>>': m1_level,
                '<<Nivel CL>>': cl_level,
                '<<Nivel Ciencias>>': cien_level,
                '<<Nivel Historia>>': hyst_level,
                '<<PlanAgosto>>': plan_agosto,
                '<<PlanSeptiembre>>': plan_septiembre,
                '<<PlanOctubre>>': plan_octubre,
            }

            # Replace all variables in the HTML content
            for var_name, var_value in variables.items():
                html_content = html_content.replace(var_name, var_value)

            logger.info("Replaced variables in template")
            return html_content

        except Exception as e:
            logger.error(f"Error replacing variables in template: {e}")
            return html_content

    def _get_assessment_level(self, assessment_result: Dict[str, Any]) -> str:
        """Get the level for a specific assessment"""
        try:
            if not assessment_result:
                return "Nivel 1"
            
            assessment_type = assessment_result.get('type', 'unknown')
            
            if assessment_type == 'percentage_based':
                # For CL assessment
                overall_percentage = assessment_result.get('overall_percentage', 0)
                if overall_percentage >= 80:
                    return "Nivel 3"
                elif overall_percentage >= 60:
                    return "Nivel 2"
                else:
                    return "Nivel 1"
            else:
                # For other assessments (M1, CIEN, HYST)
                if assessment_type == 'lecture_based_with_materia':
                    # For CIEN assessment
                    total_lectures = assessment_result.get('total_lectures', 0)
                    total_passed = assessment_result.get('total_lectures_passed', 0)
                    if total_lectures > 0:
                        percentage = (total_passed / total_lectures) * 100
                        if percentage >= 80:
                            return "Nivel 3"
                        elif percentage >= 60:
                            return "Nivel 2"
                        else:
                            return "Nivel 1"
                else:
                    # For M1 and HYST assessments
                    lectures_analyzed = assessment_result.get('lectures_analyzed', 0)
                    lectures_passed = assessment_result.get('lectures_passed', 0)
                    if lectures_analyzed > 0:
                        percentage = (lectures_passed / lectures_analyzed) * 100
                        if percentage >= 80:
                            return "Nivel 3"
                        elif percentage >= 60:
                            return "Nivel 2"
                        else:
                            return "Nivel 1"
            
            return "Nivel 1"
            
        except Exception as e:
            logger.error(f"Error getting assessment level: {e}")
            return "Nivel 1"

    def _generate_monthly_plan(self, user_results: Dict[str, Any], month: str) -> str:
        """Generate study plan for a specific month based on M1 and CL levels"""
        try:
            # Get M1 and CL levels
            m1_level = self._get_assessment_level(user_results.get('M1', {}))
            cl_level = self._get_assessment_level(user_results.get('CL', {}))
            
            # Extract numeric level (1, 2, or 3)
            m1_numeric = int(m1_level.split()[-1]) if m1_level else 1
            cl_numeric = int(cl_level.split()[-1]) if cl_level else 1
            
            # Define plans based on the combination of M1 and CL levels
            if m1_numeric == 1 and cl_numeric == 1:
                if month == 'agosto':
                    return "CL"
                elif month == 'septiembre':
                    return "M1"
                elif month == 'octubre':
                    return "M1"
                else:
                    return "Plan personalizado"
                    
            elif m1_numeric == 2 and cl_numeric == 1:
                return "Elije en base a tu carrera"
                
            elif m1_numeric == 1 and cl_numeric == 2:
                if month == 'agosto':
                    return "CL"
                elif month == 'septiembre':
                    return "M1"
                elif month == 'octubre':
                    return "M1"
                else:
                    return "Plan personalizado"
                    
            elif m1_numeric == 2 and cl_numeric == 2:
                if month == 'agosto':
                    return "CL"
                elif month == 'septiembre':
                    return "M1"
                else:
                    return "Plan personalizado"
                    
            elif m1_numeric == 3 and cl_numeric == 1:
                if month == 'agosto':
                    return "CL"
                elif month == 'septiembre':
                    return "Electivo"
                elif month == 'octubre':
                    return "Electivo"
                else:
                    return "Plan personalizado"
                    
            elif m1_numeric == 3 and cl_numeric == 2:
                if month == 'agosto':
                    return "CL"
                elif month == 'septiembre':
                    return "Electivo"
                elif month == 'octubre':
                    return "Electivo"
                else:
                    return "Plan personalizado"
                    
            elif m1_numeric == 1 and cl_numeric == 3:
                if month == 'agosto':
                    return "M1"
                elif month == 'septiembre':
                    return "M1"
                else:
                    return "Plan personalizado"
                    
            elif m1_numeric == 2 and cl_numeric == 3:
                if month == 'agosto':
                    return "M1"
                elif month == 'septiembre':
                    return "Electivo"
                elif month == 'octubre':
                    return "Electivo"
                else:
                    return "Plan personalizado"
                    
            elif m1_numeric == 3 and cl_numeric == 3:
                return "Electivo"
                
            else:
                return "Plan de estudio personalizado"
                
        except Exception as e:
            logger.error(f"Error generating monthly plan: {e}")
            return "Plan de estudio personalizado"

    def _add_comprehensive_tables_to_html(self, html_content: str, user_results: Dict[str, Any]) -> str:
        """Add comprehensive assessment tables to HTML content"""
        try:
            tables_html = ""
            
            for assessment_name, result in user_results.items():
                if not result:
                    continue
                
                assessment_html = self._generate_assessment_table(assessment_name, result)
                if assessment_html:
                    tables_html += assessment_html
            
            # Insert all tables before closing body tag
            if tables_html:
                html_content = html_content.replace('</body>', f'{tables_html}\n</body>')
                logger.info("Added comprehensive assessment tables to HTML template")
            
            return html_content

        except Exception as e:
            logger.error(f"Error adding comprehensive tables: {e}")
            return html_content

    def _get_assessment_background_image(self, assessment_name: str) -> str:
        """Get the background image data URI for a specific assessment"""
        # Background images are now handled directly in the HTML template
        return ''

    def _generate_assessment_table(self, assessment_name: str, result: Dict[str, Any]) -> str:
        """Generate HTML table for a specific assessment"""
        try:
            assessment_type = result.get('type', 'unknown')
            
            if assessment_type == 'lecture_based':
                return self._generate_lecture_based_table(assessment_name, result)
            elif assessment_type == 'lecture_based_with_materia':
                return self._generate_materia_based_table(assessment_name, result)
            elif assessment_type == 'percentage_based':
                return self._generate_percentage_based_table(assessment_name, result)
            else:
                logger.warning(f"Unknown assessment type: {assessment_type}")
                return ""
                
        except Exception as e:
            logger.error(f"Error generating table for {assessment_name}: {e}")
            return ""

    def _generate_lecture_based_table(self, assessment_name: str, result: Dict[str, Any]) -> str:
        """Generate table for lecture-based assessments (M1, HYST)"""
        try:
            lecture_results = result.get('lecture_results', {})
            if not lecture_results:
                return ""
            
            # Add assessment-specific CSS class for background image
            assessment_class = f"assessment-{assessment_name.lower()}"
            
            # Split lectures into pages of 20 each
            lecture_items = list(lecture_results.items())
            all_sections = []
            
            for i in range(0, len(lecture_items), 20):
                page_lectures = lecture_items[i:i+20]
                
                # Generate table rows for this page
                table_rows = []
                for lecture_name, lecture_data in page_lectures:
                    status_string = lecture_data.get("status", "Reprobado")
                    status_class = "status-aprobada" if status_string == "Aprobado" else "status-reprobada"
                    
                    row = f"""
        <tr>
          <td>{lecture_name}</td>
          <td class="status-cell {status_class}">{status_string}</td>
        </tr>"""
                    table_rows.append(row)
                
                # Create section for this page
                if i == 0:  # First page - include header
                    section = f"""
<section class="page {assessment_class}">
  <div class="content">
    <p class="TituloAlumno Negrita">Resultados - {assessment_name}</p>
    <p class="subtitle">Lecciones Aprobadas: {result.get('lectures_passed', 0)}/{result.get('lectures_analyzed', 0)}</p>
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
                else:  # Continuation page - include header
                    section = f"""
<section class="page {assessment_class}">
  <div class="content">
    <p class="TituloAlumno Negrita">Resultados - {assessment_name}</p>
    <p class="subtitle">Lecciones Aprobadas: {result.get('lectures_passed', 0)}/{result.get('lectures_analyzed', 0)}</p>
    <p class="subtitle">(Continuación)</p>
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
                
                all_sections.append(section)
            
            return ''.join(all_sections)

        except Exception as e:
            logger.error(f"Error generating lecture-based table: {e}")
            return ""

    def _generate_materia_based_table(self, assessment_name: str, result: Dict[str, Any]) -> str:
        """Generate table for materia-based assessments (CIEN)"""
        try:
            materia_results = result.get('materia_results', {})
            if not materia_results:
                return ""
            
            # Add assessment-specific CSS class for background image
            assessment_class = f"assessment-{assessment_name.lower()}"
            
            # Process all materias and create proper page sections
            all_sections = []
            
            for materia_name, materia_data in materia_results.items():
                lecture_results = materia_data.get('lecture_results', {})
                
                # Split lectures into pages of 20 each
                lecture_items = list(lecture_results.items())
                pages = []
                
                for i in range(0, len(lecture_items), 20):
                    page_lectures = lecture_items[i:i+20]
                    
                    # Generate table rows for this page
                    table_rows = []
                    for lecture_name, lecture_data in page_lectures:
                        status_string = lecture_data.get("status", "Reprobado")
                        status_class = "status-aprobada" if status_string == "Aprobado" else "status-reprobada"
                        
                        row = f"""
        <tr>
          <td>{lecture_name}</td>
          <td class="status-cell {status_class}">{status_string}</td>
        </tr>"""
                        table_rows.append(row)
                    
                    # Create section for this page
                    if i == 0:  # First page of this materia
                        if len(all_sections) == 0:  # First materia - include header
                            section = f"""
<section class="page {assessment_class}">
  <div class="content">
    <p class="TituloAlumno Negrita">Resultados - {assessment_name}</p>
    <p class="subtitle">Lecciones Aprobadas: {result.get('total_lectures_passed', 0)}/{result.get('total_lectures', 0)}</p>
    <p class="materia-title">{materia_name}</p>
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
                        else:  # Other materias - no header
                            section = f"""
<section class="page {assessment_class}">
  <div class="content">
    <p class="materia-title">{materia_name}</p>
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
                    else:  # Continuation page - include header
                        section = f"""
<section class="page {assessment_class}">
  <div class="content">
    <p class="TituloAlumno Negrita">Resultados - {assessment_name}</p>
    <p class="subtitle">Lecciones Aprobadas: {result.get('total_lectures_passed', 0)}/{result.get('total_lectures', 0)}</p>
    <p class="materia-title">{materia_name} (Continuación)</p>
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
                    
                    pages.append(section)
                
                all_sections.extend(pages)
            
            return ''.join(all_sections)

        except Exception as e:
            logger.error(f"Error generating materia-based table: {e}")
            return ""

    def _generate_percentage_based_table(self, assessment_name: str, result: Dict[str, Any]) -> str:
        """Generate table for percentage-based assessments (CL)"""
        try:
            lecture_results = result.get('lecture_results', {})
            if not lecture_results:
                return ""
            
            table_rows = []
            for lecture_name, lecture_data in lecture_results.items():
                percentage = lecture_data.get("percentage", 0)
                status_string = f"{percentage:.1f}%"
                
                # Color coding based on percentage
                if percentage >= 80:
                    status_class = "status-aprobada"
                elif percentage >= 60:
                    status_class = "status-intermedia"
                else:
                    status_class = "status-reprobada"
                
                row = f"""
        <tr>
          <td>{lecture_name}</td>
          <td class="status-cell {status_class}">{status_string}</td>
        </tr>"""
                table_rows.append(row)

            # Add assessment-specific CSS class for background image
            assessment_class = f"assessment-{assessment_name.lower()}"
            
            table_html = f"""
<section class="page {assessment_class}">
  <div class="content">
    <p class="TituloAlumno Negrita">Resultados - {assessment_name}</p>
    <p class="subtitle">Porcentaje General: {result.get('overall_percentage', 0):.1f}%</p>
    <table class="results-table">
      <thead>
        <tr>
          <th>Lección</th>
          <th style="text-align:center;">Porcentaje</th>
        </tr>
      </thead>
      <tbody>
        {''.join(table_rows)}
      </tbody>
    </table>
  </div>
</section>"""
            
            return table_html

        except Exception as e:
            logger.error(f"Error generating percentage-based table: {e}")
            return ""

    def save_to_drive(self, pdf_content: bytes, filename: str, folder_name: str) -> str:
        """Save PDF to Google Drive in specified folder"""
        try:
            drive_link = self.drive_service.upload_pdf_to_drive(pdf_content, filename, folder_name)
            if drive_link:
                logger.info(f"PDF saved to Google Drive: {drive_link}")
                return drive_link
            else:
                logger.warning("Failed to save PDF to Google Drive")
                return ""
        except Exception as e:
            logger.error(f"Error saving PDF to Google Drive: {e}")
            raise 
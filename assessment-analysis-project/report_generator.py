#!/usr/bin/env python3
"""
Report Generator - Generates comprehensive PDF reports with assessment results
"""

import os
import logging
from typing import Dict, Any, Tuple, List
from weasyprint import HTML
from storage import StorageClient
from drive_service import DriveService

logger = logging.getLogger(__name__)

class ReportGenerator:
    """Generates comprehensive PDF reports with assessment results"""
    
    # Class constants for better maintainability
    ASSESSMENT_TYPES = {
        'M1': 'm1_difficulty_based',
        'CL': 'cl_skill_based', 
        'CIEN': 'cien_materia_based',
        'HYST': 'hyst_difficulty_based'
    }
    
    LEVEL_THRESHOLDS = {
        'Nivel 3': 80,
        'Nivel 2': 60,
        'Nivel 1': 0
    }
    
    # Study plan combinations - easy to modify
    STUDY_PLANS = {
        (1, 1): {
            'agosto': 'CL',
            'septiembre': 'M1',
            'octubre': 'M1',
            'default': 'Ejercitación'
        },
        (2, 1): {
            'default': 'Elije en base a tu carrera'
        },
        (1, 2): {
            'agosto': 'CL',
            'septiembre': 'M1',
            'octubre': 'M1',
            'default': 'Ejercitación'
        },
        (2, 2): {
            'agosto': 'CL',
            'septiembre': 'M1',
            'default': 'Ejercitación'
        },
        (1, 3): {
            'agosto': 'M1',
            'septiembre': 'M1',
            'default': 'Ejercitación'
        },
        (3, 1): {
            'agosto': 'CL',
            'septiembre': 'Electivo',
            'octubre': 'Electivo',
            'default': 'Ejercitación'
        },
        (3, 2): {
            'agosto': 'CL',
            'septiembre': 'Electivo',
            'octubre': 'Electivo',
            'default': 'Plan personalizado'
        },
        (2, 3): {
            'agosto': 'M1',
            'septiembre': 'Electivo',
            'octubre': 'Electivo',
            'default': 'Ejercitación'
        },
        (3, 3): {
            'default': 'Electivo'
        }
    }
    
    # Conditional text combinations - combinations that need elective guidance (don't have "Electivo" in plans)
    CONDITIONAL_COMBINATIONS = {
        (1, 1), (2, 1), (1, 2), (2, 2), (1, 3)
    }
    
    # HTML templates
    CONDITIONAL_TEXT_TEMPLATE = (
        '<p style="margin: 0; font-size: 14px;">Realizarás la preparación de la PAES {elective} con el programa de tarde.</p><br>'
    )
    
    TABLE_ROW_TEMPLATE = """
        <tr>
          <td>{lecture_name}</td>
          <td class="status-cell {status_class}">{status_value}</td>
        </tr>"""
    
    SECTION_TEMPLATE = """
<section class="page {assessment_class}">
  <div class="content">
    <p class="TituloAlumno Negrita">Resultados - {assessment_name}</p>
    <p class="subtitle">{subtitle}</p>
    {continuation_text}
    <table class="results-table">
      <thead>
        <tr>
          <th>Lección</th>
          <th style="text-align:center;">{column_header}</th>
        </tr>
      </thead>
      <tbody>
        {table_rows}
      </tbody>
    </table>
  </div>
</section>"""

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
            html_content = self._load_html_template()
            html_content = self._replace_basic_variables(html_content, username, user_results)
            html_content = self._add_second_page_content(html_content, user_results)
            html_content = self._add_comprehensive_tables_to_html(html_content, user_results)
            
            logger.info("Generating PDF with weasyprint...")
            html_doc = HTML(string=html_content)
            pdf_content = html_doc.write_pdf()
            
            logger.info("✅ PDF generated successfully")
            return pdf_content
        except Exception as e:
            logger.error(f"Error generating PDF from HTML template: {e}")
            raise

    def _load_html_template(self) -> str:
        """Load HTML template from file"""
        if not os.path.exists(self.html_template_path):
            logger.error(f"HTML template not found: {self.html_template_path}")
            raise FileNotFoundError("HTML template not found")

        with open(self.html_template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        logger.info(f"Loaded HTML template, size: {len(html_content)} characters")
        return html_content

    def _replace_basic_variables(self, html_content: str, username: str, 
                               user_results: Dict[str, Any]) -> str:
        """Replace basic variables in HTML template"""
        total_assessments = len(user_results)
        assessments_with_results = sum(1 for result in user_results.values() if result is not None)

        variables = {
            '<<ALUMNO>>': username,
            '<<PD%>>': f"{assessments_with_results}/{total_assessments} evaluaciones completadas",
        }

        return self._replace_variables(html_content, variables)

    def _replace_variables(self, html_content: str, variables: Dict[str, str]) -> str:
        """Replace variables in HTML content"""
        for var_name, var_value in variables.items():
            html_content = html_content.replace(var_name, var_value)
        return html_content

    def _add_second_page_content(self, html_content: str, user_results: Dict[str, Any]) -> str:
        """Replace variables in the template with calculated values"""
        try:
            # Get levels for each assessment
            assessment_levels = self._get_all_assessment_levels(user_results)
            
            # Generate study plans for each month
            monthly_plans = self._generate_all_monthly_plans(user_results)
            
            # Get conditional text
            conditional_text = self._get_conditional_text(user_results)
            
            # Replace variables in the template
            variables = {
                '<<Nivel M1>>': assessment_levels['M1'],
                '<<Nivel CL>>': assessment_levels['CL'],
                '<<Nivel Ciencias>>': assessment_levels['CIEN'],
                '<<Nivel Historia>>': assessment_levels['HYST'],
                '<<PlanAgosto>>': monthly_plans['agosto'],
                '<<PlanSeptiembre>>': monthly_plans['septiembre'],
                '<<PlanOctubre>>': monthly_plans['octubre'],
                '<<CONDITIONAL_TEXT>>': conditional_text,
            }

            html_content = self._replace_variables(html_content, variables)
            logger.info("Replaced variables in template")
            return html_content
        except Exception as e:
            logger.error(f"Error replacing variables in template: {e}")
            return html_content

    def _get_all_assessment_levels(self, user_results: Dict[str, Any]) -> Dict[str, str]:
        """Get levels for all assessments"""
        return {
            assessment: self._get_assessment_level(user_results.get(assessment, {}))
            for assessment in ['M1', 'CL', 'CIEN', 'HYST']
        }

    def _generate_all_monthly_plans(self, user_results: Dict[str, Any]) -> Dict[str, str]:
        """Generate study plans for all months"""
        return {
            month: self._generate_monthly_plan(user_results, month)
            for month in ['agosto', 'septiembre', 'octubre']
        }

    def _get_conditional_text(self, user_results: Dict[str, Any]) -> str:
        """Generate conditional text based on M1 and CL level combinations and elective scores."""
        try:
            m1_numeric, cl_numeric = self._get_numeric_levels(user_results)
            current_combination = (m1_numeric, cl_numeric)
            
            if current_combination in self.CONDITIONAL_COMBINATIONS:
                elective_test = self._determine_best_elective(user_results)
                
                if elective_test: # Only display if a valid elective was determined
                    return self.CONDITIONAL_TEXT_TEMPLATE.format(elective=elective_test)
            return ""
        except Exception as e:
            logger.error(f"Error generating conditional text: {e}")
            return ""

    def _get_numeric_levels(self, user_results: Dict[str, Any]) -> Tuple[int, int]:
        """Get numeric levels for M1 and CL assessments"""
        m1_level = self._get_assessment_level(user_results.get('M1', {}))
        cl_level = self._get_assessment_level(user_results.get('CL', {}))
        
        m1_numeric = int(m1_level.split()[-1]) if m1_level else 1
        cl_numeric = int(cl_level.split()[-1]) if cl_level else 1
        
        return m1_numeric, cl_numeric

    def _get_assessment_level(self, assessment_result: Dict[str, Any]) -> str:
        """Get the level for a specific assessment"""
        try:
            if not assessment_result:
                return "Nivel 1"
            
            # For new assessment types, the level is already calculated
            if assessment_result.get('level'):
                return assessment_result['level']
            
            # Fallback to old method for backward compatibility
            assessment_type = assessment_result.get('type', 'unknown')
            percentage = self._calculate_percentage(assessment_result, assessment_type)
            
            return self._determine_level_from_percentage(percentage)
        except Exception as e:
            logger.error(f"Error getting assessment level: {e}")
            return "Nivel 1"

    def _calculate_percentage(self, assessment_result: Dict[str, Any], assessment_type: str) -> float:
        """Calculate percentage based on assessment type"""
        if assessment_type == 'percentage_based':
            return assessment_result.get('overall_percentage', 0)
        elif assessment_type == 'lecture_based_with_materia':
            total_lectures = assessment_result.get('total_lectures', 0)
            total_passed = assessment_result.get('total_lectures_passed', 0)
            return (total_passed / total_lectures * 100) if total_lectures > 0 else 0
        elif assessment_type in ['m1_difficulty_based', 'cl_skill_based', 'cien_materia_based', 'hyst_difficulty_based']:
            return assessment_result.get('overall_percentage', 0)
        else:  # lecture_based
            lectures_analyzed = assessment_result.get('lectures_analyzed', 0)
            lectures_passed = assessment_result.get('lectures_passed', 0)
            return (lectures_passed / lectures_analyzed * 100) if lectures_analyzed > 0 else 0

    def _determine_level_from_percentage(self, percentage: float) -> str:
        """Determine level based on percentage using thresholds"""
        for level, threshold in sorted(self.LEVEL_THRESHOLDS.items(), 
                                     key=lambda x: x[1], reverse=True):
            if percentage >= threshold:
                return level
        return "Nivel 1"

    def _generate_monthly_plan(self, user_results: Dict[str, Any], month: str) -> str:
        """Generate study plan for a specific month based on M1 and CL levels"""
        try:
            m1_numeric, cl_numeric = self._get_numeric_levels(user_results)
            combination_key = (m1_numeric, cl_numeric)
            
            if combination_key in self.STUDY_PLANS:
                plan_dict = self.STUDY_PLANS[combination_key]
                plan = plan_dict.get(month, plan_dict.get('default', 'Plan de estudio personalizado'))
                
                # Replace "Electivo" with the best elective test
                if plan == 'Electivo':
                    return self._determine_best_elective(user_results)
                
                return plan
            
            return "Plan de estudio personalizado"
        except Exception as e:
            logger.error(f"Error generating monthly plan: {e}")
            return "Plan de estudio personalizado"

    def _determine_best_elective(self, user_results: Dict[str, Any]) -> str:
        """Determine which elective test (CIEN or HYST) the student should take based on scores"""
        try:
            cien_result = user_results.get('CIEN', {})
            hyst_result = user_results.get('HYST', {})
            
            cien_percentage = self._calculate_percentage(cien_result, self.ASSESSMENT_TYPES.get('CIEN', 'unknown'))
            hyst_percentage = self._calculate_percentage(hyst_result, self.ASSESSMENT_TYPES.get('HYST', 'unknown'))
            
            # If both percentages are 0 (e.g., tests not taken or no data), return None
            if cien_percentage == 0 and hyst_percentage == 0:
                return None # Indicate no valid elective can be determined

            # Return the test with higher percentage
            if cien_percentage >= hyst_percentage:
                return 'CIEN'
            else:
                return 'HYST'
                
        except Exception as e:
            logger.error(f"Error determining best elective: {e}")
            return None # Return None on error

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
            
            if tables_html:
                html_content = html_content.replace('</body>', f'{tables_html}\n</body>')
                logger.info("Added comprehensive assessment tables to HTML template")
            
            return html_content
        except Exception as e:
            logger.error(f"Error adding comprehensive tables: {e}")
            return html_content

    def _generate_assessment_table(self, assessment_name: str, result: Dict[str, Any]) -> str:
        """Generate HTML table for a specific assessment"""
        try:
            assessment_type = result.get('type', 'unknown')
            
            table_generators = {
                'lecture_based': self._generate_lecture_based_table,
                'lecture_based_with_materia': self._generate_materia_based_table,
                'percentage_based': self._generate_percentage_based_table,
            }
            
            generator = table_generators.get(assessment_type)
            if generator:
                return generator(assessment_name, result)
            else:
                logger.warning(f"Unknown assessment type: {assessment_type}")
                return ""
        except Exception as e:
            logger.error(f"Error generating table for {assessment_name}: {e}")
            return ""

    def _generate_lecture_based_table(self, assessment_name: str, result: Dict[str, Any]) -> str:
        """Generate table for lecture-based assessments (M1, HYST)"""
        return self._generate_generic_table(
            assessment_name, result, 
            lecture_results=result.get('lecture_results', {}),
            subtitle=f"Lecciones Aprobadas: {result.get('lectures_passed', 0)}/{result.get('lectures_analyzed', 0)}",
            column_header="Estado",
            status_extractor=lambda data: data.get("status", "Reprobado"),
            status_classifier=self._get_status_class_for_lecture
        )

    def _generate_materia_based_table(self, assessment_name: str, result: Dict[str, Any]) -> str:
        """Generate table for materia-based assessments (CIEN)"""
        try:
            materia_results = result.get('materia_results', {})
            materia_lecture_results = result.get('materia_lecture_results', {})
            
            if not materia_results:
                return ""
            
            all_sections = []
            assessment_class = f"assessment-{assessment_name.lower()}"
            
            for i, (materia_name, materia_data) in enumerate(materia_results.items()):
                # Get lecture results for this materia
                materia_lecture_data = materia_lecture_results.get(materia_name, {})
                passed_lectures = materia_lecture_data.get('passed_lectures', [])
                failed_lectures = materia_lecture_data.get('failed_lectures', [])
                
                # Create lecture results format expected by generic table
                lecture_results = {}
                
                # Add passed lectures
                for lecture in passed_lectures:
                    lecture_results[lecture] = {"status": "Aprobado"}
                
                # Add failed lectures
                for lecture in failed_lectures:
                    lecture_results[lecture] = {"status": "Reprobado"}
                
                if i == 0:  # First materia
                    total_passed = result.get('passed_lectures_count', 0)
                    total_failed = result.get('failed_lectures_count', 0)
                    subtitle = f"Lecciones Aprobadas: {total_passed}/{total_passed + total_failed}"
                    continuation_text = ""
                else:
                    subtitle = ""
                    continuation_text = ""
                
                section = self._generate_generic_table(
                    assessment_name, result,
                    lecture_results=lecture_results,
                    subtitle=subtitle,
                    continuation_text=continuation_text,
                    column_header="Estado",
                    status_extractor=lambda data: data.get("status", "Reprobado"),
                    status_classifier=self._get_status_class_for_lecture,
                    assessment_class=assessment_class,
                    materia_name=materia_name
                )
                all_sections.append(section)
            
            return ''.join(all_sections)
        except Exception as e:
            logger.error(f"Error generating materia-based table: {e}")
            return ""

    def _generate_percentage_based_table(self, assessment_name: str, result: Dict[str, Any]) -> str:
        """Generate table for percentage-based assessments (CL)"""
        return self._generate_generic_table(
            assessment_name, result,
            lecture_results=result.get('lecture_results', {}),
            subtitle=f"Porcentaje General: {result.get('overall_percentage', 0):.1f}%",
            column_header="Porcentaje",
            status_extractor=lambda data: f"{data.get('percentage', 0):.1f}%",
            status_classifier=self._get_status_class_for_percentage
        )

    def _generate_generic_table(self, assessment_name: str, result: Dict[str, Any],
                               lecture_results: Dict[str, Any], subtitle: str,
                               column_header: str, status_extractor, status_classifier,
                               assessment_class: str = None, materia_name: str = None,
                               continuation_text: str = "") -> str:
        """Generic table generator to reduce code duplication"""
        try:
            if not lecture_results:
                return ""
            
            if assessment_class is None:
                assessment_class = f"assessment-{assessment_name.lower()}"
            
            # Split lectures into pages of 20 each
            lecture_items = list(lecture_results.items())
            all_sections = []
            
            for i in range(0, len(lecture_items), 20):
                page_lectures = lecture_items[i:i+20]
                table_rows = []
                
                for lecture_name, lecture_data in page_lectures:
                    status_value = status_extractor(lecture_data)
                    status_class = status_classifier(lecture_data)
                    
                    row = self.TABLE_ROW_TEMPLATE.format(
                        lecture_name=lecture_name,
                        status_class=status_class,
                        status_value=status_value
                    )
                    table_rows.append(row)
                
                # Determine if this is a continuation page
                is_continuation = i > 0
                current_continuation_text = continuation_text
                if is_continuation:
                    current_continuation_text = "<p class=\"subtitle\">(Continuación)</p>"
                
                # Add materia name if provided
                materia_text = f"<p class=\"materia-title\">{materia_name}</p>" if materia_name else ""
                
                section = self.SECTION_TEMPLATE.format(
                    assessment_class=assessment_class,
                    assessment_name=assessment_name,
                    subtitle=subtitle,
                    continuation_text=current_continuation_text + materia_text,
                    column_header=column_header,
                    table_rows=''.join(table_rows)
                )
                all_sections.append(section)
            
            return ''.join(all_sections)
        except Exception as e:
            logger.error(f"Error generating generic table: {e}")
            return ""

    def _get_status_class_for_lecture(self, lecture_data: Dict[str, Any]) -> str:
        """Get CSS class for lecture status"""
        status_string = lecture_data.get("status", "Reprobado")
        return "status-aprobada" if status_string == "Aprobado" else "status-reprobada"

    def _get_status_class_for_percentage(self, lecture_data: Dict[str, Any]) -> str:
        """Get CSS class for percentage status"""
        percentage = lecture_data.get("percentage", 0)
        if percentage >= 80:
            return "status-aprobada"
        elif percentage >= 60:
            return "status-intermedia"
        else:
            return "status-reprobada"

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
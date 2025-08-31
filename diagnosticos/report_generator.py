#!/usr/bin/env python3
"""
Report generator for individual student assessment reports
Generates PDF reports using HTML templates with variables
Uses weasyprint for HTML-to-PDF conversion
"""

import os
import logging
import csv
from typing import Dict, Any, Optional, List
from weasyprint import HTML
from storage import StorageClient
import pandas as pd

logger = logging.getLogger(__name__)

class ReportGenerator:
    def __init__(self):
        """Initialize report generator"""
        self.storage = StorageClient()
        self.templates_dir = "templates"
        self.questions_dir = "data/questions"
        self.analysis_dir = "data/analysis"

    def generate_pdf(self, assessment_title: str, analysis_result: Dict[str, Any], user_info: Dict[str, Any], incremental_mode: bool = False, analysis_df: pd.DataFrame = None) -> Optional[bytes]:
        """
        Generate PDF report for student using HTML template

        Args:
            assessment_title: Title of the assessment (M1, CL, CIEN, HYST)
            analysis_result: Analysis results from AssessmentAnalyzer
            user_info: User information
            incremental_mode: If True, use temporary analysis files
            analysis_df: Optional DataFrame with analysis data (if provided, use this instead of file)

        Returns:
            PDF content as bytes if successful, None otherwise
        """
        try:
            # Generate PDF using HTML template with weasyprint
            pdf_content = self._generate_pdf_from_html_template(assessment_title, analysis_result, user_info, incremental_mode, analysis_df)
            
            logger.info(f"Generated PDF report for {user_info.get('username', 'Unknown')} - {assessment_title}")
            return pdf_content

        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            return None

    def _generate_pdf_from_html_template(self, assessment_title: str, analysis_result: Dict[str, Any], user_info: Dict[str, Any], incremental_mode: bool = False, analysis_df: pd.DataFrame = None) -> bytes:
        """Generate PDF from HTML template using weasyprint"""
        try:
            # Determine template file based on assessment type
            template_file = f"{assessment_title}.html"
            template_path = os.path.join(self.templates_dir, template_file)
            
            # Load HTML template from local file
            if not os.path.exists(template_path):
                logger.error(f"HTML template not found: {template_path}")
                raise Exception(f"HTML template not found: {template_path}")

            with open(template_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            logger.info(f"Loaded HTML template: {template_path}, size: {len(html_content)} characters")

            # Calculate variables
            username = user_info.get('username', user_info.get('email', 'Estudiante'))
            
            # Replace basic variables in HTML
            variables = {
                '<<ALUMNO>>': username,
                '<<Nombre>>': username,
                '<<MATERIA>>': assessment_title,
                '<<Prueba>>': assessment_title,
            }

            for var_name, var_value in variables.items():
                html_content = html_content.replace(var_name, str(var_value))

            logger.info("Basic variables replaced in HTML template")

            # Add assessment-specific content based on type
            if assessment_title in ["M1", "HYST"]:
                html_content = self._add_lecture_status_table(html_content, analysis_result, assessment_title, incremental_mode, analysis_df)
            elif assessment_title == "CL":
                html_content = self._add_skill_percentage_table(html_content, analysis_result, incremental_mode, analysis_df)
            elif assessment_title == "CIEN":
                html_content = self._add_subject_lecture_table(html_content, analysis_result, assessment_title, incremental_mode, analysis_df)

            # Generate PDF using weasyprint
            logger.info("Generating PDF with weasyprint...")
            html_doc = HTML(string=html_content)
            pdf_content = html_doc.write_pdf()
            
            logger.info("✅ PDF generated successfully")
            return pdf_content

        except Exception as e:
            logger.error(f"Error generating PDF from HTML template: {e}")
            raise

    def _get_analysis_file_path(self, assessment_title: str, incremental_mode: bool = False) -> str:
        """Get the correct analysis file path based on mode"""
        if incremental_mode:
            return os.path.join(self.analysis_dir, f"temp_{assessment_title}.csv")
        else:
            return os.path.join(self.analysis_dir, f"{assessment_title}.csv")

    def _get_student_level_from_analysis_file(self, assessment_title: str, user_email: str, incremental_mode: bool = False, analysis_df: pd.DataFrame = None) -> str:
        """Get the student's level from analysis CSV file or DataFrame"""
        try:
            if analysis_df is not None:
                # Use provided DataFrame
                user_row = analysis_df[analysis_df['email'] == user_email]
                if not user_row.empty:
                    level = user_row.iloc[0].get('level', '').strip()
                    logger.info(f"Found level '{level}' for {user_email} in {assessment_title} DataFrame")
                    return level
                else:
                    logger.warning(f"No level found for user {user_email} in {assessment_title} DataFrame")
                    return ""
            else:
                # Use file-based approach
                analysis_file = self._get_analysis_file_path(assessment_title, incremental_mode)
                if not os.path.exists(analysis_file):
                    logger.error(f"Analysis file not found: {analysis_file}")
                    return ""

                with open(analysis_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f, delimiter=';')
                    for row in reader:
                        if row.get('email', '').strip() == user_email:
                            level = row.get('level', '').strip()
                            logger.info(f"Found level '{level}' for {user_email} in {assessment_title}")
                            return level

                logger.warning(f"No level found for user {user_email} in {assessment_title} analysis file")
                return ""

        except Exception as e:
            logger.error(f"Error getting student level from analysis file: {e}")
            return ""

    def _get_lecture_order_from_questions(self, assessment_title: str) -> List[str]:
        """Get the ordered list of lectures from the question file without duplicates"""
        try:
            question_file = os.path.join(self.questions_dir, f"{assessment_title}.csv")
            if not os.path.exists(question_file):
                logger.error(f"Question file not found: {question_file}")
                return []

            lectures = []
            seen_lectures = set()
            
            with open(question_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter=';')
                for row in reader:
                    lecture = row.get('lecture', '').strip()
                    if lecture and lecture not in seen_lectures:
                        lectures.append(lecture)
                        seen_lectures.add(lecture)
            
            logger.info(f"Found {len(lectures)} unique lectures in order from {assessment_title} questions")
            return lectures

        except Exception as e:
            logger.error(f"Error reading lecture order from questions: {e}")
            return []

    def _get_lecture_status_from_analysis_file(self, assessment_title: str, user_email: str, incremental_mode: bool = False, analysis_df: pd.DataFrame = None) -> Dict[str, str]:
        """Get the status (passed/failed) for each lecture from analysis CSV file or DataFrame"""
        try:
            if analysis_df is not None:
                # Use provided DataFrame
                user_row = analysis_df[analysis_df['email'] == user_email]
                if not user_row.empty:
                    row = user_row.iloc[0]
                    passed_lectures_str = row.get("passed_lectures", "")
                    failed_lectures_str = row.get("failed_lectures", "")
                    
                    # Parse lecture lists (they are pipe-separated in CSV)
                    passed_lectures = [lecture.strip() for lecture in passed_lectures_str.split('|') if lecture.strip()] if passed_lectures_str else []
                    failed_lectures = [lecture.strip() for lecture in failed_lectures_str.split('|') if lecture.strip()] if failed_lectures_str else []
                    
                    # Create status dictionary
                    lecture_status = {}
                    
                    # Add passed lectures
                    for lecture in passed_lectures:
                        lecture_status[lecture] = "passed"
                    
                    # Add failed lectures
                    for lecture in failed_lectures:
                        lecture_status[lecture] = "failed"
                    
                    logger.info(f"Found {len(passed_lectures)} passed and {len(failed_lectures)} failed lectures for {user_email} in {assessment_title} DataFrame")
                    return lecture_status
                else:
                    logger.warning(f"No data found for user {user_email} in {assessment_title} DataFrame")
                    return {}
            else:
                # Use file-based approach
                analysis_file = self._get_analysis_file_path(assessment_title, incremental_mode)
                if not os.path.exists(analysis_file):
                    logger.error(f"Analysis file not found: {analysis_file}")
                    return {}

                with open(analysis_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f, delimiter=';')
                    for row in reader:
                        if row.get('email', '').strip() == user_email:
                            passed_lectures_str = row.get("passed_lectures", "")
                            failed_lectures_str = row.get("failed_lectures", "")
                            
                            # Parse lecture lists (they are pipe-separated in CSV)
                            passed_lectures = [lecture.strip() for lecture in passed_lectures_str.split('|') if lecture.strip()] if passed_lectures_str else []
                            failed_lectures = [lecture.strip() for lecture in failed_lectures_str.split('|') if lecture.strip()] if failed_lectures_str else []
                            
                            # Create status dictionary
                            lecture_status = {}
                            
                            # Add passed lectures
                            for lecture in passed_lectures:
                                lecture_status[lecture] = "passed"
                            
                            # Add failed lectures
                            for lecture in failed_lectures:
                                lecture_status[lecture] = "failed"
                            
                            logger.info(f"Found {len(passed_lectures)} passed and {len(failed_lectures)} failed lectures for {user_email} in {assessment_title}")
                            return lecture_status

                logger.warning(f"No data found for user {user_email} in {assessment_title} analysis file")
                return {}

        except Exception as e:
            logger.error(f"Error getting lecture status from analysis file: {e}")
            return {}

    def _get_skill_data_from_analysis_file(self, assessment_title: str, user_email: str, incremental_mode: bool = False, analysis_df: pd.DataFrame = None) -> Dict[str, float]:
        """Get skill percentage data from analysis CSV file or DataFrame"""
        try:
            if analysis_df is not None:
                # Use provided DataFrame
                user_row = analysis_df[analysis_df['email'] == user_email]
                if not user_row.empty:
                    row = user_row.iloc[0]
                    skill_data = {}
                    
                    # Look for skill percentage columns
                    for key, value in row.items():
                        if key.startswith('skill_') and key.endswith('_percentage'):
                            skill_name = key.replace('skill_', '').replace('_percentage', '').title()
                            try:
                                # Convert percentage string to float
                                percentage = float(value.replace(',', '.')) if value else 0.0
                                skill_data[skill_name] = percentage
                            except (ValueError, AttributeError):
                                skill_data[skill_name] = 0.0
                    
                    logger.info(f"Found {len(skill_data)} skills for {user_email} in {assessment_title} DataFrame")
                    return skill_data
                else:
                    logger.warning(f"No data found for user {user_email} in {assessment_title} DataFrame")
                    return {}
            else:
                # Use file-based approach
                analysis_file = self._get_analysis_file_path(assessment_title, incremental_mode)
                if not os.path.exists(analysis_file):
                    logger.error(f"Analysis file not found: {analysis_file}")
                    return {}

                with open(analysis_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f, delimiter=';')
                    for row in reader:
                        if row.get('email', '').strip() == user_email:
                            skill_data = {}
                            
                            # Look for skill percentage columns
                            for key, value in row.items():
                                if key.startswith('skill_') and key.endswith('_percentage'):
                                    skill_name = key.replace('skill_', '').replace('_percentage', '').title()
                                    try:
                                        # Convert percentage string to float
                                        percentage = float(value.replace(',', '.')) if value else 0.0
                                        skill_data[skill_name] = percentage
                                    except (ValueError, AttributeError):
                                        skill_data[skill_name] = 0.0
                            
                            logger.info(f"Found {len(skill_data)} skills for {user_email} in {assessment_title}")
                            return skill_data

                logger.warning(f"No data found for user {user_email} in {assessment_title} analysis file")
                return {}

        except Exception as e:
            logger.error(f"Error getting skill data from analysis file: {e}")
            return {}

    def _get_subject_lecture_order_from_questions(self, assessment_title: str) -> List[Dict[str, str]]:
        """Get the ordered list of subject-lecture pairs from the question file without duplicates"""
        try:
            question_file = os.path.join(self.questions_dir, f"{assessment_title}.csv")
            if not os.path.exists(question_file):
                logger.error(f"Question file not found: {question_file}")
                return []

            subject_lectures = []
            seen_pairs = set()
            
            with open(question_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter=';')
                for row in reader:
                    lecture = row.get('lecture', '').strip()
                    subject = row.get('Materia', '').strip()
                    
                    if lecture and subject:
                        pair_key = f"{subject}|{lecture}"
                        if pair_key not in seen_pairs:
                            subject_lectures.append({
                                'subject': subject,
                                'lecture': lecture
                            })
                            seen_pairs.add(pair_key)
            
            logger.info(f"Found {len(subject_lectures)} unique subject-lecture pairs in order from {assessment_title} questions")
            return subject_lectures

        except Exception as e:
            logger.error(f"Error reading subject-lecture order from questions: {e}")
            return []

    def _get_subject_lecture_status_from_analysis_file(self, assessment_title: str, user_email: str, incremental_mode: bool = False, analysis_df: pd.DataFrame = None) -> Dict[str, Dict[str, str]]:
        """Get the status (passed/failed) for each subject-lecture pair from analysis CSV file or DataFrame"""
        try:
            if analysis_df is not None:
                # Use provided DataFrame
                user_row = analysis_df[analysis_df['email'] == user_email]
                if not user_row.empty:
                    row = user_row.iloc[0]
                    subject_status = {}
                    
                    # Look for materia columns
                    for key, value in row.items():
                        if key.startswith('materia_') and key.endswith('_passed_lectures'):
                            materia_name = key.replace('materia_', '').replace('_passed_lectures', '').replace('_', ' ').title()
                            passed_lectures_str = value
                            failed_lectures_str = row.get(f'materia_{key.replace("materia_", "").replace("_passed_lectures", "")}_failed_lectures', '')
                            
                            # Parse lecture lists (they are pipe-separated in CSV)
                            passed_lectures = [lecture.strip() for lecture in passed_lectures_str.split('|') if lecture.strip()] if passed_lectures_str else []
                            failed_lectures = [lecture.strip() for lecture in failed_lectures_str.split('|') if lecture.strip()] if failed_lectures_str else []
                            
                            subject_status[materia_name] = {}
                            
                            # Add passed lectures
                            for lecture in passed_lectures:
                                subject_status[materia_name][lecture] = "passed"
                            
                            # Add failed lectures
                            for lecture in failed_lectures:
                                subject_status[materia_name][lecture] = "failed"
                    
                    logger.info(f"Found status for {len(subject_status)} subjects for {user_email} in {assessment_title} DataFrame")
                    return subject_status
                else:
                    logger.warning(f"No data found for user {user_email} in {assessment_title} DataFrame")
                    return {}
            else:
                # Use file-based approach
                analysis_file = self._get_analysis_file_path(assessment_title, incremental_mode)
                if not os.path.exists(analysis_file):
                    logger.error(f"Analysis file not found: {analysis_file}")
                    return {}

                with open(analysis_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f, delimiter=';')
                    for row in reader:
                        if row.get('email', '').strip() == user_email:
                            subject_status = {}
                            
                            # Look for materia columns
                            for key, value in row.items():
                                if key.startswith('materia_') and key.endswith('_passed_lectures'):
                                    materia_name = key.replace('materia_', '').replace('_passed_lectures', '').replace('_', ' ').title()
                                    passed_lectures_str = value
                                    failed_lectures_str = row.get(f'materia_{key.replace("materia_", "").replace("_passed_lectures", "")}_failed_lectures', '')
                                    
                                    # Parse lecture lists (they are pipe-separated in CSV)
                                    passed_lectures = [lecture.strip() for lecture in passed_lectures_str.split('|') if lecture.strip()] if passed_lectures_str else []
                                    failed_lectures = [lecture.strip() for lecture in failed_lectures_str.split('|') if lecture.strip()] if failed_lectures_str else []
                                    
                                    subject_status[materia_name] = {}
                                    
                                    # Add passed lectures
                                    for lecture in passed_lectures:
                                        subject_status[materia_name][lecture] = "passed"
                                    
                                    # Add failed lectures
                                    for lecture in failed_lectures:
                                        subject_status[materia_name][lecture] = "failed"
                            
                            logger.info(f"Found status for {len(subject_status)} subjects for {user_email} in {assessment_title}")
                            return subject_status

                logger.warning(f"No data found for user {user_email} in {assessment_title} analysis file")
                return {}

        except Exception as e:
            logger.error(f"Error getting subject-lecture status from analysis file: {e}")
            return {}

    def _add_lecture_status_table(self, html_content: str, analysis_result: Dict[str, Any], assessment_title: str, incremental_mode: bool = False, analysis_df: pd.DataFrame = None) -> str:
        """Add lecture status table for M1 and HYST assessments using question order"""
        try:
            # Get user email from analysis_result or user_info
            user_email = analysis_result.get('email', '')
            if not user_email:
                logger.warning("No user email found in analysis_result")
                return html_content

            logger.info(f"Processing lecture status table for {assessment_title} - User: {user_email}")

            # Get lecture order from question file
            lecture_order = self._get_lecture_order_from_questions(assessment_title)
            if not lecture_order:
                logger.warning("No lecture order found for lecture status table")
                return html_content

            logger.info(f"Found {len(lecture_order)} lectures in question order")

            # Get lecture status from analysis file
            lecture_status = self._get_lecture_status_from_analysis_file(assessment_title, user_email, incremental_mode, analysis_df)
            if not lecture_status:
                logger.warning("No lecture status found for lecture status table")
                return html_content

            logger.info(f"Found status for {len(lecture_status)} lectures")

            # Get student level from analysis file
            student_level = self._get_student_level_from_analysis_file(assessment_title, user_email, incremental_mode, analysis_df)

            # Split lectures into pages (max 20 per page for M1, 15 for HYST due to longer names)
            if assessment_title == "HYST":
                lectures_per_page = 15
            else:
                lectures_per_page = 20
            lecture_pages = [lecture_order[i:i + lectures_per_page] for i in range(0, len(lecture_order), lectures_per_page)]

            # Create table HTML for each page
            table_sections = []
            
            for page_num, page_lectures in enumerate(lecture_pages, 1):
                table_rows = []
                
                for lecture_name in page_lectures:
                    status = lecture_status.get(lecture_name, "unknown")
                    if status == "passed":
                        status_class = "status-aprobada"
                        status_text = "Aprobada"
                        status_style = "background-color: #d4edda;"
                    elif status == "failed":
                        status_class = "status-reprobada"
                        status_text = "Reprobada"
                        status_style = "background-color: #f8d7da;"
                    else:
                        status_class = "status-unknown"
                        status_text = "Sin datos"
                        status_style = ""
                    
                    row = f"""
        <tr>
          <td style="border: 1px solid #000; padding: 8px; text-align: left;">{lecture_name}</td>
          <td style="border: 1px solid #000; padding: 8px; text-align: center; font-weight: bold; {status_style}">{status_text}</td>
        </tr>"""
                    table_rows.append(row)

                page_title = f"Resultados por Lección - Página {page_num}" if len(lecture_pages) > 1 else "Resultados por Lección"
                
                # Add level text only on first page
                level_text = ""
                if page_num == 1 and student_level:
                    level_text = f'<p style="text-align: center; margin-bottom: 15px; font-weight: bold; font-size: 18px;">Tu nivel es: {student_level}</p>'
                
                table_html = f"""
<section class="page">
  <div class="content" style="text-align: center;">
    {level_text}
    <p class="TituloAlumno Negrita">{page_title}</p>
    <table style="width: 550px; border-collapse: collapse; margin: 20px auto; border: 1px solid #000;">
      <thead>
        <tr>
          <th style="border: 1px solid #000; padding: 12px; text-align: center; background-color: #f0f0f0; font-weight: bold; width: 450px;">Lección</th>
          <th style="border: 1px solid #000; padding: 12px; text-align: center; background-color: #f0f0f0; font-weight: bold; width: 100px;">Estado</th>
        </tr>
      </thead>
      <tbody>
        {''.join(table_rows)}
      </tbody>
    </table>
  </div>
</section>"""
                table_sections.append(table_html)

            # Insert all table sections before closing body tag
            all_tables_html = '\n'.join(table_sections)
            html_content = html_content.replace('</body>', f'{all_tables_html}\n</body>')
            logger.info(f"Added lecture status table with {len(lecture_order)} lectures in {len(lecture_pages)} pages")
            return html_content

        except Exception as e:
            logger.error(f"Error adding lecture status table: {e}")
            return html_content

    def _add_skill_percentage_table(self, html_content: str, analysis_result: Dict[str, Any], incremental_mode: bool = False, analysis_df: pd.DataFrame = None) -> str:
        """Add skill percentage table for CL assessment"""
        try:
            # Get user email from analysis_result
            user_email = analysis_result.get('email', '')
            if not user_email:
                logger.warning("No user email found in analysis_result")
                return html_content

            logger.info(f"Processing skill percentage table for CL - User: {user_email}")

            # Get skill data from analysis file
            skill_data = self._get_skill_data_from_analysis_file("CL", user_email, incremental_mode, analysis_df)
            if not skill_data:
                logger.warning("No skill data found for skill percentage table")
                return html_content

            logger.info(f"Found {len(skill_data)} skills")

            # Get student level from analysis file
            student_level = self._get_student_level_from_analysis_file("CL", user_email, incremental_mode, analysis_df)

            # Create table HTML
            table_rows = []
            for skill_name, percentage in skill_data.items():
                # Convert decimal to percentage (e.g., 0.9 -> 90%)
                percentage_display = percentage * 100
                # No color coding for CL table - clean white background
                row = f"""
        <tr>
          <td style="border: 1px solid #000; padding: 8px; text-align: left;">{skill_name}</td>
          <td style="border: 1px solid #000; padding: 8px; text-align: center; font-weight: bold;">{percentage_display:.0f}%</td>
        </tr>"""
                table_rows.append(row)

            # Add level text
            level_text = ""
            if student_level:
                level_text = f'<p style="text-align: center; margin-bottom: 15px; font-weight: bold; font-size: 18px;">Tu nivel es: {student_level}</p>'

            table_html = f"""
<section class="page">
  <div class="content" style="text-align: center;">
    {level_text}
    <p class="TituloAlumno Negrita">Resultados por Habilidad</p>
    <table style="width: 550px; border-collapse: collapse; margin: 20px auto; border: 1px solid #000;">
      <thead>
        <tr>
          <th style="border: 1px solid #000; padding: 12px; text-align: center; background-color: #f0f0f0; font-weight: bold; width: 275px;">Habilidad</th>
          <th style="border: 1px solid #000; padding: 12px; text-align: center; background-color: #f0f0f0; font-weight: bold; width: 275px;">Porcentaje Dominio</th>
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
            logger.info(f"Added skill percentage table with {len(skill_data)} skills")
            return html_content

        except Exception as e:
            logger.error(f"Error adding skill percentage table: {e}")
            return html_content

    def _add_subject_lecture_table(self, html_content: str, analysis_result: Dict[str, Any], assessment_title: str, incremental_mode: bool = False, analysis_df: pd.DataFrame = None) -> str:
        """Add subject and lecture table for CIEN assessment using question order"""
        try:
            # Get user email from analysis_result
            user_email = analysis_result.get('email', '')
            if not user_email:
                logger.warning("No user email found in analysis_result")
                return html_content

            logger.info(f"Processing subject lecture table for {assessment_title} - User: {user_email}")

            # Get subject-lecture order from question file
            subject_lecture_order = self._get_subject_lecture_order_from_questions(assessment_title)
            if not subject_lecture_order:
                logger.warning("No subject-lecture order found for subject lecture table")
                return html_content

            logger.info(f"Found {len(subject_lecture_order)} subject-lecture pairs in question order")

            # Get subject-lecture status from analysis file
            subject_status = self._get_subject_lecture_status_from_analysis_file(assessment_title, user_email, incremental_mode, analysis_df)
            if not subject_status:
                logger.warning("No subject-lecture status found for subject lecture table")
                return html_content

            logger.info(f"Found status for {len(subject_status)} subjects")

            # Get student level from analysis file
            student_level = self._get_student_level_from_analysis_file(assessment_title, user_email, incremental_mode, analysis_df)

            # Split subject-lectures into pages (max 20 per page)
            items_per_page = 20
            item_pages = [subject_lecture_order[i:i + items_per_page] for i in range(0, len(subject_lecture_order), items_per_page)]

            # Create table HTML for each page
            table_sections = []
            
            for page_num, page_items in enumerate(item_pages, 1):
                table_rows = []
                
                for item in page_items:
                    subject_name = item['subject']
                    lecture_name = item['lecture']
                    
                    # Get status for this subject-lecture pair
                    subject_lecture_status = subject_status.get(subject_name, {})
                    status = subject_lecture_status.get(lecture_name, "unknown")
                    
                    if status == "passed":
                        status_class = "status-aprobada"
                        status_text = "Aprobada"
                        status_style = "background-color: #d4edda;"
                    elif status == "failed":
                        status_class = "status-reprobada"
                        status_text = "Reprobada"
                        status_style = "background-color: #f8d7da;"
                    else:
                        status_class = "status-unknown"
                        status_text = "Sin datos"
                        status_style = ""
                    
                    row = f"""
        <tr>
          <td style="border: 1px solid #000; padding: 8px; text-align: left;">{subject_name}</td>
          <td style="border: 1px solid #000; padding: 8px; text-align: left;">{lecture_name}</td>
          <td style="border: 1px solid #000; padding: 8px; text-align: center; font-weight: bold; {status_style}">{status_text}</td>
        </tr>"""
                    table_rows.append(row)

                page_title = f"Resultados por Materia y Lección - Página {page_num}" if len(item_pages) > 1 else "Resultados por Materia y Lección"
                
                # Add level text only on first page
                level_text = ""
                if page_num == 1 and student_level:
                    level_text = f'<p style="text-align: center; margin-bottom: 15px; font-weight: bold; font-size: 18px;">Tu nivel es: {student_level}</p>'
                
                table_html = f"""
<section class="page">
  <div class="content" style="text-align: center;">
    {level_text}
    <p class="TituloAlumno Negrita">{page_title}</p>
    <table style="width: 550px; border-collapse: collapse; margin: 20px auto; border: 1px solid #000;">
      <thead>
        <tr>
          <th style="border: 1px solid #000; padding: 12px; text-align: center; background-color: #f0f0f0; font-weight: bold; width: 100px;">Materia</th>
          <th style="border: 1px solid #000; padding: 12px; text-align: center; background-color: #f0f0f0; font-weight: bold; width: 100px;">Lección</th>
          <th style="border: 1px solid #000; padding: 12px; text-align: center; background-color: #f0f0f0; font-weight: bold; width: 350px;">Estado</th>
        </tr>
      </thead>
      <tbody>
        {''.join(table_rows)}
      </tbody>
    </table>
  </div>
</section>"""
                table_sections.append(table_html)

            # Insert all table sections before closing body tag
            all_tables_html = '\n'.join(table_sections)
            html_content = html_content.replace('</body>', f'{all_tables_html}\n</body>')
            logger.info(f"Added subject lecture table with {len(subject_lecture_order)} entries in {len(item_pages)} pages")
            return html_content

        except Exception as e:
            logger.error(f"Error adding subject lecture table: {e}")
            return html_content

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
        self.processed_dir = "data/processed"
        self.analysis_dir = "data/analysis"
        self.lectures_file = "data/questions/lecciones.xlsx"
        self.lectures_data = None

    def generate_pdf(self, assessment_title: str, analysis_result: Dict[str, Any], user_info: Dict[str, Any], incremental_mode: bool = False, analysis_df: pd.DataFrame = None) -> Optional[bytes]:
        """
        Generate PDF report for student using HTML template

        Args:
            assessment_title: Title of the assessment (M1, CL, CIEN, HYST)
            analysis_result: Analysis results from AssessmentAnalyzer
            user_info: User information
            incremental_mode: If True, use in-memory analysis data
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
            # Always use Portada.html template
            template_file = "Portada.html"
            template_path = os.path.join(self.templates_dir, template_file)
            
            # Always load HTML template from local filesystem (container) regardless of storage backend
            if not os.path.exists(template_path):
                logger.error(f"HTML template not found in container: {template_path}")
                raise Exception(f"HTML template not found in container: {template_path}")

            # Read template directly from local filesystem with proper encoding
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

            # Add assessment-specific content based on type (only M1 and HYST supported)
            if assessment_title in ["M1", "HYST", "F30M", "B30M", "Q30M"]:
                html_content = self._add_question_detail_table(html_content, analysis_result, assessment_title, user_info)

            # Generate PDF using weasyprint
            logger.info("Generating PDF with weasyprint...")
            html_doc = HTML(string=html_content)
            pdf_content = html_doc.write_pdf()
            
            logger.info("✅ PDF generated successfully")
            return pdf_content

        except Exception as e:
            logger.error(f"Error generating PDF from HTML template: {e}")
            raise

    def _get_analysis_file_path(self, assessment_title: str) -> str:
        """Get the analysis file path"""
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
                # Use file-based approach (only in non-incremental mode)
                if incremental_mode:
                    logger.warning(f"No analysis DataFrame provided for {user_email} in incremental mode")
                    return ""
                
                analysis_file = self._get_analysis_file_path(assessment_title)
                if not self.storage.exists(analysis_file):
                    logger.error(f"Analysis file not found: {analysis_file}")
                    return ""

                # Use StorageClient to read CSV
                analysis_df = self.storage.read_csv(analysis_file, sep=';')
                user_row = analysis_df[analysis_df['email'] == user_email]
                if not user_row.empty:
                    level = user_row.iloc[0].get('level', '').strip()
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
            if not self.storage.exists(question_file):
                logger.error(f"Question file not found: {question_file}")
                return []

            # Use StorageClient to read CSV
            questions_df = self.storage.read_csv(question_file, sep=';')
            lectures = []
            seen_lectures = set()
            
            for _, row in questions_df.iterrows():
                lecture = row.get('lecture', '').strip()
                if lecture and lecture not in seen_lectures:
                    lectures.append(lecture)
                    seen_lectures.add(lecture)
            
            logger.info(f"Found {len(lectures)} unique lectures in order from {assessment_title} questions")
            return lectures

        except Exception as e:
            logger.error(f"Error reading lecture order from questions: {e}")
            return []

    def _load_processed_data(self, assessment_title: str) -> Optional[pd.DataFrame]:
        """Load processed data file for an assessment"""
        try:
            processed_file = os.path.join(self.processed_dir, f"{assessment_title}.csv")
            if not self.storage.exists(processed_file):
                logger.warning(f"Processed file not found: {processed_file}")
                return None
            
            processed_df = self.storage.read_csv(processed_file, sep=';')
            logger.info(f"Loaded processed data for {assessment_title}")
            return processed_df
        except Exception as e:
            logger.error(f"Error loading processed data for {assessment_title}: {e}")
            return None
    
    def _load_lectures_data(self) -> Optional[pd.DataFrame]:
        """Load lectures data from Excel file"""
        try:
            if self.lectures_data is not None:
                return self.lectures_data
            
            if not self.storage.exists(self.lectures_file):
                logger.warning(f"Lectures file not found: {self.lectures_file}")
                return None
            
            # Read Excel file
            self.lectures_data = pd.read_excel(self.lectures_file)
            logger.info(f"Loaded lectures data from {self.lectures_file}")
            return self.lectures_data
        except Exception as e:
            logger.error(f"Error loading lectures data: {e}")
            return None
    
    def _get_lecture_name(self, assessment_title: str, lecture_code: str) -> str:
        """Get lecture name from Excel file"""
        try:
            lectures_df = self._load_lectures_data()
            if lectures_df is None:
                return lecture_code
            
            # Filter by assessment and lecture code
            # Assuming columns are: Assessment, Lecture, LectureName
            row = lectures_df[
                (lectures_df.iloc[:, 0] == assessment_title) & 
                (lectures_df.iloc[:, 1] == lecture_code)
            ]
            
            if not row.empty:
                lecture_name = row.iloc[0, 2]  # Third column
                logger.info(f"Found lecture name for {assessment_title}/{lecture_code}: {lecture_name}")
                return str(lecture_name)
            else:
                logger.warning(f"No lecture name found for {assessment_title}/{lecture_code}")
                return lecture_code
        except Exception as e:
            logger.error(f"Error getting lecture name: {e}")
            return lecture_code

    def _add_question_detail_table(self, html_content: str, analysis_result: Dict[str, Any], assessment_title: str, user_info: Dict[str, Any]) -> str:
        """Add question detail table with 3 columns: Pregunta, Alternativa Marcada, Lección"""
        try:
            # Get username from user_info
            username = user_info.get('username', user_info.get('email', ''))
            if not username:
                logger.warning("No username found in user_info")
                return html_content
            
            logger.info(f"Processing question detail table for {assessment_title} - User: {username}")
            
            # Load questions file
            questions_file = os.path.join(self.questions_dir, f"{assessment_title}.csv")
            if not self.storage.exists(questions_file):
                logger.error(f"Questions file not found: {questions_file}")
                return html_content
            
            questions_df = self.storage.read_csv(questions_file, sep=';')
            logger.info(f"Loaded questions data for {assessment_title}")
            
            # Load processed file
            processed_df = self._load_processed_data(assessment_title)
            if processed_df is None:
                logger.error(f"Could not load processed data for {assessment_title}")
                return html_content
            
            # Find student's answers in processed data
            # Try both 'username' and 'email' columns
            student_answers = pd.DataFrame()
            
            if 'username' in processed_df.columns:
                student_answers = processed_df[processed_df['username'] == username]
            elif 'email' in processed_df.columns:
                student_answers = processed_df[processed_df['email'] == username]
                
            if student_answers.empty:
                logger.warning(f"No processed data found for {username} in {assessment_title}")
                logger.warning(f"Available columns: {list(processed_df.columns)}")
                return html_content
            
            student_row = student_answers.iloc[0]
            
            # Get all question columns (Pregunta 1, Pregunta 2, etc.)
            question_columns = [col for col in processed_df.columns if col.startswith('Pregunta ')]
            question_columns.sort(key=lambda x: int(x.split(' ')[1]))  # Sort by question number
            
            logger.info(f"Found {len(question_columns)} questions for {assessment_title}")
            
            # Create table rows with merged lecture cells
            # First, collect all question data
            question_data = []
            for question_col in question_columns:
                question_num = question_col.split(' ')[1]
                
                # Get lecture and correct answer from questions file using question_number column
                question_row = questions_df[questions_df['question_number'] == int(question_num)]
                lecture = question_row.iloc[0].get('lecture', 'N/A') if not question_row.empty else 'N/A'
                correct_answer = question_row.iloc[0].get('correct_alternative', 'N/A') if not question_row.empty else 'N/A'
                
                # Get student's marked answer
                marked_answer = student_row.get(question_col, None)
                
                # Handle NaN, None, or empty values
                if pd.isna(marked_answer) or marked_answer == '' or marked_answer is None:
                    marked_answer = 'No respondida'
                    cell_color = "#f8d7da"  # Red for not answered
                elif str(marked_answer).strip() == str(correct_answer).strip():
                    # Correct answer - green
                    cell_color = "#d4edda"
                else:
                    # Incorrect answer - red
                    cell_color = "#f8d7da"
                
                question_data.append({
                    'number': question_num,
                    'answer': marked_answer,
                    'color': cell_color,
                    'lecture': lecture
                })
            
            # Group questions by lecture and calculate rowspan
            table_rows = []
            i = 0
            while i < len(question_data):
                current_lecture = question_data[i]['lecture']
                
                # Count consecutive questions with same lecture
                rowspan = 1
                j = i + 1
                while j < len(question_data) and question_data[j]['lecture'] == current_lecture:
                    rowspan += 1
                    j += 1
                
                # Calculate performance for this lecture
                lecture_questions = question_data[i:i + rowspan]
                total_questions = len(lecture_questions)
                correct_questions = sum(1 for q in lecture_questions if q['color'] == "#d4edda")
                percentage = (correct_questions / total_questions * 100) if total_questions > 0 else 0
                
                # Determine lecture text based on performance
                if percentage == 100:
                    lecture_text = "Felicidades! Dominas este tema"
                    lecture_style = "font-weight: bold; color: #155724;"
                elif percentage >= 49:
                    lecture_text = "Se recomienda ver la resolución de preguntas reprobadas"
                    lecture_style = "font-weight: bold; color: #856404;"
                else:
                    # Look up lecture name from Excel
                    lecture_text = self._get_lecture_name(assessment_title, current_lecture)
                    lecture_style = "font-weight: bold; color: #721c24;"
                
                logger.info(f"Lecture {current_lecture}: {correct_questions}/{total_questions} correct ({percentage:.1f}%) - Text: {lecture_text}")
                
                # Create rows for this lecture group
                for k in range(i, i + rowspan):
                    q = question_data[k]
                    
                    # Only add lecture cell for the first row in the group
                    if k == i:
                        lecture_cell = f'<td style="border: 1px solid #000; padding: 8px; text-align: left; vertical-align: middle; {lecture_style}" rowspan="{rowspan}">{lecture_text}</td>'
                    else:
                        lecture_cell = ''
                    
                    table_row = f"""
        <tr>
          <td style="border: 1px solid #000; padding: 8px; text-align: center;">{q['number']}</td>
          <td style="border: 1px solid #000; padding: 8px; text-align: center; font-weight: bold; background-color: {q['color']};">{q['answer']}</td>
          {lecture_cell}
        </tr>"""
                    table_rows.append(table_row)
                
                i += rowspan
            
            # Split into pages keeping lectures together
            # Build pages by lecture groups to avoid splitting lectures across pages
            rows_per_page = 22
            table_pages = []
            current_page_rows = []
            
            # Group table_rows by lecture (they're already grouped, just need to track boundaries)
            i = 0
            lecture_groups = []
            while i < len(question_data):
                current_lecture = question_data[i]['lecture']
                
                # Count questions in this lecture
                lecture_size = 1
                j = i + 1
                while j < len(question_data) and question_data[j]['lecture'] == current_lecture:
                    lecture_size += 1
                    j += 1
                
                # Get the HTML rows for this lecture group
                lecture_rows = table_rows[i:i + lecture_size]
                lecture_groups.append({
                    'rows': lecture_rows,
                    'size': lecture_size,
                    'lecture': current_lecture
                })
                
                i += lecture_size
            
            # Now distribute lecture groups into pages
            current_page_rows = []
            for group in lecture_groups:
                # Check if adding this lecture group would exceed page limit
                if len(current_page_rows) + group['size'] > rows_per_page and len(current_page_rows) > 0:
                    # Start a new page
                    table_pages.append(current_page_rows)
                    current_page_rows = []
                
                # Add this lecture group to current page
                current_page_rows.extend(group['rows'])
            
            # Add the last page if it has content
            if current_page_rows:
                table_pages.append(current_page_rows)
            
            # Generate HTML for each page
            final_pages = []
            for page_idx, page_rows in enumerate(table_pages):
                page_num = page_idx + 1
                
                # Map assessment types to Spanish names
                assessment_names = {
                    'M1': 'Matemática M1',
                    'HYST': 'Historia',
                    'F30M': 'Física',
                    'Q30M': 'Química',
                    'B30M': 'Biología'
                }
                
                assessment_name = assessment_names.get(assessment_title, assessment_title)
                page_title = f"Resultados {assessment_name} - Página {page_num}" if len(table_pages) > 1 else f"Resultados {assessment_name}"
                
                page_html = f"""
<section class="page">
  <div class="content" style="text-align: center;">
    <p class="TituloAlumno Negrita">{page_title}</p>
    <table style="width: 550px; border-collapse: collapse; margin: 20px auto; border: 1px solid #000; table-layout: fixed;">
      <thead>
        <tr>
          <th style="border: 1px solid #000; padding: 12px; text-align: center; background-color: #f0f0f0; font-weight: bold; width: 80px; white-space: nowrap;">Pregunta</th>
          <th style="border: 1px solid #000; padding: 12px; text-align: center; background-color: #f0f0f0; font-weight: bold; width: 170px; white-space: nowrap;">Alternativa marcada</th>
          <th style="border: 1px solid #000; padding: 12px; text-align: center; background-color: #f0f0f0; font-weight: bold; width: 300px;">Lección</th>
        </tr>
      </thead>
      <tbody>
        {''.join(page_rows)}
      </tbody>
    </table>
  </div>
</section>"""
                final_pages.append(page_html)
            
            # Insert all table pages before closing body tag
            all_tables_html = '\n'.join(final_pages)
            html_content = html_content.replace('</body>', f'{all_tables_html}\n</body>')
            logger.info(f"Added question detail table with {len(table_rows)} questions in {len(final_pages)} pages")
            return html_content
        
        except Exception as e:
            logger.error(f"Error adding question detail table: {e}")
            return html_content

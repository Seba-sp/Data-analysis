#!/usr/bin/env python3
"""
Simplified Report Generator for M30M Assessment Reports
Uses single template (Portada.html) and single analysis file (analysis.csv)
Generates PDF reports with proper placeholder replacement
"""

import os
import logging
import pandas as pd
from weasyprint import HTML
from storage import StorageClient

logger = logging.getLogger(__name__)

class ReportGenerator:
    def __init__(self):
        """Initialize report generator"""
        self.storage = StorageClient()
        self.templates_dir = "templates"
        self.analysis_file = "data/analysis/analysis.csv"
        self.template_file = "Portada.html"
        
        # File naming configuration (should match DiagnosticosApp)
        self.report_filename_prefix = "resultados_"
        self.report_filename_suffix = ".pdf"
        self.assessment_name_suffix = ""  # Can be set to assessment type if needed

    def _generate_report_filename(self, email: str = None, username: str = None, assessment_type: str = None) -> str:
        """
        Generate a standardized report filename
        
        Args:
            email: Student's email address (preferred for filename)
            username: Student's username (fallback if no email)
            assessment_type: Optional assessment type to append to filename
            
        Returns:
            Generated filename string
        """
        # Use email if available, otherwise use username
        identifier = email if email and email.strip() else username
        
        if not identifier:
            raise ValueError("Either email or username must be provided")
        
        # Clean the identifier (remove any invalid filename characters)
        import re
        clean_identifier = re.sub(r'[<>:"/\\|?*]', '_', str(identifier).strip())
        
        # Build filename components
        filename_parts = [self.report_filename_prefix, clean_identifier]
        
        # Add assessment type suffix if specified
        if assessment_type and self.assessment_name_suffix:
            filename_parts.append(self.assessment_name_suffix)
        elif assessment_type:
            filename_parts.append(f"_{assessment_type}")
        
        # Add file extension
        filename_parts.append(self.report_filename_suffix)
        
        return ''.join(filename_parts)

    def generate_report(self, username: str) -> bytes:
        """
        Generate PDF report for a student using Portada.html template

        Args:
            username: Username/email of the student

        Returns:
            PDF content as bytes
        """
        try:
            # Load the analysis data
            analysis_df = self._load_analysis_data()
            if analysis_df is None:
                raise Exception("Failed to load analysis data")
            
            # Find the student in the analysis data
            # Try different possible column names for username
            username_columns = ['username', 'email', 'user', 'student', 'estudiante']
            student_data = None
            
            for col in username_columns:
                if col in analysis_df.columns:
                    student_data = analysis_df[analysis_df[col] == username]
                    if not student_data.empty:
                        logger.info(f"Found student using column '{col}'")
                        break
            
            if student_data is None or student_data.empty:
                # Log the available columns for debugging
                logger.error(f"Available columns in analysis file: {list(analysis_df.columns)}")
                logger.error(f"First few rows of data:")
                for i, row in analysis_df.head(3).iterrows():
                    logger.error(f"Row {i}: {dict(row)}")
                raise Exception(f"Student {username} not found in analysis data. Available columns: {list(analysis_df.columns)}")
            
            student_row = student_data.iloc[0]
            
            # Load the HTML template
            template_path = os.path.join(self.templates_dir, self.template_file)
            if not self.storage.exists(template_path):
                raise Exception(f"Template file not found: {template_path}")

            html_content = self.storage.read_text(template_path)

            # Replace placeholders
            html_content = self._replace_placeholders(html_content, student_row)
            
            # Add detailed assessment tables
            html_content = self._add_assessment_tables(html_content, student_row, username)
            
            # Generate PDF
            html_doc = HTML(string=html_content)
            pdf_content = html_doc.write_pdf()
            
            logger.info(f"Generated PDF report for {username}")
            return pdf_content

        except Exception as e:
            logger.error(f"Error generating report for {username}: {str(e)}")
            raise

    def _load_analysis_data(self) -> pd.DataFrame:
        """Load the analysis.csv file"""
        try:
            if not self.storage.exists(self.analysis_file):
                logger.error(f"Analysis file not found: {self.analysis_file}")
                return None
            
            # Try to read the file directly with pandas to bypass storage issues
            try:
                # First try with pandas directly
                import pandas as pd
                df = pd.read_csv(self.analysis_file, sep=',')
                if len(df.columns) > 1:
                    logger.info(f"Successfully loaded analysis data with pandas directly")
                    logger.info(f"Columns found: {list(df.columns)}")
                    return df
            except Exception as e:
                    logger.debug(f"Pandas direct reading failed: {e}")
            
            # If direct pandas fails, try different separators
            separators = [',', ';', '\t', '|']
            
            for sep in separators:
                try:
                    df = pd.read_csv(self.analysis_file, sep=sep)
                    if len(df.columns) > 1:  # Make sure we have multiple columns
                        logger.info(f"Successfully loaded analysis data with separator '{sep}'")
                        logger.info(f"Columns found: {list(df.columns)}")
                        return df
                except Exception as e:
                    logger.debug(f"Failed to parse with separator '{sep}': {e}")
                    continue
            
            # If all separators fail, try to manually parse the file
            logger.warning("All automatic separators failed, trying manual parsing...")
            try:
                # Read the file as text first
                with open(self.analysis_file, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                
                lines = file_content.strip().split('\n')
                
                if len(lines) < 2:
                    logger.error("File has less than 2 lines")
                    return None
                
                # Log the first few lines for debugging
                logger.info(f"First line (raw): {repr(lines[0])}")
                logger.info(f"Second line (raw): {repr(lines[1])}")
                
                # Try to detect separator from the first line
                first_line = lines[0]
                possible_seps = [',', ';', '\t', '|']
                detected_sep = None
                
                for sep in possible_seps:
                    count = first_line.count(sep)
                    if count > 0:
                        detected_sep = sep
                        logger.info(f"Detected separator '{sep}' with {count} occurrences in first line")
                        break
                
                if detected_sep:
                    logger.info(f"Manually detected separator: '{detected_sep}'")
                    # Re-read with detected separator
                    df = pd.read_csv(self.analysis_file, sep=detected_sep)
                    if len(df.columns) > 1:
                        logger.info(f"Manual parsing successful with separator '{detected_sep}'")
                        logger.info(f"Columns after manual parsing: {list(df.columns)}")
                        return df
                
                logger.error("Manual parsing also failed")
                return None
                
            except Exception as e:
                logger.error(f"Manual parsing failed: {e}")
                return None

        except Exception as e:
            logger.error(f"Error loading analysis data: {str(e)}")
            return None

    def _replace_placeholders(self, html_content: str, student_row: pd.Series) -> str:
        """Replace all placeholders in the HTML template"""
        
        # Replace student name
        username = student_row.get('username', 'Estudiante')
        html_content = html_content.replace('<<ALUMNO>>', str(username))
        
        # Assessment types and their placeholders
        assessment_types = {
            'M1': '<<M1>>',
            'M2': '<<M2>>', 
            'CL': '<<CL>>',
            'HYST': '<<HYST>>',
            'CIENB': '<<CIENB>>',
            'CIENF': '<<CIENF>>',
            'CIENQ': '<<CIENQ>>',
            'CIENT': '<<CIENT>>'
        }
        
        # Replace each assessment placeholder
        for assessment_type, placeholder in assessment_types.items():
            # Check if the assessment was taken (1) or not (0)
            assessment_taken = student_row.get(assessment_type, 0)
            
            if assessment_taken == 1:
                # Assessment was taken, use the converted score
                converted_score = student_row.get(f'{assessment_type}_converted', 'N/A')
                html_content = html_content.replace(placeholder, str(converted_score))
            else:
                # Assessment was not taken
                html_content = html_content.replace(placeholder, 'No rendido')
        
        return html_content

    def _add_assessment_tables(self, html_content: str, student_row: pd.Series, username: str) -> str:
        """Add detailed question tables for each assessment type that was taken"""
        try:
            # Load all question and processed files into memory for efficiency
            questions_data = {}
            processed_data = {}
            
            assessment_types = ['M1', 'M2', 'CL', 'HYST', 'CIENB', 'CIENF', 'CIENQ', 'CIENT']
            
            # Pre-load all files
            for assessment_type in assessment_types:
                # Load questions file
                questions_file = f"data/questions/{assessment_type}.csv"
                if self.storage.exists(questions_file):
                    try:
                        questions_df = self.storage.read_csv(questions_file, sep=';')
                        questions_data[assessment_type] = questions_df
                        logger.info(f"Loaded questions data for {assessment_type}")
                    except Exception as e:
                        logger.warning(f"Could not load questions for {assessment_type}: {e}")
                        questions_data[assessment_type] = None
                
                # Load processed file
                processed_file = f"data/processed/{assessment_type}.csv"
                if self.storage.exists(processed_file):
                    try:
                        processed_df = self.storage.read_csv(processed_file, sep=';')
                        processed_data[assessment_type] = processed_df
                        logger.info(f"Loaded processed data for {assessment_type}")
                    except Exception as e:
                        logger.warning(f"Could not load processed data for {assessment_type}: {e}")
                        processed_data[assessment_type] = None
            
            # Create tables for each assessment type that was taken
            all_tables_html = []
            
            for assessment_type in assessment_types:
                assessment_taken = student_row.get(assessment_type, 0)
                
                if assessment_taken == 1 and questions_data.get(assessment_type) is not None and processed_data.get(assessment_type) is not None:
                    # Create table for this assessment type
                    table_html = self._create_question_table(
                        assessment_type, 
                        questions_data[assessment_type], 
                        processed_data[assessment_type], 
                        username
                    )
                    if table_html:
                        all_tables_html.append(table_html)
            
            # Insert all tables before closing body tag
            if all_tables_html:
                all_tables_html_str = '\n'.join(all_tables_html)
                html_content = html_content.replace('</body>', f'{all_tables_html_str}\n</body>')
                logger.info(f"Added {len(all_tables_html)} assessment tables")
            
            return html_content

        except Exception as e:
            logger.error(f"Error adding assessment tables: {str(e)}")
            return html_content

    def _create_question_table(self, assessment_type: str, questions_df: pd.DataFrame, processed_df: pd.DataFrame, username: str) -> str:
        """Create a question table for a specific assessment type"""
        try:
            # Find the student's answers in processed data
            student_answers = processed_df[processed_df['username'] == username]
            if student_answers.empty:
                logger.warning(f"No processed data found for {username} in {assessment_type}")
                return ""
            
            student_row = student_answers.iloc[0]
            
            # Get all question columns (Pregunta 1, Pregunta 2, etc.)
            question_columns = [col for col in processed_df.columns if col.startswith('Pregunta ')]
            question_columns.sort(key=lambda x: int(x.split(' ')[1]))  # Sort by question number
            
            # Debug questions DataFrame structure
            logger.info(f"Questions DataFrame columns: {list(questions_df.columns)}")
            logger.info(f"Questions DataFrame shape: {questions_df.shape}")
            logger.info(f"Sample questions data:")
            for i, row in questions_df.head(5).iterrows():
                logger.info(f"  Row {i}: {dict(row)}")
            
            # Create table rows
            table_rows = []
            for question_col in question_columns:
                question_num = question_col.split(' ')[1]
                
                # Get correct answer from questions file
                question_row = questions_df[questions_df['Pregunta'] == f'Pregunta {question_num}']
                correct_answer = question_row.iloc[0]['Alternativa correcta'] if not question_row.empty else 'N/A'
                
                # Check if this is a pilot question
                is_pilot = False
                if not question_row.empty and 'Piloto' in question_row.columns:
                    pilot_value = question_row.iloc[0]['Piloto']
                    is_pilot = pd.notna(pilot_value)
                    logger.debug(f"Question {question_num} - Pilot value: '{pilot_value}', is_pilot: {is_pilot}")
                else:
                    logger.debug(f"Question {question_num} - No 'Piloto' column found or question_row is empty")
                
                # Format question number with asterisk if it's a pilot question
                question_display = f"{question_num}*" if is_pilot else question_num
                logger.debug(f"Question {question_num} - Final display: '{question_display}'")
                
                # Get student's marked answer
                marked_answer = student_row.get(question_col, 'N/A')
                
                # Determine cell color based on whether answer is correct
                cell_color = "#d4edda" if marked_answer == correct_answer else "#f8d7da"  # Light green if correct, light red if incorrect
                
                table_row = f"""
        <tr>
          <td style="border: 1px solid #000; padding: 8px; text-align: center;">{question_display}</td>
          <td style="border: 1px solid #000; padding: 8px; text-align: center; font-weight: bold;">{correct_answer}</td>
          <td style="border: 1px solid #000; padding: 8px; text-align: center; background-color: {cell_color};">{marked_answer}</td>
        </tr>"""
                table_rows.append(table_row)
            
            # Split into pages of 22 rows each
            rows_per_page = 22
            table_pages = []
            
            for i in range(0, len(table_rows), rows_per_page):
                page_rows = table_rows[i:i + rows_per_page]
                page_num = (i // rows_per_page) + 1
                
                # Map assessment types to Spanish names
                assessment_names = {
                    'M1': 'Matemática M1',
                    'M2': 'Matemática M2',
                    'CL': 'Competencia Lectora',
                    'HYST': 'Historia',
                    'CIENB': 'Ciencias mención biología',
                    'CIENF': 'Ciencias mención física',
                    'CIENQ': 'Ciencias mención química',
                    'CIENT': 'Ciencias técnico profesional'
                }
                
                assessment_name = assessment_names.get(assessment_type, assessment_type)
                page_title = f"Resultados {assessment_name} - Página {page_num}" if len(table_rows) > rows_per_page else f"Resultados {assessment_name}"
                
                page_html = f"""
<section class="page">
  <div class="content" style="text-align: center;">
    <p class="TituloAlumno Negrita">{page_title}</p>
    <table style="width: 550px; border-collapse: collapse; margin: 20px auto; border: 1px solid #000;">
      <thead>
        <tr>
          <th style="border: 1px solid #000; padding: 12px; text-align: center; background-color: #f0f0f0; font-weight: bold; width: 183px;">Pregunta</th>
          <th style="border: 1px solid #000; padding: 12px; text-align: center; background-color: #f0f0f0; font-weight: bold; width: 183px;">Alternativa correcta</th>
          <th style="border: 1px solid #000; padding: 12px; text-align: center; background-color: #f0f0f0; font-weight: bold; width: 183px;">Alternativa marcada</th>
        </tr>
      </thead>
      <tbody>
        {''.join(page_rows)}
      </tbody>
    </table>
  </div>
</section>"""
                table_pages.append(page_html)
            
            return '\n'.join(table_pages)

        except Exception as e:
            logger.error(f"Error creating question table for {assessment_type}: {str(e)}")
            return ""

    def generate_all_reports(self) -> dict:
        """
        Generate reports for all students in the analysis file
        
        Returns:
            Dictionary mapping usernames to PDF content (bytes)
        """
        try:
            analysis_df = self._load_analysis_data()
            if analysis_df is None:
                raise Exception("Failed to load analysis data")
            
            reports = {}
            usernames = analysis_df['username'].unique()
            
            for username in usernames:
                try:
                    pdf_content = self.generate_report(username)
                    reports[username] = pdf_content
                    logger.info(f"Generated report for {username}")
                except Exception as e:
                    logger.error(f"Failed to generate report for {username}: {str(e)}")
                    continue
            
            logger.info(f"Generated {len(reports)} reports out of {len(usernames)} students")
            return reports

        except Exception as e:
            logger.error(f"Error generating all reports: {str(e)}")
            raise

    def save_report(self, username: str, output_path: str) -> bool:
        """
        Generate and save a report to a file
        
        Args:
            username: Username/email of the student
            output_path: Path where to save the PDF file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            pdf_content = self.generate_report(username)
            
            # Save PDF file using storage
            self.storage.write_bytes(output_path, pdf_content)
            
            logger.info(f"Saved report for {username} to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving report for {username}: {str(e)}")
            return False

    def save_all_reports(self, output_dir: str) -> dict:
        """
        Generate and save reports for all students
        
        Args:
            output_dir: Directory where to save all PDF files
            
        Returns:
            Dictionary mapping usernames to output file paths
        """
        try:
            reports = self.generate_all_reports()
            output_files = {}
            
            for username, pdf_content in reports.items():
                # Get email from analysis data for filename
                analysis_df = self._load_analysis_data()
                email = None
                if analysis_df is not None:
                    student_row = analysis_df[analysis_df['username'] == username]
                    if not student_row.empty and 'email' in student_row.columns:
                        email = student_row.iloc[0]['email']
                        if pd.notna(email):
                            email = str(email).strip()
                
                # Generate standardized filename
                filename = self._generate_report_filename(email=email, username=username)
                
                output_path = os.path.join(output_dir, filename)
                
                # Save file
                if self.save_report(username, output_path):
                    output_files[username] = output_path
                else:
                    logger.error(f"Failed to save report for {username}")
            
            logger.info(f"Saved {len(output_files)} reports to {output_dir}")
            return output_files

        except Exception as e:
            logger.error(f"Error saving all reports: {str(e)}")
            raise

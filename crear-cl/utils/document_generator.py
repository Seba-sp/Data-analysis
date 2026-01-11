"""
Document generation utilities for creating CSV and Word documents.
Handles article exports and question document creation.
"""
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import os

from storage import storage
from config import config


class DocumentGenerator:
    """Generates various document types for the pipeline."""
    
    def __init__(self):
        """Initialize document generator."""
        self.output_dir = config.BASE_DATA_PATH
    
    def generate_articles_csv(self, articles: List[Dict], filename: str = "articles.csv") -> str:
        """
        Generate CSV file with all article data.
        
        Args:
            articles: List of article dictionaries
            filename: Output filename
            
        Returns:
            Full path to generated CSV file
        """
        # Convert articles to DataFrame
        df = pd.DataFrame(articles)
        
        # Ensure required columns exist
        required_columns = ['title', 'url', 'source', 'license', 'date', 'summary', 'content']
        for col in required_columns:
            if col not in df.columns:
                df[col] = ''
        
        # Add metadata
        df['extracted_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Reorder columns
        column_order = ['title', 'url', 'source', 'license', 'date', 'summary', 'content', 'extracted_date']
        df = df[[col for col in column_order if col in df.columns]]
        
        # Save using storage abstraction
        file_path = storage.write_csv(df, filename)
        return file_path
    
    def generate_validated_csv(self, articles: List[Dict], filename: str = "validated_articles.csv") -> str:
        """
        Generate CSV file with validated articles including license information.
        
        Args:
            articles: List of validated article dictionaries
            filename: Output filename
            
        Returns:
            Full path to generated CSV file
        """
        df = pd.DataFrame(articles)
        
        # Save using storage abstraction
        file_path = storage.write_csv(df, filename)
        return file_path
    
    
    def generate_questions_word(self, article: Dict, questions: Dict, 
                               filename: str, is_improved: bool = False) -> str:
        """
        Generate Word document with questions.
        
        Args:
            article: Article dictionary
            questions: Questions dictionary (parsed from agent response)
            filename: Output filename
            is_improved: Whether these are improved questions
            
        Returns:
            Full path to generated Word document
        """
        doc = Document()
        
        # Title
        title = doc.add_heading(article.get('title', 'Article Questions'), 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Document type indicator
        doc_type = "Improved Questions" if is_improved else "Initial Questions"
        subtitle = doc.add_heading(doc_type, level=2)
        subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Article metadata
        doc.add_paragraph(f"Source: {article.get('source', 'Unknown')}")
        doc.add_paragraph(f"Date: {article.get('date', 'Unknown')}")
        doc.add_paragraph(f"License: {article.get('license', 'Unknown')}")
        doc.add_paragraph(f"URL: {article.get('url', '')}")
        doc.add_paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        doc.add_paragraph()  # Blank line
        
        # Add article text if available (from Agent 3 response)
        article_text = questions.get('article_text', '') if isinstance(questions, dict) else ''
        if article_text:
            doc.add_heading('TEXTO DEL ARTÍCULO', level=1)
            # Add the full text in multiple paragraphs
            paragraphs = article_text.split('\n\n')
            for para in paragraphs:
                if para.strip():
                    p = doc.add_paragraph(para.strip())
                    p.style = 'Normal'
            doc.add_page_break()  # Start questions on new page
        else:
            print("[Document Generator] WARNING: No article text found in questions dict")
        
        # Questions section header
        doc.add_heading('PREGUNTAS PAES', level=1)
        doc.add_paragraph()  # Blank line
        
        # Questions
        if isinstance(questions, dict) and 'questions' in questions:
            questions_list = questions['questions']
        elif isinstance(questions, list):
            questions_list = questions
        else:
            questions_list = []
        
        for i, q in enumerate(questions_list, 1):
            # Question number and text
            doc.add_heading(f"Pregunta {i}", level=2)
            
            if isinstance(q, dict):
                question_text = q.get('question', q.get('text', ''))
                alternatives = q.get('alternatives', {})
                clave = q.get('clave', q.get('answer', ''))
                justification = q.get('justification', q.get('explanation', ''))
                habilidad = q.get('habilidad', '')
                question_number = q.get('number', i)
            else:
                question_text = str(q)
                alternatives = {}
                clave = ''
                justification = ''
                habilidad = ''
                question_number = i
            
            # Habilidad/task label (if present)
            if habilidad:
                p = doc.add_paragraph()
                p.add_run(f"[{habilidad}]").italic = True
            
            # Question
            p = doc.add_paragraph()
            p.add_run(f'{question_number}. ').bold = True
            p.add_run(question_text)
            
            # Alternatives (A-D)
            if alternatives:
                for letter in ['A', 'B', 'C', 'D']:
                    if letter in alternatives:
                        p = doc.add_paragraph(style='List Number')
                        # Highlight correct answer with bold AND green color
                        if letter == clave:
                            run = p.add_run(f"{letter}) {alternatives[letter]} ✓")
                            run.bold = True
                            run.font.color.rgb = RGBColor(0, 128, 0)  # Green color
                        else:
                            p.add_run(f"{letter}) {alternatives[letter]}")
            else:
                # If no alternatives dict, warn user
                p = doc.add_paragraph()
                run = p.add_run("[WARNING: No alternatives found for this question]")
                run.italic = True
                run.font.color.rgb = RGBColor(255, 0, 0)  # Red color
            
            # Correct answer (clave) - explicit section
            if clave:
                p = doc.add_paragraph()
                p.add_run('Respuesta Correcta: ').bold = True
                run = p.add_run(clave)
                run.bold = True
                run.font.size = Pt(12)
            else:
                # Warn if no clave found
                p = doc.add_paragraph()
                run = p.add_run('[WARNING: No correct answer (clave) found]')
                run.italic = True
                run.font.color.rgb = RGBColor(255, 0, 0)  # Red color
            
            # Justification (if present)
            if justification:
                p = doc.add_paragraph()
                p.add_run('Justificación: ').bold = True
                p.add_run(justification)
            else:
                # Warn if no justification found
                p = doc.add_paragraph()
                run = p.add_run('[WARNING: No justification found]')
                run.italic = True
                run.font.color.rgb = RGBColor(255, 165, 0)  # Orange color
            
            # Add page break after each question (one question per page)
            if i < len(questions_list):  # Don't add page break after last question
                doc.add_page_break()
        
        # Save document
        full_path = os.path.join(self.output_dir, filename)
        os.makedirs(os.path.dirname(full_path) if os.path.dirname(full_path) else self.output_dir, exist_ok=True)
        doc.save(full_path)
        
        return full_path
    
    def parse_questions_from_response(self, response_text: str) -> Dict:
        """
        Parse questions from agent response text.
        
        Args:
            response_text: Raw text response from agent
            
        Returns:
            Dictionary with structured questions
        """
        questions = []
        lines = response_text.strip().split('\n')
        
        current_question = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('QUESTION'):
                # Save previous question if exists
                if current_question:
                    questions.append(current_question)
                    current_question = {}
                
                # Extract question text
                parts = line.split(':', 1)
                if len(parts) > 1:
                    current_question['question'] = parts[1].strip()
            
            elif line.startswith('ANSWER'):
                parts = line.split(':', 1)
                if len(parts) > 1:
                    current_question['answer'] = parts[1].strip()
            
            elif line.startswith('EXPLANATION'):
                parts = line.split(':', 1)
                if len(parts) > 1:
                    current_question['explanation'] = parts[1].strip()
        
        # Add last question
        if current_question:
            questions.append(current_question)
        
        return {'questions': questions}


# Global document generator instance
doc_generator = DocumentGenerator()


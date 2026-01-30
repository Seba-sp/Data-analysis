"""
Agent 4: Standalone Question Review Agent
Reviews questions from local Word and Excel files, independent of the main orchestrator.
"""
from google import genai
import google.generativeai as genai_legacy
from typing import Dict, Optional, List, Tuple
import os
import time
import pandas as pd
from docx import Document
from docx2pdf import convert
import shutil
import re

from config import config
from utils.pdf_loader import get_pdf_context_loader


class StandaloneReviewAgent:
    """Standalone Agent for reviewing questions from local files."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize standalone review agent.
        """
        self.api_key = api_key or config.GEMINI_API_KEY
        os.environ['GEMINI_API_KEY'] = self.api_key
        
        # Initialize Interactions API client
        self.client = genai.Client(api_key=self.api_key)
        
        # Use Gemini 3 Flash model
        self.model_id = config.GEMINI_MODEL_AGENTS234
        
        # Initialize legacy API for file upload support
        genai_legacy.configure(api_key=self.api_key)
        self.model_legacy = genai_legacy.GenerativeModel(
            model_name=self.model_id,
            generation_config={
                'temperature': 0.3,
                'top_p': 0.95,
                'max_output_tokens': 20000,
            }
        )
        
        # Load prompt template
        prompt_path = config.get_prompt_path('agent4_prompt.txt')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            self.prompt_template = f.read()
            
        # Initialize PDF Loader for Guidelines
        self.pdf_loader = get_pdf_context_loader()
        
    def review_standalone(self, folder_path: str, article_id: str) -> Dict:
        """
        Main method to review a specific article from files.
        """
        print(f"[Agent 4 Standalone] Processing {article_id} in {folder_path}")
        
        # 1. Define file paths with fuzzy matching
        docx_path = self._find_file(folder_path, article_id, r"preguntas[\s\-_+]*texto\.docx")
        xlsx_path = self._find_file(folder_path, article_id, r"preguntas[\s\-_]*datos\.xlsx")
        
        if not docx_path:
            raise FileNotFoundError(f"Word file not found for ID {article_id} (pattern: Preguntas+Texto)")
        if not xlsx_path:
            raise FileNotFoundError(f"Excel file not found for ID {article_id} (pattern: Preguntas Datos)")
            
        # 3. Parse Metadata from Excel
        metadata_df = pd.read_excel(xlsx_path)
        
        # Check for blank cells in 'Acción' column
        if 'Acción' not in metadata_df.columns:
             print(f"[Agent 4] 'Acción' column missing in {xlsx_path}. Skipping.")
             return {'article_id': article_id, 'feedback': 'Skipped: Missing Acción column'}
             
        if metadata_df['Acción'].isnull().any() or (metadata_df['Acción'].astype(str).str.strip() == '').any():
            print(f"[Agent 4] Blank cells found in 'Acción' column for {article_id}. Skipping set.")
            return {'article_id': article_id, 'feedback': 'Skipped: Blank cells in Acción'}
            
        # 2. Convert DOCX to PDF (for visual context)
        pdf_path = self._convert_docx_to_pdf(docx_path, article_id)
        
        try:
            # Identify questions to review
            # Rule: Review everything that is NOT 'ok' (case-insensitive) and NOT blank
            # This captures 'editada', 'sustituida', 'corregida', etc.
            
            if 'Acción' in metadata_df.columns:
                # Normalize column: convert to string, lowercase, strip whitespace
                accion_col = metadata_df['Acción'].astype(str).str.lower().str.strip()
                
                # Filter: Keep rows where Action is NOT 'ok' AND NOT 'nan'/'none'/empty
                target_questions = metadata_df[
                    (accion_col != 'ok') & 
                    (accion_col != 'nan') & 
                    (accion_col != 'none') & 
                    (accion_col != '')
                ]['Número de pregunta'].tolist()
            else:
                # If column missing, maybe review all? Or warn?
                print("[Agent 4] Warning: 'Acción' column missing in Excel. Reviewing all questions.")
                target_questions = metadata_df['Número de pregunta'].tolist()
            
            if not target_questions:
                print(f"[Agent 4] No questions marked for review (all are 'ok' or blank). Skipping.")
                # We can save a file saying "No review needed"
                self._save_output(folder_path, article_id, "NO REVIEW NEEDED: All questions are 'ok' or blank.")
                return {'article_id': article_id, 'feedback': 'No review needed'}
            
            print(f"[Agent 4] Target questions for review: {target_questions}")
            
            # 4. Extract Text from Word (to construct the prompt input)
            # We need to reconstruct the "PAES Format" string: Text + Questions + Keys
            paes_text = self._reconstruct_paes_format(docx_path, metadata_df)
            
            # 5. Upload PDF to Gemini
            print(f"[Agent 4] Uploading Article PDF...")
            uploaded_pdf = genai_legacy.upload_file(pdf_path, 
                                                   display_name=f"{article_id}_review_standalone.pdf")
            
            # Wait for processing
            while uploaded_pdf.state.name == "PROCESSING":
                time.sleep(2)
                uploaded_pdf = genai_legacy.get_file(uploaded_pdf.name)
            
            if uploaded_pdf.state.name != "ACTIVE":
                raise ValueError(f"PDF processing failed: {uploaded_pdf.state.name}")
            
            print(f"[Agent 4] Article PDF ready.")
            
            # 6. Prepare Guideline PDFs
            guideline_files = []
            if self.pdf_loader and self.pdf_loader.has_context():
                guideline_files = self.pdf_loader.get_file_references()
                print(f"[Agent 4] Including {len(guideline_files)} Guideline PDFs")
                
            # 7. Construct Prompt
            # Similar to agent4_review but explicitly mentioning the guidelines and the reconstructed text
            
            target_q_str = ", ".join(map(str, target_questions))
            
            review_prompt = f"""Eres revisor/a senior de preguntas PAES de Competencia Lectora.

DOCUMENTOS ADJUNTOS:
1. PDFs de LINEAMIENTOS (Guidelines): Úsalos como referencia de estándar.
2. PDF del ARTÍCULO (que incluye texto y preguntas): Úsalo para ver el formato visual y lectura.

INSTRUCCIÓN CRÍTICA:
SOLO debes revisar y entregar feedback para las siguientes preguntas: {target_q_str}.
IGNORA COMPLETAMENTE las preguntas que NO estén en esta lista (o que tengan Acción 'ok').
Para las preguntas objetivo ({target_q_str}), aplica la rúbrica completa.

PREGUNTAS Y METADATA (Reconstruido):
===================================================================
{paes_text}
===================================================================

{self.prompt_template}
"""
            
            # 8. Generate Content
            files_to_send = guideline_files + [uploaded_pdf]
            print(f"[Agent 4] Sending prompt ({len(review_prompt)} chars) + {len(files_to_send)} files")
            
            response = self.model_legacy.generate_content([review_prompt] + files_to_send)
            feedback_text = response.text
            
            # 9. Clean up Gemini upload
            try:
                genai_legacy.delete_file(uploaded_pdf.name)
            except:
                pass
                
            # 10. Save Output
            self._save_output(folder_path, article_id, feedback_text)
            
            return {
                'article_id': article_id,
                'feedback': feedback_text
            }
            
        finally:
            # Cleanup local temporary PDF if we created it just now
            # Actually, keeping it might be useful, but let's follow the pattern of cleanup if it's temp
            pass

    def _find_file(self, folder: str, article_id: str, suffix_regex: str) -> Optional[str]:
        """
        Find a file that matches the article_id and suffix pattern (case-insensitive).
        Handles variations in spaces, hyphens, etc.
        """
        # Create a regex that starts with article_id, followed by flexible separator, then suffix
        # We escape the article_id just in case it has special regex chars
        pattern = re.compile(re.escape(article_id) + r"[\s\-_]*" + suffix_regex + r"$", re.IGNORECASE)
        
        for filename in os.listdir(folder):
            if pattern.match(filename):
                return os.path.join(folder, filename)
        return None

    def _convert_docx_to_pdf(self, docx_path: str, article_id: str) -> str:
        """Convert DOCX to PDF and return path."""
        folder = os.path.dirname(docx_path)
        pdf_filename = f"{article_id}_review_context.pdf"
        pdf_path = os.path.join(folder, pdf_filename)
        
        # If it doesn't exist, convert
        if not os.path.exists(pdf_path):
            print(f"[Agent 4] Converting DOCX to PDF: {pdf_filename}")
            convert(docx_path, pdf_path)
        else:
            print(f"[Agent 4] Using existing PDF: {pdf_filename}")
            
        return pdf_path

    def _reconstruct_paes_format(self, docx_path: str, df: pd.DataFrame) -> str:
        """
        Reads Word file text and combines with Excel metadata to create
        a standard text representation for the prompt.
        """
        doc = Document(docx_path)
        full_text = []
        
        # Basic extraction: simply dump all text from Word
        # This will include the article text (first) and then questions
        # We assume the user wants the model to 'see' the text structure via the string too
        
        word_content = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        
        # Now format the metadata from Excel to append or integrate
        # Columns: [Número de pregunta, Clave, Habilidad, Tarea lectora, Justificación, Acción]
        
        metadata_text = "\n\n=== METADATA Y CLAVES (Del Excel) ===\n"
        for _, row in df.iterrows():
            try:
                q_num = row['Número de pregunta']
                clave = row['Clave']
                habilidad = row['Habilidad']
                tarea = row['Tarea lectora']
                justificacion = row['Justificación']
                
                metadata_text += f"\nPregunta {q_num}:\n"
                metadata_text += f"Clave: {clave}\n"
                metadata_text += f"Habilidad: {habilidad}\n"
                metadata_text += f"Tarea: {tarea}\n"
                metadata_text += f"Justificación: {justificacion}\n"
                
                # Include Acción so model knows context
                accion = row.get('Acción', 'N/A')
                metadata_text += f"Acción: {accion}\n"
                
            except Exception as e:
                print(f"[Agent 4] Warning parsing Excel row: {e}")
                
        return word_content + metadata_text

    def _save_output(self, folder: str, article_id: str, text: str):
        """Save the review output."""
        output_path = os.path.join(folder, f"{article_id}-Review.txt")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"[Agent 4] Saved review to {output_path}")


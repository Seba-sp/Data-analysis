"""
Agent 4: Question Review Agent
Reviews and provides feedback on generated questions using Interactions API.

Recent improvements (Jan 2026):
- Fixed input handling to use Agent 3's article_text and raw_response
- Added debug file saving (debug_review_*.txt)
- Cleaned up outdated input references
- Added DOCX file upload support for reviewing with full article context
"""
from google import genai
import google.generativeai as genai_legacy
from typing import Dict, Optional, List
import os
import time

from config import config
from utils.pdf_loader import get_pdf_context_loader


class ReviewAgent:
    """Agent for reviewing and providing feedback on questions."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize review agent.
        
        Args:
            api_key: Gemini API key (uses config if not provided)
        """
        self.api_key = api_key or config.GEMINI_API_KEY
        
        # Set API key as environment variable for genai.Client
        os.environ['GEMINI_API_KEY'] = self.api_key
        
        # Initialize Interactions API client
        self.client = genai.Client(api_key=self.api_key)
        
        # Use Gemini 3 Flash model for question review
        self.model_id = config.GEMINI_MODEL_AGENTS234
        
        # Initialize legacy API for file upload support
        genai_legacy.configure(api_key=self.api_key)
        self.model_legacy = genai_legacy.GenerativeModel(
            model_name=self.model_id,
            generation_config={
                'temperature': 0.3,
                'top_p': 0.95,
                'max_output_tokens': 8000,
            }
        )
        
        # Load prompt template
        prompt_path = config.get_prompt_path('agent4_prompt.txt')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            self.prompt_template = f.read()
        print(f"[Agent 4] Loaded prompt template ({len(self.prompt_template)} chars)")
        
        # Initialize PDF Loader for Guidelines (same as Agent 3)
        self.pdf_loader = get_pdf_context_loader()
    
    def review_questions(self, article: Dict, questions: Dict) -> Dict:
        """
        Review generated questions by uploading DOCX to Gemini.
        
        Args:
            article: Article dict with docx_path
            questions: Questions dict from Agent 3 with raw_response
        
        Returns:
            Dict with approval status and feedback
        """
        article_id = article.get('article_id', 'T01')
        docx_path = article.get('docx_path', '')
        
        print(f"[Agent 4] Reviewing questions for: {article_id}")
        
        try:
            # Reuse PDF from Agent 3 if available
            from config import config
            pdf_path = questions.get('pdf_path')
            
            if not pdf_path or not os.path.exists(pdf_path):
                # Fallback: check if PDF exists in data directory
                pdf_filename = f"{article_id}_article.pdf"
                pdf_path = os.path.join(config.BASE_DATA_PATH, pdf_filename)
                
                if not os.path.exists(pdf_path):
                    # Last resort: convert DOCX to PDF
                    from docx2pdf import convert
                    print(f"[Agent 4] Converting DOCX to PDF for review...")
                    convert(docx_path, pdf_path)
                    print(f"[Agent 4] Conversion complete: {pdf_filename}")
                else:
                    print(f"[Agent 4] Reusing existing PDF: {pdf_filename}")
            else:
                print(f"[Agent 4] Reusing PDF from Agent 3: {os.path.basename(pdf_path)}")
            
            # Upload PDF to Gemini
            uploaded_pdf = genai_legacy.upload_file(pdf_path,
                                                   display_name=f"{article_id}_review.pdf")
            
            # Wait for processing
            while uploaded_pdf.state.name == "PROCESSING":
                time.sleep(2)
                uploaded_pdf = genai_legacy.get_file(uploaded_pdf.name)
            
            if uploaded_pdf.state.name != "ACTIVE":
                raise ValueError(f"PDF processing failed: {uploaded_pdf.state.name}")
            
            print(f"[Agent 4] PDF ready for review")
            
            # Prepare Guideline PDFs (same as Agent 3)
            guideline_files = []
            if self.pdf_loader and self.pdf_loader.has_context():
                guideline_files = self.pdf_loader.get_file_references()
                print(f"[Agent 4] Including {len(guideline_files)} Guideline PDFs")
            
            # Build review prompt
            questions_text = questions.get('raw_response', '')
            review_prompt = f"""Eres revisor/a senior de preguntas PAES de Competencia Lectora.

DOCUMENTOS ADJUNTOS:
1. PDFs de LINEAMIENTOS (Guidelines): Úsalos como referencia de estándar.
2. PDF del ARTÍCULO (que incluye texto y preguntas): Úsalo para ver el formato visual y lectura.

PREGUNTAS GENERADAS:
===================================================================
{questions_text}
===================================================================

{self.prompt_template}
"""
            
            print(f"[Agent 4] Review prompt: {len(review_prompt)} chars")
            
            # Generate review with PDF file + guideline PDFs
            files_to_send = guideline_files + [uploaded_pdf]
            print(f"[Agent 4] Sending prompt + {len(files_to_send)} files")
            
            response = self.model_legacy.generate_content([review_prompt] + files_to_send)
            feedback_text = response.text
                
            # Clean up Gemini upload (keep local PDF)
            try:
                genai_legacy.delete_file(uploaded_pdf.name)
            except:
                pass
            
            # Save debug file
            self._save_debug_file(article_id, feedback_text)
            
            # Parse feedback (DEMRE format: nota/10, veredicto, diagnostico, parches)
            feedback_dict = {
                'article_id': article_id,
                'article_title': article.get('title', ''),
                'raw_feedback': feedback_text,
                'nota_global': self._extract_nota(feedback_text),
                'veredicto': self._extract_veredicto(feedback_text),
                'diagnostico_por_pregunta': self._parse_diagnostico(feedback_text),
                'parches': self._extract_parches(feedback_text),
                'top_3_fixes': self._extract_top_fixes(feedback_text)
            }
            
            nota = feedback_dict['nota_global']
            print(f"[Agent 4] Review complete: Nota {nota}/10")
            return feedback_dict
        
        except Exception as e:
            print(f"[Agent 4] ERROR reviewing: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _extract_interaction_text(self, interaction) -> str:
        """Extract text from interaction outputs."""
        if not interaction.outputs:
            return ""
        
        # Get last output (final response)
        last_output = interaction.outputs[-1]
        
        if hasattr(last_output, 'text'):
            return last_output.text
        elif isinstance(last_output, str):
            return last_output
        else:
            return str(last_output)
    
    def _save_debug_file(self, article_id: str, response_text: str):
        """Save raw response for debugging."""
        try:
            from config import config
            # Save to data directory
            debug_dir = config.BASE_DATA_PATH
            debug_file = os.path.join(debug_dir, f"debug_review_{article_id}.txt")
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write("=== RAW RESPONSE FROM AGENT 4 ===\n\n")
                f.write(response_text)
            print(f"[Agent 4] Saved debug file: {debug_file}")
        except Exception as e:
            print(f"[Agent 4] Could not save debug file: {e}")
    
    def _format_questions_for_review(self, questions: Dict) -> str:
        """
        Format questions for review prompt.
        
        Args:
            questions: Questions dictionary
            
        Returns:
            Formatted string of questions
        """
        formatted = []
        
        question_list = questions.get('questions', [])
        
        for q in question_list:
            q_num = q.get('number', 0)
            q_text = q.get('question', '')
            q_answer = q.get('answer', '')
            q_explanation = q.get('explanation', '')
            
            formatted.append(f"QUESTION {q_num}: {q_text}")
            if q_answer:
                formatted.append(f"ANSWER {q_num}: {q_answer}")
            if q_explanation:
                formatted.append(f"EXPLANATION {q_num}: {q_explanation}")
            formatted.append("")  # Blank line
        
        return '\n'.join(formatted)
    
    def _parse_feedback(self, feedback_text: str) -> list:
        """
        Parse feedback into structured format.
        
        Args:
            feedback_text: Raw feedback text
            
        Returns:
            List of feedback dictionaries
        """
        feedback_list = []
        lines = feedback_text.strip().split('\n')
        
        current_feedback = {}
        current_question_num = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check for QUESTION feedback sections
            if 'QUESTION' in line.upper() and 'FEEDBACK' in line.upper():
                # Save previous feedback
                if current_feedback and current_question_num is not None:
                    current_feedback['question_number'] = current_question_num
                    feedback_list.append(current_feedback)
                    current_feedback = {}
                
                # Extract question number
                import re
                number_match = re.search(r'(\d+)', line)
                if number_match:
                    current_question_num = int(number_match.group(1))
            
            # Check for specific feedback categories
            elif line.upper().startswith('STRENGTHS:'):
                parts = line.split(':', 1)
                if len(parts) > 1:
                    current_feedback['strengths'] = parts[1].strip()
            
            elif line.upper().startswith('IMPROVEMENTS NEEDED:'):
                parts = line.split(':', 1)
                if len(parts) > 1:
                    current_feedback['improvements'] = parts[1].strip()
            
            elif line.upper().startswith('SPECIFIC SUGGESTION:'):
                parts = line.split(':', 1)
                if len(parts) > 1:
                    current_feedback['suggestion'] = parts[1].strip()
            
            # Alternative formats
            elif line.upper().startswith('WHAT WORKS WELL:'):
                parts = line.split(':', 1)
                if len(parts) > 1:
                    current_feedback['strengths'] = parts[1].strip()
            
            elif line.upper().startswith('WHAT TO IMPROVE:'):
                parts = line.split(':', 1)
                if len(parts) > 1:
                    current_feedback['improvements'] = parts[1].strip()
        
        # Add last feedback
        if current_feedback and current_question_num is not None:
            current_feedback['question_number'] = current_question_num
            feedback_list.append(current_feedback)
        
        return feedback_list
    
    def _extract_nota(self, feedback_text: str) -> float:
        """
        Extract nota global (x/10) from DEMRE feedback.

        Args:
            feedback_text: Raw feedback text

        Returns:
            Float nota (0-10)
        """
        import re

        # Matches common patterns like "**Nota Global: 8,5/10**", "- **Nota global:** 8,5/10", "**Nota Global:** **8,2 / 10**", "*   **Nota global:** **8,8/10**"
        # Handles asterisks, dashes, bolding, extra spaces, etc.
        nota_pattern = r'(?i)[\*\s\-]*nota\s*global[\*\s]*:?[\*\s]*([0-9]+(?:[,.][0-9]+)?)\s*/\s*10'
        match = re.search(nota_pattern, feedback_text)
        if match:
            nota_str = match.group(1).replace(',', '.').strip()
            try:
                return float(nota_str)
            except ValueError:
                return 0.0

        return 0.0
    
    def _extract_veredicto(self, feedback_text: str) -> Dict:
        """
        Extract veredicto global section from DEMRE feedback.
        
        Args:
            feedback_text: Raw feedback text
            
        Returns:
            Dictionary with fortalezas, debilidades, top_3_fixes
        """
        veredicto = {
            'fortalezas': [],
            'debilidades': [],
            'top_3_fixes': []
        }
        
        import re
        
        # Extract fortalezas (3 strengths)
        fortalezas_section = re.search(r'(?:fortalezas?|strengths?).*?:\s*(.*?)(?=debilidades|top\s*3|$)', 
                                       feedback_text, re.IGNORECASE | re.DOTALL)
        if fortalezas_section:
            text = fortalezas_section.group(1)
            veredicto['fortalezas'] = [line.strip() for line in text.split('\n') 
                                       if line.strip() and (line.strip()[0] in '-•123456789')]
        
        # Extract debilidades (3 weaknesses)
        debilidades_section = re.search(r'(?:debilidades?|weaknesses?).*?:\s*(.*?)(?=top\s*3|$)', 
                                        feedback_text, re.IGNORECASE | re.DOTALL)
        if debilidades_section:
            text = debilidades_section.group(1)
            veredicto['debilidades'] = [line.strip() for line in text.split('\n') 
                                        if line.strip() and (line.strip()[0] in '-•123456789')]
        
        return veredicto
    
    def _parse_diagnostico(self, feedback_text: str) -> List[Dict]:
        """
        Parse diagnostico por pregunta section.
        
        Args:
            feedback_text: Raw feedback text
            
        Returns:
            List of diagnostico dictionaries per question
        """
        diagnostico_list = []
        
        import re
        
        # Look for question-specific feedback
        # Pattern: "Pregunta X:" or "P1:" or similar
        question_pattern = r'(?:Pregunta|P|Ítem)\s*(\d+).*?:\s*(.*?)(?=(?:Pregunta|P|Ítem)\s*\d+|$)'
        
        for match in re.finditer(question_pattern, feedback_text, re.IGNORECASE | re.DOTALL):
            q_num = int(match.group(1))
            feedback = match.group(2).strip()
            
            # Extract nota del item if present
            nota_item = 0.0
            nota_match = re.search(r'[Nn]ota.*?(\d+(?:[,\.]\d+)?)\s*/\s*10', feedback)
            if nota_match:
                try:
                    nota_item = float(nota_match.group(1).replace(',', '.'))
                except ValueError:
                    pass
            
            diagnostico_list.append({
                'question_number': q_num,
                'nota': nota_item,
                'feedback': feedback[:300]  # Limit length
            })
        
        return diagnostico_list
    
    def _extract_parches(self, feedback_text: str) -> List[str]:
        """
        Extract lista de parches (concrete fixes) from feedback.
        
        Args:
            feedback_text: Raw feedback text
            
        Returns:
            List of patch suggestions
        """
        parches = []
        
        import re
        
        # Look for "LISTA DE PARCHES" or "CAMBIOS CONCRETOS" section
        parches_section = re.search(r'(?:LISTA\s+DE\s+PARCHES|CAMBIOS\s+CONCRETOS).*?:\s*(.*?)(?:\n\n|$)', 
                                    feedback_text, re.IGNORECASE | re.DOTALL)
        
        if parches_section:
            text = parches_section.group(1)
            for line in text.split('\n'):
                line = line.strip()
                if line and (line.startswith('-') or line.startswith('•') or line.startswith('P')):
                    parches.append(line.lstrip('-•'))
        
        return parches
    
    def _extract_top_fixes(self, feedback_text: str) -> List[str]:
        """
        Extract top 3 fixes from veredicto.
        
        Args:
            feedback_text: Raw feedback text
            
        Returns:
            List of top 3 fixes
        """
        fixes = []
        
        import re
        
        # Look for "Top 3 fixes" section
        top_section = re.search(r'(?:Top\s*3\s*fixes?|3\s*cambios?).*?:\s*(.*?)(?:\n\n|$)', 
                               feedback_text, re.IGNORECASE | re.DOTALL)
        
        if top_section:
            text = top_section.group(1)
            for line in text.split('\n'):
                line = line.strip()
                if line and (line.strip()[0] in '-•123456789'):
                    fixes.append(line.lstrip('-•0123456789. '))
        
        return fixes[:3]  # Limit to 3
    
    def calculate_quality_score(self, feedback: Dict) -> float:
        """
        Calculate quality score based on feedback.
        
        Args:
            feedback: Feedback dictionary
            
        Returns:
            Quality score (0-100)
        """
        score = 100.0
        
        parsed_feedback = feedback.get('parsed_feedback', [])
        
        # Deduct points for each question needing improvements
        for item in parsed_feedback:
            if item.get('improvements'):
                score -= 5
            if not item.get('strengths'):
                score -= 3
        
        # Deduct for missing topics
        assessment = feedback.get('overall_assessment', {})
        missing_count = len(assessment.get('missing_topics', []))
        score -= missing_count * 10
        
        # Bonus for questions to keep as-is
        keep_count = len(assessment.get('keep_as_is', []))
        score += keep_count * 5
        
        # Ensure score is within bounds
        score = max(0, min(100, score))
        
        return score
    
    def get_improvement_summary(self, feedback: Dict) -> str:
        """
        Get a summary of improvements needed.
        
        Args:
            feedback: Feedback dictionary
            
        Returns:
            Summary string
        """
        parsed = feedback.get('parsed_feedback', [])
        assessment = feedback.get('overall_assessment', {})
        
        needs_revision = len(assessment.get('needs_revision', []))
        keep_as_is = len(assessment.get('keep_as_is', []))
        missing = len(assessment.get('missing_topics', []))
        
        summary = f"Questions reviewed: {len(parsed)}\n"
        summary += f"Keep as-is: {keep_as_is}\n"
        summary += f"Need revision: {needs_revision}\n"
        summary += f"Missing topics: {missing}\n"
        summary += f"Quality score: {self.calculate_quality_score(feedback):.1f}/100"
        
        return summary


# Global agent instance
review_agent = ReviewAgent()


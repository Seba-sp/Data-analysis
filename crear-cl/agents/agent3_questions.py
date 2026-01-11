"""
Agent 3: Question Generator Agent
Generates PAES-format comprehension questions from validated articles.
Uses Gemini with PDF context for question design standards.
"""
from google import genai
import google.generativeai as genai_legacy
from typing import Dict, List, Optional
import os
import re

from config import config
from utils.pdf_loader import get_pdf_context_loader


class QuestionAgent:
    """Agent for generating PAES-format comprehension questions."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize question generation agent with PDF context."""
        self.api_key = api_key or config.GEMINI_API_KEY
        os.environ['GEMINI_API_KEY'] = self.api_key
        
        # Initialize Interactions API client
        self.client = genai.Client(api_key=self.api_key)
        
        # Model configuration
        self.model_id = config.GEMINI_MODEL_AGENTS234
        
        # Also initialize legacy API for PDF support
        genai_legacy.configure(api_key=self.api_key)
        self.model_legacy = genai_legacy.GenerativeModel(
            model_name=self.model_id,
            generation_config={
                'temperature': 0.7,
                'top_p': 0.95,
                'max_output_tokens': 20000,
            }
        )
        
        # Load prompt template
        prompt_path = config.get_prompt_path('agent3_prompt.txt')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            self.prompt_template = f.read()
        print(f"[Agent 3] Loaded prompt template ({len(self.prompt_template)} chars)")
        
        # Load PDF context
        self.pdf_loader = get_pdf_context_loader()
        print(f"[Agent 3] PDF context: {self.pdf_loader.has_context()}")
    
    def generate_questions(self, article: Dict) -> Dict:
        """
        Generate PAES-format questions for an approved article.
        
        Args:
            article: Article dict from Agent 2 with fields:
                - article_id: ID (e.g., C001)
                - title: Article title
                - author: Author name
                - url: Article URL
                - source: Source/publication
                - date: Publication year
                - type: Text type (literario/expositivo/argumentativo)
                - license: License type
                - fragment_start: First 12-20 words
                - fragment_end: Last 12-20 words
                - tsv_row: Full TSV row data
        
        Returns:
            Dict with questions and raw response
        """
        article_id = article.get('article_id', 'T01')
        print(f"[Agent 3] Generating PAES questions for: {article_id}")
        
        try:
            # Build metadata section for prompt
            metadata = self._build_metadata_section(article)
            
            # Combine with prompt template
            full_prompt = metadata + "\n\n" + self.prompt_template
            
            print(f"[Agent 3] Prompt length: {len(full_prompt)} chars")
            print(f"[Agent 3] Article: {article.get('title', 'N/A')[:50]}...")
            
            # Generate using legacy API with PDF context
            if self.pdf_loader and self.pdf_loader.has_context():
                file_count = len(self.pdf_loader.get_loaded_files())
                print(f"[Agent 3] Using PDF context ({file_count} files)")
                response_text = self._generate_with_pdfs(full_prompt)
            else:
                print(f"[Agent 3] No PDF context available, using Google Search")
                response_text = self._generate_with_search(full_prompt)
            
            # Save raw response for debugging
            self._save_debug_file(article_id, response_text)
            
            # Parse questions and article text
            parsed_result = self._parse_paes_format(response_text)
            parsed_questions = parsed_result.get('questions', [])
            article_text = parsed_result.get('article_text', '')
            
            print(f"[Agent 3] Parsed {len(parsed_questions)} questions")
            self._print_parse_summary(parsed_questions)
            
            return {
                'article_id': article_id,
                'raw_response': response_text,
                'article_text': article_text,
                'questions': parsed_questions,
                'question_count': len(parsed_questions)
            }
        
        except Exception as e:
            print(f"[Agent 3] ERROR: {e}")
            import traceback
            traceback.print_exc()
            return {
                'article_id': article_id,
                'raw_response': '',
                'questions': [],
                'question_count': 0,
                'error': str(e)
            }
    
    def improve_questions(self, questions: Dict, feedback: Dict, article: Dict) -> Dict:
        """
        Improve questions based on Agent 4 feedback.
        
        Args:
            questions: Original questions dict
            feedback: Feedback from Agent 4
            article: Original article dict
        
        Returns:
            Dict with improved questions
        """
        article_id = article.get('article_id', 'T01')
        print(f"[Agent 3] Improving questions based on feedback...")
        
        try:
            # Build improvement prompt
            prompt = f"""Eres diseñador/a senior de preguntas PAES. Recibiste feedback sobre tus preguntas.

ARTÍCULO: {article.get('title', 'Unknown')}

TUS PREGUNTAS ORIGINALES:
{questions.get('raw_response', '')}

FEEDBACK RECIBIDO:
{feedback.get('raw_feedback', '')}

INSTRUCCIONES:
Revisa y mejora las preguntas incorporando el feedback. Mantén el formato PAES exacto:
- Misma estructura (LECTURA, PREGUNTAS)
- Corrige los problemas mencionados
- Mantén distribución 2-5-3
- Mejora distractores si se indicó

Entrega el set completo mejorado en el mismo formato que originalmente.
"""
            
            # Generate improved version
            interaction = self.client.interactions.create(
                model=self.model_id,
                input=prompt,
                store=False
            )
            
            response_text = self._extract_interaction_text(interaction)
            
            # Save debug file for improved questions
            self._save_debug_file(article_id, response_text, improved=True)
            
            # Parse improved questions and article text
            parsed_result = self._parse_paes_format(response_text)
            parsed_improved = parsed_result.get('questions', [])
            article_text = parsed_result.get('article_text', '')
            
            print(f"[Agent 3] Improved {len(parsed_improved)} questions")
            
            return {
                'article_id': article_id,
                'raw_response': response_text,
                'article_text': article_text,
                'questions': parsed_improved,
                'question_count': len(parsed_improved),
                'improved': True
            }
        
        except Exception as e:
            print(f"[Agent 3] ERROR improving questions: {e}")
            # Return original questions on error
            return questions
    
    def _build_metadata_section(self, article: Dict) -> str:
        """Build metadata section for prompt."""
        tsv_row = article.get('tsv_row', {})
        
        # Extract all metadata from TSV row
        metadata = f"""METADATOS:
ID: {article.get('article_id', 'T01')}
ID_RANDOM: {tsv_row.get('ID_RANDOM', '')}
Tipo: {article.get('type', 'auto')}
Tema: {tsv_row.get('Tema', '')}
Autor: {article.get('author', 'No especificado')}
Titulo: {article.get('title', 'Sin título')}
Ano: {article.get('date', 'No especificado')}
Fuente: {article.get('source', 'No especificado')}
Licencia: {article.get('license', 'No especificado')}
URL: {article.get('url', '')}
URL_Canonica: {article.get('url', '')}
Inicio_Fragmento: {article.get('fragment_start', '')}
Fin_Fragmento: {article.get('fragment_end', '')}
Recurso_Discontinuo: {tsv_row.get('Recurso_Discontinuo', 'No')}

TEXTO_BASE:
Debes acceder a la URL y extraer el texto completo del artículo.
El fragmento debe estar entre Inicio_Fragmento y Fin_Fragmento (aproximadamente 650-900 palabras continuas).
"""
        return metadata
    
    def _generate_with_pdfs(self, prompt: str) -> str:
        """Generate using legacy API with PDF context."""
        pdf_files = self.pdf_loader.get_file_references()
        content_parts = pdf_files + [prompt]
        
        response = self.model_legacy.generate_content(contents=content_parts)
        return response.text
    
    def _generate_with_search(self, prompt: str) -> str:
        """Generate using Interactions API with Google Search."""
        interaction = self.client.interactions.create(
            model=self.model_id,
            input=prompt,
            tools=[{"type": "google_search"}],
            store=False
        )
        
        return self._extract_interaction_text(interaction)
    
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
    
    def _save_debug_file(self, article_id: str, response_text: str, improved: bool = False):
        """Save raw response for debugging."""
        try:
            if improved:
                debug_file = f"debug_questions_improved_{article_id}.txt"
                header = "=== RAW RESPONSE FROM AGENT 3 (IMPROVED) ==="
            else:
                debug_file = f"debug_questions_{article_id}.txt"
                header = "=== RAW RESPONSE FROM AGENT 3 ==="
            
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(f"{header}\n\n")
                f.write(response_text)
            print(f"[Agent 3] Saved debug file: {debug_file}")
        except Exception as e:
            print(f"[Agent 3] Could not save debug file: {e}")
    
    def _parse_paes_format(self, response_text: str) -> Dict:
        """
        Parse PAES-format response including article text and questions.
        
        Expected format:
        A) LECTURA
        **TEXTO**
        [Full article text...]
        
        B) PREGUNTAS
        1. [Habilidad-tarea]
        ¿Pregunta?
        A) Alternativa A
        B) Alternativa B
        C) Alternativa C
        D) Alternativa D
        Respuesta correcta: B
        Justificación: texto. Microevidencia: "cita".
        
        Returns:
            Dict with 'article_text' and 'questions' list
        """
        result = {
            'article_text': '',
            'questions': []
        }
        
        # Extract article text from A) LECTURA section
        lectura_match = re.search(r'A\)\s*LECTURA', response_text, re.IGNORECASE)
        if lectura_match:
            # Find TEXTO section within LECTURA
            texto_match = re.search(r'\*{0,2}TEXTO\*{0,2}', response_text[lectura_match.start():], re.IGNORECASE)
            if texto_match:
                texto_start = lectura_match.start() + texto_match.end()
                
                # Find where PREGUNTAS section starts
                preguntas_match = re.search(r'B\)\s*PREGUNTAS', response_text, re.IGNORECASE)
                if preguntas_match:
                    texto_end = preguntas_match.start()
                    article_text = response_text[texto_start:texto_end].strip()
                    # Remove asterisks separator if present
                    article_text = re.sub(r'\n\*{3,}\n', '\n\n', article_text)
                    result['article_text'] = article_text
                    print(f"[Agent 3] Extracted article text ({len(article_text)} chars)")
        
        # Find PREGUNTAS section
        preguntas_match = re.search(r'B\)\s*PREGUNTAS', response_text, re.IGNORECASE)
        if not preguntas_match:
            print("[Agent 3] WARNING: PREGUNTAS section not found")
            return result
        
        preguntas_start = preguntas_match.end()
        
        # Find CLAVES section (optional, might not exist)
        claves_match = re.search(r'C\)\s*CLAVES', response_text, re.IGNORECASE)
        if claves_match:
            preguntas_section = response_text[preguntas_start:claves_match.start()]
            claves_section = response_text[claves_match.end():]
        else:
            preguntas_section = response_text[preguntas_start:]
            claves_section = ""
        
        # Parse each question from PREGUNTAS section
        questions = self._parse_preguntas_section(preguntas_section)
        
        # Parse CLAVES section if exists (can fill missing data)
        if claves_section:
            self._parse_claves_section(claves_section, questions)
        
        result['questions'] = questions
        return result
    
    def _parse_preguntas_section(self, section_text: str) -> List[Dict]:
        """Parse questions from PREGUNTAS section."""
        questions = []
        lines = section_text.split('\n')
        
        current_q = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Match: "1. [Habilidad-tarea]" or "1. [Habilidad-tarea] ¿Pregunta?"
            q_match = re.match(r'^(\d+)\.\s*\[([^\]]+)\]\s*(.*)$', line)
            if q_match:
                # Save previous question
                if current_q:
                    questions.append(current_q)
                
                # Start new question
                current_q = {
                    'number': int(q_match.group(1)),
                    'habilidad': q_match.group(2).strip(),
                    'question': q_match.group(3).strip(),
                    'alternatives': {},
                    'clave': '',
                    'justification': ''
                }
                continue
            
            # Match: "1. ¿Pregunta?" (no habilidad on same line)
            q_simple = re.match(r'^(\d+)\.\s*(.+)$', line)
            if q_simple and not current_q:
                # Start new question without habilidad
                current_q = {
                    'number': int(q_simple.group(1)),
                    'habilidad': '',
                    'question': q_simple.group(2).strip(),
                    'alternatives': {},
                    'clave': '',
                    'justification': ''
                }
                continue
            
            if not current_q:
                continue
            
            # Match alternatives: "A) texto" - check this BEFORE question text
            alt_match = re.match(r'^([ABCD])\)\s*(.+)$', line)
            if alt_match:
                letter = alt_match.group(1)
                text = alt_match.group(2).strip()
                current_q['alternatives'][letter] = text
                continue
            
            # Match "Respuesta correcta: B" or "Respuesta correcta B" (with or without colon)
            resp_match = re.match(r'^Respuesta\s+correcta\s*:?\s*([ABCD])', line, re.IGNORECASE)
            if resp_match:
                current_q['clave'] = resp_match.group(1)
                continue
            
            # Alternative format: just "Correcta: B"
            resp_alt = re.match(r'^Correcta\s*:?\s*([ABCD])', line, re.IGNORECASE)
            if resp_alt:
                current_q['clave'] = resp_alt.group(1)
                continue
            
            # Match "Justificación: texto"
            just_match = re.match(r'^Justificaci[oó]n\s*:?\s*(.+)$', line, re.IGNORECASE)
            if just_match:
                current_q['justification'] = just_match.group(1).strip()
                continue
            
            # If we have justification started, continue appending
            if current_q.get('justification') and not re.match(r'^\d+\.', line):
                current_q['justification'] += ' ' + line
                continue
            
            # If current question has no question text yet, this line is probably it
            # (Not a number, not an alternative, not a clave, not justification)
            if not current_q['question']:
                # This must be the question text
                current_q['question'] = line
                continue
        
        # Save last question
        if current_q:
            questions.append(current_q)
        
        return questions
    
    def _parse_claves_section(self, section_text: str, questions: List[Dict]):
        """Parse CLAVES section and update questions with any missing data."""
        # Pattern: "1) B. Justificación: texto. Microevidencia: "cita"."
        clave_pattern = r'(\d+)\)\s*\*{0,2}([ABCD])\*{0,2}\.?\s*(.+?)(?=\n\d+\)|$)'
        
        for match in re.finditer(clave_pattern, section_text, re.DOTALL | re.IGNORECASE):
            q_num = int(match.group(1))
            clave = match.group(2)
            justif = match.group(3).strip()
            
            # Find matching question
            for q in questions:
                if q['number'] == q_num:
                    # Update only if missing
                    if not q['clave']:
                        q['clave'] = clave
                    if not q['justification'] or len(justif) > len(q['justification']):
                        q['justification'] = justif
                    break
    
    def _print_parse_summary(self, questions: List[Dict]):
        """Print summary of parsed questions."""
        if not questions:
            print("[Agent 3] No questions parsed!")
            return
        
        print(f"\n[Agent 3] Parse Summary:")
        complete = 0
        for q in questions:
            has_question = bool(q.get('question'))
            has_4_alts = len(q.get('alternatives', {})) == 4
            has_clave = bool(q.get('clave'))
            has_just = bool(q.get('justification'))
            
            if has_question and has_4_alts and has_clave and has_just:
                complete += 1
            
            status = "OK" if (has_question and has_4_alts and has_clave and has_just) else "X"
            print(f"  Q{q.get('number', '?')}: {status} "
                  f"question={'Y' if has_question else 'N'} "
                  f"alts={len(q.get('alternatives', {}))}/4 "
                  f"clave={'Y' if has_clave else 'N'} "
                  f"just={'Y' if has_just else 'N'}")
        
        print(f"[Agent 3] Complete questions: {complete}/{len(questions)}")


# Global agent instance
question_agent = QuestionAgent()

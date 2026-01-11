"""
Agent 4: Question Review Agent
Reviews and provides feedback on generated questions using Interactions API.

Recent improvements (Jan 2026):
- Fixed input handling to use Agent 3's article_text and raw_response
- Added debug file saving (debug_review_*.txt)
- Cleaned up outdated input references
"""
from google import genai
from typing import Dict, Optional, List
import os

from config import config


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
        
        # Load prompt template
        prompt_path = config.get_prompt_path('agent4_prompt.txt')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            self.prompt_template = f.read()
        print(f"[Agent 4] Loaded prompt template ({len(self.prompt_template)} chars)")
    
    def review_questions(self, article: Dict, questions: Dict) -> Dict:
        """
        Review PAES questions using DEMRE quality standards.
        
        Args:
            article: Article dictionary
            questions: Questions dictionary from Agent 3 with 'article_text' and 'raw_response'
            
        Returns:
            Dictionary with DEMRE-style feedback (nota/10, veredicto, diagnostico)
        """
        article_id = article.get('article_id', 'T01')
        print(f"[Agent 4] Reviewing PAES questions for: {article.get('title', 'Untitled')[:50]}...")
        
        try:
            # Get article text from Agent 3's extraction (in questions dict)
            article_text = questions.get('article_text', '')
            
            # Get full PAES response from Agent 3 (includes LECTURA + PREGUNTAS sections)
            questions_paes = questions.get('raw_response', '')
            
            # If article_text is missing, try to extract it from raw_response
            if not article_text and questions_paes:
                # Agent 3 response has A) LECTURA section with the text
                # We can just send the whole raw_response since it has everything
                print(f"[Agent 4] Using full raw_response (includes LECTURA + PREGUNTAS)")
                review_input = questions_paes
            else:
                # Build input with separate sections
                print(f"[Agent 4] Article text: {len(article_text)} chars")
                print(f"[Agent 4] Questions format: {len(questions_paes)} chars")
                
                review_input = f"""FRAGMENTO:
{article_text}

PREGUNTAS Y CLAVES:
{questions_paes}
"""
            
            # Prepare prompt (template already has all instructions)
            prompt = self.prompt_template + "\n\n" + review_input
            
            print(f"[Agent 4] Prompt length: {len(prompt)} chars")
            
            # Generate feedback using Interactions API
            print(f"[Agent 4] Calling Gemini for DEMRE quality review...")
            interaction = self.client.interactions.create(
                model=self.model_id,
                input=prompt,
                store=False  # Don't store for privacy
            )
            
            # Extract response text from interaction outputs
            response_text = self._extract_interaction_text(interaction)
            
            # Save debug file
            self._save_debug_file(article_id, response_text)
            
            # Parse feedback (DEMRE format: nota/10, veredicto, diagnostico, parches)
            feedback_dict = {
                'article_id': article_id,
                'article_title': article.get('title', ''),
                'raw_feedback': response_text,
                'nota_global': self._extract_nota(response_text),
                'veredicto': self._extract_veredicto(response_text),
                'diagnostico_por_pregunta': self._parse_diagnostico(response_text),
                'parches': self._extract_parches(response_text),
                'top_3_fixes': self._extract_top_fixes(response_text)
            }
            
            nota = feedback_dict['nota_global']
            print(f"[Agent 4] Review complete: Nota {nota}/10")
            return feedback_dict
        
        except Exception as e:
            print(f"[Agent 4] Error reviewing questions: {e}")
            import traceback
            traceback.print_exc()
            return {
                'article_id': article_id,
                'article_title': article.get('title', ''),
                'raw_feedback': '',
                'nota_global': 0.0,
                'error': str(e)
            }
    
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
            debug_file = f"debug_review_{article_id}.txt"
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
        
        # Look for patterns like "Nota global: 8.5/10" or "8,5/10"
        nota_pattern = r'[Nn]ota\s*(?:global)?:?\s*(\d+(?:[,\.]\d+)?)\s*/\s*10'
        match = re.search(nota_pattern, feedback_text)
        
        if match:
            nota_str = match.group(1).replace(',', '.')
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


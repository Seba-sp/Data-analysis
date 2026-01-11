"""
Agent 2: License Validation Agent
Validates Creative Commons licensing for news articles using Gemini.
"""
import google.generativeai as genai
from typing import List, Dict, Optional, Tuple
import re

from config import config
from storage import storage


class ValidationAgent:
    """Agent for validating Creative Commons licenses."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize validation agent.
        
        Args:
            api_key: Gemini API key (uses config if not provided)
        """
        self.api_key = api_key or config.GEMINI_API_KEY
        genai.configure(api_key=self.api_key)
        
        # Initialize Gemini model (Validation)
        self.model = genai.GenerativeModel(
            model_name=config.GEMINI_MODEL_AGENTS234,
            generation_config={
                'temperature': 0.3,  # Lower temperature for more consistent validation
                'max_output_tokens': config.MAX_OUTPUT_TOKENS,
            }
        )
        
        # Load prompt template
        prompt_path = config.get_prompt_path('agent2_prompt.txt')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            self.prompt_template = f.read()
        print(f"[Agent 2] Loaded prompt template ({len(self.prompt_template)} chars)")
    
    def validate_articles(self, tsv_data: str) -> Tuple[str, List[Dict]]:
        """
        Validate articles from TSV data using legal audit prompt.
        
        Args:
            tsv_data: TSV string with candidate texts from Agent 1
            
        Returns:
            Tuple of (audit_tsv_string, list_of_approved_article_dicts)
        """
        print(f"[Agent 2] Starting legal validation audit...")
        
        try:
            # Check TSV format
            lines = tsv_data.strip().split('\n')
            if len(lines) < 2:
                print(f"[Agent 2] ERROR: TSV has insufficient data")
                return ("", [])
            
            header = lines[0].split('\t')
            print(f"[Agent 2] TSV has {len(header)} columns, {len(lines)-1} rows")
            
            # Prepare prompt with TSV data
            prompt = self.prompt_template + "\n\nTABLA A VALIDAR:\n\n" + tsv_data
            
            print(f"[Agent 2] Calling Gemini for legal audit...")
            response = self.model.generate_content(prompt)
            
            # Extract audit TSV from response
            audit_tsv = self._extract_audit_tsv(response.text)
            
            if not audit_tsv:
                print(f"[Agent 2] ERROR: No audit TSV found in response")
                return ("", [])
            
            # Parse audit results to get approved articles
            approved_articles = self._parse_audit_results(audit_tsv, tsv_data)
            
            print(f"[Agent 2] Audit complete: {len(approved_articles)} texts APROBADO")
            return (audit_tsv, approved_articles)
        
        except Exception as e:
            print(f"[Agent 2] Error during validation: {e}")
            import traceback
            traceback.print_exc()
            return ("", [])
    
    def _extract_audit_tsv(self, response_text: str) -> str:
        """
        Extract audit TSV table from response.
        
        Args:
            response_text: Raw response from Gemini
            
        Returns:
            Audit TSV string with ID, Estado, Decision, Motivo_Concreto, Accion_Recomendada
        """
        # Look for TSV code block
        tsv_match = re.search(r'```(?:tsv)?\s*\n(.*?)\n```', response_text, re.DOTALL | re.IGNORECASE)
        
        if tsv_match:
            return tsv_match.group(1).strip()
        
        # Look for lines that start with "ID\tEstado" (audit header)
        lines = response_text.split('\n')
        tsv_start = -1
        tsv_end = -1
        
        for i, line in enumerate(lines):
            if 'ID' in line and 'Estado' in line and 'Decision' in line:
                tsv_start = i
            elif tsv_start != -1 and line.strip() and '\t' in line:
                tsv_end = i
            elif tsv_start != -1 and tsv_end != -1 and not line.strip():
                break
        
        if tsv_start != -1:
            if tsv_end == -1:
                tsv_end = len(lines) - 1
            return '\n'.join(lines[tsv_start:tsv_end+1])
        
        return ""
    
    def _parse_audit_results(self, audit_tsv: str, original_tsv: str) -> List[Dict]:
        """
        Parse audit results to extract approved articles.
        
        Args:
            audit_tsv: Audit TSV from Agent 2 response
            original_tsv: Original TSV from Agent 1
            
        Returns:
            List of approved article dictionaries
        """
        approved_articles = []
        
        # Parse audit TSV
        audit_lines = audit_tsv.strip().split('\n')
        if len(audit_lines) < 2:
            return approved_articles
        
        audit_header = audit_lines[0].split('\t')
        audit_rows = []
        
        for line in audit_lines[1:]:
            if not line.strip():
                continue
            values = line.split('\t')
            audit_rows.append(dict(zip(audit_header, values)))
        
        # Parse original TSV
        original_lines = original_tsv.strip().split('\n')
        if len(original_lines) < 2:
            return approved_articles
        
        original_header = original_lines[0].split('\t')
        
        # Find approved IDs
        approved_ids = set()
        for row in audit_rows:
            estado = row.get('Estado', '').upper()
            decision = row.get('Decision', '').upper()
            
            if decision == 'OK' or estado in ['APROBADO', 'APROBADO_CONDICION']:
                approved_ids.add(row.get('ID', ''))
        
        # Extract approved articles from original TSV
        for line in original_lines[1:]:
            if not line.strip():
                continue
            
            values = line.split('\t')
            # Don't require exact column match - some TSV rows may have empty trailing columns
            # Pad with empty strings if needed
            while len(values) < len(original_header):
                values.append('')
            
            row_dict = dict(zip(original_header, values))
            article_id = row_dict.get('ID', '')
            
            if article_id in approved_ids:
                # Create article dict for Agent 3
                article = {
                    'article_id': article_id,
                    'title': row_dict.get('Titulo', ''),
                    'author': row_dict.get('Autor', ''),
                    'url': row_dict.get('URL_Canonica', row_dict.get('URL', '')),
                    'source': row_dict.get('Fuente', ''),
                    'date': row_dict.get('Ano', ''),
                    'type': row_dict.get('Tipo', ''),
                    'license': row_dict.get('Licencia', ''),
                    'license_status': 'approved',
                    'content': '',  # Will be populated if needed
                    'fragment_start': row_dict.get('Inicio_Fragmento', ''),
                    'fragment_end': row_dict.get('Fin_Fragmento', ''),
                    'tsv_row': row_dict
                }
                
                approved_articles.append(article)
        
        return approved_articles
    
    def get_audit_summary(self, audit_tsv: str) -> Dict:
        """
        Get summary statistics from audit results.
        
        Args:
            audit_tsv: Audit TSV string
            
        Returns:
            Dictionary with summary statistics
        """
        summary = {
            'total': 0,
            'aprobado': 0,
            'aprobado_condicion': 0,
            'en_riesgo': 0,
            'rechazado': 0
        }
        
        lines = audit_tsv.strip().split('\n')
        if len(lines) < 2:
            return summary
        
        header = lines[0].split('\t')
        
        for line in lines[1:]:
            if not line.strip():
                continue
            
            values = line.split('\t')
            row_dict = dict(zip(header, values))
            
            summary['total'] += 1
            estado = row_dict.get('Estado', '').upper()
            
            if estado == 'APROBADO':
                summary['aprobado'] += 1
            elif estado == 'APROBADO_CONDICION':
                summary['aprobado_condicion'] += 1
            elif estado == 'EN_RIESGO':
                summary['en_riesgo'] += 1
            elif estado == 'RECHAZADO':
                summary['rechazado'] += 1
        
        return summary
    
    def get_cc_license_types(self) -> List[str]:
        """
        Get list of recognized Creative Commons license types.
        
        Returns:
            List of CC license types
        """
        return [
            'CC0',
            'CC-BY',
            'CC-BY-SA',
            'CC-BY-NC',
            'CC-BY-ND',
            'CC-BY-NC-SA',
            'CC-BY-NC-ND'
        ]
    
    def is_valid_cc_license(self, license_type: str) -> bool:
        """
        Check if license type is a valid Creative Commons license.
        
        Args:
            license_type: License type string
            
        Returns:
            True if valid CC license, False otherwise
        """
        valid_licenses = self.get_cc_license_types()
        license_upper = license_type.upper().strip()
        
        for valid in valid_licenses:
            if valid in license_upper:
                return True
        
        return False
    
    def get_license_details(self, license_type: str) -> Dict[str, str]:
        """
        Get details about a Creative Commons license.
        
        Args:
            license_type: CC license type
            
        Returns:
            Dictionary with license details
        """
        licenses = {
            'CC0': {
                'name': 'CC0 Public Domain Dedication',
                'commercial': 'Yes',
                'derivative': 'Yes',
                'attribution': 'No'
            },
            'CC-BY': {
                'name': 'Attribution',
                'commercial': 'Yes',
                'derivative': 'Yes',
                'attribution': 'Yes'
            },
            'CC-BY-SA': {
                'name': 'Attribution-ShareAlike',
                'commercial': 'Yes',
                'derivative': 'Yes (with same license)',
                'attribution': 'Yes'
            },
            'CC-BY-NC': {
                'name': 'Attribution-NonCommercial',
                'commercial': 'No',
                'derivative': 'Yes',
                'attribution': 'Yes'
            },
            'CC-BY-ND': {
                'name': 'Attribution-NoDerivatives',
                'commercial': 'Yes',
                'derivative': 'No',
                'attribution': 'Yes'
            },
            'CC-BY-NC-SA': {
                'name': 'Attribution-NonCommercial-ShareAlike',
                'commercial': 'No',
                'derivative': 'Yes (with same license)',
                'attribution': 'Yes'
            },
            'CC-BY-NC-ND': {
                'name': 'Attribution-NonCommercial-NoDerivatives',
                'commercial': 'No',
                'derivative': 'No',
                'attribution': 'Yes'
            }
        }
        
        license_upper = license_type.upper().strip()
        
        for key, details in licenses.items():
            if key in license_upper:
                return details
        
        return {
            'name': 'Unknown',
            'commercial': 'Unknown',
            'derivative': 'Unknown',
            'attribution': 'Unknown'
        }


# Global agent instance
validation_agent = ValidationAgent()


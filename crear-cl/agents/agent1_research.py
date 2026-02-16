"""
Agent 1: Text Curation Agent for PAES

Uses Google Gemini Interactions API to discover and curate news articles.
Follows strict PAES Competencia Lectora (Chile) standards with legal validation.

Modes:
- 'agent': Deep Research agent (slow, comprehensive, background processing)
  Uses: deep-research-pro-preview-12-2025
  Built-in Google Search, multi-step research, 4-5 minutes
  
- 'model': Standard model with Google Search tool (fast, synchronous)
  Uses: gemini-3-flash-preview (or custom model)
  Explicit Google Search tool, single-pass, 30-60 seconds

Output: TSV with 28 columns per article (30 articles with 10-10-10 distribution)
Includes: ID, ID_RANDOM, metadata, license evidence, fragment markers, alerts, risks

Recent improvements:
- Fixed prompt construction (prepends parameters instead of .format())
- Enhanced Deep Research polling with better status reporting
- Improved text extraction from multiple output types
- Added ID_RANDOM column support (16-char alphanumeric)
- Better TSV extraction with fallback patterns
- Debug output saved to file when TSV extraction fails
"""
from google import genai
from typing import List, Dict, Optional
import csv
import io
import json
import re
import os

from config import config
from storage import storage 

class ResearchAgent:
    """Agent for discovering news articles using Gemini Interactions API.
    
    Supports two modes:
    - 'agent': Deep Research agent (slow, comprehensive, background processing)
    - 'model': Standard model with Google Search tool (fast, synchronous)
    """
    
    def __init__(self, api_key: Optional[str] = None, mode: Optional[str] = None):
        """
        Initialize research agent.
        
        Args:
            api_key: Gemini API key (uses config if not provided)
            mode: 'agent' for Deep Research or 'model' for fast search (uses config if not provided)
        """
        self.api_key = api_key or config.GEMINI_API_KEY
        
        # Set API key as environment variable for genai.Client
        os.environ['GEMINI_API_KEY'] = self.api_key
        
        # Initialize Interactions API client
        self.client = genai.Client(api_key=self.api_key)
        
        # Determine mode: 'agent' (Deep Research) or 'model' (Fast with Google Search)
        self.mode = mode or config.AGENT1_MODE
        
        # Configure based on mode
        if self.mode == 'agent':
            self.agent_id = config.AGENT1_DEEP_RESEARCH
            self.model_id = None
            print(f"[Agent 1] Mode: Deep Research Agent ({self.agent_id})")
        else:  # mode == 'model'
            self.agent_id = None
            self.model_id = config.AGENT1_MODEL
            print(f"[Agent 1] Mode: Model with Google Search ({self.model_id})")
        
        # Load prompt template
        prompt_path = config.get_prompt_path('agent1_prompt.txt')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            self.prompt_template = f.read()
        print(f"[Agent 1] Loaded prompt template ({len(self.prompt_template)} chars)")
    
    def find_articles(self, topic: Optional[str] = None, count: int = 30, 
                     exclude_urls: Optional[List[str]] = None, 
                     last_id: Optional[str] = None) -> str:
        """
        Find news articles using Gemini Deep Research or Model with Google Search.
        
        Args:
            topic: Topic to research (None for general news, "diversidad temática")
            count: Number of articles to find (default 30 for PAES curation)
            exclude_urls: List of URLs to exclude (already processed articles)
            last_id: Last ID used (e.g., C030) to continue numbering
            
        Returns:
            TSV string with candidate articles (28 columns as per prompt)
        """
        exclude_urls = exclude_urls or []
        
        # Determine starting ID
        if last_id:
            # Extract number and increment
            match = re.search(r'(\d+)$', last_id)
            if match:
                next_num = int(match.group(1)) + 1
                id_inicial = f"C{next_num:03d}"
            else:
                id_inicial = "C001"
        else:
            id_inicial = "C001"
        
        if exclude_urls:
            print(f"[Agent 1] Starting text curation for {count} candidates (excluding {len(exclude_urls)} already processed)...")
        else:
            print(f"[Agent 1] Starting text curation for {count} candidates...")
        
        # Build input section for prompt (prepend to the template)
        # The prompt template is complete instructions, we just add the specific parameters at the top
        registro_existente = "(vacío, primera ejecución)" if not exclude_urls else f"({len(exclude_urls)} URLs ya procesados)"
        
        urls_section = ""
        if exclude_urls:
            urls_section = "\n\nURLs ya procesados (NO repetir ninguno de estos):\n"
            urls_to_show = exclude_urls[-100:] if len(exclude_urls) > 100 else exclude_urls
            for url in urls_to_show:
                urls_section += f"- {url}\n"
            if len(exclude_urls) > 100:
                urls_section += f"... y {len(exclude_urls) - 100} URLs más (total: {len(exclude_urls)} URLs a excluir).\n"
        
        # Construct the full prompt by prepending parameters to the template
        input_section = f"""ROL
Eres curador/a senior de lecturas para PAES Competencia Lectora (Chile).

ENTRADAS PARA ESTA EJECUCIÓN:
A) REGISTRO_EXISTENTE_CSV: {registro_existente}
B) ID_INICIAL: {id_inicial}
C) TEMAS_PRIORITARIOS: {topic if topic else "diversidad temática"}
D) MODO_SALIDA: TSV
{urls_section}

---

INSTRUCCIONES COMPLETAS:
"""
        
        prompt = input_section + self.prompt_template
        
        print(f"[Agent 1] Full prompt length: {len(prompt)} chars")
        print(f"[Agent 1] Excluded URLs: {len(exclude_urls)}, Starting ID: {id_inicial}")
        
        try:
            # Generate response based on mode
            # Note: The .create() call blocks until completion, so no polling is needed
            
            if self.mode == 'agent':
                # Mode 1: Deep Research Agent (comprehensive, slow)
                print(f"[Agent 1] Calling Deep Research agent (with built-in Google Search) to curate {count} texts...")
                print(f"[Agent 1] Note: This may take 4-5 minutes, please wait...")
                
                interaction = self.client.interactions.create(
                    agent=self.agent_id,
                    input=prompt,
                    # No tools parameter - Deep Research agent has Google Search built-in
                    background=False,  # Synchronous - wait for completion
                    store=True
                )
                
                print(f"[Agent 1] Deep Research completed! Status: {interaction.status}")
                
                if interaction.status == 'failed':
                    print(f"[Agent 1] ERROR: Deep Research failed")
                    if hasattr(interaction, 'error'):
                        print(f"[Agent 1] Error details: {interaction.error}")
                    return self._generate_empty_tsv(count, id_inicial)
            
            else:  # mode == 'model'
                # Mode 2: Standard Model with Google Search Tool (faster)
                print(f"[Agent 1] Calling {self.model_id} with Google Search tool to curate {count} texts...")
                print(f"[Agent 1] This may take 30-60 seconds, please wait...")
                
                interaction = self.client.interactions.create(
                    model=self.model_id,
                    input=prompt,
                    tools=[{"type": "google_search"}],  # Explicitly add Google Search tool
                    store=False  # Don't store for privacy
                )
                
                print(f"[Agent 1] Model search completed! Status: {interaction.status}")
                
                if interaction.status == 'failed':
                    print(f"[Agent 1] ERROR: Model search failed")
                    if hasattr(interaction, 'error'):
                        print(f"[Agent 1] Error details: {interaction.error}")
                    return self._generate_empty_tsv(count, id_inicial)
            
            # Extract response text from interaction outputs
            # Handle different output types (text, tool results, etc.)
            if not interaction.outputs:
                print(f"[Agent 1] ERROR: No outputs in interaction (status: {interaction.status})")
                print(f"[Agent 1] Checking if interaction has response attribute...")
                
                # Try alternative attributes for response
                if hasattr(interaction, 'response'):
                    print(f"[Agent 1] Found response attribute")
                    response_text = str(interaction.response)
                elif hasattr(interaction, 'result'):
                    print(f"[Agent 1] Found result attribute")
                    response_text = str(interaction.result)
                else:
                    print(f"[Agent 1] No alternative response found")
                    return self._generate_empty_tsv(count, id_inicial)
            else:
                # Debug: show output types
                output_types = [type(o).__name__ for o in interaction.outputs]
                print(f"[Agent 1] Received {len(interaction.outputs)} outputs: {output_types}")
                
                response_text = self._extract_text_from_outputs(interaction.outputs)
            
            if not response_text or len(response_text.strip()) < 10:
                print(f"[Agent 1] ERROR: No substantial text response found")
                print(f"[Agent 1] Output count: {len(interaction.outputs) if interaction.outputs else 0}")
                print(f"[Agent 1] Extracted text length: {len(response_text) if response_text else 0}")
                
                # Debug: Try to inspect output structure
                if interaction.outputs:
                    for i, output in enumerate(interaction.outputs[:3]):  # Show first 3
                        print(f"[Agent 1] Output {i} type: {type(output).__name__}")
                        print(f"[Agent 1] Output {i} dir: {[attr for attr in dir(output) if not attr.startswith('_')][:10]}")
                        # Try to get any text attribute
                        for attr in ['text', 'content', 'value', 'data', 'message']:
                            if hasattr(output, attr):
                                val = getattr(output, attr)
                                print(f"[Agent 1] Output {i}.{attr}: {str(val)[:200]}")
                
                return self._generate_empty_tsv(count, id_inicial)
            
            print(f"[Agent 1] Extracted response text ({len(response_text)} chars)")
            
            # Save response for debugging (first 5000 chars)
            debug_preview = response_text[:5000] if len(response_text) > 5000 else response_text
            print(f"\n[Agent 1] Response preview (first 500 chars):\n{debug_preview[:500]}\n")
            
            # Parse response to extract TSV
            tsv_data = self._extract_tsv_from_response(response_text)
            
            if not tsv_data:
                print(f"[Agent 1] ERROR: No TSV data found in response")
                print(f"[Agent 1] Response contains: {len(response_text.split(chr(10)))} lines")
                # Save full response to file for debugging
                debug_file = f"debug_response_{id_inicial}.txt"
                try:
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(response_text)
                    print(f"[Agent 1] Saved full response to {debug_file} for debugging")
                except Exception as e:
                    print(f"[Agent 1] Could not save debug file: {e}")
                return self._generate_empty_tsv(count, id_inicial)
            
            # Validate TSV structure
            lines = tsv_data.strip().split('\n')
            if len(lines) < 2:  # Header + at least 1 row
                print(f"[Agent 1] WARNING: TSV has insufficient data ({len(lines)} lines)")
            else:
                # Check column count
                header_cols = len(lines[0].split('\t'))
                print(f"[Agent 1] TSV header has {header_cols} columns")
                
                # Validate expected 28 columns (as per prompt)
                if header_cols != 28:
                    print(f"[Agent 1] WARNING: Expected 28 columns, got {header_cols}")
            
            print(f"[Agent 1] Successfully extracted TSV with {len(lines)-1} candidate texts")
            
            # Store last TSV data for retrieval
            self._last_tsv_data = tsv_data
            
            return tsv_data
        
        except Exception as e:
            print(f"[Agent 1] Error during curation: {e}")
            return self._generate_empty_tsv(count, id_inicial)
    
    def _extract_text_from_outputs(self, outputs) -> str:
        """
        Extract text from interaction outputs, handling different content types.
        Handles both model responses and agent responses (Deep Research).
        
        Args:
            outputs: List of output content objects from interaction
            
        Returns:
            Combined text from all text outputs (excluding tool results)
        """
        if not outputs:
            return ""
        
        text_parts = []
        
        for idx, output in enumerate(outputs):
            # Get output type name
            output_type = type(output).__name__
            
            # Skip tool result objects (GoogleSearchResultContent, etc.) but NOT the final response
            # Tool results are intermediate, we want the final synthesized response
            if 'GoogleSearchResult' in output_type:
                continue  # Skip search results, we want the agent's synthesis
            
            # Try multiple ways to extract text from the output
            extracted = False
            
            # Method 1: Direct .text attribute (most common)
            if hasattr(output, 'text'):
                try:
                    text_value = output.text
                    if text_value and isinstance(text_value, str) and len(text_value.strip()) > 0:
                        text_parts.append(text_value)
                        extracted = True
                except (AttributeError, TypeError):
                    pass
            
            # Method 2: .content attribute (alternative structure)
            if not extracted and hasattr(output, 'content'):
                try:
                    content = output.content
                    if isinstance(content, str) and len(content.strip()) > 0:
                        text_parts.append(content)
                        extracted = True
                    elif isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict) and 'text' in item:
                                text_parts.append(item['text'])
                                extracted = True
                            elif hasattr(item, 'text'):
                                text_parts.append(item.text)
                                extracted = True
                            elif isinstance(item, str) and len(item.strip()) > 0:
                                text_parts.append(item)
                                extracted = True
                except (AttributeError, TypeError):
                    pass
            
            # Method 3: If it's a dict with text
            if not extracted and isinstance(output, dict):
                if 'text' in output and isinstance(output['text'], str):
                    text_parts.append(output['text'])
                    extracted = True
            
            # Method 4: .parts attribute (for structured content)
            if not extracted and hasattr(output, 'parts'):
                try:
                    parts = output.parts
                    if isinstance(parts, list):
                        for part in parts:
                            if hasattr(part, 'text'):
                                text_parts.append(part.text)
                                extracted = True
                            elif isinstance(part, str):
                                text_parts.append(part)
                                extracted = True
                except (AttributeError, TypeError):
                    pass
            
            # Method 5: Direct string conversion as last resort (avoid for objects)
            if not extracted and not output_type.startswith('_'):
                try:
                    str_repr = str(output)
                    # Only use if it looks like actual content (not object representation)
                    if str_repr and len(str_repr.strip()) > 50 and not str_repr.startswith('<'):
                        text_parts.append(str_repr)
                        extracted = True
                except:
                    pass
        
        combined_text = '\n\n'.join(text_parts)
        return combined_text
    
    def _extract_tsv_from_response(self, response_text: str) -> str:
        """
        Extract TSV table from agent response.
        Handles multiple formats: code blocks, plain TSV, etc.
        
        Args:
            response_text: Raw response from Gemini
            
        Returns:
            TSV string with header and data rows
        """
        if not response_text:
            return ""
        
        # Method 1: Look for TSV code block (```tsv or ``` with TSV content)
        tsv_patterns = [
            r'```tsv\s*\n(.*?)\n```',
            r'```\s*\n(ID\t.*?)\n```',
            r'```text\s*\n(ID\t.*?)\n```'
        ]
        
        for pattern in tsv_patterns:
            tsv_match = re.search(pattern, response_text, re.DOTALL | re.IGNORECASE)
            if tsv_match:
                tsv_content = tsv_match.group(1).strip()
                if tsv_content and '\t' in tsv_content:
                    print(f"[Agent 1] Found TSV in code block (pattern: {pattern[:20]}...)")
                    return tsv_content
        
        # Method 2: Look for lines that start with "ID\t" or "ID, " (TSV/CSV header)
        lines = response_text.split('\n')
        tsv_start = -1
        tsv_end = -1
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            # Check for TSV header (with ID_RANDOM column)
            if stripped.startswith('ID\t') or stripped.startswith('ID,'):
                # Verify it looks like our expected header
                if 'ID_RANDOM' in stripped or 'Tipo' in stripped:
                    tsv_start = i
                    print(f"[Agent 1] Found TSV header at line {i}")
            elif tsv_start != -1:
                # Continue collecting TSV rows
                if stripped and ('\t' in stripped or ',' in stripped):
                    tsv_end = i
                elif stripped == '' or stripped.startswith('---') or stripped.startswith('=='):
                    # Empty line or separator indicates end of TSV
                    break
        
        if tsv_start != -1:
            if tsv_end == -1:
                tsv_end = len(lines) - 1
            
            # Extract TSV lines
            tsv_lines = lines[tsv_start:tsv_end+1]
            # Clean up each line
            tsv_lines = [line.rstrip() for line in tsv_lines if line.strip()]
            tsv_content = '\n'.join(tsv_lines)
            
            print(f"[Agent 1] Extracted TSV from lines {tsv_start} to {tsv_end} ({len(tsv_lines)} lines)")
            return tsv_content
        
        # Method 3: Look for any substantial tabular data (last resort)
        # Count lines with tabs
        tab_lines = [line for line in lines if '\t' in line and len(line.split('\t')) > 10]
        if len(tab_lines) >= 2:  # At least header + 1 row
            print(f"[Agent 1] Found {len(tab_lines)} tab-separated lines (using as TSV)")
            return '\n'.join(tab_lines)
        
        print(f"[Agent 1] WARNING: No TSV data found in response")
        return ""
    
    def _generate_empty_tsv(self, count: int, start_id: str) -> str:
        """
        Generate an empty TSV structure when API fails.
        
        Args:
            count: Number of rows to generate
            start_id: Starting ID (e.g., C001)
            
        Returns:
            Empty TSV string with header (matches prompt specification)
        """
        # Header matches the exact specification from agent1_prompt.txt (21 columns)
        header = "ID, ID_RANDOM, Tipo, Género textual, Tema, Autor, Titulo, Ano, Fuente, URL, Licencia, Tipo_Evidencia_Licencia, Evidencia_Licencia_Ubicacion, Palabras_Fragmento_Real, Inicio_Fragmento, Fin_Fragmento, Recurso_Discontinuo, URL_Recurso, Licencia_Recurso, Tipo_Evidencia_Recurso, Evidencia_Recurso_Ubicacion"
        return header
    
    def tsv_to_article_list(self, csv_data: str) -> List[Dict]:
        """
        Convert CSV data to list of article dictionaries for processing.
        Handles semicolon or comma delimiters, quoted fields, and embedded newlines.

        Args:
            csv_data: CSV string with header and rows (21 columns)

        Returns:
            List of article dictionaries with standardized fields
        """
        articles = []

        if not csv_data or not csv_data.strip():
            print(f"[Agent 1] WARNING: CSV data is empty")
            return articles

        # Auto-detect delimiter from header line
        first_line = csv_data.split('\n', 1)[0]
        delimiter = ';' if first_line.count(';') > first_line.count(',') else ','

        reader = csv.reader(io.StringIO(csv_data), delimiter=delimiter, quotechar='"')
        rows = list(reader)

        if len(rows) < 2:
            print(f"[Agent 1] WARNING: CSV has insufficient data (only {len(rows)} rows)")
            return articles

        # Parse header
        header = [h.strip() for h in rows[0]]
        print(f"[Agent 1] CSV header: {len(header)} columns (delimiter='{delimiter}')")

        # Parse data rows
        for line_num, row in enumerate(rows[1:], start=2):
            # Skip empty rows
            if not row or all(v.strip() == '' for v in row):
                continue

            # Clean values: strip whitespace and remove embedded newlines
            values = [v.strip().replace('\n', ' ').replace('\r', '') for v in row]

            if len(values) != len(header):
                print(f"[Agent 1] WARNING: Row {line_num} has {len(values)} columns, expected {len(header)}")
                if len(values) < len(header):
                    values.extend([''] * (len(header) - len(values)))
                else:
                    values = values[:len(header)]

            # Create article dict from CSV row
            row_dict = dict(zip(header, values))

            # Map CSV columns to article format for downstream processing
            article = {
                'article_id': row_dict.get('ID', ''),
                'id_random': row_dict.get('ID_RANDOM', ''),
                'title': row_dict.get('Titulo', ''),
                'author': row_dict.get('Autor', ''),
                'url': row_dict.get('URL', ''),
                'source': row_dict.get('Fuente', ''),
                'date': row_dict.get('Ano', ''),
                'type': row_dict.get('Tipo', ''),
                'license': row_dict.get('Licencia', ''),
                'license_status': 'pending',
                'content': '',
                'tsv_row': row_dict,
                'fragment_start': row_dict.get('Inicio_Fragmento', ''),
                'fragment_end': row_dict.get('Fin_Fragmento', ''),
            }

            articles.append(article)

        print(f"[Agent 1] Parsed {len(articles)} articles from CSV")
        return articles
    
    def get_tsv_data(self) -> str:
        """
        Get the raw TSV data from the last curation run.
        
        Returns:
            TSV string
        """
        return getattr(self, '_last_tsv_data', '')


# Global agent instance
research_agent = ResearchAgent()


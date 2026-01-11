"""
PDF Context Loader for Agent 3.
Uploads reference PDFs to Gemini File API for native PDF processing.
"""
import os
from typing import Optional, List
import google.generativeai as genai
import time


class PDFContextLoader:
    """Loads and manages PDF reference documents for Agent 3 using Gemini File API."""
    
    def __init__(self, pdf_dir: str = 'agent-3-context', api_key: Optional[str] = None):
        """
        Initialize PDF context loader.
        
        Args:
            pdf_dir: Directory containing reference PDFs
            api_key: Gemini API key (uses config if not provided)
        """
        self.pdf_dir = pdf_dir
        self.uploaded_files = []  # List of Gemini File objects
        self.pdfs_loaded = []  # List of PDF filenames
        self.api_key = api_key
        self._upload_attempted = False  # Track if we've tried to upload
        
        # Don't upload PDFs here - will upload on first use (lazy loading)
    
    def _ensure_uploaded(self):
        """
        Ensure PDFs are uploaded (lazy loading).
        Only uploads once on first call.
        """
        if self._upload_attempted:
            return
        
        self._upload_attempted = True
        
        # Configure Gemini API if not already done
        if self.api_key:
            genai.configure(api_key=self.api_key)
        
        if not os.path.exists(self.pdf_dir):
            print(f"[PDF Loader] Warning: Directory '{self.pdf_dir}' not found. Agent 3 will run without PDF context.")
            return
        
        pdf_files = sorted([f for f in os.listdir(self.pdf_dir) if f.endswith('.pdf')])
        
        if not pdf_files:
            print(f"[PDF Loader] Warning: No PDF files found in '{self.pdf_dir}'")
            return
        
        print(f"[Agent 3] Uploading {len(pdf_files)} PDF reference documents to Gemini...")
        
        for pdf_file in pdf_files:
            pdf_path = os.path.join(self.pdf_dir, pdf_file)
            
            try:
                # Upload PDF to Gemini File API
                uploaded_file = genai.upload_file(pdf_path, display_name=pdf_file)
                
                # Wait for file to be processed
                while uploaded_file.state.name == "PROCESSING":
                    print(f"[Agent 3] Processing {pdf_file}...")
                    time.sleep(2)
                    uploaded_file = genai.get_file(uploaded_file.name)
                
                if uploaded_file.state.name == "ACTIVE":
                    self.uploaded_files.append(uploaded_file)
                    self.pdfs_loaded.append(pdf_file)
                    print(f"[Agent 3] OK Uploaded: {pdf_file}")
                else:
                    print(f"[Agent 3] ERROR: Failed to process {pdf_file} - State: {uploaded_file.state.name}")
            
            except Exception as e:
                print(f"[Agent 3] ERROR uploading {pdf_file}: {e}")
        
        print(f"[Agent 3] Total: {len(self.uploaded_files)} PDF reference documents ready")
    
    def get_file_references(self) -> List:
        """
        Get list of uploaded file objects for use in prompts.
        Uploads PDFs on first call (lazy loading).
        
        Returns:
            List of Gemini File objects
        """
        self._ensure_uploaded()
        return self.uploaded_files
    
    def get_context_instruction(self) -> str:
        """
        Get instruction text to include in prompts when PDFs are attached.
        
        Returns:
            Instruction text for the prompt
        """
        if not self.uploaded_files:
            return ""
        
        instruction = """
DOCUMENTOS DE REFERENCIA ADJUNTOS
===================================================================

Se han adjuntado los siguientes documentos PDF de referencia para el
diseño de ítems de Competencia Lectora según estándares DEMRE/PAES:

"""
        for pdf_name in self.pdfs_loaded:
            instruction += f"- {pdf_name}\n"
        
        instruction += """
Revisa estos documentos para:
1. Seguir los lineamientos de diseño de ítems PAES
2. Usar el formato y estructura de los ejemplos
3. Mantener el estándar de calidad DEMRE
4. Aplicar las rúbricas y criterios especificados

===================================================================

"""
        return instruction
    
    def has_context(self) -> bool:
        """
        Check if PDF files were successfully uploaded.
        Uploads PDFs on first call (lazy loading).
        
        Returns:
            True if files are uploaded, False otherwise
        """
        self._ensure_uploaded()
        return len(self.uploaded_files) > 0
    
    def get_loaded_files(self) -> list:
        """
        Get list of successfully loaded PDF files.
        
        Returns:
            List of PDF filenames
        """
        return self.pdfs_loaded.copy()
    
    def get_summary(self) -> str:
        """
        Get a summary of uploaded PDFs.
        
        Returns:
            Summary string
        """
        if not self.pdfs_loaded:
            return "No PDF context uploaded"
        
        summary = f"Uploaded {len(self.pdfs_loaded)} PDF(s) to Gemini:\n"
        for i, (pdf_file, file_obj) in enumerate(zip(self.pdfs_loaded, self.uploaded_files)):
            summary += f"  - {pdf_file} (URI: {file_obj.uri})\n"
        
        return summary


# Global PDF context loader instance (lazy initialization)
pdf_context_loader = None

def get_pdf_context_loader() -> PDFContextLoader:
    """
    Get or create the global PDF context loader instance.
    
    Returns:
        PDFContextLoader instance
    """
    global pdf_context_loader
    if pdf_context_loader is None:
        from config import config
        pdf_context_loader = PDFContextLoader(
            pdf_dir=config.AGENT3_CONTEXT_DIR,
            api_key=config.GEMINI_API_KEY
        )
    return pdf_context_loader


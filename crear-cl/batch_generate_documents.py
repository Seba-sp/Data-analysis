"""
Batch document generation script.
Scans a folder for all debug_questions*.txt files and generates Word + Excel documents.

Usage:
    python batch_generate_documents.py <folder_path>
    python batch_generate_documents.py .                    # Current directory
    python batch_generate_documents.py data/                # Data folder
    python batch_generate_documents.py C:/path/to/folder    # Absolute path
"""
import os
import sys
import re
from pathlib import Path
from agents.agent3_questions import QuestionAgent
from utils.document_generator import DocumentGenerator


def read_debug_file(filepath: str) -> str:
    """Read debug file content and extract raw response."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract raw response (remove header if present)
    if '=== RAW RESPONSE' in content:
        parts = content.split('===', 2)
        if len(parts) >= 3:
            return parts[2].strip()
    
    return content


def extract_article_info(filepath: str) -> dict:
    """
    Extract article ID and improvement status from filename.
    
    Examples:
        debug_questions_C001.txt -> {'article_id': 'C001', 'is_improved': False}
        debug_questions_improved_C001.txt -> {'article_id': 'C001', 'is_improved': True}
        debug_questions_C123.txt -> {'article_id': 'C123', 'is_improved': False}
    """
    filename = os.path.basename(filepath)
    
    # Check if improved
    is_improved = 'improved' in filename.lower()
    
    # Extract article ID (pattern: C followed by digits)
    match = re.search(r'C\d+', filename)
    if match:
        article_id = match.group(0)
    else:
        # Fallback: use filename without extension
        article_id = os.path.splitext(filename)[0].replace('debug_questions_', '').replace('improved_', '')
    
    return {
        'article_id': article_id,
        'is_improved': is_improved
    }


def extract_article_metadata(raw_response: str) -> dict:
    """
    Extract article metadata from raw response.
    
    Tries to find: author, title, source, date, license, URL
    """
    metadata = {
        'title': 'Unknown',
        'author': 'Unknown',
        'source': 'Unknown',
        'date': 'Unknown',
        'license': 'Unknown',
        'url': ''
    }
    
    lines = raw_response.split('\n')
    
    for line in lines[:20]:  # Check first 20 lines
        line_lower = line.lower()
        
        # Extract author and title from format: "Author, Title (Year)"
        if ', "' in line and '(' in line:
            match = re.search(r'([^,]+),\s*"([^"]+)"\s*\((\d{4})\)', line)
            if match:
                metadata['author'] = match.group(1).strip()
                metadata['title'] = match.group(2).strip()
                metadata['date'] = match.group(3).strip()
        
        # Extract source
        if 'fuente:' in line_lower or 'source:' in line_lower:
            parts = line.split(':')
            if len(parts) > 1:
                source_part = parts[1].strip()
                # Remove URL if present
                source_part = re.sub(r'URL:.*', '', source_part).strip()
                source_part = re.sub(r'http.*', '', source_part).strip()
                if source_part:
                    metadata['source'] = source_part.rstrip('.')
        
        # Extract license
        if any(lic in line for lic in ['Dominio Público', 'CC-BY', 'CC BY', 'Public Domain']):
            for lic in ['Dominio Público', 'Public Domain', 'CC-BY-SA', 'CC-BY', 'CC BY-SA', 'CC BY']:
                if lic in line:
                    metadata['license'] = lic
                    break
        
        # Extract URL
        if 'url:' in line_lower:
            match = re.search(r'URL:\s*(https?://[^\s]+)', line, re.IGNORECASE)
            if match:
                metadata['url'] = match.group(1).strip()
    
    return metadata


def process_file(filepath: str, question_agent: QuestionAgent, doc_generator: DocumentGenerator, source_docx: str = None) -> bool:
    """
    Process a single debug file and generate Word + Excel documents.
    
    Returns:
        True if successful, False otherwise
    """
    filename = os.path.basename(filepath)
    
    print(f"\n{'='*80}")
    print(f"Processing: {filename}")
    print('='*80)
    
    try:
        # Extract info from filename
        info = extract_article_info(filepath)
        article_id = info['article_id']
        is_improved = info['is_improved']
        
        print(f"  Article ID: {article_id}")
        print(f"  Improved: {is_improved}")
        
        # Read file
        print(f"\n  [1/4] Reading file...")
        raw_response = read_debug_file(filepath)
        print(f"  [OK] Read {len(raw_response):,} characters")
        
        # Parse with Agent 3's parser
        print(f"  [2/4] Parsing questions...")
        parsed_data = question_agent._parse_paes_format(raw_response)
        
        if not parsed_data:
            print(f"  [ERROR] Parsing failed (no data returned)")
            return False
            
        questions_list = parsed_data.get('questions', [])
        article_text = parsed_data.get('article_text', '')
        
        print(f"  [OK] Parsed {len(questions_list)} questions")
        print(f"  [OK] Article text: {len(article_text):,} characters")
        
        if not questions_list:
            print("  [WARNING] No questions found in the file! Generated documents will be empty of questions.")
        
        # Count complete questions
        complete = sum(1 for q in questions_list 
                      if q.get('question') and q.get('alternatives') 
                      and q.get('clave') and q.get('justification'))
        print(f"  [OK] Complete questions: {complete}/{len(questions_list)}")
        
        # Extract article metadata
        metadata = extract_article_metadata(raw_response)
        
        # Create article dict
        article = {
            'article_id': article_id,
            'title': metadata['title'],
            'author': metadata['author'],
            'source': metadata['source'],
            'date': metadata['date'],
            'license': metadata['license'],
            'url': metadata['url']
        }
        
        # Prepare questions dict
        questions_dict = {
            'article_text': article_text,
            'questions': questions_list,
            'question_count': len(questions_list)
        }
        
        # Generate filenames (save in same directory as input file unless output_dir is set)
        input_dir = os.path.dirname(os.path.abspath(filepath))
        output_dir = doc_generator.output_dir if hasattr(doc_generator, 'output_dir') and doc_generator.output_dir else input_dir
        
        # Ensure output directory exists
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            
        if is_improved:
            word_filename = f"{article_id}-Preguntas+Texto.docx"
            excel_filename = f"{article_id}-Preguntas Datos.xlsx"
        else:
            word_filename = f"{article_id}-Preguntas+Texto (Inicial).docx"
            excel_filename = f"{article_id}-Preguntas Datos (Inicial).xlsx"
        
        # Full paths including directory
        word_fullpath = os.path.join(output_dir, word_filename)
        excel_fullpath = os.path.join(output_dir, excel_filename)
        
        # Generate Word document
        print(f"  [3/4] Generating Word document...")
        
        if source_docx and os.path.exists(source_docx):
            print(f"  Using source DOCX: {source_docx}")
            word_path = doc_generator.merge_text_and_questions_docx(
                source_docx_path=source_docx,
                questions=questions_dict,
                output_path=word_fullpath,
                title=article.get('title', '')
            )
        else:
            word_path = doc_generator.generate_questions_word(
                article=article,
                questions=questions_dict,
                filename=word_fullpath,  # Pass full path
                is_improved=is_improved
            )
        print(f"  [OK] Word: {word_filename} ({os.path.getsize(word_path):,} bytes)")
        
        # Generate Excel file
        print(f"  [4/4] Generating Excel file...")
        excel_path = doc_generator.generate_questions_excel(
            questions=questions_dict,
            filename=excel_fullpath  # Pass full path
        )
        print(f"  [OK] Excel: {excel_filename} ({os.path.getsize(excel_path):,} bytes)")
        
        print(f"\n  [SUCCESS] {filename} -> Word + Excel generated")
        return True
        
    except Exception as e:
        print(f"\n  [ERROR] Failed to process {filename}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Batch document generation script.')
    parser.add_argument('path', help='File or folder path to process')
    parser.add_argument('--output-dir', help='Optional output directory for generated files')
    parser.add_argument('--docx', help='Optional path to source DOCX file (for single file processing)')
    
    args = parser.parse_args()
    
    path_arg = args.path
    output_dir = args.output_dir
    source_docx = args.docx
    
    # Check if path exists
    if not os.path.exists(path_arg):
        print(f"ERROR: Path not found: {path_arg}")
        sys.exit(1)

    # Check if it is a file or directory
    if os.path.isfile(path_arg):
        # Single file processing
        print("="*80)
        print(f"SINGLE DOCUMENT GENERATION")
        print("="*80)
        print(f"File: {os.path.abspath(path_arg)}")
        if output_dir:
            print(f"Output Directory: {os.path.abspath(output_dir)}")
        if source_docx:
            print(f"Source DOCX: {os.path.abspath(source_docx)}")
        print("="*80)
        
        print("\nInitializing agents...")
        question_agent = QuestionAgent()
        doc_generator = DocumentGenerator()
        if output_dir:
            doc_generator.output_dir = output_dir # Override output dir
        
        process_file(path_arg, question_agent, doc_generator, source_docx)
        
    else:
        # Directory processing
        if output_dir:
             print(f"Output Directory override: {os.path.abspath(output_dir)}")
        
        if source_docx:
            print("WARNING: --docx argument ignored for directory processing. Only supported for single file.")
            
        scan_and_generate(path_arg, output_dir)

def scan_and_generate(folder_path: str, output_dir: str = None):
    """
    Scan folder for debug_questions*.txt files and generate documents.
    
    Args:
        folder_path: Path to folder containing debug files
        output_dir: Optional output directory
    """
    # Validate folder
    if not os.path.exists(folder_path):
        print(f"ERROR: Folder not found: {folder_path}")
        return
    
    if not os.path.isdir(folder_path):
        print(f"ERROR: Not a directory: {folder_path}")
        return
    
    # Find all debug_questions*.txt files
    pattern = os.path.join(folder_path, 'debug_questions*.txt')
    files = []
    
    for file in Path(folder_path).glob('debug_questions*.txt'):
        files.append(str(file))
    
    if not files:
        print(f"No debug_questions*.txt files found in: {folder_path}")
        print(f"Searched for pattern: debug_questions*.txt")
        return
    
    # Sort files for consistent processing
    files.sort()
    
    print("="*80)
    print(f"BATCH DOCUMENT GENERATION")
    print("="*80)
    print(f"Folder: {os.path.abspath(folder_path)}")
    print(f"Files found: {len(files)}")
    if output_dir:
        print(f"Output Directory: {os.path.abspath(output_dir)}")
    print("="*80)
    
    # List files
    print("\nFiles to process:")
    for i, file in enumerate(files, 1):
        print(f"  {i}. {os.path.basename(file)}")
    
    # Initialize
    print("\nInitializing agents...")
    question_agent = QuestionAgent()
    doc_generator = DocumentGenerator()
    if output_dir:
        doc_generator.output_dir = output_dir
    
    # Process each file
    print("\nProcessing files...")
    results = {'success': 0, 'failed': 0}
    
    for file in files:
        success = process_file(file, question_agent, doc_generator)
        if success:
            results['success'] += 1
        else:
            results['failed'] += 1
    
    # Summary
    print("\n" + "="*80)
    print("BATCH GENERATION COMPLETE")
    print("="*80)
    print(f"Total files: {len(files)}")
    print(f"Successful: {results['success']}")
    print(f"Failed: {results['failed']}")
    print("="*80)
    
    save_path = output_dir if output_dir else folder_path
    if results['success'] > 0:
        print(f"\nGenerated files saved to: {os.path.abspath(save_path)}")


if __name__ == '__main__':
    main()

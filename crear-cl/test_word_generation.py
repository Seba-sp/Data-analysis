"""
Test script for new Word and Excel document generation format.
Tests with debug_questions_C001.txt and debug_questions_improved_C001.txt files.
"""
import os
import sys
from agents.agent3_questions import QuestionAgent
from utils.document_generator import DocumentGenerator


def read_debug_file(filepath: str) -> str:
    """Read debug file content."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract raw response (remove header if present)
    if '=== RAW RESPONSE' in content:
        parts = content.split('===', 2)
        if len(parts) >= 3:
            return parts[2].strip()
    
    return content


def test_document_generation():
    """Test Word and Excel generation with debug files."""
    
    print("=" * 80)
    print("TEST: Word and Excel Document Generation")
    print("=" * 80)
    print()
    
    # Initialize
    question_agent = QuestionAgent()
    doc_generator = DocumentGenerator()
    
    # Test files
    test_files = [
        {
            'file': 'debug_questions_C001.txt',
            'article_id': 'C001',
            'is_improved': False
        },
        {
            'file': 'debug_questions_improved_C001.txt',
            'article_id': 'C001',
            'is_improved': True
        }
    ]
    
    for test_case in test_files:
        filepath = test_case['file']
        article_id = test_case['article_id']
        is_improved = test_case['is_improved']
        
        print(f"\n{'='*80}")
        print(f"Testing: {filepath}")
        print(f"Article ID: {article_id}")
        print(f"Improved: {is_improved}")
        print('='*80)
        
        # Check file exists
        if not os.path.exists(filepath):
            print(f"[ERROR] File not found: {filepath}")
            continue
        
        # Read debug file
        print(f"\n[1/5] Reading debug file...")
        raw_response = read_debug_file(filepath)
        print(f"[OK] Read {len(raw_response)} characters")
        
        # Parse with Agent 3's parser
        print(f"\n[2/5] Parsing with Agent 3 parser...")
        parsed_data = question_agent._parse_paes_format(raw_response)
        
        if not parsed_data or 'questions' not in parsed_data:
            print(f"[ERROR] Parsing failed")
            continue
        
        questions_list = parsed_data['questions']
        article_text = parsed_data.get('article_text', '')
        
        print(f"[OK] Parsed {len(questions_list)} questions")
        print(f"[OK] Article text: {len(article_text)} characters")
        
        # Show parse summary
        question_agent._print_parse_summary(questions_list)
        
        # Create mock article dict
        article = {
            'article_id': article_id,
            'title': 'El alma de la máquina',
            'author': 'Baldomero Lillo',
            'source': 'Wikisource',
            'date': '1907',
            'license': 'Dominio Público',
            'url': 'https://es.wikisource.org/wiki/Sub_sole/El_alma_de_la_m%C3%A1quina'
        }
        
        # Prepare questions dict
        questions_dict = {
            'article_text': article_text,
            'questions': questions_list,
            'question_count': len(questions_list)
        }
        
        # Generate Word document
        print(f"\n[3/5] Generating Word document...")
        suffix = '_improved' if is_improved else '_initial'
        word_filename = f"test_output_{article_id}{suffix}.docx"
        
        try:
            word_path = doc_generator.generate_questions_word(
                article=article,
                questions=questions_dict,
                filename=word_filename,
                is_improved=is_improved
            )
            print(f"[OK] Word document created: {word_path}")
            print(f"  Size: {os.path.getsize(word_path):,} bytes")
        except Exception as e:
            print(f"[ERROR] generating Word document: {e}")
            import traceback
            traceback.print_exc()
            continue
        
        # Generate Excel file
        print(f"\n[4/5] Generating Excel file...")
        excel_filename = f"test_output_{article_id}{suffix}.xlsx"
        
        try:
            excel_path = doc_generator.generate_questions_excel(
                questions=questions_dict,
                filename=excel_filename
            )
            print(f"[OK] Excel file created: {excel_path}")
            print(f"  Size: {os.path.getsize(excel_path):,} bytes")
        except Exception as e:
            print(f"[ERROR] generating Excel file: {e}")
            import traceback
            traceback.print_exc()
            continue
        
        # Summary
        print(f"\n[5/5] Summary for {filepath}")
        print(f"  Article Text: {len(article_text)} characters")
        print(f"  Questions: {len(questions_list)} total")
        
        # Count complete questions
        complete = sum(1 for q in questions_list 
                      if q.get('question') and q.get('alternatives') 
                      and q.get('clave') and q.get('justification'))
        print(f"  Complete: {complete}/{len(questions_list)}")
        
        # Check Excel columns
        import pandas as pd
        df = pd.read_excel(excel_path)
        print(f"\n  Excel columns: {list(df.columns)}")
        print(f"  Excel rows: {len(df)}")
        print(f"\n  First 3 rows preview:")
        print(df[['Número de pregunta', 'Clave', 'Habilidad', 'Tarea lectora']].head(3).to_string(index=False))
        
        if complete == len(questions_list):
            print(f"\n[SUCCESS] All questions complete!")
        else:
            print(f"\n[WARNING] {len(questions_list) - complete} incomplete questions")
    
    print(f"\n{'='*80}")
    print("TEST COMPLETE")
    print(f"{'='*80}")


if __name__ == '__main__':
    test_document_generation()

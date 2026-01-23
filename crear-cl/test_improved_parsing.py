"""
Test script to validate parsing of improved questions from debug files.
Focuses on files that had issues (C015, C018, C022).
"""
import os
from agents.agent3_questions import QuestionAgent
from utils.document_generator import DocumentGenerator

def test_improved_parsing():
    """Test parsing of improved questions."""
    
    print("="*70)
    print("IMPROVED QUESTIONS PARSING TEST")
    print("="*70)
    
    # Test problematic files
    test_files = [
        'debug_questions_improved_C010.txt',
        'debug_questions_improved_C011.txt',
        'debug_questions_improved_C012.txt',
        'debug_questions_improved_C003.txt',
        'debug_questions_improved_C007.txt',
            ]
    
    # Initialize components
    agent = QuestionAgent()
    doc_gen = DocumentGenerator()
    
    for debug_file in test_files:
        if not os.path.exists(debug_file):
            print(f"\n[Test] SKIP: {debug_file} not found")
            continue
        
        print(f"\n{'='*70}")
        print(f"Testing: {debug_file}")
        print(f"{'='*70}")
        
        article_id = debug_file.replace('debug_questions_improved_', '').replace('.txt', '')
        
        # Read raw response
        with open(debug_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Skip header
        if '=== RAW RESPONSE FROM AGENT 3 (IMPROVED) ===' in content:
            content = content.split('=== RAW RESPONSE FROM AGENT 3 (IMPROVED) ===')[1].strip()
        
        print(f"\n[Test] Read {len(content)} characters")
        
        # Parse using Agent 3's parser
        print(f"[Test] Parsing with Agent 3 parser...")
        parsed_result = agent._parse_paes_format(content)
        
        article_text = parsed_result.get('article_text', '')
        questions = parsed_result.get('questions', [])
        
        print(f"[Test] Article text: {len(article_text)} chars")
        print(f"[Test] Parsed questions: {len(questions)}")
        
        # Print parse summary
        agent._print_parse_summary(questions)
        
        # Show detailed info for incomplete questions
        for q in questions:
            has_question = bool(q.get('question'))
            has_4_alts = len(q.get('alternatives', {})) == 4
            has_clave = bool(q.get('clave'))
            has_just = bool(q.get('justification'))
            
            if not (has_question and has_4_alts and has_clave and has_just):
                print(f"\n[Test] INCOMPLETE Q{q.get('number', '?')}:")
                print(f"  - Question text: {'YES' if has_question else 'NO'} - {q.get('question', 'MISSING')[:60]}")
                print(f"  - Alternatives: {len(q.get('alternatives', {}))}/4 - {list(q.get('alternatives', {}).keys())}")
                print(f"  - Clave: {'YES' if has_clave else 'NO'} - {q.get('clave', 'MISSING')}")
                print(f"  - Justification: {'YES' if has_just else 'NO'} - {q.get('justification', 'MISSING')[:60]}")
        
        # Count complete
        complete = sum(1 for q in questions 
                      if q.get('question') and len(q.get('alternatives', {})) == 4 
                      and q.get('clave') and q.get('justification'))
        
        if article_text and complete == 10:
            print(f"\n[Test] SUCCESS for {article_id}: {complete}/10 questions complete, article text extracted")
        else:
            print(f"\n[Test] ISSUE for {article_id}:")
            if not article_text:
                print(f"  - Missing article text")
            if complete < 10:
                print(f"  - Only {complete}/10 complete questions")
        
        # Generate Word document to verify
        article = {
            'article_id': article_id,
            'title': f'Test Improved {article_id}',
            'author': 'Test',
            'source': 'Test',
            'date': '2026',
            'license': 'CC-BY',
            'url': 'https://test.com'
        }
        
        questions_dict = {
            'article_text': article_text,
            'questions': questions,
            'question_count': len(questions)
        }
        
        output_file = f"questions_improved_{article_id}.docx"
        doc_gen.generate_questions_word(article, questions_dict, output_file, is_improved=True)
        print(f"[Test] Generated: {output_file}")
    
    print(f"\n{'='*70}")
    print("TEST COMPLETE")
    print(f"{'='*70}")
    print("\nOpen generated files to verify:")
    for f in test_files:
        aid = f.replace('debug_questions_improved_', '').replace('.txt', '')
        print(f"  - questions_improved_{aid}.docx")

if __name__ == '__main__':
    test_improved_parsing()

"""
Test script to validate Word document generation from debug files.
Reads raw model responses from debug_questions_*.txt files and generates Word documents.
"""
import os
import glob
from agents.agent3_questions import QuestionAgent
from utils.document_generator import DocumentGenerator

def test_word_generation():
    """Test Word document generation from debug files."""
    
    print("="*70)
    print("WORD DOCUMENT GENERATION TEST")
    print("="*70)
    
    # Find all debug files
    debug_files = sorted(glob.glob("debug_questions_*.txt"))
    
    if not debug_files:
        print("\n❌ No debug files found!")
        print("Expected files like: debug_questions_C001.txt")
        return
    
    print(f"\nFound {len(debug_files)} debug file(s):")
    for f in debug_files:
        print(f"  - {f}")
    
    # Initialize components
    agent = QuestionAgent()
    doc_gen = DocumentGenerator()
    
    # Process each debug file
    for debug_file in debug_files:
        print(f"\n{'='*70}")
        print(f"Processing: {debug_file}")
        print(f"{'='*70}")
        
        # Extract article ID from filename (e.g., C001 from debug_questions_C001.txt)
        article_id = debug_file.replace('debug_questions_', '').replace('.txt', '')
        
        # Read raw response
        try:
            with open(debug_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Skip header if present
            if '=== RAW RESPONSE FROM AGENT 3 ===' in content:
                content = content.split('=== RAW RESPONSE FROM AGENT 3 ===')[1].strip()
            
            print(f"\n[Test] Read {len(content)} characters from {debug_file}")
            
            # Parse using Agent 3's parser
            print(f"[Test] Parsing with Agent 3 parser...")
            parsed_result = agent._parse_paes_format(content)
            
            article_text = parsed_result.get('article_text', '')
            questions = parsed_result.get('questions', [])
            
            print(f"[Test] Extracted article text: {len(article_text)} chars")
            print(f"[Test] Parsed {len(questions)} questions")
            
            # Print parse summary
            agent._print_parse_summary(questions)
            
            # Create mock article data
            article = {
                'article_id': article_id,
                'title': f'Test Article {article_id}',
                'author': 'Test Author',
                'source': 'Test Source',
                'date': '2026',
                'license': 'CC-BY',
                'license_type': 'CC-BY',
                'url': 'https://example.com/test'
            }
            
            # Create questions dict with article_text
            questions_dict = {
                'article_id': article_id,
                'raw_response': content,
                'article_text': article_text,
                'questions': questions,
                'question_count': len(questions)
            }
            
            # Generate Word document
            output_filename = f"test_output_{article_id}.docx"
            print(f"\n[Test] Generating Word document: {output_filename}")
            
            doc_path = doc_gen.generate_questions_word(
                article=article,
                questions=questions_dict,
                filename=output_filename,
                is_improved=False
            )
            
            print(f"[Test] OK Word document created: {doc_path}")
            
            # Verification checks
            print(f"\n[Test] VERIFICATION:")
            print(f"  > Article text included: {'YES' if article_text else 'NO (WARNING!)'}")
            print(f"  > Questions parsed: {len(questions)}/10")
            
            # Check question completeness
            complete_count = 0
            for q in questions:
                has_question = bool(q.get('question'))
                has_4_alts = len(q.get('alternatives', {})) == 4
                has_clave = bool(q.get('clave'))
                has_just = bool(q.get('justification'))
                
                if has_question and has_4_alts and has_clave and has_just:
                    complete_count += 1
            
            print(f"  > Complete questions: {complete_count}/10")
            
            if article_text and complete_count == 10:
                print(f"\n[Test] SUCCESS - Document should be complete!")
            else:
                print(f"\n[Test] WARNING - Document may be incomplete:")
                if not article_text:
                    print(f"    - Missing article text")
                if complete_count < 10:
                    print(f"    - Only {complete_count}/10 complete questions")
            
            print(f"\n[Test] OPEN THIS FILE TO VERIFY:")
            print(f"    {output_filename}")
            print(f"\n[Test] CHECK FOR:")
            print(f"    1. Article text at the beginning")
            print(f"    2. Page break after article text")
            print(f"    3. All 10 questions with:")
            print(f"       - Question number and text")
            print(f"       - Habilidad label [xxx-x]")
            print(f"       - All 4 alternatives (A-D)")
            print(f"       - Correct answer highlighted (green, bold)")
            print(f"       - Justification with microevidencia")
            
        except Exception as e:
            print(f"\n[Test] ERROR processing {debug_file}:")
            print(f"    {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*70}")
    print("TEST COMPLETE")
    print(f"{'='*70}")
    print(f"\nGenerated {len(debug_files)} Word document(s):")
    for debug_file in debug_files:
        article_id = debug_file.replace('debug_questions_', '').replace('.txt', '')
        print(f"  - test_output_{article_id}.docx")
    
    print(f"\nNext steps:")
    print(f"  1. Open the generated Word documents")
    print(f"  2. Verify article text is at the beginning")
    print(f"  3. Verify all questions are complete")
    print(f"  4. Check for NO red/orange warnings")

if __name__ == '__main__':
    test_word_generation()

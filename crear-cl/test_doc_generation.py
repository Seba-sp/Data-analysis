"""
Test document generation to verify Word and Excel files are created.
"""
import sys
import os

from utils.document_generator import DocumentGenerator

def test_document_generation():
    """Test Word and Excel generation."""
    
    # Mock data
    article_id = "TEST01"
    title = "Test Article Title"
    docx_path = r"C:\Users\Seba\Downloads\M30M\Data-analysis\crear-cl\data\Textos MJ\C001.docx"
    
    # Mock questions (simplified)
    questions = {
        'article_id': article_id,
        'questions': [
            {
                'question': 'Test question 1?',
                'alternatives': ['A) Option A', 'B) Option B', 'C) Option C', 'D) Option D'],
                'clave': 'A',
                'justification': 'Test justification for question 1.',
                'habilidad': 'a'
            },
            {
                'question': 'Test question 2?',
                'alternatives': ['A) Option A', 'B) Option B', 'C) Option C', 'D) Option D'],
                'clave': 'B',
                'justification': 'Test justification for question 2.',
                'habilidad': 'b'
            }
        ]
    }
    
    print("="*70)
    print("Testing Document Generation")
    print("="*70)
    print()
    
    try:
        doc_gen = DocumentGenerator()
        print(f"[Test] Output directory: {doc_gen.output_dir}")
        print()
        
        # Test 1: Generate merged Word document
        print("[Test 1] Generating merged Word document...")
        word_path = doc_gen.merge_text_and_questions_docx(
            source_docx_path=docx_path,
            questions=questions,
            output_path=f"./data/test_questions_{article_id}.docx",
            title=title
        )
        
        if os.path.exists(word_path):
            size_kb = os.path.getsize(word_path) / 1024
            print(f"[Test 1] SUCCESS - Word file created!")
            print(f"  Path: {word_path}")
            print(f"  Size: {size_kb:.2f} KB")
        else:
            print(f"[Test 1] FAIL - File not found: {word_path}")
            return False
        
        print()
        
        # Test 2: Generate Excel document
        print("[Test 2] Generating Excel document...")
        excel_path = doc_gen.generate_questions_excel(
            questions,
            f"test_questions_{article_id}.xlsx"
        )
        
        if os.path.exists(excel_path):
            size_kb = os.path.getsize(excel_path) / 1024
            print(f"[Test 2] SUCCESS - Excel file created!")
            print(f"  Path: {excel_path}")
            print(f"  Size: {size_kb:.2f} KB")
        else:
            print(f"[Test 2] FAIL - File not found: {excel_path}")
            return False
        
        print()
        print("="*70)
        print("ALL TESTS PASSED!")
        print("="*70)
        print()
        print("Generated files:")
        print(f"  - {word_path}")
        print(f"  - {excel_path}")
        
        return True
        
    except Exception as e:
        print()
        print("="*70)
        print("TEST FAILED")
        print("="*70)
        print(f"Error: {e}")
        print()
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_document_generation()
    sys.exit(0 if success else 1)

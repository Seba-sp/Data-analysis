"""
Test the merge_text_and_questions_docx function.
"""
import sys
import os

from utils.document_generator import doc_generator

def test_merge():
    """Test merging DOCX with questions."""
    
    source_docx = r"C:\Users\Seba\Downloads\M30M\Data-analysis\crear-cl\data\Textos MJ\C001.docx"
    
    questions = {
        'article_id': 'C001',
        'questions': [
            {
                'question': '¿Cuál es la pregunta de prueba?',
                'alternatives': {
                    'A': 'Esta es la opción A completa.',
                    'B': 'Esta es la opción B completa.',
                    'C': 'Esta es la opción C completa.',
                    'D': 'Esta es la opción D completa.'
                },
                'clave': 'A'
            }
        ]
    }
    
    output_path = "./data/test_merge_C001.docx"
    title = "Test Article Title"
    
    print("="*70)
    print("Testing DOCX Merge")
    print("="*70)
    print(f"Source: {source_docx}")
    print(f"Output: {output_path}")
    print()
    
    try:
        result = doc_generator.merge_text_and_questions_docx(
            source_docx_path=source_docx,
            questions=questions,
            output_path=output_path,
            title=title
        )
        
        if os.path.exists(result):
            size = os.path.getsize(result) / 1024
            print(f"\n[SUCCESS] File created: {result}")
            print(f"Size: {size:.2f} KB")
            return True
        else:
            print(f"\n[FAIL] File not found: {result}")
            return False
            
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_merge()
    sys.exit(0 if success else 1)

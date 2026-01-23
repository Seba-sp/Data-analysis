"""
Test Agent 4 in isolation to see what's failing.
"""
import sys
import os

from agents.agent4_review import ReviewAgent

def test_agent4():
    """Test Agent 4 review."""
    
    article = {
        'article_id': 'C002',
        'title': 'SHEGO - No lo volveré a hacer',
        'docx_path': r'C:\Users\Seba\Downloads\M30M\Data-analysis\crear-cl\data\Textos MJ\C002.docx'
    }
    
    # Mock questions result from Agent 3
    questions = {
        'article_id': 'C002',
        'raw_response': """A) Cuadro resumen
- LECTURA C002

B) PREGUNTAS (1-10)

1. Test question?
A) Option A
B) Option B
C) Option C
D) Option D

Respuesta correcta A
""",
        'questions': [{'question': 'Test question?', 'clave': 'A'}]
    }
    
    print("="*70)
    print("Testing Agent 4 Review")
    print("="*70)
    
    try:
        print("[Test] Creating Agent 4...")
        r_agent = ReviewAgent()
        
        print("[Test] Starting review...")
        feedback = r_agent.review_questions(article, questions)
        
        print("[Test] SUCCESS!")
        print(f"  Nota: {feedback.get('nota_global', 'N/A')}/10")
        print(f"  Veredicto: {feedback.get('veredicto', 'N/A')}")
        print()
        return True
        
    except Exception as e:
        print()
        print("="*70)
        print("ERROR IN AGENT 4")
        print("="*70)
        print(f"Error: {e}")
        print()
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_agent4()
    sys.exit(0 if success else 1)

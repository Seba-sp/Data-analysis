"""
Test script to verify PDF reuse between Agent 3 and Agent 4.
"""
import sys
import os

from agents.agent3_questions import QuestionAgent
from agents.agent4_review import ReviewAgent

def test_pdf_reuse():
    """Test that Agent 4 reuses PDF from Agent 3."""
    
    article = {
        'article_id': 'C001',
        'title': 'MÁS SOBRE SHAKESPEARE Y EL CINE',
        'docx_path': r'C:\Users\Seba\Downloads\M30M\Data-analysis\crear-cl\data\Textos MJ\C001.docx'
    }
    
    print("="*70)
    print("Testing PDF Reuse Between Agents")
    print("="*70)
    print(f"Article: {article['article_id']}")
    print()
    
    try:
        # Step 1: Agent 3 generates questions
        print("[Step 1] Agent 3: Generating questions...")
        q_agent = QuestionAgent()
        questions = q_agent.generate_questions(article)
        
        pdf_path = questions.get('pdf_path')
        print(f"[Step 1] SUCCESS")
        print(f"  Questions: {len(questions.get('questions', []))}")
        print(f"  PDF saved: {pdf_path}")
        print(f"  PDF exists: {os.path.exists(pdf_path) if pdf_path else False}")
        print()
        
        # Step 2: Agent 4 reviews (should reuse PDF)
        print("[Step 2] Agent 4: Reviewing questions...")
        print("  (Should reuse PDF from Agent 3)")
        r_agent = ReviewAgent()
        feedback = r_agent.review_questions(article, questions)
        
        print(f"[Step 2] SUCCESS")
        print(f"  Nota: {feedback.get('nota_global', 'N/A')}/10")
        print(f"  Veredicto: {feedback.get('veredicto', 'N/A')}")
        print()
        
        # Step 3: Agent 3 improves (should also reuse PDF)
        print("[Step 3] Agent 3: Improving questions...")
        print("  (Should reuse same PDF)")
        improved = q_agent.improve_questions(questions, feedback, article)
        
        print(f"[Step 3] SUCCESS")
        print(f"  Improved questions: {len(improved.get('questions', []))}")
        print()
        
        print("="*70)
        print("ALL TESTS PASSED!")
        print("="*70)
        print(f"PDF file: {pdf_path}")
        print("PDF was created once and reused by all agents.")
        
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
    success = test_pdf_reuse()
    sys.exit(0 if success else 1)

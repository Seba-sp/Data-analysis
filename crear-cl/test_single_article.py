"""
Test script to process a single article and see detailed error output.
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.agent3_questions import QuestionAgent
from agents.agent4_review import ReviewAgent
from utils.document_generator import DocumentGenerator

def test_single_article():
    """Test processing a single article."""
    
    # Test article
    article = {
        'article_id': 'C001',
        'title': 'MÁS SOBRE SHAKESPEARE Y EL CINE',
        'author': 'María José Suárez',
        'type': 'Argumentativo',
        'docx_path': r'C:\Users\Seba\Downloads\M30M\Data-analysis\crear-cl\data\Textos MJ\C001.docx'
    }
    
    print("="*70)
    print("Testing Single Article Processing")
    print("="*70)
    print(f"Article: {article['article_id']} - {article['title']}")
    print()
    
    try:
        # Step 1: Generate questions
        print("[Step 1] Creating Agent 3...")
        q_agent = QuestionAgent()
        
        print("[Step 1] Generating questions...")
        questions = q_agent.generate_questions(article)
        print(f"[Step 1] SUCCESS - Generated {len(questions.get('questions', []))} questions")
        print()
        
        # Step 2: Review questions
        print("[Step 2] Creating Agent 4...")
        r_agent = ReviewAgent()
        
        print("[Step 2] Reviewing questions...")
        feedback = r_agent.review_questions(article, questions)
        print(f"[Step 2] SUCCESS - Review complete")
        print(f"[Step 2] Nota: {feedback.get('nota_global', 'N/A')}/10")
        print()
        
        # Step 3: Improve questions
        print("[Step 3] Improving questions...")
        improved = q_agent.improve_questions(questions, feedback, article)
        print(f"[Step 3] SUCCESS - Improved {len(improved.get('questions', []))} questions")
        print()
        
        # Step 4: Generate documents
        print("[Step 4] Generating documents...")
        doc_gen = DocumentGenerator()
        
        # Generate Word document
        word_path = doc_gen.merge_text_and_questions_docx(
            source_docx_path=article['docx_path'],
            questions=improved,
            output_path=f"./data/test_output_{article['article_id']}.docx",
            title=article['title']
        )
        print(f"[Step 4] SUCCESS - Word document: {word_path}")
        
        # Generate Excel
        excel_path = doc_gen.generate_questions_excel(
            improved,
            f"test_output_{article['article_id']}.xlsx"
        )
        print(f"[Step 4] SUCCESS - Excel document: {excel_path}")
        print()
        
        print("="*70)
        print("ALL STEPS COMPLETED SUCCESSFULLY!")
        print("="*70)
        
        return True
        
    except Exception as e:
        print()
        print("="*70)
        print("ERROR ENCOUNTERED")
        print("="*70)
        print(f"Error: {e}")
        print()
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_single_article()
    sys.exit(0 if success else 1)

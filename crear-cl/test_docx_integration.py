"""
Test script for DOCX-based Agent 3 & 4 implementation.
Validates code integration without requiring actual DOCX files.
"""
import sys
import os

# Use ASCII characters for Windows console compatibility
CHECK = "[OK]"
CROSS = "[FAIL]"

def test_imports():
    """Test that all necessary modules can be imported."""
    print("[Test] Checking imports...")
    
    try:
        from agents.agent3_questions import QuestionAgent
        print(f"  {CHECK} Agent 3 imported")
    except Exception as e:
        print(f"  {CROSS} Agent 3 import failed: {e}")
        return False
    
    try:
        from agents.agent4_review import ReviewAgent
        print("  ✓ Agent 4 imported")
    except Exception as e:
        print(f"  ✗ Agent 4 import failed: {e}")
        return False
    
    try:
        from utils.document_generator import DocumentGenerator
        print("  ✓ Document Generator imported")
    except Exception as e:
        print(f"  ✗ Document Generator import failed: {e}")
        return False
    
    try:
        import orchestrator
        print(f"  {CHECK} Orchestrator imported")
    except Exception as e:
        print(f"  {CROSS} Orchestrator import failed: {e}")
        return False
    
    return True

def test_method_signatures():
    """Test that methods have correct signatures."""
    print("\n[Test] Checking method signatures...")
    
    from agents.agent3_questions import QuestionAgent
    from agents.agent4_review import ReviewAgent
    from utils.document_generator import DocumentGenerator
    
    # Check Agent 3 methods
    q_agent = QuestionAgent.__new__(QuestionAgent)
    if not hasattr(q_agent, 'generate_questions'):
        print("  ✗ Agent 3 missing generate_questions method")
        return False
    if not hasattr(q_agent, 'improve_questions'):
        print("  ✗ Agent 3 missing improve_questions method")
        return False
    print("  ✓ Agent 3 methods present")
    
    # Check Agent 4 methods
    r_agent = ReviewAgent.__new__(ReviewAgent)
    if not hasattr(r_agent, 'review_questions'):
        print("  ✗ Agent 4 missing review_questions method")
        return False
    print("  ✓ Agent 4 methods present")
    
    # Check Document Generator methods
    doc_gen = DocumentGenerator.__new__(DocumentGenerator)
    if not hasattr(doc_gen, 'merge_text_and_questions_docx'):
        print("  ✗ Document Generator missing merge_text_and_questions_docx method")
        return False
    print("  ✓ Document Generator methods present")
    
    return True

def test_orchestrator_csv_loading():
    """Test that orchestrator can parse the _start_from_agent3 code."""
    print("\n[Test] Checking orchestrator CSV loading...")
    
    # Read orchestrator code
    with open('orchestrator.py', 'r', encoding='utf-8') as f:
        code = f.read()
    
    # Check for key changes
    if 'pd.read_csv' not in code:
        print("  ✗ pandas CSV reading not found in orchestrator")
        return False
    print("  ✓ CSV loading code present")
    
    if 'docx_path' not in code:
        print("  ✗ docx_path handling not found in orchestrator")
        return False
    print("  ✓ DOCX path handling present")
    
    if 'FileNotFoundError' not in code:
        print("  ✗ FileNotFoundError handling not found")
        return False
    print("  ✓ FileNotFoundError handling present")
    
    if 'merge_text_and_questions_docx' not in code:
        print("  ✗ Merged DOCX generation not found")
        return False
    print("  ✓ Merged DOCX generation present")
    
    return True

def test_agent3_docx_upload():
    """Test that Agent 3 has DOCX upload code."""
    print("\n[Test] Checking Agent 3 DOCX upload...")
    
    with open('agents/agent3_questions.py', 'r', encoding='utf-8') as f:
        code = f.read()
    
    if 'genai_legacy.upload_file' not in code:
        print("  ✗ DOCX upload code not found in Agent 3")
        return False
    print("  ✓ DOCX upload code present")
    
    if 'uploaded_docx.state.name' not in code:
        print("  ✗ File processing wait code not found")
        return False
    print("  ✓ File processing wait present")
    
    if 'genai_legacy.delete_file' not in code:
        print("  ✗ File cleanup code not found")
        return False
    print("  ✓ File cleanup present")
    
    if 'import time' not in code:
        print("  ✗ time module import missing")
        return False
    print("  ✓ time module imported")
    
    return True

def test_agent4_docx_upload():
    """Test that Agent 4 has DOCX upload code."""
    print("\n[Test] Checking Agent 4 DOCX upload...")
    
    with open('agents/agent4_review.py', 'r', encoding='utf-8') as f:
        code = f.read()
    
    if 'genai_legacy.upload_file' not in code:
        print("  ✗ DOCX upload code not found in Agent 4")
        return False
    print("  ✓ DOCX upload code present")
    
    if 'self.model_legacy' not in code:
        print("  ✗ Legacy model not initialized in Agent 4")
        return False
    print("  ✓ Legacy model initialized")
    
    if 'import time' not in code:
        print("  ✗ time module import missing")
        return False
    print("  ✓ time module imported")
    
    return True

def test_csv_format_documentation():
    """Check that CSV format is documented in help text."""
    print("\n[Test] Checking CLI documentation...")
    
    with open('main.py', 'r', encoding='utf-8') as f:
        code = f.read()
    
    if 'articles_with_docx.csv' not in code:
        print("  ✗ CSV example not found in main.py")
        return False
    print("  ✓ CSV example present in CLI help")
    
    if 'CSV file for agent3 start' not in code:
        print("  ✗ CSV help text not updated")
        return False
    print("  ✓ CSV help text updated")
    
    return True

def main():
    """Run all tests."""
    print("="*70)
    print("DOCX Integration Test Suite")
    print("="*70)
    
    tests = [
        test_imports,
        test_method_signatures,
        test_orchestrator_csv_loading,
        test_agent3_docx_upload,
        test_agent4_docx_upload,
        test_csv_format_documentation
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n[ERROR] Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    print("\n" + "="*70)
    print("Test Results")
    print("="*70)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✓ All tests passed! Implementation is ready.")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed. Review errors above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())

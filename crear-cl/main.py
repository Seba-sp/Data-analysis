"""
PAES Question Generation Pipeline
Multi-agent system for generating educational questions from news articles.

Main entry point for the pipeline with flexible start modes and configuration.
"""
import argparse
import sys
import os

from config import config
from orchestrator import orchestrator
from agents.agent4_standalone import StandaloneReviewAgent
import re


def validate_config() -> bool:
    """
    Validate configuration before running pipeline.
    
    Returns:
        True if config is valid, False otherwise
    """
    errors = []
    
    # Check Gemini API key
    if not config.GEMINI_API_KEY:
        errors.append("GEMINI_API_KEY not set in .env file")
    
    # Check Google Drive credentials
    if not os.path.exists(config.GOOGLE_DRIVE_CREDENTIALS):
        errors.append(f"Google Drive credentials not found: {config.GOOGLE_DRIVE_CREDENTIALS}")
    
    # Check data directory
    if not os.path.exists(config.BASE_DATA_PATH):
        print(f"[Config] Creating data directory: {config.BASE_DATA_PATH}")
        os.makedirs(config.BASE_DATA_PATH, exist_ok=True)
    
    # Check PDF context directory
    if not os.path.exists(config.AGENT3_CONTEXT_DIR):
        print(f"[Config] WARNING: PDF context directory not found: {config.AGENT3_CONTEXT_DIR}")
        print(f"[Config] Agent 3 will run without reference documents")
    
    # Check Agent 1 mode
    if config.AGENT1_MODE not in ['agent', 'model']:
        errors.append(f"AGENT1_MODE must be 'agent' or 'model', got: {config.AGENT1_MODE}")
    
    # Print errors
    if errors:
        print("\n" + "="*70)
        print("CONFIGURATION ERRORS")
        print("="*70)
        for error in errors:
            print(f"  [X] {error}")
        print("="*70 + "\n")
        return False
    
    # Print success
    print("\n" + "="*70)
    print("CONFIGURATION VALID")
    print("="*70)
    print(f"  [OK] Gemini API Key: Configured")
    print(f"  [OK] Google Drive Credentials: {config.GOOGLE_DRIVE_CREDENTIALS}")
    print(f"  [OK] Data Directory: {config.BASE_DATA_PATH}")
    print(f"  [OK] Agent 1 Mode: {config.AGENT1_MODE}")
    print(f"  [OK] Model: {config.GEMINI_MODEL_AGENTS234}")
    
    # Show PDF context status
    pdf_count = 0
    if os.path.exists(config.AGENT3_CONTEXT_DIR):
        pdf_files = [f for f in os.listdir(config.AGENT3_CONTEXT_DIR) if f.endswith('.pdf')]
        pdf_count = len(pdf_files)
    
    if pdf_count > 0:
        print(f"  [OK] PDF Context: {pdf_count} reference documents")
    else:
        print(f"  [WARNING] PDF Context: None (Agent 3 will use Google Search)")
    
    print("="*70 + "\n")
    return True


def test_mode(args):
    """Run single batch test mode."""
    print("\n" + "="*70)
    print("TEST MODE - Single Batch")
    print("="*70 + "\n")
    
    orchestrator.run_pipeline(
        num_batches=1,
        topic=args.topic,
        count=args.count,
        agent1_mode=args.agent1_mode,
        start_from=args.start_from,
        tsv_file=args.tsv_file,
        candidatos_file=args.candidatos_file,
        reverse=args.reverse
    )


def batch_mode(args):
    """Run multiple batch production mode."""
    print("\n" + "="*70)
    print(f"PRODUCTION MODE - {args.batches} Batches")
    print("="*70 + "\n")
    
    orchestrator.run_pipeline(
        num_batches=args.batches,
        topic=args.topic,
        count=args.count,
        agent1_mode=args.agent1_mode,
        start_from=args.start_from,
        tsv_file=args.tsv_file,
        candidatos_file=args.candidatos_file,
        reverse=args.reverse
    )


def review_standalone_mode(args):
    """Run standalone Agent 4 review on local files."""
    if not args.folder:
        print("[Error] --folder argument is required for standalone review mode")
        sys.exit(1)
        
    folder_path = args.folder
    if not os.path.exists(folder_path):
        print(f"[Error] Folder not found: {folder_path}")
        sys.exit(1)
        
    print("\n" + "="*70)
    print(f"STANDALONE REVIEW MODE - Folder: {folder_path}")
    print("="*70 + "\n")
    
    # Initialize Agent
    agent = StandaloneReviewAgent()
    
    # Scan for files
    excel_files = [f for f in os.listdir(folder_path) if f.endswith('-Preguntas Datos.xlsx')]
    
    if not excel_files:
        print(f"[Warning] No matching Excel files found in {folder_path}")
        print("Expected format: {id}-Preguntas Datos.xlsx")
        return
        
    print(f"Found {len(excel_files)} articles to review")
    
    for xlsx_file in excel_files:
        try:
            # Extract ID
            # Format: "{id}-Preguntas Datos.xlsx"
            match = re.match(r'^(.*)-Preguntas Datos\.xlsx$', xlsx_file)
            if not match:
                continue
                
            article_id = match.group(1)
            print(f"\nProcessing Article ID: {article_id}")
            
            # Run review
            agent.review_standalone(folder_path, article_id)
            
        except Exception as e:
            print(f"[Error] Failed to review {xlsx_file}: {e}")
            import traceback
            traceback.print_exc()


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description='PAES Question Generation Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test mode (1 batch, 30 candidates)
  python main.py --test-mode
  
  # Production mode (5 batches)
  python main.py --batches 5
  
  # Custom topic and count
  python main.py --batches 3 --topic "inteligencia artificial" --count 30
  
  # Start from Agent 2 (skip research)
  python main.py --start-from agent2 --tsv-file data/candidatos_20260110.tsv
  
  # Start from Agent 3 (skip research and validation) - with CSV file containing DOCX paths
  python main.py --start-from agent3 --tsv-file data/articles_with_docx.csv
  
  # Parallel processing - Terminal 1 (from top)
  python main.py --start-from agent3 --batches 1 --tsv-file data/agent2_mj.csv
  
  # Parallel processing - Terminal 2 (from bottom)
  python main.py --start-from agent3 --batches 1 --tsv-file data/agent2_mj.csv --reverse
  
  # Validate configuration only
  python main.py --validate-only
  
  # Override Agent 1 mode
  python main.py --batches 2 --agent1-mode model
  
  # Standalone Review Mode
  python main.py --review-standalone --folder "data/my_questions"
        """
    )
    
    # Mode selection
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        '--test-mode',
        action='store_true',
        help='Run single batch test (30 candidates)'
    )
    mode_group.add_argument(
        '--batches',
        type=int,
        metavar='N',
        help='Number of batches to process (production mode)'
    )
    mode_group.add_argument(
        '--validate-only',
        action='store_true',
        help='Validate configuration and exit'
    )
    mode_group.add_argument(
        '--review-standalone',
        action='store_true',
        help='Run standalone Agent 4 review on local files'
    )
    
    # Pipeline parameters
    parser.add_argument(
        '--topic',
        type=str,
        help='Research topic filter (default: diversidad temática)'
    )
    parser.add_argument(
        '--count',
        type=int,
        default=30,
        help='Candidates per batch (default: 30 for PAES 10-10-10)'
    )
    parser.add_argument(
        '--agent1-mode',
        choices=['agent', 'model'],
        help='Override Agent 1 mode: agent (Deep Research, 4-5 min) or model (Fast, 30-60s)'
    )
    
    # Start mode options
    parser.add_argument(
        '--start-from',
        choices=['agent1', 'agent2', 'agent3'],
        default='agent1',
        help='Pipeline start point (default: agent1)'
    )
    parser.add_argument(
        '--tsv-file',
        type=str,
        help='CSV file for agent3 start (with Docx_Path column), or TSV file for agent2 start'
    )
    parser.add_argument(
        '--candidatos-file',
        type=str,
        help='Optional candidatos TSV file (for backward compatibility with old audit files when starting from agent3)'
    )
    parser.add_argument(
        '--reverse',
        action='store_true',
        help='Process articles in reverse order (bottom to top) - useful for parallel processing'
    )
    parser.add_argument(
        '--folder',
        type=str,
        help='Input folder for standalone review mode'
    )
    
    args = parser.parse_args()
    
    # Validate configuration first
    if not validate_config():
        print("[Error] Fix configuration errors before running pipeline")
        sys.exit(1)
    
    # Validate-only mode
    if args.validate_only:
        print("[Success] Configuration is valid")
        sys.exit(0)
    
    # Validate start mode requirements
    if args.start_from == 'agent3' and not args.tsv_file:
        print("\n[Error] --tsv-file is required when starting from agent3")
        print("Example:")
        print("  python main.py --start-from agent3 --tsv-file data/articles_with_docx.csv")
        if args.candidatos_file:
            print("\nNote: --candidatos-file is optional (only for old audit files)")
        sys.exit(1)
    
    # Run appropriate mode
    try:
        if args.test_mode:
            test_mode(args)
        elif args.batches:
            batch_mode(args)
        elif args.review_standalone:
            review_standalone_mode(args)
        else:
            # No mode specified, show help
            parser.print_help()
            sys.exit(0)
    
    except KeyboardInterrupt:
        print("\n\n[Info] Pipeline interrupted by user (Ctrl+C)")
        print("[Info] Progress has been saved to state file")
        sys.exit(0)
    
    except Exception as e:
        print(f"\n[Error] Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

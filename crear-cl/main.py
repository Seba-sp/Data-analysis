"""
PAES Question Generation Pipeline
Multi-agent system for generating educational questions from news articles.

Main entry point for the pipeline with flexible start modes and configuration.
"""
import argparse
import sys
import os

from config import config
# from orchestrator import orchestrator # Imported inside functions to avoid early initialization
# from agents.agent4_standalone import StandaloneReviewAgent # Imported inside function
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


def batch_mode(args):
    """Run multiple batch production mode."""
    print("\n" + "="*70)
    print(f"PRODUCTION MODE - {args.batches} Batches")
    print("="*70 + "\n")
    
    from orchestrator import orchestrator
    orchestrator.run_pipeline(
        num_batches=args.batches,
        topic=args.topic,
        count=args.count,
        agent1_mode=args.agent1_mode,
        start_from=args.start_from,
        tsv_file=args.tsv_file,
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
    from agents.agent4_standalone import StandaloneReviewAgent
    agent = StandaloneReviewAgent()
    
    # Scan for files
    # Robust discovery regex: ID + separator + Preguntas + separator + Datos + .xlsx
    # Captures ID in group 1
    discovery_pattern = re.compile(r"^(.*?)[\s\-_]*preguntas[\s\-_]*datos\.xlsx$", re.IGNORECASE)
    
    excel_files = []
    file_to_id_map = {}
    
    for f in os.listdir(folder_path):
        match = discovery_pattern.match(f)
        if match:
            excel_files.append(f)
            file_to_id_map[f] = match.group(1)
    
    if not excel_files:
        print(f"[Warning] No matching Excel files found in {folder_path}")
        print("Expected format: {id} Preguntas Datos.xlsx (case insensitive, flexible separators)")
        return
        
    print(f"Found {len(excel_files)} articles to review")
    
    skipped_sets = []
    
    for xlsx_file in excel_files:
        try:
            # Extract ID using the map
            article_id = file_to_id_map[xlsx_file]
            
            print(f"\nProcessing Article ID: {article_id}")
            
            # Run review
            result = agent.review_standalone(folder_path, article_id)
            
            # Check if skipped
            if result and result.get('feedback', '').startswith('Skipped:'):
                skipped_sets.append(article_id)
            
        except Exception as e:
            print(f"[Error] Failed to review {xlsx_file}: {e}")
            import traceback
            traceback.print_exc()

    # Save skipped sets to file
    if skipped_sets:
        skipped_file = os.path.join(folder_path, "textos incompletos - no revisados.txt")
        try:
            with open(skipped_file, 'w', encoding='utf-8') as f:
                f.write("=== TEXTOS OMITIDOS (columna acción incompleta) ===\n")
                for item in skipped_sets:
                    f.write(f"- {item}\n")
            print(f"\n[Info] Saved list of {len(skipped_sets)} skipped texts to: {skipped_file}")
        except Exception as e:
            print(f"[Error] Failed to save skipped list: {e}")


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description='PAES Question Generation Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
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

  # Batch from debug TXT + DOCX
  python main.py --batch-debug --txt-folder "data/debug_txt" --docx-folder "data/source_docx"
        """
    )
    
    # Mode selection
    mode_group = parser.add_mutually_exclusive_group()
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
    mode_group.add_argument(
        '--batch-debug',
        action='store_true',
        help='Generate Word/Excel from debug TXT + DOCX folders'
    )
    mode_group.add_argument(
        '--single-debug',
        action='store_true',
        help='Generate Word/Excel from one debug TXT + one DOCX file'
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
        '--reverse',
        action='store_true',
        help='Process articles in reverse order (bottom to top) - useful for parallel processing'
    )
    parser.add_argument(
        '--folder',
        type=str,
        help='Input folder for standalone review mode'
    )
    parser.add_argument(
        '--txt-folder',
        type=str,
        help='Folder containing debug_questions_improved_{id}.txt files'
    )
    parser.add_argument(
        '--docx-folder',
        type=str,
        help='Folder containing {id}.docx source files'
    )
    parser.add_argument(
        '--output-folder',
        type=str,
        help='Optional output folder for generated documents (defaults to DOCX folder)'
    )
    parser.add_argument(
        '--txt-file',
        type=str,
        help='Debug TXT file: debug_questions_improved_{id}.txt'
    )
    parser.add_argument(
        '--docx-file',
        type=str,
        help='Source DOCX file: {id}.docx'
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
        sys.exit(1)
    
    # Run appropriate mode
    try:
        # Check if we should run pipeline mode
        should_run_pipeline = False
        
        if args.batches:
            should_run_pipeline = True
        elif args.start_from in ['agent2', 'agent3']:
            # Implicitly run pipeline (1 batch) if starting from agent2/3
            # But only if we have the required file
            if args.tsv_file:
                args.batches = 1
                should_run_pipeline = True
        
        if should_run_pipeline:
            batch_mode(args)
        elif args.batch_debug:
            if not args.txt_folder or not args.docx_folder:
                print("\n[Error] --txt-folder and --docx-folder are required for --batch-debug")
                sys.exit(1)
            from batch_generate_documents import run_batch_from_debug
            run_batch_from_debug(args.txt_folder, args.docx_folder, args.output_folder)
        elif args.single_debug:
            if not args.txt_file or not args.docx_file:
                print("\n[Error] --txt-file and --docx-file are required for --single-debug")
                sys.exit(1)
            from batch_generate_documents import run_single_from_debug
            ok = run_single_from_debug(args.txt_file, args.docx_file, args.output_folder)
            if not ok:
                sys.exit(1)
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

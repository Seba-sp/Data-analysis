"""
Main CLI entry point for the Generador de Guías Escolares system.
"""

import argparse
import sys
from storage import StorageClient
from config import ensure_directories, SUBJECT_FOLDERS, INPUT_DIR
from question_processor import QuestionProcessor
from excel_processor import ExcelProcessor
from master_consolidator import MasterConsolidator

def process_single_set(base_filename: str, subject: str, storage: StorageClient) -> bool:
    """
    Process a single set of Word and Excel files with the same base name.
    
    Args:
        base_filename: Base filename (without extension) for both Word and Excel files
        subject: Subject area
        storage: Storage client
        
    Returns:
        True if successful, False otherwise
    """
    # Construct full paths using INPUT_DIR from config
    docx_path = INPUT_DIR / f"{base_filename}.docx"
    excel_path = INPUT_DIR / f"{base_filename}.xlsx"
    
    print(f"\n{'='*60}")
    print(f"Processing set: {base_filename}")
    print(f"Subject: {subject}")
    print(f"Input directory: {INPUT_DIR}")
    print(f"Files: {docx_path.name} + {excel_path.name}")
    print(f"{'='*60}")
    
    # Check if files exist
    if not storage.exists(str(docx_path)):
        print(f"Error: Word document not found: {docx_path}")
        return False
    
    if not storage.exists(str(excel_path)):
        print(f"Error: Excel file not found: {excel_path}")
        return False
    
    try:
        # Initialize processors
        question_processor = QuestionProcessor(storage)
        excel_processor = ExcelProcessor(storage)
        
        # Step 1: Process Excel file and generate PreguntaIDs
        print("\n1. Processing Excel file and generating PreguntaIDs...")
        df = excel_processor.read_excel_metadata(str(excel_path))
        
        if df.empty:
            print("Error: Could not read Excel file")
            return False
        
        print(f"   Found {len(df)} questions in Excel")
        
        # Validate Excel structure
        issues = excel_processor.validate_excel_structure(df)
        
        # Check for critical errors (invalid values) - these should stop processing
        if issues['invalid_values']:
            print("   [ERROR] CRITICAL ERROR: Invalid values found in Excel:")
            for issue in issues['invalid_values']:
                print(f"     {issue}")
            print(f"\n[STOP] Processing stopped. Fix invalid values before continuing.")
            return False
        
        # Check for warnings (missing columns, empty values) - these should continue
        if issues['missing_columns']:
            print("   [WARNING] Excel has missing columns:")
            for issue in issues['missing_columns']:
                print(f"     {issue}")
            print("   Continuing with processing...")
        
        if issues['empty_values']:
            print("   [WARNING] Excel has empty values:")
            for issue in issues['empty_values']:
                print(f"     {issue}")
            print("   Continuing with processing...")
        
        # Generate PreguntaIDs
        df = excel_processor.generate_pregunta_ids(df)
        print(f"   Generated PreguntaIDs for {len(df)} questions")
        
        # Step 2: Process Word document
        print("\n2. Processing Word document...")
        page_docs = question_processor.split_document_by_pages(str(docx_path))
        
        if not page_docs:
            print("Error: Could not split Word document into pages")
            return False
        
        print(f"   Split Word document into {len(page_docs)} pages")
        
        # CRITICAL VALIDATION: Check if Excel and Word have matching number of questions
        excel_questions = len(df)
        word_questions = len(page_docs)
        
        if excel_questions != word_questions:
            print(f"\n[ERROR] CRITICAL ERROR: Mismatch detected!")
            print(f"   Excel has {excel_questions} questions")
            print(f"   Word has {word_questions} questions")
            print(f"   These numbers must match for processing to continue.")
            print(f"\n[STOP] Processing stopped. No files will be saved.")
            return False
        
        print(f"   [OK] Validation passed: {excel_questions} questions in both Excel and Word")
        
        # Step 3: Create individual question files
        print("\n3. Creating individual question files...")
        processing_results = question_processor.process_word_document(str(docx_path), df.to_dict('records'), subject)
        
        successful_files = [r for r in processing_results if r['success']]
        failed_files = [r for r in processing_results if not r['success']]
        
        print(f"   Successfully created {len(successful_files)} question files")
        if failed_files:
            print(f"   Failed to create {len(failed_files)} files:")
            for failed in failed_files:
                print(f"     {failed['pregunta_id']}: {failed.get('error', 'Unknown error')}")
            
            # CRITICAL VALIDATION: Stop if any files failed to create
            if len(failed_files) > 0:
                print(f"\n[ERROR] CRITICAL ERROR: {len(failed_files)} files failed to create!")
                print(f"[STOP] Processing stopped. No files will be saved.")
                return False
        
        # Step 4: Update Excel with file paths
        print("\n4. Updating Excel with file paths...")
        df = excel_processor.add_file_paths(df, processing_results, subject)
        
        # Step 5: Save updated Excel
        print("\n5. Saving updated Excel...")
        output_path = excel_processor.save_updated_excel(df, str(excel_path), subject)
        
        if output_path:
            print(f"   Updated Excel saved to: {output_path}")
        else:
            print("   Error: Could not save updated Excel")
            return False
        
        print(f"\n[SUCCESS] Set processing completed successfully!")
        print(f"   Individual files: {len(successful_files)}")
        print(f"   Updated Excel: {output_path}")
        
        return True
        
    except Exception as e:
        print(f"Error processing set: {e}")
        return False

def consolidate_subject(subject: str, storage: StorageClient) -> bool:
    """
    Consolidate all Excel files for a subject into a master file.
    
    Args:
        subject: Subject area
        storage: Storage client
        
    Returns:
        True if successful, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"Consolidating {subject} Excel files...")
    print(f"{'='*60}")
    
    try:
        consolidator = MasterConsolidator(storage)
        
        # Consolidate and save
        df, output_path = consolidator.consolidate_and_save(subject)
        
        if df.empty:
            print(f"No data found for {subject}")
            return False
        
        # Get summary
        summary = consolidator.get_consolidation_summary(df, subject)
        print(f"\n Consolidation Summary for {subject}:")
        print(f"   Total questions: {summary['total_questions']}")
        print(f"   Source files: {len(summary.get('source_files', {}))}")
        print(f"   Areas: {list(summary.get('areas', {}).keys())}")
        print(f"   Difficulties: {summary.get('difficulties', {})}")
        
        # Validate data
        issues = consolidator.validate_consolidated_data(df)
        if any(issues.values()):
            print(f"\n  Validation issues found:")
            for issue_type, issue_list in issues.items():
                if issue_list:
                    print(f"   {issue_type}: {issue_list}")
        
        print(f"\n[SUCCESS] Master Excel saved: {output_path}")
        return True
        
    except Exception as e:
        print(f"Error consolidating {subject}: {e}")
        return False

def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Generador de Guías Escolares - M30M",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a single set (looks for test_base.docx and test_base.xlsx in input/ directory)
  python main.py process-set test_base --subject F30M
  
  # Process another set
  python main.py process-set ensayo_fisica --subject F30M
  
  # Consolidate all Excel files for a subject
  python main.py consolidate --subject F30M
  
  # Consolidate all subjects
  python main.py consolidate --all-subjects
  
  # Initialize directories
  python main.py init
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Process single set command
    process_parser = subparsers.add_parser('process-set', help='Process a single Word/Excel set')
    process_parser.add_argument('base_filename', help='Base filename (without extension) for both Word and Excel files')
    process_parser.add_argument('--subject', required=True, choices=list(SUBJECT_FOLDERS.keys()),
                               help='Subject area')
    
    # Consolidate command
    consolidate_parser = subparsers.add_parser('consolidate', help='Consolidate Excel files')
    consolidate_parser.add_argument('--subject', choices=list(SUBJECT_FOLDERS.keys()),
                                   help='Subject to consolidate')
    consolidate_parser.add_argument('--all-subjects', action='store_true',
                                   help='Consolidate all subjects')
    
    # Init command
    init_parser = subparsers.add_parser('init', help='Initialize project directories')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize storage
    storage = StorageClient()
    
    # Ensure directories exist
    ensure_directories()
    
    if args.command == 'init':
        print("[SUCCESS] Project directories initialized successfully!")
        return
    
    elif args.command == 'process-set':
        success = process_single_set(args.base_filename, args.subject, storage)
        sys.exit(0 if success else 1)
    
    elif args.command == 'consolidate':
        if args.all_subjects:
            print("Consolidating all subjects...")
            consolidator = MasterConsolidator(storage)
            results = consolidator.consolidate_all_subjects()
            
            if results:
                print(f"\n[SUCCESS] Successfully consolidated {len(results)} subjects")
                for subject, (df, output_path) in results.items():
                    print(f"   {subject}: {len(df)} questions -> {output_path}")
            else:
                print("No subjects to consolidate")
                sys.exit(1)
        else:
            if not args.subject:
                print("Error: --subject is required when not using --all-subjects")
                sys.exit(1)
            
            success = consolidate_subject(args.subject, storage)
            sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

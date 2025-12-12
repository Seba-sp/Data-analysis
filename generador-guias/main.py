"""
Main CLI entry point for the Generador de Guías Escolares system.
"""

import argparse
import sys
from pathlib import Path
from storage import StorageClient
from config import ensure_directories, SUBJECT_FOLDERS, INPUT_DIR, EXCELS_ACTUALIZADOS_DIR
from question_processor import QuestionProcessor
from excel_processor import ExcelProcessor
from master_consolidator import MasterConsolidator

def get_available_subjects(storage: StorageClient) -> list:
    """
    Get list of available subject folders in input directory.
    
    Returns:
        List of subject folder names
    """
    subjects = []
    for subject in SUBJECT_FOLDERS.keys():
        subject_path = INPUT_DIR / subject
        if storage.exists(str(subject_path)):
            subjects.append(subject)
    return subjects

def get_file_pairs_in_subject(subject: str, storage: StorageClient) -> list:
    """
    Get list of matching Word/Excel file pairs in a subject folder.
    
    Args:
        subject: Subject folder name
        storage: Storage client
        
    Returns:
        List of tuples: (base_filename, docx_path, xlsx_path)
    """
    subject_path = INPUT_DIR / subject
    
    if not storage.exists(str(subject_path)):
        return []
    
    # Get all .docx and .xlsx files
    try:
        all_files = storage.list_files(str(subject_path))
    except:
        return []
    
    # Extract just the filename from full path (for local storage) or path (for GCS)
    docx_files = {}
    xlsx_files = {}
    
    for file_path in all_files:
        filename = Path(file_path).name
        if filename.endswith('.docx'):
            docx_files[Path(filename).stem] = filename
        elif filename.endswith('.xlsx'):
            xlsx_files[Path(filename).stem] = filename
    
    # Find matching pairs
    pairs = []
    for base_name in docx_files.keys():
        if base_name in xlsx_files:
            pairs.append((
                base_name,
                str(subject_path / docx_files[base_name]),
                str(subject_path / xlsx_files[base_name])
            ))
    
    return sorted(pairs)

def select_subject_interactive(storage: StorageClient) -> str:
    """
    Interactive menu to select a subject folder.
    
    Returns:
        Selected subject name or None if cancelled
    """
    subjects = get_available_subjects(storage)
    
    if not subjects:
        print("\n[ERROR] No subject folders found in input directory!")
        print(f"Please create folders for subjects in: {INPUT_DIR}")
        print(f"Available subjects: {', '.join(SUBJECT_FOLDERS.keys())}")
        return None
    
    print("\n" + "="*60)
    print("SELECT SUBJECT FOLDER")
    print("="*60)
    
    for idx, subject in enumerate(subjects, 1):
        # Show count of file pairs in each subject
        pairs_count = len(get_file_pairs_in_subject(subject, storage))
        print(f"  [{idx}] {subject} ({pairs_count} file pair{'s' if pairs_count != 1 else ''})")
    
    print(f"  [0] Cancel")
    print("="*60)
    
    while True:
        try:
            choice = input("\nEnter your choice (number): ").strip()
            choice_num = int(choice)
            
            if choice_num == 0:
                print("Cancelled.")
                return None
            
            if 1 <= choice_num <= len(subjects):
                selected = subjects[choice_num - 1]
                print(f"\n✓ Selected: {selected}")
                return selected
            else:
                print(f"Invalid choice. Please enter a number between 0 and {len(subjects)}")
        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\nCancelled.")
            return None

def select_file_pair_interactive(subject: str, storage: StorageClient) -> tuple:
    """
    Interactive menu to select a file pair from a subject folder.
    
    Args:
        subject: Subject folder name
        storage: Storage client
        
    Returns:
        Tuple of (base_filename, docx_path, xlsx_path) or (None, None, None) if cancelled
    """
    pairs = get_file_pairs_in_subject(subject, storage)
    
    if not pairs:
        print(f"\n[ERROR] No matching Word/Excel file pairs found in {INPUT_DIR / subject}")
        print("Make sure you have matching .docx and .xlsx files with the same base name.")
        return None, None, None
    
    print("\n" + "="*60)
    print(f"SELECT FILE PAIR IN {subject}")
    print("="*60)
    
    for idx, (base_name, docx_path, xlsx_path) in enumerate(pairs, 1):
        print(f"  [{idx}] {base_name}")
        print(f"      • {Path(docx_path).name}")
        print(f"      • {Path(xlsx_path).name}")
        print()
    
    print(f"  [0] Go back")
    print("="*60)
    
    while True:
        try:
            choice = input("\nEnter your choice (number): ").strip()
            choice_num = int(choice)
            
            if choice_num == 0:
                print("Going back...")
                return None, None, None
            
            if 1 <= choice_num <= len(pairs):
                selected = pairs[choice_num - 1]
                print(f"\n✓ Selected: {selected[0]}")
                return selected
            else:
                print(f"Invalid choice. Please enter a number between 0 and {len(pairs)}")
        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\nGoing back...")
            return None, None, None

def process_single_set(base_filename: str, subject: str, storage: StorageClient, docx_path: str = None, xlsx_path: str = None) -> bool:
    """
    Process a single set of Word and Excel files with the same base name.
    
    Args:
        base_filename: Base filename (without extension) for both Word and Excel files
        subject: Subject area
        storage: Storage client
        docx_path: Optional full path to Word document (if not provided, uses old structure)
        xlsx_path: Optional full path to Excel file (if not provided, uses old structure)
        
    Returns:
        True if successful, False otherwise
    """
    # Use provided paths or construct using new structure (input/{subject}/)
    if docx_path is None:
        docx_path = INPUT_DIR / subject / f"{base_filename}.docx"
    else:
        docx_path = Path(docx_path)
        
    if xlsx_path is None:
        excel_path = INPUT_DIR / subject / f"{base_filename}.xlsx"
    else:
        excel_path = Path(xlsx_path)
    
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
    
    # Check if this file set has already been processed
    subject_folder = SUBJECT_FOLDERS.get(subject, subject.upper())
    output_dir = EXCELS_ACTUALIZADOS_DIR / subject_folder
    output_filename = f"{base_filename}_actualizado.xlsx"
    output_path = output_dir / output_filename
    
    if storage.exists(str(output_path)):
        print(f"\n{'='*60}")
        print(f"⚠️  FILE ALREADY PROCESSED")
        print(f"{'='*60}")
        print(f"❌ Cannot process this file set because it has already been processed.")
        print(f"\n📁 Processed file exists at:")
        print(f"   {output_path}")
        print(f"\n💡 If you want to reprocess this file:")
        print(f"   1. Delete or rename the existing processed file:")
        print(f"      {output_path}")
        print(f"   2. Run the process-set command again")
        print(f"\n⚠️  Warning: Reprocessing will create new PreguntaIDs and may cause")
        print(f"   duplicates in the master Excel file.")
        print(f"{'='*60}\n")
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

def consolidate_subject(subject: str, storage: StorageClient, full: bool = False) -> bool:
    """
    Consolidate Excel files for a subject into a master file.
    By default, uses incremental consolidation (only new files).
    
    Args:
        subject: Subject area
        storage: Storage client
        full: If True, performs full consolidation (resets master). Default is False (incremental).
        
    Returns:
        True if successful, False otherwise
    """
    consolidation_mode = "Full (reset)" if full else "Incremental (new files only)"
    print(f"\n{'='*60}")
    print(f"Consolidating {subject} Excel files...")
    print(f"Mode: {consolidation_mode}")
    print(f"{'='*60}")
    
    try:
        consolidator = MasterConsolidator(storage)
        
        # Choose consolidation method based on mode
        if full:
            # Full consolidation - resets the master file
            df, output_path = consolidator.consolidate_and_save(subject)
        else:
            # Incremental consolidation - only adds new files
            df, output_path = consolidator.consolidate_and_append_new(subject)
        
        if df.empty:
            if full:
                print(f"No data found for {subject}")
            else:
                print(f"No new data to add for {subject}")
            return False
        
        # Get summary
        summary = consolidator.get_consolidation_summary(df, subject)
        summary_label = "Total questions" if full else "New questions added"
        print(f"\n Consolidation Summary for {subject}:")
        print(f"   {summary_label}: {summary['total_questions']}")
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
  # Interactive mode - select subject and files from menus
  python main.py process-set
  
  # Legacy mode - specify files directly (looks in input/{subject}/ folder)
  python main.py process-set test_base --subject F30M
  
  # Consolidate Excel files for a subject (incremental - only new files)
  python main.py consolidate --subject F30M
  
  # Full consolidation (reset master file)
  python main.py consolidate --subject F30M --full
  
  # Consolidate all subjects (incremental by default)
  python main.py consolidate --all-subjects
  
  # Full consolidation for all subjects
  python main.py consolidate --all-subjects --full
  
  # Initialize directories
  python main.py init

Directory Structure:
  input/
    ├── F30M/          # Physics files
    │   ├── file1.docx
    │   └── file1.xlsx
    ├── M30M/          # Math files
    └── ... (other subjects)
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Process single set command
    process_parser = subparsers.add_parser('process-set', help='Process a single Word/Excel set (interactive mode)')
    process_parser.add_argument('base_filename', nargs='?', help='[OPTIONAL] Base filename (without extension). If not provided, uses interactive mode.')
    process_parser.add_argument('--subject', choices=list(SUBJECT_FOLDERS.keys()),
                               help='[OPTIONAL] Subject area. If not provided, uses interactive mode.')
    
    # Consolidate command
    consolidate_parser = subparsers.add_parser('consolidate', help='Consolidate Excel files (incremental by default)')
    consolidate_parser.add_argument('--subject', choices=list(SUBJECT_FOLDERS.keys()),
                                   help='Subject to consolidate')
    consolidate_parser.add_argument('--all-subjects', action='store_true',
                                   help='Consolidate all subjects')
    consolidate_parser.add_argument('--full', action='store_true',
                                   help='Full consolidation (reset master file). Default is incremental (only new files).')
    
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
        # Interactive mode if no arguments provided
        if not args.base_filename or not args.subject:
            print("\n🎯 INTERACTIVE MODE - Process File Set")
            
            # Step 1: Select subject
            subject = select_subject_interactive(storage)
            if not subject:
                sys.exit(1)
            
            # Step 2: Select file pair
            base_filename, docx_path, xlsx_path = select_file_pair_interactive(subject, storage)
            if not base_filename:
                sys.exit(1)
            
            # Step 3: Process the selected pair
            success = process_single_set(base_filename, subject, storage, docx_path, xlsx_path)
            sys.exit(0 if success else 1)
        else:
            # Legacy mode with arguments
            if not args.subject:
                print("Error: --subject is required when providing base_filename")
                sys.exit(1)
            
        success = process_single_set(args.base_filename, args.subject, storage)
        sys.exit(0 if success else 1)
    
    elif args.command == 'consolidate':
        if args.all_subjects:
            consolidation_mode = "Full (reset)" if args.full else "Incremental (new files only)"
            print(f"Consolidating all subjects...")
            print(f"Mode: {consolidation_mode}")
            consolidator = MasterConsolidator(storage)
            
            if args.full:
                # Full consolidation for all subjects
                results = consolidator.consolidate_all_subjects()
            else:
                # Incremental consolidation for all subjects
                results = consolidator.consolidate_all_subjects_incremental()
            
            if results:
                print(f"\n[SUCCESS] Successfully consolidated {len(results)} subjects")
                for subject, (df, output_path) in results.items():
                    questions_label = "total questions" if args.full else "new questions"
                    print(f"   {subject}: {len(df)} {questions_label} -> {output_path}")
            else:
                print("No subjects to consolidate")
                sys.exit(1)
        else:
            if not args.subject:
                print("Error: --subject is required when not using --all-subjects")
                sys.exit(1)
            
            success = consolidate_subject(args.subject, storage, full=args.full)
            sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

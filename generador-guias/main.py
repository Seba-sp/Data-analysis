"""
Main CLI entry point for the Generador de Guías Escolares system.
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
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
        # Skip temporary files
        if filename.startswith('~$'):
            continue
            
        if filename.lower().endswith('.docx'):
            docx_files[Path(filename).stem] = filename
        elif filename.lower().endswith('.xlsx'):
            xlsx_files[Path(filename).stem] = filename
    
    # Find matching pairs
    pairs = []
    
    # Create lowercase map for xlsx to allow case-insensitive matching
    xlsx_lower = {k.lower(): k for k in xlsx_files.keys()}
    
    for base_name in docx_files.keys():
        if base_name in xlsx_files:
            pairs.append((
                base_name,
                str(subject_path / docx_files[base_name]),
                str(subject_path / xlsx_files[base_name])
            ))
        elif base_name.lower() in xlsx_lower:
            # Case-insensitive match found
            xlsx_real_name = xlsx_files[xlsx_lower[base_name.lower()]]
            pairs.append((
                base_name,
                str(subject_path / docx_files[base_name]),
                str(subject_path / xlsx_real_name)
            ))
    
    return sorted(pairs)

def get_incomplete_sets_in_subject(subject: str, storage: StorageClient) -> list:
    """
    Get list of incomplete file sets (missing docx or xlsx) in a subject folder.
    
    Args:
        subject: Subject folder name
        storage: Storage client
        
    Returns:
        List of tuples: (base_filename, reason)
    """
    subject_path = INPUT_DIR / subject
    
    if not storage.exists(str(subject_path)):
        return []
    
    # Get all .docx and .xlsx files
    try:
        all_files = storage.list_files(str(subject_path))
    except:
        return []
    
    # Extract just the filename from full path
    docx_files = set()
    xlsx_files = set()
    
    for file_path in all_files:
        filename = Path(file_path).name
        # Skip temporary files
        if filename.startswith('~$'):
            continue
            
        if filename.lower().endswith('.docx'):
            docx_files.add(Path(filename).stem)
        elif filename.lower().endswith('.xlsx'):
            xlsx_files.add(Path(filename).stem)
    
    incomplete = []
    
    # Create lowercase sets for case-insensitive checking
    docx_lower = {b.lower() for b in docx_files}
    xlsx_lower = {b.lower() for b in xlsx_files}
    
    # Check docx without xlsx
    for base in docx_files:
        if base not in xlsx_files and base.lower() not in xlsx_lower:
            incomplete.append((base, "Missing .xlsx file"))
            
    # Check xlsx without docx
    for base in xlsx_files:
        if base not in docx_files and base.lower() not in docx_lower:
            incomplete.append((base, "Missing .docx file"))
            
    return sorted(incomplete)

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

def process_single_set(base_filename: str, subject: str, storage: StorageClient, docx_path: str = None, xlsx_path: str = None) -> tuple:
    """
    Process a single set of Word and Excel files with the same base name.
    
    Args:
        base_filename: Base filename (without extension) for both Word and Excel files
        subject: Subject area
        storage: Storage client
        docx_path: Optional full path to Word document (if not provided, uses old structure)
        xlsx_path: Optional full path to Excel file (if not provided, uses old structure)
        
    Returns:
        tuple: (success (bool), message (str))
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
        msg = f"Error: Word document not found: {docx_path}"
        print(msg)
        return False, msg
    
    if not storage.exists(str(excel_path)):
        msg = f"Error: Excel file not found: {excel_path}"
        print(msg)
        return False, msg
    
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
        return False, "File already processed"
    
    try:
        # Initialize processors
        question_processor = QuestionProcessor(storage)
        excel_processor = ExcelProcessor(storage)
        
        # Step 1: Process Excel file and generate PreguntaIDs
        print("\n1. Processing Excel file and generating PreguntaIDs...")
        df = excel_processor.read_excel_metadata(str(excel_path))
        
        if df.empty:
            msg = "Error: Could not read Excel file"
            print(msg)
            return False, msg
        
        print(f"   Found {len(df)} questions in Excel")
        
        # Validate Excel structure
        issues = excel_processor.validate_excel_structure(df)
        
        # Check for critical errors (invalid values or missing columns) - these should stop processing
        if issues['missing_columns']:
            print("   [ERROR] CRITICAL ERROR: Excel is missing required columns:")
            for issue in issues['missing_columns']:
                print(f"     {issue}")
            print(f"\n[STOP] Processing stopped. Add missing columns before continuing.")
            return False, f"Missing columns in Excel: {', '.join(issues['missing_columns'])}"

        if issues['invalid_values']:
            print("   [ERROR] CRITICAL ERROR: Invalid values found in Excel:")
            error_details = []
            for issue in issues['invalid_values']:
                print(f"     {issue}")
                error_details.append(issue)
            print(f"\n[STOP] Processing stopped. Fix invalid values before continuing.")
            return False, f"Invalid values in Excel: {'; '.join(error_details[:3])}..."
        
        # Check for empty values
        # "Instrumento" and "N pregunta instrumento" are STRICTLY REQUIRED (cannot be empty)
        # Other columns generate warnings but allow processing to continue
        if issues['empty_values']:
            critical_empty_cols = ["Instrumento", "N pregunta instrumento"]
            critical_errors = []
            
            for issue in issues['empty_values']:
                for crit_col in critical_empty_cols:
                    if issue.startswith(f"{crit_col}:"):
                        critical_errors.append(issue)
            
            if critical_errors:
                print("   [ERROR] CRITICAL ERROR: Mandatory columns have empty values:")
                for error in critical_errors:
                    print(f"     {error}")
                print(f"\n[STOP] Processing stopped. Fill in missing values for mandatory columns before continuing.")
                return False, f"Empty mandatory values in Excel: {', '.join(critical_errors)}"

            print("   [WARNING] Excel has empty values (non-critical columns):")
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
            msg = "Error: Could not split Word document into pages"
            print(msg)
            return False, msg
        
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
            return False, f"Mismatch: Excel ({excel_questions}) vs Word ({word_questions})"
        
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
                return False, f"Failed to create {len(failed_files)} question files"
        
        # Step 4: Update Excel with file paths
        print("\n4. Updating Excel with file paths...")
        df = excel_processor.add_file_paths(df, processing_results, subject)
        
        # Step 5: Save updated Excel
        print("\n5. Saving updated Excel...")
        output_path = excel_processor.save_updated_excel(df, str(excel_path), subject)
        
        if output_path:
            print(f"   Updated Excel saved to: {output_path}")
        else:
            msg = "Error: Could not save updated Excel"
            print(msg)
            return False, msg
        
        print(f"\n[SUCCESS] Set processing completed successfully!")
        print(f"   Individual files: {len(successful_files)}")
        print(f"   Updated Excel: {output_path}")
        
        return True, "Success"
        
    except Exception as e:
        msg = f"Error processing set: {str(e)}"
        print(msg)
        return False, msg

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

def save_processing_report(subject: str, total: int, processed: int, failed: int, failed_details: list, storage: StorageClient, mode: str, other_incomplete: list = None):
    """Save processing report to a text file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"resultados_procesar_{subject}_{timestamp}.txt"
    report_path = INPUT_DIR / subject / filename
    
    report_content = [
        "="*60,
        f"PROCESSING REPORT - {subject}",
        f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Mode: {mode}",
        "="*60,
        f"Total sets: {total}",
        f"Successfully processed: {processed}",
        f"Failed to process: {failed}",
        "="*60,
        ""
    ]
    
    if failed_details:
        report_content.append("FAILED SETS DETAILS:")
        report_content.append("-" * 56)
        for name, reason in failed_details:
            report_content.append(f"❌ {name}: {reason}")
    else:
        report_content.append("All sets processed successfully!")

    if other_incomplete:
        report_content.append("")
        report_content.append("="*60)
        report_content.append("⚠️  OTHER INCOMPLETE SETS FOUND (Not in procesar.txt)")
        report_content.append("="*60)
        report_content.append(f"Found {len(other_incomplete)} other incomplete sets in the folder:")
        for name, reason in other_incomplete:
            report_content.append(f"   • {name}: {reason}")
        report_content.append("="*60)
        
    try:
        storage.write_bytes(str(report_path), "\n".join(report_content).encode('utf-8'))
        print(f"\n📄 Report saved to: {report_path}")
    except Exception as e:
        print(f"\n[WARNING] Could not save report file: {e}")

def process_multiple_files_from_list(subject: str, storage: StorageClient) -> bool:
    """
    Process multiple file sets listed in 'procesar.txt' file in the subject folder.
    
    Args:
        subject: Subject area
        storage: Storage client
        
    Returns:
        True if at least one file was processed, False otherwise
    """
    list_path = INPUT_DIR / subject / "procesar.txt"
    
    if not storage.exists(str(list_path)):
        print(f"\n[ERROR] List file not found: {list_path}")
        print("Please create a file named 'procesar.txt' in the subject folder with one set name per line.")
        return False
    
    try:
        content = storage.read_text(str(list_path))
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        
        if not lines:
            print(f"\n[WARNING] 'procesar.txt' is empty.")
            return False
        
        print(f"\nFound {len(lines)} sets to process in 'procesar.txt'")
        
        # Get available file pairs to match paths
        available_pairs = get_file_pairs_in_subject(subject, storage)
        # Create a dictionary mapping base_name to (docx_path, xlsx_path)
        pairs_map = {pair[0]: (pair[1], pair[2]) for pair in available_pairs}
        # Create case-insensitive lookup
        pairs_map_lower = {k.lower(): k for k in pairs_map.keys()}
        
        # Get incomplete sets to identify partial matches
        incomplete_sets = dict(get_incomplete_sets_in_subject(subject, storage))
        # Create case-insensitive lookup
        incomplete_sets_lower = {k.lower(): k for k in incomplete_sets.keys()}
        
        processed_count = 0
        failed_count = 0
        missing_count = 0
        
        failed_sets = []  # List to store failed sets info: (name, reason)
        
        for base_name in lines:
            target_name = base_name
            # Try exact match first, then case-insensitive
            if target_name not in pairs_map and target_name.lower() in pairs_map_lower:
                target_name = pairs_map_lower[target_name.lower()]
                
            if target_name in pairs_map:
                docx_path, xlsx_path = pairs_map[target_name]
                success, msg = process_single_set(target_name, subject, storage, docx_path, xlsx_path)
                if success:
                    processed_count += 1
                else:
                    failed_count += 1
                    failed_sets.append((base_name, msg))
            else:
                missing_count += 1
                failed_count += 1 # Count missing as failed for the report
                
                # Check incomplete sets with case-insensitivity
                incomplete_name = base_name
                if incomplete_name not in incomplete_sets and incomplete_name.lower() in incomplete_sets_lower:
                    incomplete_name = incomplete_sets_lower[incomplete_name.lower()]
                
                if incomplete_name in incomplete_sets:
                    reason = incomplete_sets[incomplete_name]
                    print(f"\n[WARNING] Incomplete set: {base_name}" + (f" (found as {incomplete_name})" if base_name != incomplete_name else ""))
                    print(f"Reason: {reason}")
                    failed_sets.append((base_name, reason))
                else:
                    print(f"\n[WARNING] Set not found: {base_name}")
                    print(f"Make sure both {base_name}.docx and {base_name}.xlsx exist in {INPUT_DIR / subject}")
                    failed_sets.append((base_name, "Files not found"))
        
        # Check for other incomplete sets in the folder that were not in the list
        all_incomplete = set(incomplete_sets.keys())
        processed_bases_lower = {b.lower() for b in lines}
        
        other_incomplete = []
        for inc_base in all_incomplete:
            if inc_base.lower() not in processed_bases_lower:
                other_incomplete.append(inc_base)
                
        print(f"\n{'='*60}")
        print(f"Batch Processing Summary for {subject}")
        print(f"{'='*60}")
        print(f"   Total requested: {len(lines)}")
        print(f"   Successfully processed: {processed_count}")
        print(f"   Failed to process: {failed_count}")
        
        if failed_sets:
            print(f"\n   FAILED SETS DETAILS:")
            print(f"   {'-'*56}")
            for name, reason in failed_sets:
                print(f"   ❌ {name}: {reason}")
        
        # Prepare other_incomplete list with reasons for reporting
        other_incomplete_with_reasons = []
        if other_incomplete:
            print(f"\n{'='*60}")
            print(f"⚠️  OTHER INCOMPLETE SETS FOUND (Not in procesar.txt)")
            print(f"{'='*60}")
            print(f"Found {len(other_incomplete)} other incomplete sets in the folder:")
            for name in sorted(other_incomplete):
                reason = incomplete_sets[name]
                print(f"   • {name}: {reason}")
                other_incomplete_with_reasons.append((name, reason))
            print(f"{'='*60}")
        
        print(f"{'='*60}")
        
        # Save report
        save_processing_report(subject, len(lines), processed_count, failed_count, failed_sets, storage, "Batch List (procesar.txt)", other_incomplete_with_reasons)
        
        return processed_count > 0
        
    except Exception as e:
        print(f"Error reading list file: {e}")
        return False

def process_all_in_subject(subject: str, storage: StorageClient) -> bool:
    """
    Process all available file sets in the subject folder.
    
    Args:
        subject: Subject area
        storage: Storage client
        
    Returns:
        True if at least one file was processed, False otherwise
    """
    pairs = get_file_pairs_in_subject(subject, storage)
    
    if not pairs:
        print(f"\n[WARNING] No file pairs found in {subject}")
        return False
    
    print(f"\nFound {len(pairs)} sets to process in {subject}")
    
    processed_count = 0
    failed_count = 0
    failed_sets = [] # List to store failed sets info: (name, reason)
    
    # Process valid pairs
    for base_name, docx_path, xlsx_path in pairs:
        success, msg = process_single_set(base_name, subject, storage, docx_path, xlsx_path)
        if success:
            processed_count += 1
        else:
            failed_count += 1
            failed_sets.append((base_name, msg))
    
    # Check for incomplete sets (orphans)
    incomplete_sets = get_incomplete_sets_in_subject(subject, storage)
    if incomplete_sets:
        for base_name, reason in incomplete_sets:
            failed_count += 1
            failed_sets.append((base_name, reason))
            
    print(f"\n{'='*60}")
    print(f"All Files Processing Summary for {subject}")
    print(f"{'='*60}")
    # Total found is pairs + orphans
    total_found = len(pairs) + len(incomplete_sets)
    print(f"   Total found: {total_found}")
    print(f"   Successfully processed: {processed_count}")
    print(f"   Failed to process: {failed_count}")
    
    if failed_sets:
        print(f"\n   FAILED SETS DETAILS:")
        print(f"   {'-'*56}")
        for name, reason in failed_sets:
            print(f"   ❌ {name}: {reason}")
            
    print(f"{'='*60}")
    
    # Save report
    save_processing_report(subject, total_found, processed_count, failed_count, failed_sets, storage, "All Files in Folder")
    
    return processed_count > 0

def interactive_menu(storage: StorageClient):
    """
    Main interactive menu for the application.
    """
    while True:
        print("\n" + "="*60)
        print("  GENERADOR DE GUÍAS - MAIN MENU")
        print("="*60)
        print("  [1] Process file set (Word + Excel)")
        print("  [2] Consolidate Excel files")
        print("  [3] Exit")
        print("="*60)
        
        try:
            choice = input("\nEnter your choice (number): ").strip()
            
            if choice == '1':
                # Process Set
                subject = select_subject_interactive(storage)
                if not subject:
                    continue
                
                print("\n" + "="*60)
                print(f"PROCESS FILES IN {subject}")
                print("="*60)
                print("  [1] Process single file")
                print("  [2] Process multiple files (from procesar.txt)")
                print("  [3] Process all files in folder")
                print("  [0] Go back")
                print("="*60)
                
                try:
                    mode_choice = input("\nEnter your choice (number): ").strip()
                    
                    if mode_choice == '1':
                        base_filename, docx_path, xlsx_path = select_file_pair_interactive(subject, storage)
                        if not base_filename:
                            continue
                        
                        process_single_set(base_filename, subject, storage, docx_path, xlsx_path)
                        input("\nPress Enter to continue...")
                        
                    elif mode_choice == '2':
                        process_multiple_files_from_list(subject, storage)
                        input("\nPress Enter to continue...")
                        
                    elif mode_choice == '3':
                        process_all_in_subject(subject, storage)
                        input("\nPress Enter to continue...")
                        
                    elif mode_choice == '0':
                        continue
                    else:
                        print("Invalid choice.")
                        
                except ValueError:
                    print("Invalid input.")
                
            elif choice == '2':
                # Consolidate
                subjects = get_available_subjects(storage)
                if not subjects:
                    print("No subjects found.")
                    continue

                while True:
                    print("\n" + "="*60)
                    print("SELECT SUBJECT TO CONSOLIDATE")
                    print("="*60)
                    for idx, subject in enumerate(subjects, 1):
                        print(f"  [{idx}] {subject}")
                    print(f"  [{len(subjects)+1}] ALL SUBJECTS")
                    print(f"  [0] Go back")
                    print("="*60)
                    
                    sub_choice = input("\nEnter your choice (number): ").strip()
                    
                    if sub_choice == '0':
                        break
                        
                    if not sub_choice.isdigit():
                        print("Invalid input. Please enter a number.")
                        continue
                        
                    try:
                        sub_idx = int(sub_choice)
                        if not (1 <= sub_idx <= len(subjects) + 1):
                            print(f"Invalid choice. Please enter a number between 0 and {len(subjects)+1}")
                            continue
                            
                        # Valid selection
                        selected_subject = None
                        is_all = False
                        
                        if sub_idx == len(subjects) + 1:
                            is_all = True
                        else:
                            selected_subject = subjects[sub_idx-1]
                        
                        # Mode selection
                        full = False
                        back_to_subjects = False
                        
                        while True:
                            print("\nConsolidation Mode:")
                            print("  [1] Incremental (Only process new files)")
                            print("  [2] Full (Reset master file and reprocess all)")
                            print("  [0] Go back")
                            
                            mode_choice = input("Enter choice (number): ").strip()
                            
                            if mode_choice == '0':
                                back_to_subjects = True
                                break
                            elif mode_choice == '1':
                                full = False
                                break
                            elif mode_choice == '2':
                                full = True
                                break
                            else:
                                print("Invalid choice. Please enter 1, 2 or 0.")
                        
                        if back_to_subjects:
                            continue
                        
                        if is_all:
                            consolidator = MasterConsolidator(storage)
                            if full:
                                results = consolidator.consolidate_all_subjects()
                            else:
                                results = consolidator.consolidate_all_subjects_incremental()
                                
                            if results:
                                print(f"\n[SUCCESS] Successfully consolidated {len(results)} subjects")
                                for s, (df, path) in results.items():
                                    lbl = "total questions" if full else "new questions"
                                    print(f"   {s}: {len(df)} {lbl} -> {path}")
                            else:
                                print("No subjects to consolidate")
                        else:
                            consolidate_subject(selected_subject, storage, full=full)
                        
                        input("\nPress Enter to continue...")
                        break
                        
                    except ValueError:
                        print("Invalid input. Please enter a number.")
                        
            elif choice == '3':
                print("Exiting...")
                sys.exit(0)
            
            else:
                print("Invalid choice. Please enter 1, 2 or 3.")
                
        except KeyboardInterrupt:
            print("\nCancelled.")
            continue

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
    
    # Initialize storage
    storage = StorageClient()
    
    # Ensure directories exist
    ensure_directories()
    
    if not args.command:
        # Launch main interactive menu
        try:
            interactive_menu(storage)
        except KeyboardInterrupt:
            print("\nCancelled.")
            sys.exit(0)
        return
    
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
            success, _ = process_single_set(base_filename, subject, storage, docx_path, xlsx_path)
            sys.exit(0 if success else 1)
        else:
            # Legacy mode with arguments
            if not args.subject:
                print("Error: --subject is required when providing base_filename")
                sys.exit(1)
            
            success, _ = process_single_set(args.base_filename, args.subject, storage)
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

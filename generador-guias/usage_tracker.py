"""
Usage tracking module for monitoring question usage in generated guides.
"""

import pandas as pd
from datetime import datetime
from typing import List, Dict, Any

from config import USAGE_TRACKING_BASE_COLUMNS, EXCELES_MAESTROS_DIR, get_usage_column_names
from storage import StorageClient


class UsageTracker:
    """Handles tracking of question usage in generated guides."""
    
    def __init__(self, storage_client: StorageClient):
        self.storage = storage_client
    
    def update_question_usage(self, subject: str, question_ids: List[str], guide_name: str) -> bool:
        """
        Update the master Excel file with usage tracking information.
        
        Args:
            subject: Subject area (e.g., 'M30M', 'Ciencias')
            question_ids: List of question IDs that were used
            guide_name: Name of the guide that was generated
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            print(f"DEBUG: Updating usage for subject '{subject}' with {len(question_ids)} questions")
            
            # Determine the master file path
            if subject == "Ciencias":
                # For Ciencias, we need to update all three subject files
                subjects_to_update = ["F30M", "Q30M", "B30M"]
                success_count = 0
                total_subjects = len(subjects_to_update)
                
                for subj in subjects_to_update:
                    print(f"DEBUG: Updating usage for {subj}")
                    if self._update_single_subject_usage(subj, question_ids, guide_name):
                        success_count += 1
                        print(f"DEBUG: Successfully updated {subj}")
                    else:
                        print(f"DEBUG: Failed to update {subj}")
                
                # Return True if at least one subject was updated successfully
                success = success_count > 0
                print(f"DEBUG: Ciencias update result: {success_count}/{total_subjects} subjects updated successfully")
                return success
            else:
                return self._update_single_subject_usage(subject, question_ids, guide_name)
                
        except Exception as e:
            print(f"Error updating question usage: {e}")
            return False
    
    def _update_single_subject_usage(self, subject: str, question_ids: List[str], guide_name: str) -> bool:
        """
        Update usage tracking for a single subject.
        
        Args:
            subject: Subject area
            question_ids: List of question IDs that were used
            guide_name: Name of the guide that was generated
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            # Load the master Excel file
            master_file = EXCELES_MAESTROS_DIR / f"excel_maestro_{subject.lower()}.xlsx"
            
            if not self.storage.exists(str(master_file)):
                print(f"Master file not found: {master_file}")
                return False
            
            # Read the Excel file
            df = pd.read_excel(master_file)
            
            # Ensure usage tracking columns exist
            df = self._ensure_usage_columns(df)
            
            # Get current date
            current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Track which questions were successfully updated
            updated_questions = []
            missing_questions = []
            
            # Update usage for each question
            for question_id in question_ids:
                # Find the row with this question ID
                mask = df['PreguntaID'] == question_id
                if mask.any():
                    row_idx = df[mask].index[0]
                    
                    # Get current usage count
                    current_uses = df.loc[row_idx, 'Número de usos']
                    if pd.isna(current_uses):
                        current_uses = 0
                    else:
                        current_uses = int(current_uses)
                    
                    # Increment usage count
                    new_uses = current_uses + 1
                    df.loc[row_idx, 'Número de usos'] = new_uses
                    
                    # Add new columns for this use if they don't exist
                    guide_name_col, date_col = get_usage_column_names(new_uses)
                    
                    # Ensure the new columns exist in the DataFrame
                    if guide_name_col not in df.columns:
                        df[guide_name_col] = None
                    if date_col not in df.columns:
                        df[date_col] = None
                    
                    # Update the new usage columns
                    df.loc[row_idx, guide_name_col] = guide_name
                    df.loc[row_idx, date_col] = current_date
                    
                    updated_questions.append(question_id)
                else:
                    missing_questions.append(question_id)
                    print(f"WARNING: Question {question_id} not found in {subject} master file")
            
            # Save the updated Excel file
            df.to_excel(master_file, index=False)
            
            # Report results
            if missing_questions:
                print(f"WARNING: {len(missing_questions)} questions not found in {subject}: {missing_questions}")
                print(f"Successfully updated {len(updated_questions)} out of {len(question_ids)} questions in {subject}")
                # Still return True if at least some questions were updated
                return len(updated_questions) > 0
            else:
                print(f"Successfully updated usage tracking for all {len(question_ids)} questions in {subject}")
                return True
            
        except Exception as e:
            print(f"Error updating usage for subject {subject}: {e}")
            return False
    
    def _ensure_usage_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Ensure that base usage tracking columns exist in the DataFrame.
        
        Args:
            df: DataFrame to check and update
            
        Returns:
            DataFrame with base usage tracking columns
        """
        for column in USAGE_TRACKING_BASE_COLUMNS:
            if column not in df.columns:
                df[column] = None
        
        return df
    
    def get_question_usage_stats(self, subject: str) -> Dict[str, Any]:
        """
        Get usage statistics for questions in a subject.
        
        Args:
            subject: Subject area
            
        Returns:
            Dictionary with usage statistics
        """
        try:
            master_file = EXCELES_MAESTROS_DIR / f"excel_maestro_{subject.lower()}.xlsx"
            
            if not self.storage.exists(str(master_file)):
                return {"error": f"Master file not found: {master_file}"}
            
            df = pd.read_excel(master_file)
            
            # Ensure usage tracking columns exist
            df = self._ensure_usage_columns(df)
            
            # Calculate statistics
            total_questions = len(df)
            
            # Fill NaN values with 0 for unused questions
            df['Número de usos'] = df['Número de usos'].fillna(0)
            
            unused_questions = len(df[df['Número de usos'] == 0])
            used_questions = total_questions - unused_questions
            
            # Count questions by usage frequency
            usage_counts = df['Número de usos'].value_counts().sort_index()
            
            return {
                "total_questions": total_questions,
                "unused_questions": unused_questions,
                "used_questions": used_questions,
                "usage_distribution": usage_counts.to_dict(),
                "usage_percentage": (used_questions / total_questions * 100) if total_questions > 0 else 0
            }
            
        except Exception as e:
            return {"error": f"Error getting usage stats: {e}"}
    
    def get_all_guides_for_subject(self, subject: str) -> List[Dict[str, Any]]:
        """
        Get list of all guides created for a subject with their details.
        
        Args:
            subject: Subject area
            
        Returns:
            List of dictionaries with guide information
        """
        try:
            if subject == "Ciencias":
                # For Ciencias, we need to check all three subject files and aggregate properly
                subjects_to_check = ["F30M", "Q30M", "B30M"]
                all_guides = []
                
                for subj in subjects_to_check:
                    guides = self._get_guides_from_single_subject(subj)
                    # Add subject source to each guide
                    for guide in guides:
                        guide['subject_source'] = subj
                    all_guides.extend(guides)
                
                # Create unique guides - each guide should be separate even if they have the same name and date
                # We'll use a combination of name, date, subject_source, and questions to create uniqueness
                unique_guides = {}
                for guide in all_guides:
                    # Create a unique key that includes subject source and questions to distinguish guides
                    # Even if they have the same name and date, they should be separate if they have different questions
                    questions_key = tuple(sorted(guide['questions']))
                    unique_key = (guide['guide_name'], guide['date'], guide['subject_source'], questions_key)
                    
                    if unique_key not in unique_guides:
                        # First time seeing this guide
                        unique_guides[unique_key] = {
                            'guide_name': guide['guide_name'],
                            'date': guide['date'],
                            'question_count': guide['question_count'],
                            'questions': set(guide['questions']),
                            'subject_sources': [guide['subject_source']],
                            'usage_numbers': guide.get('usage_numbers', []),
                            'unique_id': f"{guide['guide_name']}_{guide['date']}_{guide['subject_source']}_{len(guide['questions'])}"
                        }
                    else:
                        # This should rarely happen now, but if it does, merge the data
                        existing = unique_guides[unique_key]
                        existing['questions'].update(guide['questions'])
                        existing['question_count'] = len(existing['questions'])
                        if guide['subject_source'] not in existing['subject_sources']:
                            existing['subject_sources'].append(guide['subject_source'])
                        # Merge usage numbers
                        existing['usage_numbers'].extend(guide.get('usage_numbers', []))
                        existing['usage_numbers'] = sorted(list(set(existing['usage_numbers'])))
                
                # Convert back to list format and add creation order
                final_guides = []
                for guide_data in unique_guides.values():
                    final_guides.append({
                        'guide_name': guide_data['guide_name'],
                        'date': guide_data['date'],
                        'question_count': guide_data['question_count'],
                        'questions': list(guide_data['questions']),
                        'subject_sources': guide_data['subject_sources'],
                        'usage_numbers': guide_data['usage_numbers'],
                        'unique_id': guide_data['unique_id']
                    })
                
                # Sort by date (oldest first) to assign creation order numbers
                sorted_by_creation = sorted(final_guides, key=lambda x: x['date'] if x['date'] else '', reverse=False)
                
                # Add creation order number to each guide
                for i, guide in enumerate(sorted_by_creation, 1):
                    guide['creation_order'] = i
                
                # Now sort by date (newest first) for display
                return sorted(sorted_by_creation, key=lambda x: x['date'] if x['date'] else '', reverse=True)
            else:
                return self._get_guides_from_single_subject(subject)
                
        except Exception as e:
            print(f"Error getting guides for subject {subject}: {e}")
            return []
    
    def _get_guides_from_single_subject(self, subject: str) -> List[Dict[str, Any]]:
        """
        Get guides from a single subject file.
        
        Args:
            subject: Subject area
            
        Returns:
            List of guide dictionaries
        """
        try:
            master_file = EXCELES_MAESTROS_DIR / f"excel_maestro_{subject.lower()}.xlsx"
            
            if not self.storage.exists(str(master_file)):
                return []
            
            df = pd.read_excel(master_file)
            df = self._ensure_usage_columns(df)
            
            # Dictionary to store unique guides with their questions
            unique_guides = {}
            
            # Look through all usage columns to find guides
            # We need to process each usage column separately to avoid mixing different guide instances
            for col in df.columns:
                if col.startswith('Nombre guía (uso '):
                    # Extract usage number
                    usage_num = int(col.split('(')[1].split(')')[0].split()[1])
                    
                    # Get the corresponding date column
                    date_col = f"Fecha descarga (uso {usage_num})"
                    
                    # Get unique guide names from this column
                    guide_names = df[col].dropna().unique()
                    
                    for guide_name in guide_names:
                        if pd.notna(guide_name) and guide_name.strip():
                            # Find questions that used this guide in this specific usage number
                            mask = df[col] == guide_name
                            questions_used = df[mask]['PreguntaID'].tolist()
                            
                            # Get the date for this specific usage
                            date_value = None
                            if date_col in df.columns and mask.any():
                                date_value = df[mask][date_col].iloc[0]
                            
                            # Create a unique key based on guide name and date only
                            # This groups guides with the same name and date together
                            guide_key = (guide_name, date_value)
                            
                            if guide_key not in unique_guides:
                                # First time seeing this guide instance
                                # Find all questions that have this guide name and date in ANY usage column
                                all_questions = set()
                                for usage_col in df.columns:
                                    if usage_col.startswith('Nombre guía (uso '):
                                        usage_date_col = f"Fecha descarga (uso {usage_col.split('(')[1].split(')')[0].split()[1]})"
                                        if usage_date_col in df.columns:
                                            # Find questions that have this guide name and date
                                            guide_mask = (df[usage_col] == guide_name) & (df[usage_date_col] == date_value)
                                            questions_in_this_usage = df[guide_mask]['PreguntaID'].tolist()
                                            all_questions.update(questions_in_this_usage)
                                
                                unique_guides[guide_key] = {
                                    'guide_name': guide_name,
                                    'date': date_value,
                                    'question_count': len(all_questions),
                                    'questions': all_questions,
                                    'usage_numbers': [usage_num]
                                }
                            else:
                                # Guide already exists, just add this usage number if not already present
                                existing_guide = unique_guides[guide_key]
                                if usage_num not in existing_guide['usage_numbers']:
                                    existing_guide['usage_numbers'].append(usage_num)
            
            # Convert sets back to lists and create final guide list
            guides = []
            for guide_data in unique_guides.values():
                guides.append({
                    'guide_name': guide_data['guide_name'],
                    'date': guide_data['date'],
                    'question_count': guide_data['question_count'],
                    'questions': list(guide_data['questions']),
                    'usage_numbers': sorted(guide_data['usage_numbers'])
                })
            
            # Sort by date (oldest first) to assign creation order numbers
            sorted_by_creation = sorted(guides, key=lambda x: x['date'] if x['date'] else '', reverse=False)
            
            # Add creation order number to each guide
            for i, guide in enumerate(sorted_by_creation, 1):
                guide['creation_order'] = i
            
            # Now sort by date (newest first) for display
            return sorted(sorted_by_creation, key=lambda x: x['date'] if x['date'] else '', reverse=True)
            
        except Exception as e:
            print(f"Error getting guides from single subject {subject}: {e}")
            return []
    
    def delete_specific_guide_usage(self, subject: str, guide_name: str, guide_date: str = None, questions: list = None, subject_sources: list = None) -> Dict[str, Any]:
        """
        Delete a specific guide by matching name, date, and optionally questions/subject_sources.
        This is more precise than the regular delete_guide_usage method.
        
        Args:
            subject: Subject area
            guide_name: Name of the guide to delete
            guide_date: Date of the guide (optional, for disambiguation)
            questions: List of question IDs in the guide (optional, for precise matching)
            subject_sources: List of subject sources (optional, for Ciencias guides)
            
        Returns:
            Dictionary with deletion results
        """
        try:
            if subject == "Ciencias":
                # For Ciencias, we need to update all three subject files
                subjects_to_update = ["F30M", "Q30M", "B30M"]
                total_deleted = 0
                results = {}
                
                for subj in subjects_to_update:
                    # Only process this subject if it's in the subject_sources or if no subject_sources specified
                    if subject_sources is None or subj in subject_sources:
                        result = self._delete_specific_guide_from_single_subject(subj, guide_name, guide_date, questions)
                        results[subj] = result
                        if result['success']:
                            total_deleted += result['questions_deleted']
                
                return {
                    'success': any(r['success'] for r in results.values()),
                    'total_questions_deleted': total_deleted,
                    'subject_results': results,
                    'message': f"Deleted specific guide '{guide_name}' from {total_deleted} questions across all Ciencias subjects"
                }
            else:
                return self._delete_specific_guide_from_single_subject(subject, guide_name, guide_date, questions)
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Error deleting specific guide: {e}"
            }

    
    def _delete_specific_guide_from_single_subject(self, subject: str, guide_name: str, guide_date: str = None, questions: list = None) -> Dict[str, Any]:
        """
        Delete a specific guide from a single subject file by matching name, date, and questions.
        This is more precise than the regular deletion method.
        
        Args:
            subject: Subject area
            guide_name: Name of the guide to delete
            guide_date: Date of the guide (optional, for disambiguation)
            questions: List of question IDs in the guide (optional, for precise matching)
            
        Returns:
            Dictionary with deletion results
        """
        try:
            master_file = EXCELES_MAESTROS_DIR / f"excel_maestro_{subject.lower()}.xlsx"
            
            if not self.storage.exists(str(master_file)):
                return {
                    'success': False,
                    'error': f"Master file not found: {master_file}"
                }
            
            # Read the Excel file
            df = pd.read_excel(master_file)
            df = self._ensure_usage_columns(df)
            
            # Find all questions that used this specific guide and track which usage numbers to remove
            questions_to_update = {}  # question_id -> list of usage numbers to remove for this question
            
            print(f"DEBUG: Looking for specific guide '{guide_name}' with date '{guide_date}' and questions {questions} in {subject}")
            
            # Look through all guide name columns
            for col in df.columns:
                if col.startswith('Nombre guía (uso '):
                    usage_num = int(col.split('(')[1].split(')')[0].split()[1])
                    date_col = f"Fecha descarga (uso {usage_num})"
                    
                    # Find rows where this guide was used
                    if guide_date:
                        # Match both guide name and date
                        mask = (df[col] == guide_name) & (df[date_col] == guide_date)
                    else:
                        # Match only guide name
                        mask = df[col] == guide_name
                    
                    if mask.any():
                        # For each question that used this guide, check if it matches our criteria
                        for idx in df[mask].index:
                            question_id = df.loc[idx, 'PreguntaID']
                            
                            # If questions list is provided, only process questions that are in that list
                            if questions is not None and question_id not in questions:
                                continue
                            
                            if question_id not in questions_to_update:
                                questions_to_update[question_id] = []
                            questions_to_update[question_id].append(usage_num)
                            print(f"DEBUG: Question {question_id} used specific guide in usage {usage_num}")
            
            print(f"DEBUG: Total questions to update: {len(questions_to_update)}")
            
            if not questions_to_update:
                return {
                    'success': False,
                    'error': f"Specific guide '{guide_name}' not found in {subject} with the given criteria"
                }
            
            # For each question, remove only the specific usage numbers for this guide
            total_questions_affected = 0
            for question_id, usage_numbers_to_remove in questions_to_update.items():
                self._remove_specific_usage_from_question(df, question_id, usage_numbers_to_remove)
                total_questions_affected += 1
            
            # Save the updated Excel file
            df.to_excel(master_file, index=False)
            
            return {
                'success': True,
                'questions_deleted': total_questions_affected,
                'questions_affected': list(questions_to_update.keys()),
                'message': f"Successfully deleted specific guide '{guide_name}' from {total_questions_affected} questions in {subject}"
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Error deleting specific guide from {subject}: {e}"
            }
    
    def _remove_specific_usage_from_question(self, df: pd.DataFrame, question_id: str, usage_numbers_to_remove: List[int]):
        """
        Remove specific usage numbers from a question and shift other usages down.
        This method is more precise and only removes the exact usage entries specified.
        
        Args:
            df: DataFrame to modify
            question_id: Question ID to update
            usage_numbers_to_remove: List of specific usage numbers to remove for this question
        """
        try:
            # Find the row with this question ID
            mask = df['PreguntaID'] == question_id
            if not mask.any():
                print(f"DEBUG: Question {question_id} not found in DataFrame")
                return
            
            row_idx = df[mask].index[0]
            
            # Get current usage count
            current_uses = df.loc[row_idx, 'Número de usos']
            if pd.isna(current_uses) or current_uses == 0:
                print(f"DEBUG: Question {question_id} has no usage count")
                return
            
            current_uses = int(current_uses)
            print(f"DEBUG: Question {question_id} has {current_uses} uses, removing specific usages: {usage_numbers_to_remove}")
            
            # Create a mapping of old usage numbers to new usage numbers
            # Only shift down the usage numbers that come after the removed ones
            usage_mapping = {}
            new_usage_count = 0
            
            for old_usage in range(1, current_uses + 1):
                if old_usage not in usage_numbers_to_remove:
                    new_usage_count += 1
                    usage_mapping[old_usage] = new_usage_count
            
            print(f"DEBUG: New usage count will be {new_usage_count}, mapping: {usage_mapping}")
            
            # Update the usage count
            df.loc[row_idx, 'Número de usos'] = new_usage_count
            
            # Create new columns with shifted usage numbers
            new_guide_columns = {}
            new_date_columns = {}
            
            for old_usage, new_usage in usage_mapping.items():
                old_guide_col = f"Nombre guía (uso {old_usage})"
                old_date_col = f"Fecha descarga (uso {old_usage})"
                new_guide_col = f"Nombre guía (uso {new_usage})"
                new_date_col = f"Fecha descarga (uso {new_usage})"
                
                if old_guide_col in df.columns:
                    new_guide_columns[new_guide_col] = df.loc[row_idx, old_guide_col]
                if old_date_col in df.columns:
                    new_date_columns[new_date_col] = df.loc[row_idx, old_date_col]
            
            # Clear all old usage columns for this question
            for old_usage in range(1, current_uses + 1):
                old_guide_col = f"Nombre guía (uso {old_usage})"
                old_date_col = f"Fecha descarga (uso {old_usage})"
                
                if old_guide_col in df.columns:
                    df.loc[row_idx, old_guide_col] = None
                if old_date_col in df.columns:
                    df.loc[row_idx, old_date_col] = None
            
            # Set new usage columns with shifted numbers
            for col_name, value in new_guide_columns.items():
                if col_name not in df.columns:
                    df[col_name] = None
                df.loc[row_idx, col_name] = value
            
            for col_name, value in new_date_columns.items():
                if col_name not in df.columns:
                    df[col_name] = None
                df.loc[row_idx, col_name] = value
            
            print(f"DEBUG: Successfully updated question {question_id}")
            
        except Exception as e:
            print(f"Error removing specific usage from question {question_id}: {e}")

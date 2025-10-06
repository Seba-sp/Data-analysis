"""
Usage tracking module for monitoring question usage in generated guides.
"""

import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import os

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
    
    def get_latest_usage_info(self, df: pd.DataFrame, question_id: str) -> Dict[str, Any]:
        """
        Get the latest usage information for a specific question.
        
        Args:
            df: DataFrame containing the question data
            question_id: The question ID to look up
            
        Returns:
            Dictionary with latest usage information
        """
        try:
            # Find the row with this question ID
            mask = df['PreguntaID'] == question_id
            if not mask.any():
                return {"error": "Question not found"}
            
            row_idx = df[mask].index[0]
            usage_count = df.loc[row_idx, 'Número de usos']
            
            if pd.isna(usage_count) or usage_count == 0:
                return {
                    "usage_count": 0,
                    "latest_guide": None,
                    "latest_date": None
                }
            
            usage_count = int(usage_count)
            
            # Get the latest usage information
            guide_name_col, date_col = get_usage_column_names(usage_count)
            
            latest_guide = None
            latest_date = None
            
            if guide_name_col in df.columns:
                latest_guide = df.loc[row_idx, guide_name_col]
            if date_col in df.columns:
                latest_date = df.loc[row_idx, date_col]
            
            return {
                "usage_count": usage_count,
                "latest_guide": latest_guide,
                "latest_date": latest_date
            }
            
        except Exception as e:
            return {"error": f"Error getting latest usage info: {e}"}
    
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
            unused_questions = len(df[df['Número de usos'].isna() | (df['Número de usos'] == 0)])
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
    
    def get_unused_questions(self, subject: str) -> List[str]:
        """
        Get list of unused question IDs for a subject.
        
        Args:
            subject: Subject area
            
        Returns:
            List of unused question IDs
        """
        try:
            master_file = EXCELES_MAESTROS_DIR / f"excel_maestro_{subject.lower()}.xlsx"
            
            if not self.storage.exists(str(master_file)):
                return []
            
            df = pd.read_excel(master_file)
            df = self._ensure_usage_columns(df)
            
            # Get questions with no usage or 0 usage
            unused_mask = df['Número de usos'].isna() | (df['Número de usos'] == 0)
            unused_questions = df[unused_mask]['PreguntaID'].tolist()
            
            return unused_questions
            
        except Exception as e:
            print(f"Error getting unused questions: {e}")
            return []
    
    def get_questions_by_usage_count(self, subject: str, usage_count: int) -> List[str]:
        """
        Get list of question IDs that have been used exactly 'usage_count' times.
        
        Args:
            subject: Subject area
            usage_count: Number of times the question has been used
            
        Returns:
            List of question IDs with the specified usage count
        """
        try:
            master_file = EXCELES_MAESTROS_DIR / f"excel_maestro_{subject.lower()}.xlsx"
            
            if not self.storage.exists(str(master_file)):
                return []
            
            df = pd.read_excel(master_file)
            df = self._ensure_usage_columns(df)
            
            # Get questions with the specified usage count
            usage_mask = df['Número de usos'] == usage_count
            questions = df[usage_mask]['PreguntaID'].tolist()
            
            return questions
            
        except Exception as e:
            print(f"Error getting questions by usage count: {e}")
            return []
    
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
                
                # Aggregate guides with the same name and date across all subjects
                aggregated_guides = {}
                for guide in all_guides:
                    key = (guide['guide_name'], guide['date'])
                    
                    if key not in aggregated_guides:
                        # First time seeing this guide
                        aggregated_guides[key] = {
                            'guide_name': guide['guide_name'],
                            'date': guide['date'],
                            'question_count': guide['question_count'],
                            'questions': set(guide['questions']),
                            'subject_sources': [guide['subject_source']],
                            'usage_numbers': guide.get('usage_numbers', [])
                        }
                    else:
                        # Guide already exists, aggregate the data
                        existing = aggregated_guides[key]
                        existing['questions'].update(guide['questions'])
                        existing['question_count'] = len(existing['questions'])
                        if guide['subject_source'] not in existing['subject_sources']:
                            existing['subject_sources'].append(guide['subject_source'])
                        # Merge usage numbers
                        existing['usage_numbers'].extend(guide.get('usage_numbers', []))
                        existing['usage_numbers'] = sorted(list(set(existing['usage_numbers'])))
                
                # Convert back to list format
                final_guides = []
                for guide_data in aggregated_guides.values():
                    final_guides.append({
                        'guide_name': guide_data['guide_name'],
                        'date': guide_data['date'],
                        'question_count': guide_data['question_count'],
                        'questions': list(guide_data['questions']),
                        'subject_sources': guide_data['subject_sources'],
                        'usage_numbers': guide_data['usage_numbers']
                    })
                
                return sorted(final_guides, key=lambda x: x['date'] if x['date'] else '', reverse=True)
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
            for col in df.columns:
                if col.startswith('Nombre guía (uso '):
                    # Extract usage number
                    usage_num = int(col.split('(')[1].split(')')[0].split()[1])
                    
                    # Get unique guide names from this column
                    guide_names = df[col].dropna().unique()
                    
                    for guide_name in guide_names:
                        if pd.notna(guide_name) and guide_name.strip():
                            # Get the corresponding date column
                            date_col = f"Fecha descarga (uso {usage_num})"
                            
                            # Find questions that used this guide
                            questions_used = df[df[col] == guide_name]['PreguntaID'].tolist()
                            
                            # Get the date (use the first occurrence)
                            date_value = None
                            if date_col in df.columns:
                                date_mask = df[col] == guide_name
                                if date_mask.any():
                                    date_value = df[date_mask][date_col].iloc[0]
                            
                            # Create a unique key for this guide (name + date)
                            guide_key = (guide_name, date_value)
                            
                            if guide_key not in unique_guides:
                                # First time seeing this guide
                                unique_guides[guide_key] = {
                                    'guide_name': guide_name,
                                    'date': date_value,
                                    'question_count': len(questions_used),
                                    'questions': set(questions_used),  # Use set to avoid duplicates
                                    'usage_numbers': [usage_num]
                                }
                            else:
                                # Guide already exists, add questions and usage numbers
                                existing_guide = unique_guides[guide_key]
                                existing_guide['questions'].update(questions_used)
                                existing_guide['question_count'] = len(existing_guide['questions'])
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
            
            # Sort by date (most recent first)
            return sorted(guides, key=lambda x: x['date'] if x['date'] else '', reverse=True)
            
        except Exception as e:
            print(f"Error getting guides from single subject {subject}: {e}")
            return []
    
    def delete_guide_usage(self, subject: str, guide_name: str, guide_date: str = None) -> Dict[str, Any]:
        """
        Delete a guide and un-use all its questions from the Excel files.
        
        Args:
            subject: Subject area
            guide_name: Name of the guide to delete
            guide_date: Date of the guide (optional, for disambiguation)
            
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
                    result = self._delete_guide_from_single_subject(subj, guide_name, guide_date)
                    results[subj] = result
                    if result['success']:
                        total_deleted += result['questions_deleted']
                
                return {
                    'success': any(r['success'] for r in results.values()),
                    'total_questions_deleted': total_deleted,
                    'subject_results': results,
                    'message': f"Deleted guide '{guide_name}' from {total_deleted} questions across all Ciencias subjects"
                }
            else:
                return self._delete_guide_from_single_subject(subject, guide_name, guide_date)
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Error deleting guide: {e}"
            }
    
    def _delete_guide_from_single_subject(self, subject: str, guide_name: str, guide_date: str = None) -> Dict[str, Any]:
        """
        Delete a guide from a single subject file.
        
        Args:
            subject: Subject area
            guide_name: Name of the guide to delete
            guide_date: Date of the guide (optional, for disambiguation)
            
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
            
            # Find all questions that used this guide and collect usage numbers
            questions_to_update = set()
            usage_numbers_to_remove = set()
            
            print(f"DEBUG: Looking for guide '{guide_name}' with date '{guide_date}' in {subject}")
            
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
                        # Add questions that used this guide
                        questions_in_this_usage = df[mask]['PreguntaID'].tolist()
                        questions_to_update.update(questions_in_this_usage)
                        usage_numbers_to_remove.add(usage_num)
                        print(f"DEBUG: Found {len(questions_in_this_usage)} questions in usage {usage_num}")
            
            print(f"DEBUG: Total questions to update: {len(questions_to_update)}")
            print(f"DEBUG: Usage numbers to remove: {usage_numbers_to_remove}")
            
            if not questions_to_update:
                return {
                    'success': False,
                    'error': f"Guide '{guide_name}' not found in {subject}"
                }
            
            # Convert to lists for easier handling
            questions_to_update = list(questions_to_update)
            usage_numbers_to_remove = list(usage_numbers_to_remove)
            
            # For each question, remove the usage and shift other usages down
            for question_id in questions_to_update:
                self._remove_usage_from_question(df, question_id, usage_numbers_to_remove)
            
            # Save the updated Excel file
            df.to_excel(master_file, index=False)
            
            return {
                'success': True,
                'questions_deleted': len(questions_to_update),
                'questions_affected': questions_to_update,
                'message': f"Successfully deleted guide '{guide_name}' from {len(questions_to_update)} questions in {subject}"
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Error deleting guide from {subject}: {e}"
            }
    
    def _remove_usage_from_question(self, df: pd.DataFrame, question_id: str, usage_numbers_to_remove: List[int]):
        """
        Remove specific usage numbers from a question and shift other usages down.
        
        Args:
            df: DataFrame to modify
            question_id: Question ID to update
            usage_numbers_to_remove: List of usage numbers to remove
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
            print(f"DEBUG: Question {question_id} has {current_uses} uses, removing {usage_numbers_to_remove}")
            
            # Create a mapping of old usage numbers to new usage numbers
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
            
            # Remove old usage columns for this question
            for old_usage in range(1, current_uses + 1):
                old_guide_col = f"Nombre guía (uso {old_usage})"
                old_date_col = f"Fecha descarga (uso {old_usage})"
                
                if old_guide_col in df.columns:
                    df.loc[row_idx, old_guide_col] = None
                if old_date_col in df.columns:
                    df.loc[row_idx, old_date_col] = None
            
            # Set new usage columns
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
            print(f"Error removing usage from question {question_id}: {e}")
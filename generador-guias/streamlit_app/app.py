"""
Streamlit web application for generating custom educational guides.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import os
import sys
from io import BytesIO
import shutil
import zipfile
import tempfile

# Add parent directory to path to import our modules
sys.path.append(str(Path(__file__).parent.parent))

from storage import StorageClient
from config import EXCELES_MAESTROS_DIR, SUBJECT_FOLDERS, STREAMLIT_CONFIG, CHART_COLORS, NOMBRES_GUIAS_PATH
from master_consolidator import MasterConsolidator
from usage_tracker import UsageTracker

# Configure Streamlit page
st.set_page_config(
    page_title=STREAMLIT_CONFIG['page_title'],
    page_icon=STREAMLIT_CONFIG['page_icon'],
    layout=STREAMLIT_CONFIG['layout'],
    initial_sidebar_state=STREAMLIT_CONFIG['initial_sidebar_state']
)

# Initialize storage
@st.cache_resource
def get_storage_client():
    return StorageClient()

def add_smooth_scrolling():
    """Add simple smooth scrolling behavior for better UX."""
    st.markdown("""
    <style>
    html {
        scroll-behavior: smooth;
    }
    </style>
    """, unsafe_allow_html=True)

def preserve_scroll_on_rerun():
    """Add JavaScript to preserve scroll position only during reruns."""
    st.markdown("""
    <script>
    // Store scroll position before any rerun
    function storeScrollPosition() {
        sessionStorage.setItem('scrollPosition', window.pageYOffset);
    }
    
    // Restore scroll position after rerun
    function restoreScrollPosition() {
        const scrollPosition = sessionStorage.getItem('scrollPosition');
        if (scrollPosition && scrollPosition !== '0') {
            setTimeout(function() {
                window.scrollTo({
                    top: parseInt(scrollPosition),
                    behavior: 'instant'
                });
            }, 100);
        }
    }
    
    // Store position before any form interaction that might cause rerun
    document.addEventListener('click', function(e) {
        if (e.target.type === 'checkbox' || e.target.tagName === 'SELECT' || e.target.type === 'button') {
            storeScrollPosition();
        }
    });
    
    // Restore position after page load
    window.addEventListener('load', restoreScrollPosition);
    document.addEventListener('DOMContentLoaded', restoreScrollPosition);
    </script>
    """, unsafe_allow_html=True)

def load_allowed_guide_names() -> pd.DataFrame:
    """
    Load allowed guide names from Excel file.
    
    Returns:
        DataFrame with 'Asignatura' and 'nombre guía' columns
    """
    try:
        project_root = Path(__file__).parent.parent
        nombres_path = project_root / NOMBRES_GUIAS_PATH
        
        if not os.path.exists(nombres_path):
            st.warning(f"Archivo de nombres de guías no encontrado: {nombres_path}")
            return pd.DataFrame()
        
        df = pd.read_excel(nombres_path)
        return df
        
    except Exception as e:
        st.error(f"Error cargando nombres de guías: {e}")
        return pd.DataFrame()

def load_master_excel(subject: str) -> pd.DataFrame:
    """
    Load master Excel file for a subject.
    
    Args:
        subject: Subject area
        
    Returns:
        DataFrame with question data
    """
    try:
        storage = get_storage_client()
        consolidator = MasterConsolidator(storage)
        
        # Special handling for Ciencias subject - combine F30M, Q30M, and B30M
        if subject == "Ciencias":
            df = load_ciencias_combined_data(storage, consolidator)
        else:
            # Try to load existing master file
            master_file = EXCELES_MAESTROS_DIR / f"excel_maestro_{subject.lower()}.xlsx"
            
            if storage.exists(str(master_file)):
                df = pd.read_excel(master_file)
            else:
                # If master file doesn't exist, try to consolidate
                st.warning(f"Master file not found for {subject}. Attempting to consolidate...")
                df, _ = consolidator.consolidate_and_save(subject)
        
        # Ensure usage tracking columns exist in the loaded DataFrame
        if not df.empty:
            usage_tracker = UsageTracker(storage)
            df = usage_tracker._ensure_usage_columns(df)
        
        return df
            
    except Exception as e:
        st.error(f"Error loading master Excel for {subject}: {e}")
        return pd.DataFrame()

def load_ciencias_combined_data(storage, consolidator) -> pd.DataFrame:
    """
    Load and combine data from F30M, Q30M, and B30M subjects for Ciencias.
    
    Args:
        storage: Storage client
        consolidator: Master consolidator instance
        
    Returns:
        Combined DataFrame with questions from all three subjects
    """
    try:
        combined_dfs = []
        subjects_to_combine = ["F30M", "Q30M", "B30M"]
        
        for subject in subjects_to_combine:
            try:
                # Try to load existing master file first
                master_file = EXCELES_MAESTROS_DIR / f"excel_maestro_{subject.lower()}.xlsx"
                
                if storage.exists(str(master_file)):
                    df = pd.read_excel(master_file)
                    if not df.empty:
                        # Add a column to identify the source subject
                        df['Subject_Source'] = subject
                        # Ensure usage tracking columns exist
                        usage_tracker = UsageTracker(storage)
                        df = usage_tracker._ensure_usage_columns(df)
                        combined_dfs.append(df)
                        st.info(f"✅ Loaded {len(df)} questions from {subject}")
                else:
                    # If master file doesn't exist, try to consolidate
                    st.warning(f"Master file not found for {subject}. Attempting to consolidate...")
                    df, _ = consolidator.consolidate_and_save(subject)
                    if not df.empty:
                        df['Subject_Source'] = subject
                        # Ensure usage tracking columns exist
                        usage_tracker = UsageTracker(storage)
                        df = usage_tracker._ensure_usage_columns(df)
                        combined_dfs.append(df)
                        st.info(f"✅ Consolidated and loaded {len(df)} questions from {subject}")
                    else:
                        st.warning(f"⚠️ No questions found for {subject}")
                        
            except Exception as e:
                st.error(f"Error loading {subject}: {e}")
                continue
        
        if combined_dfs:
            # Combine all DataFrames
            combined_df = pd.concat(combined_dfs, ignore_index=True)
            st.success(f"🎉 Successfully combined {len(combined_df)} questions from {len(combined_dfs)} subjects")
            return combined_df
        else:
            st.error("❌ No data could be loaded from any of the Ciencias subjects (F30M, Q30M, B30M)")
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Error combining Ciencias data: {e}")
        return pd.DataFrame()


def sort_questions_for_display(df: pd.DataFrame, subject: str) -> pd.DataFrame:
    """
    Sort questions for display by the specified criteria.
    
    Args:
        df: DataFrame with questions
        subject: Current subject (to check if it's Ciencias)
        
    Returns:
        Sorted DataFrame
    """
    try:
        # Create a copy to avoid modifying the original
        sorted_df = df.copy()
        
        # Define the sorting columns based on subject
        if subject == "Ciencias":
            # For Ciencias: subject, area, subtema, habilidad, dificultad
            sort_columns = ['Subject_Source', 'Área temática', 'Conocimiento/Subtema', 'Habilidad', 'Dificultad']
        else:
            # For other subjects: area, subtema, habilidad, dificultad
            sort_columns = ['Área temática', 'Conocimiento/Subtema', 'Habilidad', 'Dificultad']
        
        # Filter out columns that don't exist in the dataframe
        existing_columns = [col for col in sort_columns if col in sorted_df.columns]
        
        if existing_columns:
            # Sort by the existing columns
            sorted_df = sorted_df.sort_values(existing_columns, na_position='last')
        
        return sorted_df
        
    except Exception as e:
        st.error(f"Error sorting questions: {e}")
        return df


def assign_next_position(pregunta_id: str):
    """
    Assign the next available position to a newly selected question.
    
    Args:
        pregunta_id: Question ID to assign position to
    """
    try:
        # Get all current positions
        current_positions = set(st.session_state['question_positions'].values())
        
        # Find the next available position
        next_position = 1
        while next_position in current_positions:
            next_position += 1
        
        # Assign the position
        st.session_state['question_positions'][pregunta_id] = next_position
        
    except Exception as e:
        st.error(f"Error assigning position: {e}")

def remove_question_and_renumber(pregunta_id: str):
    """
    Remove a question and renumber all questions that were after it.
    
    Args:
        pregunta_id: Question ID to remove
    """
    try:
        if pregunta_id in st.session_state['question_positions']:
            removed_position = st.session_state['question_positions'][pregunta_id]
            
            # Remove the question from positions
            del st.session_state['question_positions'][pregunta_id]
            
            # Renumber all questions that were after the removed position
            for qid, position in st.session_state['question_positions'].items():
                if position > removed_position:
                    st.session_state['question_positions'][qid] = position - 1
                    
    except Exception as e:
        st.error(f"Error removing question and renumbering: {e}")

def update_question_position(pregunta_id: str, new_position: int):
    """
    Update a question's position and reorder other questions accordingly.
    
    Args:
        pregunta_id: Question ID to move
        new_position: New position to assign
    """
    try:
        if pregunta_id not in st.session_state['question_positions']:
            return
        
        old_position = st.session_state['question_positions'][pregunta_id]
        
        if old_position == new_position:
            return
        
        # Update the moved question's position
        st.session_state['question_positions'][pregunta_id] = new_position
        
        # Handle other questions based on direction of move
        if new_position > old_position:
            # Moving down: shift questions between old and new position up
            for qid, position in st.session_state['question_positions'].items():
                if qid != pregunta_id and old_position < position <= new_position:
                    st.session_state['question_positions'][qid] = position - 1
        else:
            # Moving up: shift questions between new and old position down
            for qid, position in st.session_state['question_positions'].items():
                if qid != pregunta_id and new_position <= position < old_position:
                    st.session_state['question_positions'][qid] = position + 1
        
        # Update the ordered list based on new positions
        update_ordered_list_from_positions()
        
    except Exception as e:
        st.error(f"Error updating question position: {e}")

def update_ordered_list_from_positions():
    """
    Update the ordered questions list based on current positions.
    """
    try:
        # Sort questions by their positions
        sorted_questions = sorted(
            st.session_state['question_positions'].items(),
            key=lambda x: x[1]
        )
        
        # Update the ordered list
        st.session_state['selected_questions_ordered'] = [qid for qid, _ in sorted_questions]
        
    except Exception as e:
        st.error(f"Error updating ordered list: {e}")

def track_guide_download(subject: str, question_ids: list, guide_name: str, selected_count: int = None):
    """
    Track guide download by updating usage statistics and reloading data.
    This function is called when the download button is clicked.
    
    Args:
        subject: Subject area
        question_ids: List of question IDs that were used
        guide_name: Name of the guide that was downloaded
        selected_count: Total number of selected questions (for consistency)
    """
    try:
        print(f"DEBUG: Starting usage tracking for guide '{guide_name}' with {len(question_ids)} questions")
        print(f"DEBUG: Question IDs: {question_ids}")
        
        # Update usage tracking in master Excel files
        storage = get_storage_client()
        usage_tracker = UsageTracker(storage)
        
        # Update usage tracking for all selected questions
        success = usage_tracker.update_question_usage(
            subject, 
            question_ids, 
            guide_name
        )
        
        print(f"DEBUG: Usage tracking result: {success}")
        
        if success:
            # Immediately reload the data to get updated usage information
            current_subject = st.session_state.get('subject', subject)
            df = load_master_excel(current_subject)
            if not df.empty:
                st.session_state['questions_df'] = df
                st.session_state['download_tracking_success'] = True
                # Use the selected count if provided, otherwise use the question_ids length
                actual_question_count = selected_count if selected_count is not None else len(question_ids)
                st.session_state['download_tracking_message'] = f"✅ Registro de uso actualizado para {actual_question_count} preguntas. Datos recargados."
                print(f"DEBUG: Setting tracking message with {actual_question_count} questions (selected_count: {selected_count}, question_ids length: {len(question_ids)})")
                # Reset guide name selection to default
                st.session_state['guide_name_select'] = ""
                # Force a page refresh to show updated data
                st.session_state['force_refresh'] = True
                print(f"DEBUG: Successfully updated usage tracking and reloaded data")
            else:
                st.session_state['download_tracking_success'] = False
                st.session_state['download_tracking_message'] = "❌ Error al recargar los datos"
                print(f"DEBUG: Failed to reload data after usage tracking")
        else:
            st.session_state['download_tracking_success'] = False
            st.session_state['download_tracking_message'] = "⚠️ Error al actualizar el registro de uso"
            print(f"DEBUG: Usage tracking failed")
            
    except Exception as e:
        st.session_state['download_tracking_success'] = False
        st.session_state['download_tracking_message'] = f"❌ Error al actualizar uso: {e}"
        print(f"DEBUG: Exception in track_guide_download: {e}")

def filter_questions(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """
    Filter questions based on user criteria.
    
    Args:
        df: DataFrame with questions
        filters: Dictionary with filter criteria
        
    Returns:
        Filtered DataFrame
    """
    filtered_df = df.copy()
    
    # Apply filters
    if filters.get('area_tematica'):
        filtered_df = filtered_df[filtered_df['Área temática'] == filters['area_tematica']]
    
    if filters.get('dificultad'):
        filtered_df = filtered_df[filtered_df['Dificultad'] == filters['dificultad']]
    
    if filters.get('habilidad'):
        filtered_df = filtered_df[filtered_df['Habilidad'] == filters['habilidad']]
    
    if filters.get('subtema'):
        filtered_df = filtered_df[filtered_df['Conocimiento/Subtema'] == filters['subtema']]
    
    if filters.get('subject'):
        filtered_df = filtered_df[filtered_df['Subject_Source'] == filters['subject']]
    
    # Apply usage filter
    if filters.get('usage') is not None:
        usage_filter = filters['usage']
        
        # Ensure usage tracking columns exist
        if 'Número de usos' not in filtered_df.columns:
            filtered_df['Número de usos'] = 0
        
        # Convert usage counts to numeric, handling any string values
        filtered_df['Número de usos'] = pd.to_numeric(filtered_df['Número de usos'], errors='coerce').fillna(0)
        
        if usage_filter == 'unused':
            # Show only unused questions
            filtered_df = filtered_df[filtered_df['Número de usos'] == 0]
        elif usage_filter == '4+':
            # Show questions used 4 or more times
            filtered_df = filtered_df[filtered_df['Número de usos'] >= 4]
        elif isinstance(usage_filter, int):
            # Show questions used exactly this many times
            filtered_df = filtered_df[filtered_df['Número de usos'] == usage_filter]
    
    return filtered_df

# Removed HTML conversion functions - using only LibreOffice direct conversion

# Removed all HTML conversion functions - using only LibreOffice direct conversion

def display_question_preview(pregunta_id: str, file_path: str):
    """
    Display preview of a question from Word file as images using LibreOffice.
    
    Args:
        pregunta_id: Question ID
        file_path: Path to Word file (relative from project root)
    """
    try:
        storage = get_storage_client()
        
        # Convert relative path to absolute path from project root
        project_root = Path(__file__).parent.parent
        absolute_path = project_root / file_path
        
        if not storage.exists(str(absolute_path)):
            st.error(f"File not found: {absolute_path}")
            return
        
        # Convert document to images using LibreOffice
        with st.spinner("🔄 Converting document to images (optimized for speed)..."):
            preview_images = convert_docx_to_images(str(absolute_path))
        
        if preview_images:
            # Display the images with smaller width
            for i, image_data in enumerate(preview_images):
                st.image(image_data, width=800)
        else:
            # Show installation instructions
            st.warning("⚠️ Image conversion failed. Please ensure LibreOffice is installed:")
            st.code("""
# On Windows:
# Download LibreOffice from: https://www.libreoffice.org/download/download/

# On Linux:
sudo apt-get install libreoffice  # Ubuntu/Debian

# On macOS:
brew install --cask libreoffice
            """)
            st.error("Could not convert document to images. Please check LibreOffice installation.")
        
    except Exception as e:
        st.error(f"Error displaying question preview: {e}")

@st.cache_data(ttl=7200)  # Cache for 2 hours (longer cache for better performance)
def convert_docx_to_images(docx_path: str) -> list:
    """
    Convert Word document to images for preview using LibreOffice direct conversion.
    Results are cached to avoid re-converting the same documents.
    
    Args:
        docx_path: Path to the Word document
        
    Returns:
        List of image data (bytes) for each page
    """
    try:
        # Add file modification time to cache key for better cache invalidation
        file_mtime = os.path.getmtime(docx_path)
        cache_key = f"{docx_path}_{file_mtime}"
        
        return convert_docx_to_images_via_libreoffice_direct(docx_path)
    except Exception as e:
        st.error(f"Error converting document to images: {e}")
        return []

# Removed PIL conversion function - using only LibreOffice direct conversion

# Removed all helper functions - using only LibreOffice direct conversion

def convert_docx_to_images_via_libreoffice_direct(docx_path: str) -> list:
    """
    Convert Word document to images using LibreOffice directly (optimized for speed).
    
    Args:
        docx_path: Path to the Word document
        
    Returns:
        List of image data (bytes) for each page
    """
    try:
        import subprocess
        
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Try different LibreOffice paths for Windows
            libreoffice_paths = [
                "libreoffice",  # If in PATH
                r"C:\Program Files\LibreOffice\program\soffice.exe",
                r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"
            ]
            
            result = None
            for libreoffice_path in libreoffice_paths:
                try:
                    # Convert DOCX to images using LibreOffice with balanced speed and reliability
                    result = subprocess.run([
                        libreoffice_path, 
                        "--headless", 
                        "--invisible",
                        "--nodefault",
                        "--nolockcheck",
                        "--nologo",
                        "--norestore",
                        "--convert-to", "png", 
                        "--outdir", temp_dir, 
                        docx_path
                    ], capture_output=True, text=True, timeout=30)  # Increased timeout for reliability
                    
                    if result.returncode == 0:
                        break
                except FileNotFoundError:
                    continue
                except subprocess.TimeoutExpired:
                    st.warning(f"LibreOffice conversion timed out for {libreoffice_path}")
                    continue
            
            if not result or result.returncode != 0:
                error_msg = result.stderr if result and result.stderr else 'LibreOffice not found'
                if result and result.stdout:
                    error_msg += f" | Output: {result.stdout}"
                raise Exception(f"LibreOffice conversion failed: {error_msg}")
            
            # Find generated image files
            image_files = []
            for file in os.listdir(temp_dir):
                if file.endswith('.png'):
                    image_files.append(os.path.join(temp_dir, file))
            
            if not image_files:
                raise Exception("No image files were generated")
            
            # Read image files with optimized processing
            images = []
            for image_file in sorted(image_files):
                with open(image_file, 'rb') as f:
                    images.append(f.read())
            
            return images
        
    except Exception as e:
        st.warning(f"LibreOffice direct conversion failed: {e}")
        return []

# Removed PDF conversion function - using only LibreOffice direct conversion

# Removed old LibreOffice function - using optimized version

# Removed docx2pdf function as it uses Microsoft Word and causes performance issues

def extract_text_from_docx(docx_path: str) -> str:
    """
    Extract text content from Word document.
    
    Args:
        docx_path: Path to the Word document
        
    Returns:
        Extracted text content
    """
    try:
        import xml.etree.ElementTree as ET
        
        # Extract the document
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(docx_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Read document.xml
            doc_xml_path = os.path.join(temp_dir, "word", "document.xml")
            if not os.path.exists(doc_xml_path):
                return ""
            
            tree = ET.parse(doc_xml_path)
            root = tree.getroot()
            
            # Extract all text content
            text_parts = []
            
            for elem in root.iter():
                if elem.tag.endswith('t') and elem.text:
                    text_parts.append(elem.text)
            
            return '\n'.join(text_parts)
        
    except Exception as e:
        st.error(f"Error extracting text from document: {e}")
        return ""

def create_word_document(ordered_questions: list, questions_df: pd.DataFrame, subject: str) -> BytesIO:
    """
    Create Word document for the selected questions in the specified order.
    
    Args:
        ordered_questions: List of question IDs in the desired order
        questions_df: DataFrame with all questions
        subject: Subject area
        
    Returns:
        BytesIO object containing the Word document
    """
    try:
        # Filter selected questions and preserve order
        selected_df = questions_df[questions_df['PreguntaID'].isin(ordered_questions)]
        
        if selected_df.empty:
            return None
        
        # Create Word document using ZIP structure approach with preserved order
        word_buffer = create_word_guide(selected_df, ordered_questions)
        
        return word_buffer
        
    except Exception as e:
        st.error(f"Error creating Word document: {e}")
        return None


def create_word_guide(questions_df: pd.DataFrame, ordered_questions: list) -> BytesIO:
    """
    Create a Word document by merging the selected Word documents using ZIP structure approach.
    This preserves ALL formatting, images, and tables perfectly, and respects the order.
    
    Args:
        questions_df: DataFrame with selected questions
        ordered_questions: List of question IDs in the desired order
        
    Returns:
        BytesIO object containing the Word document
    """
    try:
        project_root = Path(__file__).parent.parent
        
        # Create a temporary directory for merging
        with tempfile.TemporaryDirectory() as temp_dir:
            merged_doc_path = os.path.join(temp_dir, "merged_document.docx")
            
            # Process questions in the specified order
            first_doc_path = None
            processed_questions = []
            
            # First pass: find the first valid document
            for question_id in ordered_questions:
                row = questions_df[questions_df['PreguntaID'] == question_id]
                if not row.empty:
                    file_path = row.iloc[0].get('Ruta relativa', '')
                    if file_path:
                        absolute_path = project_root / file_path
                        if os.path.exists(str(absolute_path)):
                            first_doc_path = str(absolute_path)
                            processed_questions.append((question_id, str(absolute_path)))
                            break
            
            if not first_doc_path:
                st.error("No se encontraron documentos válidos")
                return None
            
            # Copy the first document as the base
            shutil.copy2(first_doc_path, merged_doc_path)
            
            # Second pass: collect all other documents in order
            for question_id in ordered_questions:
                row = questions_df[questions_df['PreguntaID'] == question_id]
                if not row.empty:
                    file_path = row.iloc[0].get('Ruta relativa', '')
                if file_path:
                    absolute_path = project_root / file_path
                    if os.path.exists(str(absolute_path)) and str(absolute_path) != first_doc_path:
                            processed_questions.append((question_id, str(absolute_path)))
            
            # Calculate total questions
            total_questions = len(processed_questions)
            
            # Add header to the first question directly
            if total_questions > 0:
                add_question_header_to_document(merged_doc_path, 1, total_questions)
            
            # Merge all other documents in order with question numbering
            for i, (question_id, doc_path) in enumerate(processed_questions[1:], start=2):  # Skip first (already used as base)
                merge_word_documents_zip(merged_doc_path, doc_path, i, total_questions)
            
            # Read the merged document
            with open(merged_doc_path, 'rb') as f:
                merged_content = f.read()
            
            # Create BytesIO buffer
            buffer = BytesIO(merged_content)
            buffer.seek(0)
            
            return buffer
        
    except Exception as e:
        st.error(f"Error creating Word document: {e}")
        return None

def merge_word_documents_zip(target_doc_path: str, source_doc_path: str, question_number: int = None, total_questions: int = None):
    """
    Merge a source Word document into a target Word document using ZIP structure approach.
    This preserves ALL formatting, images, and tables perfectly.
    
    Args:
        target_doc_path: Path to the target document (will be modified)
        source_doc_path: Path to the source document to merge
        question_number: Current question number (optional)
        total_questions: Total number of questions (optional)
    """
    try:
        # Create temporary directory for extraction
        with tempfile.TemporaryDirectory() as temp_dir:
            # Extract target document
            target_extract_dir = os.path.join(temp_dir, "target")
            with zipfile.ZipFile(target_doc_path, 'r') as zip_ref:
                zip_ref.extractall(target_extract_dir)
            
            # Extract source document
            source_extract_dir = os.path.join(temp_dir, "source")
            with zipfile.ZipFile(source_doc_path, 'r') as zip_ref:
                zip_ref.extractall(source_extract_dir)
            
            # Copy images first and get the mapping
            image_mapping = copy_images_with_mapping(source_extract_dir, target_extract_dir)
            
            # Merge the document.xml files with proper relationship handling
            merge_document_xml_with_relationships(target_extract_dir, source_extract_dir, image_mapping, question_number, total_questions)
            
            # Create new merged document
            with zipfile.ZipFile(target_doc_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
                for root, dirs, files in os.walk(target_extract_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arc_name = os.path.relpath(file_path, target_extract_dir)
                        zip_ref.write(file_path, arc_name)
        
    except Exception as e:
        st.error(f"Error merging document {source_doc_path}: {e}")


def copy_images_with_mapping(source_extract_dir: str, target_extract_dir: str) -> dict:
    """
    Copy all images from source to target document and return mapping.
    
    Args:
        source_extract_dir: Directory where source document is extracted
        target_extract_dir: Directory where target document is extracted
        
    Returns:
        Dictionary mapping old image names to new image names
    """
    try:
        source_media_dir = os.path.join(source_extract_dir, "word", "media")
        target_media_dir = os.path.join(target_extract_dir, "word", "media")
        
        image_mapping = {}
        
        if os.path.exists(source_media_dir):
            # Ensure target media directory exists
            os.makedirs(target_media_dir, exist_ok=True)
            
            # Get existing images in target to avoid conflicts
            existing_images = set()
            if os.path.exists(target_media_dir):
                existing_images = set(os.listdir(target_media_dir))
            
            # Copy all images from source to target with unique names
            for filename in os.listdir(source_media_dir):
                source_file = os.path.join(source_media_dir, filename)
                
                # Create unique filename if it already exists
                if filename in existing_images:
                    name, ext = os.path.splitext(filename)
                    counter = 1
                    while f"{name}_{counter}{ext}" in existing_images:
                        counter += 1
                    new_filename = f"{name}_{counter}{ext}"
                else:
                    new_filename = filename
                
                target_file = os.path.join(target_media_dir, new_filename)
                shutil.copy2(source_file, target_file)
                image_mapping[filename] = new_filename
                existing_images.add(new_filename)
        
        return image_mapping
        
    except Exception as e:
        st.error(f"Error copying images: {e}")
        return {}

def merge_document_xml_with_relationships(target_extract_dir: str, source_extract_dir: str, image_mapping: dict, question_number: int = None, total_questions: int = None):
    """
    Merge the document.xml files from source into target with proper relationship handling.
    
    Args:
        target_extract_dir: Directory where target document is extracted
        source_extract_dir: Directory where source document is extracted
        image_mapping: Dictionary mapping old image names to new image names
        question_number: Current question number (optional)
        total_questions: Total number of questions (optional)
    """
    try:
        import xml.etree.ElementTree as ET
        
        # Read target document.xml
        target_xml_path = os.path.join(target_extract_dir, "word", "document.xml")
        target_tree = ET.parse(target_xml_path)
        target_root = target_tree.getroot()
        
        # Read source document.xml
        source_xml_path = os.path.join(source_extract_dir, "word", "document.xml")
        source_tree = ET.parse(source_xml_path)
        source_root = source_tree.getroot()
        
        # Find body elements
        target_body = None
        source_body = None
        
        for elem in target_root.iter():
            if elem.tag.endswith('body'):
                target_body = elem
                break
        
        for elem in source_root.iter():
            if elem.tag.endswith('body'):
                source_body = elem
                break
        
        if target_body is None or source_body is None:
            st.error("Could not find body elements in documents")
            return
        
        # Create relationship mapping for this source document
        relationship_mapping = create_relationship_mapping(target_extract_dir, source_extract_dir, image_mapping)
        
        # Add page break before merging
        page_break = ET.Element('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p')
        br = ET.SubElement(page_break, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}r')
        page_br = ET.SubElement(br, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}br')
        page_br.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}type', 'page')
        target_body.append(page_break)
        
        # Copy all elements from source body to target body
        for i, element in enumerate(source_body):
            # Skip section properties (we'll keep the target's)
            if not element.tag.endswith('sectPr'):
                # Update relationship IDs in the element
                updated_element = update_relationship_ids(element, relationship_mapping)
                
                # Add question number to the first paragraph if question number is provided
                if question_number is not None and total_questions is not None and i == 0 and element.tag.endswith('p'):
                    add_question_number_to_first_text(updated_element, question_number)
                
                target_body.append(updated_element)
        
        # Write back the modified target document.xml
        target_tree.write(target_xml_path, encoding='utf-8', xml_declaration=True)
        
    except Exception as e:
        st.error(f"Error merging document XML: {e}")

def add_question_number_to_first_text(paragraph, question_number: int):
    """
    Add question number to the first text element in a paragraph.
    This preserves all formatting by only modifying the text content.
    
    Args:
        paragraph: XML paragraph element
        question_number: Current question number
    """
    try:
        # Find the first text element in the paragraph
        for elem in paragraph.iter():
            if elem.tag.endswith('t') and elem.text:
                # Prepend the question number to the existing text
                elem.text = f"{question_number}. {elem.text}"
                break  # Only modify the first text element
        else:
            # If no text element found, find the first run and add text
            for elem in paragraph.iter():
                if elem.tag.endswith('r'):
                    # Create a text element in the first run
                    text_elem = ET.SubElement(elem, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t')
                    text_elem.text = f"{question_number}. "
                    break
        
    except Exception as e:
        st.error(f"Error adding question number to text: {e}")

def add_question_header_to_document(doc_path: str, question_number: int, total_questions: int):
    """
    Add a question header to the beginning of a Word document.
    
    Args:
        doc_path: Path to the Word document
        question_number: Current question number
        total_questions: Total number of questions
    """
    try:
        import xml.etree.ElementTree as ET
        
        # Create temporary directory for extraction
        with tempfile.TemporaryDirectory() as temp_dir:
            # Extract document
            with zipfile.ZipFile(doc_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Read document.xml
            doc_xml_path = os.path.join(temp_dir, "word", "document.xml")
            tree = ET.parse(doc_xml_path)
            root = tree.getroot()
            
            # Find the body element
            body = None
            for elem in root.iter():
                if elem.tag.endswith('body'):
                    body = elem
                    break
            
            if body is None:
                st.error("Could not find body element in document")
                return
            
            # Add question number to the first paragraph
            first_paragraph = None
            for elem in body:
                if elem.tag.endswith('p'):
                    first_paragraph = elem
                    break
            
            if first_paragraph is not None:
                add_question_number_to_first_text(first_paragraph, question_number)
            
            # Write back the modified document.xml
            tree.write(doc_xml_path, encoding='utf-8', xml_declaration=True)
            
            # Create new document
            with zipfile.ZipFile(doc_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arc_name = os.path.relpath(file_path, temp_dir)
                        zip_ref.write(file_path, arc_name)
        
    except Exception as e:
        st.error(f"Error adding question header to document: {e}")

def create_relationship_mapping(target_extract_dir: str, source_extract_dir: str, image_mapping: dict) -> dict:
    """
    Create a mapping of old relationship IDs to new ones for the source document.
    
    Args:
        target_extract_dir: Directory where target document is extracted
        source_extract_dir: Directory where source document is extracted
        image_mapping: Dictionary mapping old image names to new image names
        
    Returns:
        Dictionary mapping old relationship IDs to new ones
    """
    try:
        import xml.etree.ElementTree as ET
        
        # Get the highest relationship ID in target document
        max_rel_id = get_max_relationship_id(target_extract_dir)
        
        # Read source relationships file
        source_rels_path = os.path.join(source_extract_dir, "word", "_rels", "document.xml.rels")
        if not os.path.exists(source_rels_path):
            return {}
        
        source_rels_tree = ET.parse(source_rels_path)
        source_rels_root = source_rels_tree.getroot()
        
        relationship_mapping = {}
        
        # Create mapping for image relationships
        for relationship in source_rels_root.iter():
            if relationship.tag.endswith('Relationship'):
                target = relationship.get('Target')
                if target and target.startswith('media/'):
                    old_filename = os.path.basename(target)
                    if old_filename in image_mapping:
                        old_rel_id = relationship.get('Id')
                        max_rel_id += 1
                        new_rel_id = f"rId{max_rel_id}"
                        relationship_mapping[old_rel_id] = new_rel_id
        
        # Update the target relationships file with new relationships
        update_relationships_file_with_mapping(target_extract_dir, source_extract_dir, image_mapping, relationship_mapping)
        
        return relationship_mapping
        
    except Exception as e:
        st.error(f"Error creating relationship mapping: {e}")
        return {}

def get_max_relationship_id(target_extract_dir: str) -> int:
    """
    Get the highest relationship ID in the target document.
    
    Args:
        target_extract_dir: Directory where target document is extracted
        
    Returns:
        Highest relationship ID found
    """
    try:
        import xml.etree.ElementTree as ET
        
        rels_xml_path = os.path.join(target_extract_dir, "word", "_rels", "document.xml.rels")
        if not os.path.exists(rels_xml_path):
            return 0
        
        rels_tree = ET.parse(rels_xml_path)
        rels_root = rels_tree.getroot()
        
        max_id = 0
        for relationship in rels_root.iter():
            if relationship.tag.endswith('Relationship'):
                rel_id = relationship.get('Id')
                if rel_id and rel_id.startswith('rId'):
                    try:
                        id_num = int(rel_id[3:])  # Remove 'rId' prefix
                        max_id = max(max_id, id_num)
                    except ValueError:
                        pass
        
        return max_id
        
    except Exception as e:
        st.error(f"Error getting max relationship ID: {e}")
        return 0

def update_relationship_ids(element, relationship_mapping: dict):
    """
    Update relationship IDs in an element using the provided mapping.
    
    Args:
        element: XML element to update
        relationship_mapping: Dictionary mapping old relationship IDs to new ones
        
    Returns:
        Updated element
    """
    try:
        import xml.etree.ElementTree as ET
        
        # Create a copy of the element
        updated_element = ET.fromstring(ET.tostring(element))
        
        # Update relationship IDs
        for elem in updated_element.iter():
            # Update drawing elements (newer image format)
            if elem.tag.endswith('blip'):
                embed_id = elem.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
                if embed_id and embed_id in relationship_mapping:
                    new_embed_id = relationship_mapping[embed_id]
                    elem.set('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed', new_embed_id)
            
            # Update pict elements (older image format)
            elif elem.tag.endswith('imagedata'):
                src = elem.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
                if src and src in relationship_mapping:
                    new_src = relationship_mapping[src]
                    elem.set('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id', new_src)
        
        return updated_element
        
    except Exception as e:
        st.error(f"Error updating relationship IDs: {e}")
        return element

def update_relationships_file_with_mapping(target_extract_dir: str, source_extract_dir: str, image_mapping: dict, relationship_mapping: dict):
    """
    Update the relationships file with new image relationships using the provided mapping.
    
    Args:
        target_extract_dir: Directory where target document is extracted
        source_extract_dir: Directory where source document is extracted
        image_mapping: Dictionary mapping old image names to new image names
        relationship_mapping: Dictionary mapping old relationship IDs to new ones
    """
    try:
        import xml.etree.ElementTree as ET
        
        # Read target relationships file
        target_rels_path = os.path.join(target_extract_dir, "word", "_rels", "document.xml.rels")
        target_rels_tree = ET.parse(target_rels_path)
        target_rels_root = target_rels_tree.getroot()
        
        # Read source relationships file
        source_rels_path = os.path.join(source_extract_dir, "word", "_rels", "document.xml.rels")
        if not os.path.exists(source_rels_path):
            return
        
        source_rels_tree = ET.parse(source_rels_path)
        source_rels_root = source_rels_tree.getroot()
        
        # Add new relationships for images using the mapping
        for relationship in source_rels_root.iter():
            if relationship.tag.endswith('Relationship'):
                target = relationship.get('Target')
                if target and target.startswith('media/'):
                    old_filename = os.path.basename(target)
                    if old_filename in image_mapping:
                        old_rel_id = relationship.get('Id')
                        if old_rel_id in relationship_mapping:
                            new_rel_id = relationship_mapping[old_rel_id]
                            new_filename = image_mapping[old_filename]
                            new_target = f"media/{new_filename}"
                            
                            # Create new relationship element
                            new_rel = ET.Element('{http://schemas.openxmlformats.org/package/2006/relationships}Relationship')
                            new_rel.set('Id', new_rel_id)
                            new_rel.set('Type', relationship.get('Type', ''))
                            new_rel.set('Target', new_target)
                            
                            target_rels_root.append(new_rel)
        
        # Write back the updated relationships file
        target_rels_tree.write(target_rels_path, encoding='utf-8', xml_declaration=True)
        
    except Exception as e:
        st.error(f"Error updating relationships file: {e}")


def create_pie_chart(values, names, title, total_questions):
    """
    Create a pie chart with consistent styling.
    
    Args:
        values: Chart values
        names: Chart labels
        title: Chart title
        total_questions: Total number of questions
        
    Returns:
        Plotly figure
    """
    import plotly.express as px
    
    fig = px.pie(
        values=values,
        names=names,
        title=f"{title}<br><sub>{total_questions} preguntas</sub>",
        color_discrete_sequence=CHART_COLORS
    )
    
    fig.update_traces(
        textposition='inside',
        textinfo='value+percent',
        texttemplate='%{value}<br>(%{percent})',
        hovertemplate='<b>%{label}</b><br>Cantidad: %{value}<br>Porcentaje: %{percent}<extra></extra>'
    )
    
    fig.update_layout(
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.1,
            xanchor="center",
            x=0.5
        ),
        height=400,
        font=dict(size=12)
    )
    
    return fig

def create_summary_charts(selected_df: pd.DataFrame, subject: str):
    """
    Create summary pie charts for selected questions.
    
    Args:
        selected_df: DataFrame with selected questions
        subject: Current subject
    """
    try:
        import plotly.express as px
        import plotly.graph_objects as go
        
        if selected_df.empty:
            st.info("No hay preguntas seleccionadas para mostrar gráficos.")
            return
        
        total_questions = len(selected_df)
        
        # First row: Subject and Area charts
        if subject == "Ciencias" and 'Subject_Source' in selected_df.columns:
            # For Ciencias: show Subject and Area side by side
            col1, col2 = st.columns(2)
            
            with col1:
                # Subject pie chart
                subject_counts = selected_df['Subject_Source'].value_counts()
                fig_subject = create_pie_chart(
                    subject_counts.values,
                    subject_counts.index,
                    "Distribución por Asignatura",
                    total_questions
                )
                st.plotly_chart(fig_subject, use_container_width=True)
            
            with col2:
                # Area pie chart
                if 'Área temática' in selected_df.columns:
                    area_counts = selected_df['Área temática'].value_counts()
                    fig_area = create_pie_chart(
                        area_counts.values,
                        area_counts.index,
                        "Distribución por Área Temática",
                        total_questions
                    )
                    st.plotly_chart(fig_area, use_container_width=True)
        else:
            # For other subjects: show Area full width
            if 'Área temática' in selected_df.columns:
                area_counts = selected_df['Área temática'].value_counts()
                fig_area = create_pie_chart(
                    area_counts.values,
                    area_counts.index,
                    "Distribución por Área Temática",
                    total_questions
                )
                st.plotly_chart(fig_area, use_container_width=True)
        
        # Second row: Habilidad and Dificultad charts
        col3, col4 = st.columns(2)
        
        with col3:
            # Habilidad pie chart
            if 'Habilidad' in selected_df.columns:
                habilidad_counts = selected_df['Habilidad'].value_counts()
                fig_habilidad = create_pie_chart(
                    habilidad_counts.values,
                    habilidad_counts.index,
                    "Distribución por Habilidad",
                    total_questions
                )
                st.plotly_chart(fig_habilidad, use_container_width=True)
        
        with col4:
            # Dificultad pie chart
            if 'Dificultad' in selected_df.columns:
                dificultad_counts = selected_df['Dificultad'].value_counts()
                fig_dificultad = create_pie_chart(
                    dificultad_counts.values,
                    dificultad_counts.index,
                    "Distribución por Dificultad",
                    total_questions
                )
                st.plotly_chart(fig_dificultad, use_container_width=True)
        
        # Third row: Subtema chart (full width)
        if 'Conocimiento/Subtema' in selected_df.columns:
            subtema_counts = selected_df['Conocimiento/Subtema'].value_counts()
            
            # Limit to top 10 subtemas if there are too many
            if len(subtema_counts) > 10:
                top_subtemas = subtema_counts.head(10)
                others_count = subtema_counts.iloc[10:].sum()
                if others_count > 0:
                    top_subtemas['Otros'] = others_count
                subtema_counts = top_subtemas
            
            fig_subtema = create_pie_chart(
                subtema_counts.values,
                subtema_counts.index,
                "Distribución por Subtema",
                total_questions
            )
            # Override height for subtema chart
            fig_subtema.update_layout(height=500)
            st.plotly_chart(fig_subtema, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error creating summary charts: {e}")

def main():
    """Main Streamlit application."""
    
    # Add smooth scrolling and scroll preservation for better UX
    add_smooth_scrolling()
    preserve_scroll_on_rerun()
    
    # Check if we need to force refresh after download tracking or guide deletion
    if st.session_state.get('force_refresh', False):
        st.session_state['force_refresh'] = False
        # Reload data if it's already loaded
        if 'questions_df' in st.session_state:
            current_subject = st.session_state.get('subject')
            if current_subject:
                with st.spinner("Actualizando datos..."):
                    df = load_master_excel(current_subject)
                    if not df.empty:
                        st.session_state['questions_df'] = df
        st.rerun()
    
    # Header
    st.title("🧠 Generador de Guías M30M")
    st.markdown("---")
    
    # Sidebar for filters
    st.sidebar.header("🔍 Filtros de Búsqueda")
    
    # Subject selection
    subject = st.sidebar.selectbox(
        "Seleccionar Asignatura",
        options=list(SUBJECT_FOLDERS.keys()),
        help="Selecciona la asignatura para cargar las preguntas"
    )
    
    # Load data button
    if st.sidebar.button("Cargar Preguntas", type="primary"):
        with st.spinner(f"Cargando preguntas de {subject}..."):
            df = load_master_excel(subject)
            
            if not df.empty:
                st.session_state['questions_df'] = df
                st.session_state['subject'] = subject
                
                # Clear all selections when loading a new subject
                st.session_state['selected_questions'] = set()
                st.session_state['selected_questions_ordered'] = []
                st.session_state['question_positions'] = {}
                st.session_state['preview_question'] = None
                st.session_state['preview_file_path'] = None
                # Clear guide name selection when subject changes
                if 'guide_name_select' in st.session_state:
                    del st.session_state['guide_name_select']
                
                st.success(f"✅ Cargadas {len(df)} preguntas de {subject}")
                st.info("🔄 Selecciones anteriores limpiadas al cambiar de asignatura")
            else:
                st.error(f"No se pudieron cargar preguntas para {subject}")
    
    # Usage statistics section
    st.sidebar.markdown("---")
    st.sidebar.header("📊 Estadísticas de Uso")
    
    if st.sidebar.button("Ver Estadísticas", help="Mostrar estadísticas de uso de preguntas"):
        with st.spinner("Cargando estadísticas..."):
            storage = get_storage_client()
            usage_tracker = UsageTracker(storage)
            
            if subject == "Ciencias":
                # Show stats for all three subjects
                for subj in ["F30M", "Q30M", "B30M"]:
                    stats = usage_tracker.get_question_usage_stats(subj)
                    if "error" not in stats:
                        st.sidebar.write(f"**{subj}:**")
                        st.sidebar.write(f"• Total: {stats['total_questions']}")
                        st.sidebar.write(f"• Usadas: {stats['used_questions']}")
                        st.sidebar.write(f"• Sin usar: {stats['unused_questions']}")
                        st.sidebar.write(f"• % Uso: {stats['usage_percentage']:.1f}%")
                        st.sidebar.write("")
            else:
                stats = usage_tracker.get_question_usage_stats(subject)
                if "error" not in stats:
                    st.sidebar.write(f"**{subject}:**")
                    st.sidebar.write(f"• Total: {stats['total_questions']}")
                    st.sidebar.write(f"• Usadas: {stats['used_questions']}")
                    st.sidebar.write(f"• Sin usar: {stats['unused_questions']}")
                    st.sidebar.write(f"• % Uso: {stats['usage_percentage']:.1f}%")
                    
                    # Show usage distribution
                    if stats['usage_distribution']:
                        st.sidebar.write("**Distribución:**")
                        for usage_count, count in stats['usage_distribution'].items():
                            if not pd.isna(usage_count):
                                st.sidebar.write(f"• {int(usage_count)} uso(s): {count} preguntas")
                else:
                    st.sidebar.error(stats['error'])
    
    # Guide deletion section
    st.sidebar.markdown("---")
    st.sidebar.header("🗑️ Eliminar Guías")
    
    # Initialize guide deletion state
    if 'show_guide_deletion' not in st.session_state:
        st.session_state['show_guide_deletion'] = False
    if 'available_guides' not in st.session_state:
        st.session_state['available_guides'] = []
    if 'selected_guide_for_deletion' not in st.session_state:
        st.session_state['selected_guide_for_deletion'] = None
    
    if st.sidebar.button("Ver Guías Creadas", help="Mostrar guías creadas para eliminar"):
        with st.spinner("Cargando guías creadas..."):
            storage = get_storage_client()
            usage_tracker = UsageTracker(storage)
            
            guides = usage_tracker.get_all_guides_for_subject(subject)
            st.session_state['available_guides'] = guides
            st.session_state['show_guide_deletion'] = True
            st.session_state['selected_guide_for_deletion'] = None  # Reset selection
    
    # Show guide deletion interface if guides are loaded
    if st.session_state['show_guide_deletion'] and st.session_state['available_guides']:
        guides = st.session_state['available_guides']
        st.sidebar.write(f"**Guías encontradas para {subject}:**")
        
        # Create a selectbox for guide selection
        guide_options = []
        for i, guide in enumerate(guides):
            date_str = guide['date'] if guide['date'] else 'Sin fecha'
            if subject == "Ciencias" and 'subject_sources' in guide:
                # Show all subject sources for Ciencias guides
                subjects_str = ', '.join(guide['subject_sources'])
                option_text = f"{guide['guide_name']} ({subjects_str}) - {date_str} - {guide['question_count']} preguntas"
            else:
                option_text = f"{guide['guide_name']} - {date_str} - {guide['question_count']} preguntas"
            guide_options.append((option_text, i))
        
        if guide_options:
            # Add empty option at the beginning
            options_with_empty = [""] + [opt[0] for opt in guide_options]
            
            # Get current selection from session state
            current_selection = st.session_state.get('selected_guide_for_deletion', "")
            if current_selection not in options_with_empty:
                current_selection = ""
            
            selected_option = st.sidebar.selectbox(
                "Seleccionar guía a eliminar:",
                options=options_with_empty,
                index=options_with_empty.index(current_selection) if current_selection in options_with_empty else 0,
                help="Selecciona la guía que quieres eliminar",
                key="guide_deletion_selectbox"
            )
            
            # Update session state with selection
            st.session_state['selected_guide_for_deletion'] = selected_option
            
            if selected_option and selected_option != "":
                # Find the selected guide
                selected_index = next(i for i, (opt, _) in enumerate(guide_options) if opt == selected_option)
                selected_guide = guides[selected_index]
                
                # Show guide details
                st.sidebar.write("**Detalles de la guía:**")
                st.sidebar.write(f"• Nombre: {selected_guide['guide_name']}")
                st.sidebar.write(f"• Fecha: {selected_guide['date'] if selected_guide['date'] else 'Sin fecha'}")
                st.sidebar.write(f"• Preguntas: {selected_guide['question_count']}")
                if subject == "Ciencias" and 'subject_sources' in selected_guide:
                    subjects_str = ', '.join(selected_guide['subject_sources'])
                    st.sidebar.write(f"• Asignaturas: {subjects_str}")
                
                # Confirmation and deletion
                st.sidebar.write("**⚠️ ADVERTENCIA:** Esta acción eliminará el registro de uso de esta guía de todas las preguntas afectadas.")
                
                if st.sidebar.button("🗑️ ELIMINAR GUÍA", type="secondary", help="Eliminar esta guía y descontar su uso"):
                    with st.spinner("Eliminando guía..."):
                        storage = get_storage_client()
                        usage_tracker = UsageTracker(storage)
                        
                        result = usage_tracker.delete_guide_usage(
                            subject, 
                            selected_guide['guide_name'], 
                            selected_guide['date']
                        )
                        
                        if result['success']:
                            st.sidebar.success(f"✅ {result['message']}")
                            
                            # Show detailed results for Ciencias
                            if subject == "Ciencias" and 'subject_results' in result:
                                st.sidebar.write("**Resultados por asignatura:**")
                                for subj, subj_result in result['subject_results'].items():
                                    if subj_result['success']:
                                        st.sidebar.write(f"• {subj}: {subj_result['questions_deleted']} preguntas")
                                    else:
                                        st.sidebar.write(f"• {subj}: Error - {subj_result.get('error', 'Desconocido')}")
                            
                            # Reset the guide deletion state
                            st.session_state['show_guide_deletion'] = False
                            st.session_state['available_guides'] = []
                            st.session_state['selected_guide_for_deletion'] = None
                            
                            # Force refresh to update the main view
                            st.session_state['force_refresh'] = True
                            
                            # Immediately refresh the page to close the interface and update data
                            st.rerun()
                        else:
                            st.sidebar.error(f"❌ Error: {result.get('error', 'Error desconocido')}")
            else:
                st.sidebar.info("Selecciona una guía para ver sus detalles y eliminarla.")
        
        # Add a button to close the guide deletion interface
        if st.sidebar.button("❌ Cerrar", help="Cerrar la interfaz de eliminación de guías"):
            st.session_state['show_guide_deletion'] = False
            st.session_state['available_guides'] = []
            st.session_state['selected_guide_for_deletion'] = None
            st.rerun()
    
    # Check if data is loaded
    if 'questions_df' not in st.session_state:
        st.info("👈 Selecciona una asignatura y haz clic en 'Cargar Preguntas' para comenzar")
        return
    
    df = st.session_state['questions_df']
    current_subject = st.session_state['subject']
    
    # Display data summary
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Preguntas", len(df))
    
    with col2:
        areas = df['Área temática'].nunique() if 'Área temática' in df.columns else 0
        st.metric("Áreas Temáticas", areas)
    
    with col3:
        difficulties = df['Dificultad'].nunique() if 'Dificultad' in df.columns else 0
        st.metric("Niveles Dificultad", difficulties)
    
    with col4:
        skills = df['Habilidad'].nunique() if 'Habilidad' in df.columns else 0
        st.metric("Habilidades", skills)
    
    st.markdown("---")
    
    # Filters
    st.subheader("🎯 Filtrar Preguntas")
    
    # First row: Asignatura and Área Temática (for Ciencias) or just Área Temática (for others)
    if current_subject == "Ciencias":
        col_asig, col_area = st.columns(2)
        
        with col_asig:
            # Subject filter for Ciencias
            if 'Subject_Source' in df.columns:
                subjects = ['Todas'] + sorted(df['Subject_Source'].unique().tolist())
                selected_subject = st.selectbox("Asignatura", subjects)
                subject_filter = None if selected_subject == 'Todas' else selected_subject
            else:
                subject_filter = None
        
        with col_area:
            # Area filter
            if 'Área temática' in df.columns:
                areas = ['Todas'] + sorted(df['Área temática'].unique().tolist())
                selected_area = st.selectbox("Área Temática", areas)
                area_filter = None if selected_area == 'Todas' else selected_area
            else:
                area_filter = None
    else:
        # For other subjects, just show Área Temática in full width
        if 'Área temática' in df.columns:
            areas = ['Todas'] + sorted(df['Área temática'].unique().tolist())
            selected_area = st.selectbox("Área Temática", areas)
            area_filter = None if selected_area == 'Todas' else selected_area
        else:
            area_filter = None
        
    
    # Second row: Subtema (full width) - dynamic based on selected filters
    if 'Conocimiento/Subtema' in df.columns:
        # Filter subtemas based on selected area and subject (for Ciencias)
        filtered_df_for_subtema = df.copy()
        
        # Apply subject filter first (for Ciencias)
        if current_subject == "Ciencias" and 'subject_filter' in locals() and subject_filter is not None:
            filtered_df_for_subtema = filtered_df_for_subtema[filtered_df_for_subtema['Subject_Source'] == subject_filter]
        
        # Apply area filter
        if area_filter is not None:
            filtered_df_for_subtema = filtered_df_for_subtema[filtered_df_for_subtema['Área temática'] == area_filter]
        
        available_subtemas = sorted(filtered_df_for_subtema['Conocimiento/Subtema'].unique().tolist())
        subtemas = ['Todos'] + available_subtemas
        selected_subtema = st.selectbox("Subtema", subtemas)
        subtema_filter = None if selected_subtema == 'Todos' else selected_subtema
    else:
        subtema_filter = None
    
    # Third row: Habilidad and Dificultad
    col_hab, col_dif = st.columns(2)
    
    with col_hab:
        # Skill filter
        if 'Habilidad' in df.columns:
            skills = ['Todas'] + sorted(df['Habilidad'].unique().tolist())
            selected_skill = st.selectbox("Habilidad", skills)
            skill_filter = None if selected_skill == 'Todas' else selected_skill
        else:
            skill_filter = None
    
    with col_dif:
        # Difficulty filter
        if 'Dificultad' in df.columns:
            difficulties = ['Todas'] + sorted(df['Dificultad'].unique().tolist())
            selected_difficulty = st.selectbox("Dificultad", difficulties)
            difficulty_filter = None if selected_difficulty == 'Todas' else selected_difficulty
        else:
            difficulty_filter = None
    
    # Fourth row: Usage filter
    col_usage = st.columns(1)[0]
    with col_usage:
        # Usage filter - dynamic based on actual usage in the data
        usage_options = ['Todas', 'Sin usar']
        
        # Get unique usage counts from the data
        if 'Número de usos' in df.columns:
            usage_counts = df['Número de usos'].dropna().unique()
            usage_counts = sorted([int(x) for x in usage_counts if x > 0])
            
            # Add specific usage count options
            for count in usage_counts:
                if count == 1:
                    usage_options.append('Usadas 1 vez')
                elif count == 2:
                    usage_options.append('Usadas 2 veces')
                elif count == 3:
                    usage_options.append('Usadas 3 veces')
                else:
                    usage_options.append(f'Usadas {count} veces')
            
            # Add "high usage" option if there are questions with 4+ uses
            if any(count >= 4 for count in usage_counts):
                usage_options.append('Usadas 4+ veces')
        
        selected_usage = st.selectbox("Filtrar por uso", usage_options)
        
        if selected_usage == 'Sin usar':
            usage_filter = 'unused'
        elif selected_usage == 'Usadas 1 vez':
            usage_filter = 1
        elif selected_usage == 'Usadas 2 veces':
            usage_filter = 2
        elif selected_usage == 'Usadas 3 veces':
            usage_filter = 3
        elif selected_usage == 'Usadas 4+ veces':
            usage_filter = '4+'
        elif selected_usage.startswith('Usadas ') and selected_usage.endswith(' veces'):
            # Extract number from "Usadas X veces"
            try:
                count = int(selected_usage.split()[1])
                usage_filter = count
            except (ValueError, IndexError):
                usage_filter = None
        else:
            usage_filter = None
    
    # Apply filters
    filters = {
        'area_tematica': area_filter,
        'dificultad': difficulty_filter,
        'habilidad': skill_filter,
        'subtema': subtema_filter,
        'usage': usage_filter
    }
    
    # Add subject filter for Ciencias
    if current_subject == "Ciencias":
        filters['subject'] = subject_filter if 'subject_filter' in locals() else None
    
    filtered_df = filter_questions(df, filters)
    
    # Sort questions by the specified criteria
    if len(filtered_df) > 0:
        filtered_df = sort_questions_for_display(filtered_df, current_subject)
    
    st.markdown(f"**Preguntas encontradas: {len(filtered_df)}**")
    
    if len(filtered_df) > 0:
        # Question selection
        st.subheader("📋 Seleccionar Preguntas")
        
        # Initialize selected questions in session state
        if 'selected_questions' not in st.session_state:
            st.session_state['selected_questions'] = set()
        if 'selected_questions_ordered' not in st.session_state:
            st.session_state['selected_questions_ordered'] = []
        
        # Initialize question positions if not exists
        if 'question_positions' not in st.session_state:
            st.session_state['question_positions'] = {}
        
        # Display questions in a table
        for idx, row in filtered_df.iterrows():
            pregunta_id = row.get('PreguntaID', f'Q{idx+1}')
            
            col1, col2, col3, col4 = st.columns([1, 1, 6, 1])
            
            with col1:
                is_selected = pregunta_id in st.session_state['selected_questions']
                new_selection = st.checkbox("Seleccionar", value=is_selected, key=f"select_{pregunta_id}", label_visibility="collapsed")
                
                # Only update state if selection actually changed
                if new_selection != is_selected:
                    if new_selection:
                        st.session_state['selected_questions'].add(pregunta_id)
                        # Add to ordered list if not already there
                        if pregunta_id not in st.session_state['selected_questions_ordered']:
                            st.session_state['selected_questions_ordered'].append(pregunta_id)
                        # Assign next available position
                        assign_next_position(pregunta_id)
                    else:
                        st.session_state['selected_questions'].discard(pregunta_id)
                        # Remove from ordered list and positions
                        if pregunta_id in st.session_state['selected_questions_ordered']:
                            st.session_state['selected_questions_ordered'].remove(pregunta_id)
                        # Remove position and renumber
                        remove_question_and_renumber(pregunta_id)
                    
                    # Rerun to immediately show/hide position selector
                    st.rerun()
            
            with col2:
                # Position selector (only show if selected)
                if is_selected:
                    current_position = st.session_state['question_positions'].get(pregunta_id, 0)
                    max_position = len(st.session_state['selected_questions'])
                    
                    # Create position options - just numbers
                    position_options = list(range(1, max_position + 1))
                    
                    # Find current position index
                    current_index = position_options.index(current_position) if current_position in position_options else 0
                    
                    new_position = st.selectbox(
                        "Posición",
                        options=position_options,
                        index=current_index,
                        key=f"position_{pregunta_id}",
                        label_visibility="collapsed"
                    )
                    
                    # Update position if changed
                    if new_position != current_position:
                        update_question_position(pregunta_id, new_position)
                        # Rerun to immediately update all position selectors
                        st.rerun()
                else:
                    st.write("")  # Empty space for alignment
            
            with col3:
                # Show subject source for Ciencias
                subject_info = ""
                if 'Subject_Source' in row and row['Subject_Source']:
                    subject_info = f" [{row['Subject_Source']}]"
                
                # Show usage information
                usage_info = ""
                if 'Número de usos' in row and not pd.isna(row['Número de usos']) and row['Número de usos'] > 0:
                    usage_count = int(row['Número de usos'])
                    usage_info = f" | 🔄 **Usada {usage_count} ve{'ces' if usage_count > 1 else 'z'}**"
                    
                    # Show latest guide name if available
                    latest_guide_col = f"Nombre guía (uso {usage_count})"
                    if latest_guide_col in row and not pd.isna(row[latest_guide_col]):
                        usage_info += f" (última: {row[latest_guide_col]})"
                
                st.write(f"**{pregunta_id}**{subject_info} | "
                        f"Área: **{row.get('Área temática', 'N/A')}** | "
                        f"Dificultad: **{row.get('Dificultad', 'N/A')}** | "
                        f"Habilidad: **{row.get('Habilidad', 'N/A')}**{usage_info}")
                st.write(f"{row.get('Conocimiento/Subtema', 'Sin subtema')}")
            
            with col4:
                col_preview, col_history = st.columns(2)
                
                with col_preview:
                    if st.button("👁️", key=f"preview_{pregunta_id}", help="Ver pregunta"):
                        # Store the question to preview in session state
                        st.session_state['preview_question'] = pregunta_id
                        st.session_state['preview_file_path'] = row.get('Ruta relativa', '')
                        # Don't rerun here - let the preview show below
                
                with col_history:
                    # Show usage history button if question has been used
                    if 'Número de usos' in row and not pd.isna(row['Número de usos']) and row['Número de usos'] > 0:
                        if st.button("📊", key=f"history_{pregunta_id}", help="Ver historial de uso"):
                            st.session_state['show_usage_history'] = pregunta_id
            
            # Show usage history below this question if it's the one being viewed
            if st.session_state.get('show_usage_history') == pregunta_id:
                st.markdown("---")
                
                # Usage history section
                with st.container():
                    col_title, col_close = st.columns([4, 1])
                    with col_title:
                        st.subheader(f"📊 Historial de Uso: {pregunta_id}")
                    with col_close:
                        if st.button("❌", key=f"close_history_{pregunta_id}", help="Cerrar historial"):
                            st.session_state['show_usage_history'] = None
                            st.rerun()
                    
                    # Display usage history
                    if 'Número de usos' in row and not pd.isna(row['Número de usos']) and row['Número de usos'] > 0:
                        usage_count = int(row['Número de usos'])
                        
                        # Create a table with usage history
                        history_data = []
                        for i in range(1, usage_count + 1):
                            guide_col = f"Nombre guía (uso {i})"
                            date_col = f"Fecha descarga (uso {i})"
                            
                            guide_name = row.get(guide_col, 'N/A')
                            date = row.get(date_col, 'N/A')
                            
                            history_data.append({
                                "Uso #": i,
                                "Nombre de Guía": guide_name,
                                "Fecha de Descarga": date
                            })
                        
                        if history_data:
                            history_df = pd.DataFrame(history_data)
                            st.dataframe(history_df, use_container_width=True, hide_index=True)
                        else:
                            st.info("No hay historial de uso disponible")
                    else:
                        st.info("Esta pregunta no ha sido utilizada aún")
                
                st.markdown("---")
            
            # Show preview below this question if it's the one being previewed
            if st.session_state.get('preview_question') == pregunta_id:
                st.markdown("---")
                
                # Full-width preview section
                with st.container():
                    col_title, col_close = st.columns([4, 1])
                    with col_title:
                        st.subheader(f"📄 Complete Question Preview: {pregunta_id}")
                    with col_close:
                        if st.button("❌", key=f"close_preview_{pregunta_id}", help="Cerrar preview"):
                            st.session_state['preview_question'] = None
                            st.session_state['preview_file_path'] = None
                            st.rerun()
                    
                    # Full-width image container
                    file_path = st.session_state.get('preview_file_path', '')
                    if file_path:
                        display_question_preview(pregunta_id, file_path)
                    else:
                        st.error("Ruta de archivo no disponible")
                
                st.markdown("---")
        
        # Selected questions summary
        st.markdown("---")
        st.subheader("📊 Resumen de Selección")
        
        selected_count = len(st.session_state['selected_questions'])
        
        if selected_count > 0:
            # Show selected questions with ordering and preview
            # Use original df instead of filtered_df to ensure selected questions are always available
            selected_df = df[df['PreguntaID'].isin(st.session_state['selected_questions'])]
            
            # Display summary metrics for selected questions
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Preguntas", selected_count)
            
            with col2:
                areas = selected_df['Área temática'].nunique() if 'Área temática' in selected_df.columns else 0
                st.metric("Áreas Temáticas", areas)
            
            with col3:
                difficulties = selected_df['Dificultad'].nunique() if 'Dificultad' in selected_df.columns else 0
                st.metric("Niveles Dificultad", difficulties)
            
            with col4:
                skills = selected_df['Habilidad'].nunique() if 'Habilidad' in selected_df.columns else 0
                st.metric("Habilidades", skills)
            
            st.markdown("---")
        
        if selected_count > 0:
            
            # Use ordered list for display, but ensure it only contains currently selected questions
            ordered_questions = [q for q in st.session_state['selected_questions_ordered'] if q in st.session_state['selected_questions']]
            st.session_state['selected_questions_ordered'] = ordered_questions
            
            
            # Display each selected question with controls (ordered by position)
            sorted_questions = sorted(
                st.session_state['question_positions'].items(),
                key=lambda x: x[1]
            )
            
            for position, (pregunta_id, _) in enumerate(sorted_questions, 1):
                # Find the row for this question
                question_row = selected_df[selected_df['PreguntaID'] == pregunta_id]
                if question_row.empty:
                    continue
                    
                row = question_row.iloc[0]
                
                # Create columns for question info, preview, and unselect
                col_info, col_preview, col_unselect = st.columns([8, 1, 1])
                
                with col_info:
                    # Show subject source for Ciencias
                    subject_info = ""
                    if 'Subject_Source' in row and row['Subject_Source']:
                        subject_info = f" [{row['Subject_Source']}]"
                    
                    st.write(f"**{position}.** {pregunta_id}{subject_info} | "
                            f"Área: **{row.get('Área temática', 'N/A')}** | "
                            f"Dificultad: **{row.get('Dificultad', 'N/A')}** | "
                            f"Habilidad: **{row.get('Habilidad', 'N/A')}**")
                    st.write(f"{row.get('Conocimiento/Subtema', 'Sin subtema')}")
                
                with col_preview:
                    if st.button("👁️", key=f"summary_preview_{pregunta_id}", help="Ver pregunta"):
                        # Store the question to preview in session state
                        st.session_state['preview_question'] = pregunta_id
                        st.session_state['preview_file_path'] = row.get('Ruta relativa', '')
                        # Don't rerun here - let the preview show below
                
                with col_unselect:
                    if st.button("❌", key=f"summary_unselect_{pregunta_id}", help="Deseleccionar pregunta"):
                        # Remove question from selection
                        st.session_state['selected_questions'].discard(pregunta_id)
                        # Remove from ordered list and positions
                        if pregunta_id in st.session_state['selected_questions_ordered']:
                            st.session_state['selected_questions_ordered'].remove(pregunta_id)
                        # Remove position and renumber
                        remove_question_and_renumber(pregunta_id)
                        st.success(f"✅ Pregunta {pregunta_id} deseleccionada")
                        st.rerun()
                
                # Show preview below this question if it's the one being previewed from summary
                if st.session_state.get('preview_question') == pregunta_id and st.session_state.get('preview_file_path'):
                    st.markdown("---")
                    
                    # Full-width preview section
                    with st.container():
                        col_title, col_close = st.columns([4, 1])
                        with col_title:
                            st.subheader(f"📄 Preview: {pregunta_id}")
                        with col_close:
                            if st.button("❌", key=f"close_summary_preview_{pregunta_id}", help="Cerrar preview"):
                                st.session_state['preview_question'] = None
                                st.session_state['preview_file_path'] = None
                                st.rerun()
                        
                        # Full-width preview container
                        file_path = st.session_state.get('preview_file_path', '')
                        if file_path:
                            display_question_preview(pregunta_id, file_path)
                        else:
                            st.error("Ruta de archivo no disponible")
                    
                    st.markdown("---")
            
            # Summary Charts Section
            st.markdown("---")
            st.subheader("📊 Gráficos Resumen")
            
            # Create summary charts
            create_summary_charts(selected_df, current_subject)
            
            # Guide naming section
            st.markdown("---")
            
            # Load allowed guide names
            nombres_df = load_allowed_guide_names()
            
            # Use columns for proper alignment
            col_nombre, col_lista = st.columns([1, 3])
            
            with col_nombre:

                if not nombres_df.empty:
                    # Filter names by current subject
                    if current_subject in nombres_df['Asignatura'].values:
                        available_names = nombres_df[nombres_df['Asignatura'] == current_subject]['nombre guía'].tolist()
                    else:
                        available_names = []
                        st.warning(f"No hay nombres de guías disponibles para {current_subject}")
                    
                    if available_names:
                        # Add empty option at the beginning
                        options_with_empty = [""] + available_names
                        # Make the label text bigger using markdown
                        st.markdown("<span style='font-size: 1.3em; font-weight: bold;'>Selecciona el nombre de la guía:</span>", unsafe_allow_html=True)
                        
                        # Check if we need to reset the guide name selection
                        default_index = 0  # First option is empty string
                        if 'guide_name_select' in st.session_state:
                            # If there's a stored value, find its index
                            try:
                                stored_value = st.session_state['guide_name_select']
                                if stored_value in options_with_empty:
                                    default_index = options_with_empty.index(stored_value)
                                else:
                                    default_index = 0
                            except (ValueError, TypeError):
                                default_index = 0
                        
                        selected_guide_name = st.selectbox(
                            "Nombre de guía",
                            options=options_with_empty,
                            index=default_index,
                            key="guide_name_select",
                            label_visibility="collapsed"
                        )
                        # Convert empty string to None
                        if selected_guide_name == "":
                            selected_guide_name = None
                    else:
                        selected_guide_name = None
                        st.info("No hay nombres disponibles para esta asignatura")
                else:
                    selected_guide_name = None
                    st.error("No se pudieron cargar los nombres de guías")
            
            # Generate guide section
            st.markdown("---")
            col_generate, col_clear = st.columns([3, 1])
            
            with col_generate:
                # Generate guide button - disabled if no guide name selected
                is_guide_name_selected = bool(selected_guide_name)
                if st.button("📝 Generar Guía Word", type="primary", disabled=not is_guide_name_selected):
                    # Clear any previous download tracking messages
                    if 'download_tracking_message' in st.session_state:
                        del st.session_state['download_tracking_message']
                    if 'download_tracking_success' in st.session_state:
                        del st.session_state['download_tracking_success']
                    
                    with st.spinner("Generando documento Word..."):
                        # Create Word document using ordered questions
                        word_buffer = create_word_document(
                            ordered_questions, 
                            df, 
                            current_subject
                        )
                    
                    if word_buffer:
                        st.success("🎉 ¡Guía Word generada exitosamente!")
                        
                        # Create download button with selected guide name
                        if selected_guide_name:
                            # Clean the guide name for filename
                            filename = f"{current_subject} {selected_guide_name}.docx"
                        
                        # Store the guide data in session state for download tracking
                        st.session_state['generated_guide_data'] = {
                            'buffer': word_buffer,
                            'filename': filename,
                            'subject': current_subject,
                            'questions': ordered_questions,
                            'guide_name': selected_guide_name
                        }
                        
                        st.download_button(
                            label="📝 Descargar Guía Word",
                            data=word_buffer.getvalue(),
                            file_name=filename,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            type="primary",
                            on_click=track_guide_download,
                            args=(current_subject, ordered_questions, selected_guide_name, selected_count)
                        )
                        
                        # Show download tracking message if available
                        if 'download_tracking_message' in st.session_state:
                            if st.session_state.get('download_tracking_success', False):
                                st.success(st.session_state['download_tracking_message'])
                            else:
                                st.warning(st.session_state['download_tracking_message'])
                            
                            # Clear the message after showing it
                            del st.session_state['download_tracking_message']
                            del st.session_state['download_tracking_success']
                        
                        # Show summary
                        st.info(f"📊 **Resumen:** {selected_count} preguntas seleccionadas de {current_subject}")
                        st.info("💡 **Recomendación:** El documento Word contiene todas las preguntas con formato perfecto, imágenes y tablas preservadas.")
                        
                    else:
                        st.error("❌ Error al generar el documento Word")
        
            with col_clear:
                # Clear selection button
                if st.button("🗑️ Limpiar Selección"):
                    st.session_state['selected_questions'] = set()
                    st.session_state['selected_questions_ordered'] = []
                    st.session_state['question_positions'] = {}
                    st.success("✅ Selección limpiada")
                    st.rerun()
    
    else:
        st.info("No se encontraron preguntas con los filtros seleccionados.")

if __name__ == "__main__":
    main()

"""
Streamlit web application for generating custom educational guides.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import os
import sys
from io import BytesIO
from datetime import datetime
import shutil
import zipfile
import tempfile

# Add parent directory to path to import our modules
sys.path.append(str(Path(__file__).parent.parent))

from storage import StorageClient
from config import EXCELES_MAESTROS_DIR, SUBJECT_FOLDERS, STREAMLIT_CONFIG
from master_consolidator import MasterConsolidator

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

def preserve_scroll_position():
    """Add JavaScript to preserve scroll position on page reload."""
    st.markdown("""
    <script>
    // Store scroll position before page reload
    window.addEventListener('beforeunload', function() {
        sessionStorage.setItem('scrollPosition', window.pageYOffset);
    });
    
    // Restore scroll position after page load with delay
    window.addEventListener('load', function() {
        setTimeout(function() {
            const scrollPosition = sessionStorage.getItem('scrollPosition');
            if (scrollPosition) {
                window.scrollTo({
                    top: parseInt(scrollPosition),
                    behavior: 'instant'
                });
            }
        }, 100);
    });
    
    // Also restore on DOM content loaded
    document.addEventListener('DOMContentLoaded', function() {
        setTimeout(function() {
            const scrollPosition = sessionStorage.getItem('scrollPosition');
            if (scrollPosition) {
                window.scrollTo({
                    top: parseInt(scrollPosition),
                    behavior: 'instant'
                });
            }
        }, 50);
    });
    </script>
    """, unsafe_allow_html=True)

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
            return load_ciencias_combined_data(storage, consolidator)
        
        # Try to load existing master file
        master_file = EXCELES_MAESTROS_DIR / f"excel_maestro_{subject.lower()}.xlsx"
        
        if storage.exists(str(master_file)):
            df = pd.read_excel(master_file)
            return df
        else:
            # If master file doesn't exist, try to consolidate
            st.warning(f"Master file not found for {subject}. Attempting to consolidate...")
            df, _ = consolidator.consolidate_and_save(subject)
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
                        combined_dfs.append(df)
                        st.info(f"✅ Loaded {len(df)} questions from {subject}")
                else:
                    # If master file doesn't exist, try to consolidate
                    st.warning(f"Master file not found for {subject}. Attempting to consolidate...")
                    df, _ = consolidator.consolidate_and_save(subject)
                    if not df.empty:
                        df['Subject_Source'] = subject
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

def sort_questions_by_criteria(ordered_questions: list, df: pd.DataFrame, sort_by: str) -> list:
    """
    Sort questions by specified criteria.
    
    Args:
        ordered_questions: Current ordered list of questions
        df: DataFrame with question data
        sort_by: 'area' or 'subject'
        
    Returns:
        Sorted list of questions
    """
    if not ordered_questions:
        return ordered_questions
    
    # Get data for selected questions
    selected_df = df[df['PreguntaID'].isin(ordered_questions)]
    
    if sort_by == 'area':
        # Sort by area temática
        sorted_df = selected_df.sort_values('Área temática')
        return sorted_df['PreguntaID'].tolist()
    elif sort_by == 'subject':
        # Sort by subject source (for Ciencias)
        if 'Subject_Source' in selected_df.columns:
            sorted_df = selected_df.sort_values('Subject_Source')
            return sorted_df['PreguntaID'].tolist()
    
    return ordered_questions

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
    
    if filters.get('tipo'):
        filtered_df = filtered_df[filtered_df['Tipo'] == filters['tipo']]
    
    if filters.get('subject'):
        filtered_df = filtered_df[filtered_df['Subject_Source'] == filters['subject']]
    
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
                fig_subject = px.pie(
                    values=subject_counts.values,
                    names=subject_counts.index,
                    title=f"Distribución por Asignatura<br><sub>{total_questions} preguntas</sub>",
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig_subject.update_traces(
                    textposition='inside',
                    textinfo='value+percent',
                    texttemplate='%{value}<br>(%{percent})',
                    hovertemplate='<b>%{label}</b><br>Cantidad: %{value}<br>Porcentaje: %{percent}<extra></extra>'
                )
                fig_subject.update_layout(
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
                st.plotly_chart(fig_subject, use_container_width=True)
            
            with col2:
                # Area pie chart
                if 'Área temática' in selected_df.columns:
                    area_counts = selected_df['Área temática'].value_counts()
                    fig_area = px.pie(
                        values=area_counts.values,
                        names=area_counts.index,
                        title=f"Distribución por Área Temática<br><sub>{total_questions} preguntas</sub>",
                        color_discrete_sequence=px.colors.qualitative.Set2
                    )
                    fig_area.update_traces(
                        textposition='inside',
                        textinfo='value+percent',
                        texttemplate='%{value}<br>(%{percent})',
                        hovertemplate='<b>%{label}</b><br>Cantidad: %{value}<br>Porcentaje: %{percent}<extra></extra>'
                    )
                    fig_area.update_layout(
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
                    st.plotly_chart(fig_area, use_container_width=True)
        else:
            # For other subjects: show Area full width
            if 'Área temática' in selected_df.columns:
                area_counts = selected_df['Área temática'].value_counts()
                fig_area = px.pie(
                    values=area_counts.values,
                    names=area_counts.index,
                    title=f"Distribución por Área Temática<br><sub>{total_questions} preguntas</sub>",
                    color_discrete_sequence=px.colors.qualitative.Set2
                )
                fig_area.update_traces(
                    textposition='inside',
                    textinfo='value+percent',
                    texttemplate='%{value}<br>(%{percent})',
                    hovertemplate='<b>%{label}</b><br>Cantidad: %{value}<br>Porcentaje: %{percent}<extra></extra>'
                )
                fig_area.update_layout(
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
                st.plotly_chart(fig_area, use_container_width=True)
        
        # Second row: Habilidad and Dificultad charts
        col3, col4 = st.columns(2)
        
        with col3:
            # Habilidad pie chart
            if 'Habilidad' in selected_df.columns:
                habilidad_counts = selected_df['Habilidad'].value_counts()
                fig_habilidad = px.pie(
                    values=habilidad_counts.values,
                    names=habilidad_counts.index,
                    title=f"Distribución por Habilidad<br><sub>{total_questions} preguntas</sub>",
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                fig_habilidad.update_traces(
                    textposition='inside',
                    textinfo='value+percent',
                    texttemplate='%{value}<br>(%{percent})',
                    hovertemplate='<b>%{label}</b><br>Cantidad: %{value}<br>Porcentaje: %{percent}<extra></extra>'
                )
                fig_habilidad.update_layout(
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
                st.plotly_chart(fig_habilidad, use_container_width=True)
        
        with col4:
            # Dificultad pie chart
            if 'Dificultad' in selected_df.columns:
                dificultad_counts = selected_df['Dificultad'].value_counts()
                fig_dificultad = px.pie(
                    values=dificultad_counts.values,
                    names=dificultad_counts.index,
                    title=f"Distribución por Dificultad<br><sub>{total_questions} preguntas</sub>",
                    color_discrete_sequence=px.colors.qualitative.Antique
                )
                fig_dificultad.update_traces(
                    textposition='inside',
                    textinfo='value+percent',
                    texttemplate='%{value}<br>(%{percent})',
                    hovertemplate='<b>%{label}</b><br>Cantidad: %{value}<br>Porcentaje: %{percent}<extra></extra>'
                )
                fig_dificultad.update_layout(
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
            
            fig_subtema = px.pie(
                values=subtema_counts.values,
                names=subtema_counts.index,
                title=f"Distribución por Subtema<br><sub>{total_questions} preguntas</sub>",
                color_discrete_sequence=px.colors.qualitative.Vivid
            )
            fig_subtema.update_traces(
                textposition='inside',
                textinfo='value+percent',
                texttemplate='%{value}<br>(%{percent})',
                hovertemplate='<b>%{label}</b><br>Cantidad: %{value}<br>Porcentaje: %{percent}<extra></extra>'
            )
            fig_subtema.update_layout(
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="top",
                    y=-0.1,
                    xanchor="center",
                    x=0.5
                ),
                height=500,
                font=dict(size=12)
            )
            st.plotly_chart(fig_subtema, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error creating summary charts: {e}")

def main():
    """Main Streamlit application."""
    
    # Add scroll position preservation
    preserve_scroll_position()
    
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
    
    # Load data
    if st.sidebar.button("Cargar Preguntas", type="primary"):
        with st.spinner(f"Cargando preguntas de {subject}..."):
            df = load_master_excel(subject)
            
            if not df.empty:
                st.session_state['questions_df'] = df
                st.session_state['subject'] = subject
                
                # Clear all selections when loading a new subject
                st.session_state['selected_questions'] = set()
                st.session_state['selected_questions_ordered'] = []
                st.session_state['preview_question'] = None
                st.session_state['preview_file_path'] = None
                
                st.success(f"✅ Cargadas {len(df)} preguntas de {subject}")
                st.info("🔄 Selecciones anteriores limpiadas al cambiar de asignatura")
            else:
                st.error(f"No se pudieron cargar preguntas para {subject}")
    
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
    
    # Apply filters
    filters = {
        'area_tematica': area_filter,
        'dificultad': difficulty_filter,
        'habilidad': skill_filter,
        'subtema': subtema_filter
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
        
        # Display questions in a table
        for idx, row in filtered_df.iterrows():
            pregunta_id = row.get('PreguntaID', f'Q{idx+1}')
            
            col1, col2, col3 = st.columns([1, 8, 1])
            
            with col1:
                is_selected = pregunta_id in st.session_state['selected_questions']
                new_selection = st.checkbox("", value=is_selected, key=f"select_{pregunta_id}")
                
                # Only update state if selection actually changed
                if new_selection != is_selected:
                    if new_selection:
                        st.session_state['selected_questions'].add(pregunta_id)
                        # Add to ordered list if not already there
                        if pregunta_id not in st.session_state['selected_questions_ordered']:
                            st.session_state['selected_questions_ordered'].append(pregunta_id)
                    else:
                        st.session_state['selected_questions'].discard(pregunta_id)
                        # Remove from ordered list
                        if pregunta_id in st.session_state['selected_questions_ordered']:
                            st.session_state['selected_questions_ordered'].remove(pregunta_id)
            
            with col2:
                # Show subject source for Ciencias
                subject_info = ""
                if 'Subject_Source' in row and row['Subject_Source']:
                    subject_info = f" [{row['Subject_Source']}]"
                
                st.write(f"**{pregunta_id}**{subject_info} | "
                        f"Área: **{row.get('Área temática', 'N/A')}** | "
                        f"Dificultad: **{row.get('Dificultad', 'N/A')}** | "
                        f"Habilidad: **{row.get('Habilidad', 'N/A')}**")
                st.write(f"{row.get('Conocimiento/Subtema', 'Sin subtema')}")
            
            with col3:
                if st.button("👁️", key=f"preview_{pregunta_id}", help="Ver pregunta"):
                    # Store the question to preview in session state
                    st.session_state['preview_question'] = pregunta_id
                    st.session_state['preview_file_path'] = row.get('Ruta relativa', '')
                    # Don't rerun here - let the preview show below
            
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
            
            # Drag and Drop Interface
            st.write("**🖱️ Reordenar preguntas:**")
            
            # Add sorting buttons inside the reorder section
            col_sort1, col_sort2, col_sort3 = st.columns(3)
            
            with col_sort1:
                 # Only show subject sort for Ciencias
                if current_subject == "Ciencias" and 'Subject_Source' in selected_df.columns:
                    if st.button("📚 Ordenar por Asignatura", key="sort_by_subject", help="Ordenar preguntas por Asignatura"):
                        sorted_questions = sort_questions_by_criteria(ordered_questions, selected_df, 'subject')
                        st.session_state['selected_questions_ordered'] = sorted_questions
                        st.success("✅ Preguntas ordenadas por asignatura")
                        st.rerun()
                else:
                    if st.button("📊 Ordenar por Área", key="sort_by_area", help="Ordenar preguntas por área temática"):
                        sorted_questions = sort_questions_by_criteria(ordered_questions, selected_df, 'area')
                        st.session_state['selected_questions_ordered'] = sorted_questions
                        st.success("✅ Preguntas ordenadas por área temática")
                        st.rerun()

            
            with col_sort2:
                if current_subject == "Ciencias" and 'Subject_Source' in selected_df.columns:
                    if st.button("📊 Ordenar por Área", key="sort_by_area", help="Ordenar preguntas por área temática"):
                        sorted_questions = sort_questions_by_criteria(ordered_questions, selected_df, 'area')
                        st.session_state['selected_questions_ordered'] = sorted_questions
                        st.success("✅ Preguntas ordenadas por área temática")
                        st.rerun()

            
            with col_sort3:
                st.write("")  # Empty space for alignment
            
            st.markdown("---")
            
            # Info box moved below the line
            st.info("💡 Selecciona una pregunta y elige su nueva posición para reordenar")
            
            # Question selection for moving
            if len(ordered_questions) > 1:
                col_move1, col_move2, col_move3 = st.columns([2, 1, 2])
                
                with col_move1:
                    # Select question to move
                    question_options = {f"{i+1}. {qid}": qid for i, qid in enumerate(ordered_questions)}
                    selected_question_display = st.selectbox(
                        "Seleccionar pregunta a mover:",
                        options=list(question_options.keys()),
                        key="drag_question_select"
                    )
                    selected_question_id = question_options[selected_question_display]
                
                with col_move2:
                    st.write("")  # Empty space
                    st.markdown("<div style='text-align: center; font-size: 24px; margin-top: 20px;'>➡️</div>", unsafe_allow_html=True)  # Bigger centered arrow
                
                with col_move3:
                    # Select target position
                    current_position = ordered_questions.index(selected_question_id)
                    position_options = []
                    
                    # Create position options with context
                    for i in range(len(ordered_questions)):
                        if i == current_position:
                            position_options.append(f"Posición {i+1} (actual)")
                        elif i == 0:
                            position_options.append(f"Posición {i+1} (inicio)")
                        elif i == len(ordered_questions) - 1:
                            position_options.append(f"Posición {i+1} (final)")
                        else:
                            # Show what question will be after this position
                            next_question = ordered_questions[i] if i < len(ordered_questions) else "final"
                            position_options.append(f"Posición {i+1} (antes de {next_question})")
                    
                    target_position_display = st.selectbox(
                        "Mover a posición:",
                        options=position_options,
                        index=current_position,
                        key="drop_position_select"
                    )
                    target_position = position_options.index(target_position_display)
                
                # Move button
                if st.button("🔄 Mover Pregunta", key="move_question_btn", type="primary"):
                    if target_position != current_position:
                        # Remove question from current position
                        updated_list = [q for q in ordered_questions if q != selected_question_id]
                        # Insert at new position
                        updated_list.insert(target_position, selected_question_id)
                        st.session_state['selected_questions_ordered'] = updated_list
                        st.success(f"✅ Pregunta {selected_question_id} movida a posición {target_position + 1}")
                        st.rerun()
                    else:
                        st.info("La pregunta ya está en esa posición")
                
            
            st.markdown("---")
            
            # Display each selected question with controls
            for i, pregunta_id in enumerate(ordered_questions):
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
                    
                    st.write(f"**{i+1}.** {pregunta_id}{subject_info} | "
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
                        # Remove from ordered list
                        if pregunta_id in st.session_state['selected_questions_ordered']:
                            st.session_state['selected_questions_ordered'].remove(pregunta_id)
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
            
            # Generate guide section
            st.markdown("---")
            col_generate, col_clear = st.columns([3, 1])
            
            with col_generate:
                # Generate guide button
                if st.button("📝 Generar Guía Word", type="primary"):
                    with st.spinner("Generando documento Word..."):
                        # Create Word document using ordered questions
                        word_buffer = create_word_document(
                            ordered_questions, 
                            df, 
                            current_subject
                        )
                    
                    if word_buffer:
                        st.success("🎉 ¡Guía Word generada exitosamente!")
                        
                        # Create download button
                        st.download_button(
                            label="📝 Descargar Guía Word",
                                data=word_buffer.getvalue(),
                                file_name=f"guia_{current_subject.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            type="primary"
                            )
                        
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
                    st.rerun()
    
    else:
        st.info("No se encontraron preguntas con los filtros seleccionados.")

if __name__ == "__main__":
    main()

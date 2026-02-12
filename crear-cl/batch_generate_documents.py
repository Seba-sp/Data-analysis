"""
Batch document generation from debug TXT + source DOCX files.

Expected filenames:
  - debug_questions_improved_{id}.txt
  - {id}.docx

Produces:
  - {id}-Preguntas+Texto.docx
  - {id}-Preguntas Datos.xlsx
"""
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Optional

from utils.document_generator import DocumentGenerator


DEBUG_PATTERN = re.compile(r"^debug_questions_improved_(.+)\.txt$", re.IGNORECASE)


def read_debug_file(filepath: str) -> str:
    """Read debug file content and extract raw response."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove markdown bold markers
    if "**" in content:
        content = content.replace("**", "")

    # Extract raw response (remove header if present)
    if '=== RAW RESPONSE' in content:
        parts = content.split('===', 2)
        if len(parts) >= 3:
            return parts[2].strip()

    return content


def find_debug_files(txt_folder: str) -> List[Tuple[str, str]]:
    """
    Find debug TXT files and extract article IDs.

    Returns list of (article_id, filepath).
    """
    results: List[Tuple[str, str]] = []
    for file in Path(txt_folder).glob("debug_questions_improved_*.txt"):
        match = DEBUG_PATTERN.match(file.name)
        if not match:
            continue
        article_id = match.group(1).strip()
        if article_id:
            results.append((article_id, str(file)))
    return sorted(results, key=lambda x: x[0].lower())


def resolve_docx_path(docx_folder: str, article_id: str) -> str:
    """Build absolute path to source DOCX for an article."""
    filename = f"{article_id}.docx"
    return os.path.abspath(os.path.join(docx_folder, filename))


def parse_paes_format(response_text: str) -> dict:
    """Parse PAES-format response including article text and questions."""
    result = {'article_text': '', 'questions': []}

    lectura_match = re.search(r'(?:###\s*)?A\)\s*LECTURA', response_text, re.IGNORECASE)
    if lectura_match:
        texto_match = re.search(r'\*{0,2}TEXTO\*{0,2}', response_text[lectura_match.start():], re.IGNORECASE)
        if texto_match:
            texto_start = lectura_match.start() + texto_match.end()
            preguntas_match = re.search(r'(?:###\s*)?B\)\s*PREGUNTAS', response_text, re.IGNORECASE)
            if preguntas_match:
                texto_end = preguntas_match.start()
                article_text = response_text[texto_start:texto_end].strip()
                article_text = re.sub(r'\n\*{3,}\n', '\n\n', article_text)
                result['article_text'] = article_text

    preguntas_match = re.search(r'(?:###\s*)?B\)\s*PREGUNTAS', response_text, re.IGNORECASE)
    if not preguntas_match:
        return result

    preguntas_start = preguntas_match.end()
    claves_match = re.search(r'(?:###\s*)?C\)\s*CLAVES', response_text, re.IGNORECASE)
    if claves_match:
        preguntas_section = response_text[preguntas_start:claves_match.start()]
        claves_section = response_text[claves_match.end():]
    else:
        preguntas_section = response_text[preguntas_start:]
        claves_section = ""

    questions = parse_preguntas_section(preguntas_section)
    if claves_section:
        parse_claves_section(claves_section, questions)

    result['questions'] = questions
    return result


def parse_preguntas_section(section_text: str) -> list:
    """Parse questions from PREGUNTAS section."""
    questions = []
    lines = section_text.split('\n')
    current_q = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        q_match = re.match(r'^\*{0,2}(\d+)\.\s*\[([^\]]+)\]\*{0,2}\s*(.*)$', line)
        if q_match:
            if current_q:
                questions.append(current_q)
            current_q = {
                'number': int(q_match.group(1)),
                'habilidad': q_match.group(2).strip(),
                'question': q_match.group(3).strip(),
                'alternatives': {},
                'clave': '',
                'justification': ''
            }
            continue

        q_simple = re.match(r'^(\d+)\.\s*(.+)$', line)
        if q_simple and not current_q:
            current_q = {
                'number': int(q_simple.group(1)),
                'habilidad': '',
                'question': q_simple.group(2).strip(),
                'alternatives': {},
                'clave': '',
                'justification': ''
            }
            continue

        if not current_q:
            continue

        alt_match = re.match(r'^([ABCD])\)\s*(.+)$', line)
        if alt_match:
            letter = alt_match.group(1)
            text = alt_match.group(2).strip()
            current_q['alternatives'][letter] = text
            continue

        resp_match = re.match(r'^\*{0,2}Respuesta\s+correcta\s*:?\s*\*{0,2}\s*([ABCD])\*{0,2}', line, re.IGNORECASE)
        if resp_match:
            current_q['clave'] = resp_match.group(1)
            continue

        resp_alt = re.match(r'^\*{0,2}Correcta\s*:?\s*\*{0,2}\s*([ABCD])\*{0,2}', line, re.IGNORECASE)
        if resp_alt:
            current_q['clave'] = resp_alt.group(1)
            continue

        just_match = re.match(r'^\*{0,2}Justificaci[o\u00f3]n\s*:?\*{0,2}\s*(.+)$', line, re.IGNORECASE)
        if just_match:
            current_q['justification'] = just_match.group(1).strip()
            continue

        if current_q.get('justification') and not re.match(r'^\d+\.', line):
            current_q['justification'] += ' ' + line
            continue

        if not current_q['question']:
            current_q['question'] = line
            continue

    if current_q:
        questions.append(current_q)

    return questions


def parse_claves_section(section_text: str, questions: list):
    """Parse CLAVES section and update questions with any missing data."""
    clave_pattern = r'(\d+)\)\s*\*{0,2}([ABCD])\*{0,2}\.?\s*(.+?)(?=\n\d+\)|$)'

    for match in re.finditer(clave_pattern, section_text, re.DOTALL | re.IGNORECASE):
        q_num = int(match.group(1))
        clave = match.group(2)
        justif = match.group(3).strip()

        for q in questions:
            if q['number'] == q_num:
                if not q['clave']:
                    q['clave'] = clave
                if not q['justification'] or len(justif) > len(q['justification']):
                    q['justification'] = justif
                break


def process_one(
    article_id: str,
    debug_path: str,
    docx_path: str,
    output_folder: str,
    doc_generator: DocumentGenerator
) -> bool:
    """Process a single debug TXT + DOCX pair."""
    print(f"\n{'='*80}")
    print(f"Article ID: {article_id}")
    print(f"TXT:  {debug_path}")
    print(f"DOCX: {docx_path}")
    print('='*80)

    if not os.path.exists(docx_path):
        print(f"[ERROR] DOCX not found: {docx_path}")
        return False

    try:
        raw_response = read_debug_file(debug_path)
        parsed = parse_paes_format(raw_response)

        if not parsed or 'questions' not in parsed:
            print("[ERROR] Failed to parse questions from debug TXT")
            return False

        questions_list = parsed.get('questions', [])
        if not questions_list:
            print("[ERROR] No questions found in parsed data")
            return False

        # Output paths
        word_path = os.path.join(output_folder, f"{article_id}-Preguntas+Texto.docx")
        excel_path = os.path.join(output_folder, f"{article_id}-Preguntas Datos.xlsx")

        # Generate merged Word (article text from DOCX + questions)
        doc_generator.merge_text_and_questions_docx(
            source_docx_path=docx_path,
            questions=parsed,
            output_path=word_path,
            title=""
        )
        print(f"[OK] Word: {word_path}")

        # Generate Excel
        doc_generator.generate_questions_excel(parsed, excel_path)
        print(f"[OK] Excel: {excel_path}")

        return True

    except Exception as e:
        print(f"[ERROR] Failed to process {article_id}: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_batch_from_debug(
    txt_folder: str,
    docx_folder: str,
    output_folder: Optional[str] = None
) -> None:
    """Run batch generation using debug TXT + DOCX sources."""
    if not os.path.isdir(txt_folder):
        print(f"[ERROR] TXT folder not found: {txt_folder}")
        return
    if not os.path.isdir(docx_folder):
        print(f"[ERROR] DOCX folder not found: {docx_folder}")
        return

    output_folder = output_folder or docx_folder
    os.makedirs(output_folder, exist_ok=True)

    debug_files = find_debug_files(txt_folder)
    if not debug_files:
        print(f"[WARNING] No debug TXT files found in: {txt_folder}")
        print("Expected pattern: debug_questions_improved_{id}.txt")
        return

    print("="*80)
    print("BATCH DEBUG GENERATION")
    print("="*80)
    print(f"TXT folder:  {os.path.abspath(txt_folder)}")
    print(f"DOCX folder: {os.path.abspath(docx_folder)}")
    print(f"Output:      {os.path.abspath(output_folder)}")
    print(f"Files found: {len(debug_files)}")
    print("="*80)

    doc_generator = DocumentGenerator()

    results = {"success": 0, "failed": 0}
    for article_id, debug_path in debug_files:
        docx_path = resolve_docx_path(docx_folder, article_id)
        ok = process_one(
            article_id,
            debug_path,
            docx_path,
            output_folder,
            doc_generator
        )
        if ok:
            results["success"] += 1
        else:
            results["failed"] += 1

    print("\n" + "="*80)
    print("BATCH DEBUG GENERATION COMPLETE")
    print("="*80)
    print(f"Total:     {len(debug_files)}")
    print(f"Success:   {results['success']}")
    print(f"Failed:    {results['failed']}")
    print("="*80)


def _extract_id_from_debug_filename(debug_path: str) -> Optional[str]:
    filename = os.path.basename(debug_path)
    match = DEBUG_PATTERN.match(filename)
    if not match:
        return None
    return match.group(1).strip() or None


def _extract_id_from_docx_filename(docx_path: str) -> Optional[str]:
    filename = os.path.basename(docx_path)
    if not filename.lower().endswith(".docx"):
        return None
    return os.path.splitext(filename)[0].strip() or None


def run_single_from_debug(
    txt_file: str,
    docx_file: str,
    output_folder: Optional[str] = None
) -> bool:
    """Run single-file generation using one debug TXT + one DOCX."""
    if not os.path.isfile(txt_file):
        print(f"[ERROR] TXT file not found: {txt_file}")
        return False
    if not os.path.isfile(docx_file):
        print(f"[ERROR] DOCX file not found: {docx_file}")
        return False

    txt_id = _extract_id_from_debug_filename(txt_file)
    docx_id = _extract_id_from_docx_filename(docx_file)

    if not txt_id:
        print("[ERROR] TXT filename must match: debug_questions_improved_{id}.txt")
        return False
    if not docx_id:
        print("[ERROR] DOCX filename must match: {id}.docx")
        return False
    if txt_id != docx_id:
        print(f"[ERROR] ID mismatch: TXT id '{txt_id}' vs DOCX id '{docx_id}'")
        print("Please select matching IDs.")
        return False

    output_folder = output_folder or os.path.dirname(os.path.abspath(docx_file))
    os.makedirs(output_folder, exist_ok=True)

    doc_generator = DocumentGenerator()

    return process_one(
        txt_id,
        txt_file,
        docx_file,
        output_folder,
        doc_generator
    )

def main():
    """CLI entry point (txt_folder, docx_folder, output_folder optional)."""
    if len(sys.argv) < 3:
        print("ERROR: Missing arguments")
        print()
        print("Usage:")
        print(f"  python {os.path.basename(__file__)} <txt_folder> <docx_folder> [output_folder]")
        sys.exit(1)

    txt_folder = sys.argv[1]
    docx_folder = sys.argv[2]
    output_folder = sys.argv[3] if len(sys.argv) > 3 else None

    run_batch_from_debug(txt_folder, docx_folder, output_folder)


if __name__ == '__main__':
    main()

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH

def get_alignment_name(alignment):
    if alignment == WD_ALIGN_PARAGRAPH.LEFT: return "LEFT"
    if alignment == WD_ALIGN_PARAGRAPH.CENTER: return "CENTER"
    if alignment == WD_ALIGN_PARAGRAPH.RIGHT: return "RIGHT"
    if alignment == WD_ALIGN_PARAGRAPH.JUSTIFY: return "JUSTIFY"
    return str(alignment)

def inspect_docx(filename):
    print(f"\n--- Inspecting {filename} (Questions part) ---")
    try:
        doc = docx.Document(filename)
        
        # Check paragraphs 20-35 (likely questions)
        start = 20
        end = 40
        print(f"\n[Paragraphs {start}-{end}]")
        for i, p in enumerate(doc.paragraphs[start:end]): 
            idx = start + i
            text_snippet = p.text[:50] + "..." if len(p.text) > 50 else p.text
            print(f"\nParagraph {idx}: '{text_snippet}'")
            print(f"  Alignment: {get_alignment_name(p.alignment)}")
            
            runs = p.runs
            if runs:
                r = runs[0]
                size = r.font.size if r.font.size else "Inherited"
                name = r.font.name if r.font.name else "Inherited"
                print(f"  Run 0 Font: {name} (Size: {size}, Bold: {r.font.bold})")

    except Exception as e:
        print(f"Error reading {filename}: {e}")

if __name__ == "__main__":
    inspect_docx("expected format.docx")

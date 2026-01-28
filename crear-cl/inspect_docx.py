import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH

def get_alignment_name(alignment):
    if alignment == WD_ALIGN_PARAGRAPH.LEFT: return "LEFT"
    if alignment == WD_ALIGN_PARAGRAPH.CENTER: return "CENTER"
    if alignment == WD_ALIGN_PARAGRAPH.RIGHT: return "RIGHT"
    if alignment == WD_ALIGN_PARAGRAPH.JUSTIFY: return "JUSTIFY"
    return str(alignment)

def inspect_docx(filename):
    print(f"\n--- Inspecting {filename} ---")
    try:
        doc = docx.Document(filename)
        
        # Check Styles
        print("\n[Styles]")
        for style in doc.styles:
            if style.type == 1: # Paragraph style
                font = style.font
                print(f"Style '{style.name}': Font={font.name}, Size={font.size}")

        print("\n[Paragraphs Analysis]")
        for i, p in enumerate(doc.paragraphs[:15]): # Check first 15 paragraphs
            print(f"\nParagraph {i}: '{p.text[:50]}...'")
            print(f"  Style: {p.style.name}")
            print(f"  Alignment: {get_alignment_name(p.alignment)}")
            
            # Run details
            runs = p.runs
            if runs:
                r = runs[0]
                print(f"  Run 0 Font: {r.font.name} (Size: {r.font.size}, Bold: {r.font.bold})")
                
                # Check if font info is missing in run, check style
                if not r.font.name:
                    print(f"  (Inherits Font from style: {p.style.font.name})")
                if not r.font.size:
                    print(f"  (Inherits Size from style: {p.style.font.size})")

    except Exception as e:
        print(f"Error reading {filename}: {e}")

if __name__ == "__main__":
    inspect_docx("expected format.docx")

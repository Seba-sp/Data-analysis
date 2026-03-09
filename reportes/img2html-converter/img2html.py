#!/usr/bin/env python3
"""
img2html.py  --  Convierte una imagen JPEG o PNG en un HTML auto-contenido (data-URI).

Uso:
    python img2html.py imagen.jpg [ancho_mm alto_mm]
    python img2html.py imagen.png [ancho_mm alto_mm]
Si no indicas ancho/alto, usará 210 mm x 297 mm (A-4 vertical).
El HTML se guardará con el mismo nombre que la imagen.

Formatos soportados: JPEG (.jpg, .jpeg) y PNG (.png)
"""

import sys, base64, pathlib, textwrap

def encode_image(path: pathlib.Path) -> str:
    """Encode image to data-URI, supporting only JPEG and PNG formats"""
    # Check file extension
    valid_extensions = {'.jpg', '.jpeg', '.png'}
    file_extension = path.suffix.lower()
    
    if file_extension not in valid_extensions:
        raise ValueError(f"Formato no soportado: {file_extension}. Solo se aceptan: {', '.join(valid_extensions)}")
    
    # Determine MIME type based on extension
    mime_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg', 
        '.png': 'image/png'
    }
    mime = mime_types[file_extension]
    
    # Read and encode the image
    try:
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{b64}"
    except Exception as e:
        raise ValueError(f"Error al leer la imagen {path}: {str(e)}")

def build_html(data_uri: str, w_mm: int, h_mm: int, filename: str) -> str:
    return textwrap.dedent(f"""\
        <!DOCTYPE html>
        <html lang="es">
        <head>
        <meta charset="utf-8">
        <title>{filename}</title>
        <style>
          html,body{{margin:0;padding:0;}}
          img.folio{{width:{w_mm}mm;height:{h_mm}mm;display:block;}}
        </style>
        </head>
        <body>
          <img class="folio" src="{data_uri}" alt="{filename}">
        </body>
        </html>
    """)

def validate_inputs(src_path: pathlib.Path, dst_path: pathlib.Path, w_mm: int, h_mm: int):
    """Validate input parameters"""
    # Check if source file exists
    if not src_path.exists():
        sys.exit(f"❌ Error: El archivo de origen no existe: {src_path}")
    
    # Check if source file is readable
    if not src_path.is_file():
        sys.exit(f"❌ Error: El origen no es un archivo válido: {src_path}")
    
    # Validate dimensions
    if w_mm <= 0 or h_mm <= 0:
        sys.exit(f"❌ Error: Las dimensiones deben ser positivas: {w_mm}mm x {h_mm}mm")
    
    # Check if output directory exists
    dst_dir = dst_path.parent
    if dst_dir and not dst_dir.exists():
        try:
            dst_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            sys.exit(f"❌ Error: No se puede crear el directorio de salida: {e}")

def main():
    if len(sys.argv) < 2:
        sys.exit("Uso: python img2html.py imagen.jpg [ancho_mm alto_mm]")

    src = pathlib.Path(sys.argv[1]).expanduser()
    w_mm = int(sys.argv[2]) if len(sys.argv) > 2 else 210
    h_mm = int(sys.argv[3]) if len(sys.argv) > 3 else 297
    
    # Generate output HTML file with same name as image
    dst = src.with_suffix('.html')

    # Validate inputs
    validate_inputs(src, dst, w_mm, h_mm)

    try:
        # Get the original filename without extension
        original_filename = src.stem
        html = build_html(encode_image(src), w_mm, h_mm, original_filename)
        dst.write_text(html, encoding="utf-8")
        print(f"✅ HTML guardado en: {dst}")
    except ValueError as e:
        sys.exit(f"❌ Error: {e}")
    except Exception as e:
        sys.exit(f"❌ Error inesperado: {e}")

if __name__ == "__main__":
    main() 
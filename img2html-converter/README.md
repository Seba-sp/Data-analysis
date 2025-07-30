# Image to HTML Converter

This project contains a Python script that converts images to HTML files with embedded data-URI encoding.

## Features

- Converts images to self-contained HTML files
- Embeds images as base64 data-URI
- Configurable dimensions (defaults to A4 size)
- Supports JPEG (.jpg, .jpeg) and PNG (.png) formats only

## Usage

```bash
python img2html.py imagen.jpg [ancho_mm alto_mm]
```

### Parameters

- `imagen.jpg`: Source image file path
- `ancho_mm`: Width in millimeters (optional, default: 210mm)
- `alto_mm`: Height in millimeters (optional, default: 297mm)

**Note:** The HTML file will be automatically created with the same name as the image file.

### Examples

```bash
# Convert JPEG image with default A4 size
python img2html.py imagen.jpg

# Convert PNG image with custom dimensions
python img2html.py imagen.png 150 200

# Convert image with square dimensions
python img2html.py imagen.jpg 200 200
```

## Requirements

- Python 3.6+
- No external dependencies required (uses only standard library)

## How it works

1. The script reads the image file and encodes it as base64
2. Creates a data-URI with the appropriate MIME type
3. Generates an HTML file with embedded CSS styling
4. The image is displayed with the specified dimensions

## Output

The generated HTML file will contain:
- A self-contained HTML document
- Embedded CSS for proper image sizing
- The image encoded as a data-URI
- No external dependencies

## Supported Image Formats

- JPEG (.jpg, .jpeg)
- PNG (.png)

**Note:** Only JPEG and PNG formats are supported for optimal compatibility and file size. 
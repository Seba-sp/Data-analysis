import boto3, pathlib

REGION = "us-east-2"             # cambia si usas otra región
TEMPLATE_NAME = "links_zoom_clases"  # el nombre que usarás al enviar

# Rutas de los archivos de plantilla
html_path = pathlib.Path("plantilla.html")
text_path = pathlib.Path("plantilla.txt")
subject = "Links Clases"

html = html_path.read_text(encoding="utf-8")
text = text_path.read_text(encoding="utf-8")

ses = boto3.client("sesv2", region_name=REGION)

content = {"Subject": subject, "Html": html, "Text": text}

# Intenta crear; si ya existe, actualiza
try:
    ses.create_email_template(TemplateName=TEMPLATE_NAME, TemplateContent=content)
    print(f"Creada plantilla '{TEMPLATE_NAME}'")
except ses.exceptions.AlreadyExistsException:
    ses.update_email_template(TemplateName=TEMPLATE_NAME, TemplateContent=content)
    print(f"Actualizada plantilla '{TEMPLATE_NAME}'")
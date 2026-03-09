"""
Email template constants for the test_de_eje report type.

Each report type can provide its own subject and body by creating an
``email_template.py`` module in its plugin directory. The runner resolves
this module at send time — no changes to shared runner or sender code needed.
"""

SUBJECT = "Tu plan de estudio personalizado"

BODY = """Hola,

Has completado tu Test de Eje correctamente. En el informe adjunto encontrarás tú plan de estudio personalizado con las lecciones a realizar

Cualquier consulta, estamos aquí para ayudarte.

Un abrazo a la distancia
"""

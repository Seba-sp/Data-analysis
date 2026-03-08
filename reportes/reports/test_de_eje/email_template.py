"""
Email template constants for the test_de_eje report type.

Each report type can provide its own subject and body by creating an
``email_template.py`` module in its plugin directory. The runner resolves
this module at send time — no changes to shared runner or sender code needed.
"""

SUBJECT = "Tu informe Test de Eje"

BODY = """Hola,

Has completado tu Test de Eje correctamente. En el informe adjunto encontrarás:
1. Tu nivel de dominio por unidad
2. Un plan de estudio personalizado con las lecciones recomendadas
3. El detalle de tu rendimiento en cada pregunta

Cualquier consulta, estamos aquí para ayudarte.

Un abrazo a la distancia
"""

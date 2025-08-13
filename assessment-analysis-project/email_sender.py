#!/usr/bin/env python3
"""
Email Sender - Sends comprehensive assessment reports via email
"""

import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class EmailSender:
    def __init__(self):
        """Initialize email sender"""
        self.email_from = os.getenv("EMAIL_FROM")
        self.email_pass = os.getenv("EMAIL_PASS")
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        
        if not all([self.email_from, self.email_pass]):
            raise ValueError("Missing required environment variables: EMAIL_FROM, EMAIL_PASS")
    
    def send_comprehensive_report_email(self, recipient_email: str, pdf_content: bytes, 
                                      username: str, filename: str, drive_link: str = None) -> bool:
        """
        Send comprehensive assessment report email
        
        Args:
            recipient_email: Email address to send to
            pdf_content: PDF content as bytes
            username: Username for personalization
            filename: Filename for the attachment
            drive_link: Optional Google Drive link
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            logger.info(f"Sending comprehensive report email to {recipient_email}")
            
            # Create email message
            msg = MIMEMultipart()
            msg["Subject"] = f"Plan de Estudio Completo - {username}"
            msg["From"] = self.email_from
            msg["To"] = recipient_email
            
            # Email body
            body = f"""Hola {username},

Has completado exitosamente todas las evaluaciones de diagnóstico. Adjuntamos tu plan de estudio completo con los resultados detallados.

En este informe encontrarás:
- Resultados de todas las evaluaciones (M1, CL, CIEN, HYST)
- Análisis por lección y materia
- Recomendaciones para tu plan de estudio

Evaluaciones incluidas:
- M1: Análisis de lecciones aprobadas/reprobadas
- CL: Porcentajes de acierto por lección
- CIEN: Análisis por materia y lección
- HYST: Análisis de lecciones aprobadas/reprobadas

Recuerda que para aprobar una lección en M1, CIEN y HYST debes responder correctamente todas las preguntas relacionadas con esa lección.

Si tienes alguna pregunta sobre tus resultados, no dudes en contactarnos.

Saludos,
Tu equipo de aprendizaje
"""
            
            if drive_link:
                body += f"\n\nTambién puedes acceder al informe desde Google Drive: {drive_link}"
            
            msg.attach(MIMEText(body, "plain", "utf-8"))
            
            # Attach PDF report
            pdf_attachment = MIMEBase("application", "pdf")
            pdf_attachment.set_payload(pdf_content)
            encoders.encode_base64(pdf_attachment)
            pdf_attachment.add_header(
                "Content-Disposition",
                f"attachment; filename= {filename}"
            )
            msg.attach(pdf_attachment)
            
            logger.info(f"PDF attached: {filename}")
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_from, self.email_pass)
                server.send_message(msg)
            
            logger.info(f"Comprehensive report email sent successfully to {recipient_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending comprehensive report email to {recipient_email}: {str(e)}")
            return False
    
 
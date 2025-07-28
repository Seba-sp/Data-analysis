#!/usr/bin/env python3
"""
Email sender for individual student assessment reports
Handles sending PDF reports via email
"""

import os
import logging
import smtplib
from email.message import EmailMessage
from pathlib import Path
from storage import StorageClient

logger = logging.getLogger(__name__)

class EmailSender:
    def __init__(self):
        """Initialize email sender with SMTP configuration"""
        self.storage = StorageClient()
        
        # Email configuration
        self.email_from = os.getenv("EMAIL_FROM")
        self.email_pass = os.getenv("EMAIL_PASS")
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        
        # Validate configuration
        if not all([self.email_from, self.email_pass]):
            raise ValueError("EMAIL_FROM and EMAIL_PASS environment variables are required")
    
    def send_report_email(self, recipient_email: str, report_path: Path, username: str) -> bool:
        """
        Send assessment report via email
        
        Args:
            recipient_email: Recipient's email address
            report_path: Path to PDF report
            username: Student's username for personalization
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            logger.info(f"Sending report email to {recipient_email}")
            
            # Create email message
            msg = EmailMessage()
            msg["Subject"] = "Tu informe de resultados - Diagnóstico"
            msg["From"] = self.email_from
            msg["To"] = recipient_email
            
            # Email body
            body = f"""Hola {username},

Has completado exitosamente tu evaluación de diagnóstico. Adjuntamos tu informe personalizado con los resultados.

En este informe encontrarás:
- Tu nivel asignado
- Áreas donde necesitas reforzar conocimientos
- Recomendaciones para tu aprendizaje

Si tienes alguna pregunta sobre tus resultados, no dudes en contactarnos.

Saludos,
Tu equipo de aprendizaje
"""
            
            msg.set_content(body)
            
            # Attach PDF report
            if self.storage.exists(str(report_path)):
                pdf_content = self.storage.read_bytes(str(report_path))
                msg.add_attachment(
                    pdf_content,
                    maintype="application",
                    subtype="pdf",
                    filename=report_path.name
                )
                logger.info(f"PDF attached: {report_path.name}")
            else:
                logger.error(f"Report file not found: {report_path}")
                return False
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_from, self.email_pass)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {recipient_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email to {recipient_email}: {str(e)}")
            return False
    
    def send_error_notification(self, error_details: str) -> bool:
        """
        Send error notification to admin (optional)
        
        Args:
            error_details: Details about the error
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        try:
            admin_email = os.getenv("ADMIN_EMAIL")
            if not admin_email:
                logger.warning("ADMIN_EMAIL not configured, skipping error notification")
                return False
            
            msg = EmailMessage()
            msg["Subject"] = "Webhook Service Error Alert"
            msg["From"] = self.email_from
            msg["To"] = admin_email
            
            body = f"""Webhook Service Error Alert

An error occurred in the webhook service:

{error_details}

Please check the logs for more details.
"""
            
            msg.set_content(body)
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_from, self.email_pass)
                server.send_message(msg)
            
            logger.info(f"Error notification sent to {admin_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending error notification: {str(e)}")
            return False 
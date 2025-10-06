#!/usr/bin/env python3
"""
Email Sender - Sends comprehensive assessment reports via email
"""

import os
import logging
import smtplib
import pandas as pd
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv
from typing import Dict, Optional

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
        self.analysis_data = None
        
        if not all([self.email_from, self.email_pass]):
            raise ValueError("Missing required environment variables: EMAIL_FROM, EMAIL_PASS")
        
        # Load analysis data
        self._load_analysis_data()
    
    def _load_analysis_data(self) -> None:
        """
        Load analysis data from CSV file
        """
        try:
            analysis_path = "data/analysis/analysis.csv"
            if os.path.exists(analysis_path):
                self.analysis_data = pd.read_csv(analysis_path)
                logger.info(f"Loaded analysis data with {len(self.analysis_data)} records")
            else:
                logger.warning(f"Analysis file not found: {analysis_path}")
                self.analysis_data = pd.DataFrame(columns=['email', 'username'])
        except Exception as e:
            logger.error(f"Error loading analysis data: {str(e)}")
            self.analysis_data = pd.DataFrame(columns=['email', 'username'])
    
    def get_username_for_email(self, email: str) -> str:
        """
        Get username for a given email from analysis data
        
        Args:
            email: Email address to look up
            
        Returns:
            Username if found, otherwise the email address
        """
        if self.analysis_data is not None:
            try:
                # Look for exact email match
                match = self.analysis_data[self.analysis_data['email'].str.lower() == email.lower()]
                if not match.empty:
                    username = match.iloc[0]['username']
                    if pd.notna(username) and username.strip():
                        return username.strip()
            except Exception as e:
                logger.warning(f"Error looking up username for {email}: {str(e)}")
        
        # Fallback to email address
        return email
    
    def send_comprehensive_report_email(self, recipient_email: str, pdf_content: bytes, 
                                      email_for_lookup: str, filename: str, drive_link: str = None) -> bool:
        """
        Send comprehensive assessment report email
        
        Args:
            recipient_email: Email address to send to
            pdf_content: PDF content as bytes
            email_for_lookup: Email to lookup username in analysis data
            filename: Filename for the attachment
            drive_link: Optional Google Drive link
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            logger.info(f"Sending comprehensive report email to {recipient_email}")
            
            # Get username from analysis data
            username = self.get_username_for_email(email_for_lookup)
            
            # Create email message
            msg = MIMEMultipart()
            msg["Subject"] = f"Asunto: Resultados de tu Ensayo Intensivo M30M"
            msg["From"] = self.email_from
            msg["To"] = recipient_email
            
            # Email body
            body = f"""Hola {username},

Adjunto encontrarás en PDF los resultados de los ensayos que realizaste dentro del Intensivo M30M.
📌 Ten en cuenta lo siguiente:
    
    1. El documento incluye únicamente los ensayos rendidos hasta el miércoles 3 de septiembre, previo al envío de este correo.

    2. Para los ensayos que realices después de esa fecha, tendrás disponible en la plataforma una tabla de conversión de puntajes para calcular tu resultado.

    
Sigue utilizando esta instancia para medir tu progreso y orientar mejor tus próximos estudios.
¡Vamos con todo rumbo a la PAES! 🚀

Un abrazo,
Equipo M30M
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

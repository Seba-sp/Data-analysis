#!/usr/bin/env python3
"""
Slack service for sending notifications
Project-agnostic service that can be used across multiple projects
Handles sending notifications to Slack channels with flexible message formatting
"""

import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

# Try to import Slack libraries
try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
    SLACK_AVAILABLE = True
except ImportError:
    SLACK_AVAILABLE = False
    logging.warning("Slack libraries not available. Install with: pip install slack-sdk")

logger = logging.getLogger(__name__)

class SlackService:
    def __init__(self, bot_token: Optional[str] = None, default_channel: Optional[str] = None):
        """
        Initialize Slack service
        
        Args:
            bot_token: Slack bot token (defaults to SLACK_BOT_TOKEN env var)
            default_channel: Default channel for notifications (defaults to SLACK_CHANNEL env var)
        """
        self.bot_token = bot_token or os.getenv('SLACK_BOT_TOKEN')
        self.default_channel = default_channel or os.getenv('SLACK_CHANNEL')
        self.client = None
        
        # Only try to initialize if we have the required token
        if self.bot_token:
            try:
                self.client = self._get_slack_client()
                logger.info("Slack service initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Slack service: {e}")
                self.client = None
        else:
            logger.info("Slack not configured (SLACK_BOT_TOKEN not set)")
            self.client = None
    
    def _get_slack_client(self) -> WebClient:
        """Initialize Slack client"""
        if not SLACK_AVAILABLE:
            raise ImportError("Slack libraries not available")
        
        if not self.bot_token:
            raise ValueError("SLACK_BOT_TOKEN environment variable not set")
        
        return WebClient(token=self.bot_token)
    
    def send_message(self, text: str, channel: Optional[str] = None, blocks: Optional[List[Dict]] = None) -> bool:
        """
        Send a simple text message to Slack
        
        Args:
            text: Message text
            channel: Channel to send to (defaults to default_channel)
            blocks: Optional Slack blocks for rich formatting
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            logger.warning("Slack not available, skipping message")
            return False
        
        channel = channel or self.default_channel
        if not channel:
            logger.error("No channel specified for Slack message")
            return False
        
        try:
            message_args = {
                'channel': channel,
                'text': text
            }
            if blocks:
                message_args['blocks'] = blocks
            
            self.client.chat_postMessage(**message_args)
            logger.info(f"Slack message sent to {channel}")
            return True
            
        except SlackApiError as e:
            logger.error(f"Slack API error: {e.response['error']}")
            return False
        except Exception as e:
            logger.error(f"Error sending Slack message: {e}")
            return False
    
    def send_course_analysis_notification(self, category: str, course_id: str, course_name: str, 
                                        drive_links: List[str], channel: Optional[str] = None) -> bool:
        """
        Send notification for course analysis completion
        
        Args:
            category: Course category
            course_id: Course ID
            course_name: Course name
            drive_links: List of Google Drive links to files
            channel: Channel to send to (defaults to default_channel)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            logger.warning("Slack not available, skipping notification")
            return False
        
        channel = channel or self.default_channel
        if not channel:
            logger.error("No channel specified for Slack notification")
            return False
        
        try:
            # Create message blocks
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"📊 Reporte de Análisis de Curso - {course_name} ({category})"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Categoría:* {category}\n*Curso:* {course_name}\n*ID del Curso:* {course_id}\n*Análisis completado:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    }
                }
            ]
            
            # Add file links
            if drive_links:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*📁 Archivos Generados:*"
                    }
                })
                
                for link in drive_links:
                    # Determine file type from link or filename
                    file_type = "Archivo"
                    if "file" in link.lower():
                        file_type = "PDF"
                    elif "spreadsheets" in link.lower():
                        file_type = "Excel"
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"• <{link}|Ver Archivo ({file_type})>"
                        }
                    })
            
            # Add divider
            blocks.append({"type": "divider"})
            
            # Add footer
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "🤖 Automatizado por el Pipeline de Análisis de Cursos"
                    }
                ]
            })
            
            # Create fallback text
            fallback_text = f"📊 Reporte de Análisis de Curso - {course_name} ({category})\nCategoría: {category}\nCurso: {course_name}\nID del Curso: {course_id}\nAnálisis completado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            if drive_links:
                fallback_text += f"\nArchivos generados: {len(drive_links)} archivos"
            
            # Send message
            self.client.chat_postMessage(
                channel=channel,
                text=fallback_text,  # Required for accessibility
                blocks=blocks
            )
            
            logger.info(f"Course analysis notification sent to {channel}")
            return True
            
        except SlackApiError as e:
            logger.error(f"Slack API error: {e.response['error']}")
            return False
        except Exception as e:
            logger.error(f"Error sending course analysis notification: {e}")
            return False
    
    def send_file_upload_notification(self, category: str, course_id: str, course_name: str, 
                                    uploaded_files: Dict[str, str], channel: Optional[str] = None) -> bool:
        """
        Send notification for file uploads
        
        Args:
            category: Course category
            course_id: Course ID
            course_name: Course name
            uploaded_files: Dictionary of {filename: drive_link}
            channel: Channel to send to (defaults to default_channel)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            logger.warning("Slack not available, skipping notification")
            return False
        
        channel = channel or self.default_channel
        if not channel:
            logger.error("No channel specified for Slack notification")
            return False
        
        if not uploaded_files:
            logger.info("No files uploaded, skipping notification")
            return True
        
        try:
            text = f"Se han subido los siguientes archivos para la categoría *{category}*, curso *{course_name}* ({course_id}):\n"
            for filename, link in uploaded_files.items():
                text += f"• <{link}|{filename}>\n"
            
            self.client.chat_postMessage(
                channel=channel,
                text=text
            )
            
            logger.info(f"File upload notification sent to {channel}")
            return True
            
        except SlackApiError as e:
            logger.error(f"Slack API error: {e.response['error']}")
            return False
        except Exception as e:
            logger.error(f"Error sending file upload notification: {e}")
            return False
    
    def send_custom_notification(self, title: str, content: str, attachments: Optional[List[Dict]] = None,
                               channel: Optional[str] = None) -> bool:
        """
        Send a custom notification with flexible formatting
        
        Args:
            title: Notification title
            content: Main content text
            attachments: Optional list of attachments/links
            channel: Channel to send to (defaults to default_channel)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            logger.warning("Slack not available, skipping notification")
            return False
        
        channel = channel or self.default_channel
        if not channel:
            logger.error("No channel specified for Slack notification")
            return False
        
        try:
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": title
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": content
                    }
                }
            ]
            
            # Add attachments if provided
            if attachments:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*📎 Archivos Adjuntos:*"
                    }
                })
                
                for attachment in attachments:
                    if isinstance(attachment, dict):
                        name = attachment.get('name', 'Archivo')
                        link = attachment.get('link', '#')
                        blocks.append({
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"• <{link}|{name}>"
                            }
                        })
                    else:
                        # Handle simple string attachments
                        blocks.append({
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"• {attachment}"
                            }
                        })
            
            # Add footer
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"🤖 Enviado el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    }
                ]
            })
            
            self.client.chat_postMessage(
                channel=channel,
                text=title,  # Fallback text
                blocks=blocks
            )
            
            logger.info(f"Custom notification sent to {channel}")
            return True
            
        except SlackApiError as e:
            logger.error(f"Slack API error: {e.response['error']}")
            return False
        except Exception as e:
            logger.error(f"Error sending custom notification: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if Slack service is available and configured"""
        return self.client is not None

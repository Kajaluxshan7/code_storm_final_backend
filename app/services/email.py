"""
Email Service
Email sending functionality for user verification and notifications
"""
from typing import List, Optional
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Email configuration
def get_email_config() -> ConnectionConfig:
    """Get email configuration"""
    return ConnectionConfig(
        MAIL_USERNAME=settings.MAIL_USERNAME,
        MAIL_PASSWORD=settings.MAIL_PASSWORD,
        MAIL_FROM=settings.MAIL_FROM,
        MAIL_PORT=settings.MAIL_PORT,
        MAIL_SERVER=settings.MAIL_SERVER,
        MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
        MAIL_STARTTLS=settings.MAIL_STARTTLS,
        MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
        USE_CREDENTIALS=settings.USE_CREDENTIALS,
        VALIDATE_CERTS=settings.VALIDATE_CERTS,
        TEMPLATE_FOLDER="app/templates/email"
    )


class EmailService:
    """Email service for sending various types of emails"""
    
    def __init__(self):
        self.config = get_email_config()
        self.fast_mail = FastMail(self.config)
    
    async def send_email_verification(
        self,
        email: str,
        first_name: str,
        verification_token: str
    ) -> bool:
        """Send email verification email"""
        try:
            logger.info(f"Preparing to send verification email to {email}")
            verification_url = f"{settings.FRONTEND_URL}/auth/verify-email?token={verification_token}"
            logger.info(f"Verification URL: {verification_url}")
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Verify Your Email - EduCapture</title>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
                    .button {{ display: inline-block; background: #667eea; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                    .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Welcome to EduCapture!</h1>
                    </div>
                    <div class="content">
                        <h2>Hi {first_name},</h2>
                        <p>Thank you for registering with EduCapture. To complete your registration and start uploading and enhancing your notes, please verify your email address.</p>
                        <p>Click the button below to verify your email:</p>
                        <a href="{verification_url}" class="button">Verify Email Address</a>
                        <p>Or copy and paste this link into your browser:</p>
                        <p style="word-break: break-all; color: #667eea;">{verification_url}</p>
                        <p>This verification link will expire in 24 hours for security reasons.</p>
                        <p>If you didn't create an account with EduCapture, please ignore this email.</p>
                    </div>
                    <div class="footer">
                        <p>© 2024 EduCapture. All rights reserved.</p>
                        <p>This is an automated message, please do not reply to this email.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            logger.info(f"Creating message schema for {email}")
            message = MessageSchema(
                subject="Verify Your Email - EduCapture",
                recipients=[email],
                body=html_content,
                subtype=MessageType.html
            )
            
            logger.info(f"Sending message via FastMail to {email}")
            await self.fast_mail.send_message(message)
            logger.info(f"Verification email sent successfully to {email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send verification email to {email}: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    async def send_password_reset(
        self,
        email: str,
        first_name: str,
        reset_token: str
    ) -> bool:
        """Send password reset email"""
        try:
            reset_url = f"{settings.FRONTEND_URL}/auth/reset-password?token={reset_token}"
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Reset Your Password - EduCapture</title>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
                    .button {{ display: inline-block; background: #667eea; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                    .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
                    .warning {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 15px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Password Reset Request</h1>
                    </div>
                    <div class="content">
                        <h2>Hi {first_name},</h2>
                        <p>We received a request to reset your password for your EduCapture account.</p>
                        <p>Click the button below to reset your password:</p>
                        <a href="{reset_url}" class="button">Reset Password</a>
                        <p>Or copy and paste this link into your browser:</p>
                        <p style="word-break: break-all; color: #667eea;">{reset_url}</p>
                        <div class="warning">
                            <strong>Important:</strong> This reset link will expire in 1 hour for security reasons. If you didn't request a password reset, please ignore this email and consider updating your account security.
                        </div>
                        <p>For your security, never share this link with anyone.</p>
                    </div>
                    <div class="footer">
                        <p>© 2024 EduCapture. All rights reserved.</p>
                        <p>This is an automated message, please do not reply to this email.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            message = MessageSchema(
                subject="Reset Your Password - EduCapture",
                recipients=[email],
                body=html_content,
                subtype=MessageType.html
            )
            
            await self.fast_mail.send_message(message)
            logger.info(f"Password reset email sent to {email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send password reset email to {email}: {str(e)}")
            return False
    
    async def send_welcome_email(
        self,
        email: str,
        first_name: str,
        auth_provider: str = "email"
    ) -> bool:
        """Send welcome email after successful verification"""
        try:
            dashboard_url = f"{settings.FRONTEND_URL}/dashboard"
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Welcome to EduCapture!</title>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
                    .button {{ display: inline-block; background: #667eea; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                    .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
                    .feature {{ background: white; padding: 20px; margin: 15px 0; border-radius: 5px; border-left: 4px solid #667eea; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🎉 Welcome to EduCapture!</h1>
                    </div>
                    <div class="content">
                        <h2>Hi {first_name},</h2>
                        <p>Your account has been successfully verified and you're now ready to start using EduCapture!</p>
                        
                        <div class="feature">
                            <h3>📝 Upload Your Notes</h3>
                            <p>Upload both handwritten and printed notes in various formats</p>
                        </div>
                        
                        <div class="feature">
                            <h3>✨ Enhance & Organize</h3>
                            <p>Use our AI-powered tools to enhance and organize your study materials</p>
                        </div>
                        
                        <div class="feature">
                            <h3>🔍 Search & Discover</h3>
                            <p>Easily find and access your notes with powerful search capabilities</p>
                        </div>
                        
                        <p>Ready to get started?</p>
                        <a href="{dashboard_url}" class="button">Go to Dashboard</a>
                        
                        <p>If you have any questions or need help getting started, don't hesitate to reach out to our support team.</p>
                    </div>
                    <div class="footer">
                        <p>© 2024 EduCapture. All rights reserved.</p>
                        <p>This is an automated message, please do not reply to this email.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            message = MessageSchema(
                subject="Welcome to EduCapture - Let's Get Started!",
                recipients=[email],
                body=html_content,
                subtype=MessageType.html
            )
            
            await self.fast_mail.send_message(message)
            logger.info(f"Welcome email sent to {email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send welcome email to {email}: {str(e)}")
            return False


# Global email service instance - initialized lazily
_email_service_instance = None

def get_email_service() -> EmailService:
    """Get email service instance (lazy loading)"""
    global _email_service_instance
    if _email_service_instance is None:
        _email_service_instance = EmailService()
    return _email_service_instance

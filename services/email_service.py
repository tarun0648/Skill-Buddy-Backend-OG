# services/email_service.py (UPDATED - Handles No Name Gracefully)
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
import logging
from typing import List, Optional, Dict, Any
import ssl
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class EmailService:
    """Service for sending emails via SMTP - Updated to handle missing names gracefully"""
    
    def __init__(self):
        # Load configuration
        self.smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', 587))
        self.smtp_username = os.environ.get('SMTP_USERNAME')
        self.smtp_password = os.environ.get('SMTP_PASSWORD')
        self.use_tls = os.environ.get('SMTP_USE_TLS', 'True').lower() == 'true'
        self.from_email = os.environ.get('FROM_EMAIL', self.smtp_username)
        self.from_name = os.environ.get('FROM_NAME', 'Skill Buddy')
        
        # Validate configuration
        if not all([self.smtp_username, self.smtp_password]):
            logger.warning("SMTP credentials not configured. Email functionality will be disabled.")
            self.enabled = False
        else:
            self.enabled = True
            logger.info(f"Email service initialized with SMTP server: {self.smtp_server}:{self.smtp_port}")
    
    def _get_display_name(self, user_name: str, user_email: str = None) -> str:
        """Get appropriate display name for email, handling empty names"""
        if user_name and user_name.strip():
            return user_name.strip()
        elif user_email:
            # Extract username from email and make it presentable
            username = user_email.split('@')[0]
            # Capitalize and clean up username
            display_name = username.replace('.', ' ').replace('_', ' ').replace('-', ' ')
            return ' '.join(word.capitalize() for word in display_name.split())
        else:
            return 'User'
    
    def _create_server(self):
        """Create and configure SMTP server connection"""
        try:
            if self.smtp_port == 465:
                # Use SSL for port 465
                context = ssl.create_default_context()
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, context=context)
            else:
                # Use TLS for other ports (typically 587)
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                if self.use_tls:
                    server.starttls()
            
            server.login(self.smtp_username, self.smtp_password)
            return server
            
        except Exception as e:
            logger.error(f"Failed to create SMTP server connection: {e}")
            raise Exception(f"SMTP connection failed: {str(e)}")
    
    def send_email(self, 
                   to_emails: List[str], 
                   subject: str, 
                   html_content: str = None, 
                   text_content: str = None,
                   cc_emails: List[str] = None,
                   bcc_emails: List[str] = None,
                   attachments: List[Dict[str, Any]] = None) -> bool:
        """Send email to recipients"""
        if not self.enabled:
            logger.warning("Email service is disabled. Skipping email send.")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = subject
            msg['Date'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
            
            if cc_emails:
                msg['Cc'] = ', '.join(cc_emails)
            
            # Add text content
            if text_content:
                text_part = MIMEText(text_content, 'plain', 'utf-8')
                msg.attach(text_part)
            
            # Add HTML content
            if html_content:
                html_part = MIMEText(html_content, 'html', 'utf-8')
                msg.attach(html_part)
            
            # Add attachments
            if attachments:
                for attachment in attachments:
                    filename = attachment.get('filename')
                    content = attachment.get('content')
                    
                    if filename and content:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(content)
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename= {filename}'
                        )
                        msg.attach(part)
            
            # Prepare recipient list
            all_recipients = to_emails[:]
            if cc_emails:
                all_recipients.extend(cc_emails)
            if bcc_emails:
                all_recipients.extend(bcc_emails)
            
            # Send email
            server = self._create_server()
            text = msg.as_string()
            server.sendmail(self.from_email, all_recipients, text)
            server.quit()
            
            logger.info(f"Email sent successfully to {len(all_recipients)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def send_password_change_notification(self, user_email: str, user_name: str = None) -> bool:
        """Send password change notification email - Updated to handle no name"""
        if not self.enabled:
            return False
        
        # Get appropriate display name
        display_name = self._get_display_name(user_name, user_email)
        
        subject = "Password Changed Successfully - Skill Buddy"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Password Changed</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #007bff; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9f9f9; }}
                .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
                .alert {{ background-color: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Skill Buddy</h1>
                </div>
                <div class="content">
                    <h2>Password Changed Successfully</h2>
                    <p>Hello {display_name},</p>
                    <div class="alert">
                        <strong>Your password has been changed successfully!</strong>
                    </div>
                    <p>Your Skill Buddy account password was changed on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}.</p>
                    <p><strong>If you made this change:</strong> No further action is required.</p>
                    <p><strong>If you did not make this change:</strong> Please contact our support team immediately to secure your account.</p>
                    <p>For security reasons, we recommend:</p>
                    <ul>
                        <li>Using a unique, strong password</li>
                        <li>Not sharing your password with anyone</li>
                        <li>Logging out of shared devices</li>
                    </ul>
                    <p>If you need help or have questions, please contact our support team.</p>
                    <p>Best regards,<br>The Skill Buddy Team</p>
                </div>
                <div class="footer">
                    <p>This is an automated message. Please do not reply to this email.</p>
                    <p>&copy; 2024 Skill Buddy. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Password Changed Successfully - Skill Buddy
        
        Hello {display_name},
        
        Your Skill Buddy account password was changed on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}.
        
        If you made this change: No further action is required.
        
        If you did not make this change: Please contact our support team immediately to secure your account.
        
        For security reasons, we recommend:
        - Using a unique, strong password
        - Not sharing your password with anyone
        - Logging out of shared devices
        
        If you need help or have questions, please contact our support team.
        
        Best regards,
        The Skill Buddy Team
        
        This is an automated message. Please do not reply to this email.
        """
        
        return self.send_email([user_email], subject, html_content, text_content)
    
    def send_welcome_email(self, user_email: str, user_name: str = None) -> bool:
        """Send welcome email to new users - Updated to handle no name"""
        if not self.enabled:
            return False
        
        # Get appropriate display name
        display_name = self._get_display_name(user_name, user_email)
        
        subject = "Welcome to Skill Buddy! 🎉"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Welcome to Skill Buddy</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #28a745; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9f9f9; }}
                .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
                .feature {{ margin: 15px 0; padding: 15px; background-color: white; border-radius: 5px; }}
                .cta {{ background-color: #007bff; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 20px 0; }}
                .greeting {{ color: #28a745; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to Skill Buddy! 🎉</h1>
                </div>
                <div class="content">
                    <h2 class="greeting">Hello {display_name}!</h2>
                    <p>Welcome to Skill Buddy - your AI-powered career companion! We're excited to help you on your career journey.</p>
                    
                    <div class="feature">
                        <h3>🎯 Complete Your Profile</h3>
                        <p>Get started by completing your profile to unlock personalized features and earn XP!</p>
                    </div>
                    
                    <div class="feature">
                        <h3>📄 Resume Analysis</h3>
                        <p>Upload your resume for AI-powered analysis and get tailored interview questions.</p>
                    </div>
                    
                    <div class="feature">
                        <h3>🔗 Profile Analysis</h3>
                        <p>Connect your LinkedIn and GitHub profiles for comprehensive career insights.</p>
                    </div>
                    
                    <div class="feature">
                        <h3>🌐 Portfolio Review</h3>
                        <p>Get your portfolio website analyzed with detailed improvement suggestions.</p>
                    </div>
                    
                    <div class="feature">
                        <h3>👥 Community Platform</h3>
                        <p>Connect with other professionals, share experiences, and learn together.</p>
                    </div>
                    
                    <p><strong>Ready to get started?</strong> Log in to Skill Buddy and start building your professional profile!</p>
                    
                    <p>Best regards,<br>The Skill Buddy Team</p>
                </div>
                <div class="footer">
                    <p>This is an automated message. Please do not reply to this email.</p>
                    <p>&copy; 2024 Skill Buddy. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Welcome to Skill Buddy!
        
        Hello {display_name}!
        
        Welcome to Skill Buddy - your AI-powered career companion! We're excited to help you on your career journey.
        
        Here's what you can do:
        
        🎯 Complete Your Profile
        Get started by completing your profile to unlock personalized features and earn XP!
        
        📄 Resume Analysis
        Upload your resume for AI-powered analysis and get tailored interview questions.
        
        🔗 Profile Analysis
        Connect your LinkedIn and GitHub profiles for comprehensive career insights.
        
        🌐 Portfolio Review
        Get your portfolio website analyzed with detailed improvement suggestions.
        
        👥 Community Platform
        Connect with other professionals, share experiences, and learn together.
        
        Ready to get started? Log in to Skill Buddy and start building your professional profile!
        
        Best regards,
        The Skill Buddy Team
        
        This is an automated message. Please do not reply to this email.
        """
        
        return self.send_email([user_email], subject, html_content, text_content)
    
    def send_password_reset_email(self, user_email: str, user_name: str = None, reset_token: str = None, reset_url: str = None) -> bool:
        """Send password reset email - Updated to handle no name"""
        if not self.enabled:
            return False
        
        # Get appropriate display name
        display_name = self._get_display_name(user_name, user_email)
        
        if not reset_url and reset_token:
            reset_url = f"https://your-frontend-domain.com/reset-password?token={reset_token}"
        
        subject = "Reset Your Password - Skill Buddy"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Reset Your Password</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #dc3545; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9f9f9; }}
                .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
                .cta {{ background-color: #007bff; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 20px 0; }}
                .warning {{ background-color: #fff3cd; border: 1px solid #ffeaa7; color: #856404; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .url-box {{ background-color: #e9ecef; padding: 10px; border-radius: 3px; word-break: break-all; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Password Reset Request</h1>
                </div>
                <div class="content">
                    <h2>Hello {display_name},</h2>
                    <p>We received a request to reset your password for your Skill Buddy account.</p>
                    
                    <p>Click the button below to reset your password:</p>
                    <a href="{reset_url}" class="cta">Reset My Password</a>
                    
                    <p>Or copy and paste this link into your browser:</p>
                    <div class="url-box">{reset_url}</div>
                    
                    <div class="warning">
                        <strong>Important:</strong> This link will expire in 1 hour for security reasons.
                    </div>
                    
                    <p><strong>If you did not request this password reset:</strong> Please ignore this email. Your password will remain unchanged.</p>
                    
                    <p>For security reasons:</p>
                    <ul>
                        <li>Never share this reset link with anyone</li>
                        <li>The link will expire after one use</li>
                        <li>Choose a strong, unique password</li>
                    </ul>
                    
                    <p>If you need help, please contact our support team.</p>
                    <p>Best regards,<br>The Skill Buddy Team</p>
                </div>
                <div class="footer">
                    <p>This is an automated message. Please do not reply to this email.</p>
                    <p>&copy; 2024 Skill Buddy. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Password Reset Request - Skill Buddy
        
        Hello {display_name},
        
        We received a request to reset your password for your Skill Buddy account.
        
        Please visit the following link to reset your password:
        {reset_url}
        
        Important: This link will expire in 1 hour for security reasons.
        
        If you did not request this password reset: Please ignore this email. Your password will remain unchanged.
        
        For security reasons:
        - Never share this reset link with anyone
        - The link will expire after one use
        - Choose a strong, unique password
        
        If you need help, please contact our support team.
        
        Best regards,
        The Skill Buddy Team
        
        This is an automated message. Please do not reply to this email.
        """
        
        return self.send_email([user_email], subject, html_content, text_content)
    
    def send_profile_completion_milestone_email(self, user_email: str, user_name: str = None, milestone: int = 0, xp_earned: int = 0) -> bool:
        """Send profile completion milestone celebration email - Updated to handle no name"""
        if not self.enabled:
            return False
        
        # Get appropriate display name
        display_name = self._get_display_name(user_name, user_email)
        
        subject = f"🎉 Milestone Achieved! {milestone}% Profile Complete - Skill Buddy"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Milestone Achieved!</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #28a745; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9f9f9; }}
                .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
                .milestone {{ background-color: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 20px; border-radius: 5px; margin: 20px 0; text-align: center; }}
                .xp-badge {{ background-color: #007bff; color: white; padding: 10px 20px; border-radius: 20px; display: inline-block; margin: 10px; }}
                .celebration {{ font-size: 2em; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Congratulations!</h1>
                </div>
                <div class="content">
                    <h2>Great job, {display_name}!</h2>
                    
                    <div class="milestone">
                        <div class="celebration">🎯</div>
                        <h3>Milestone Achieved!</h3>
                        <h2>{milestone}% Profile Complete</h2>
                        <div class="xp-badge">+{xp_earned} XP Earned!</div>
                    </div>
                    
                    <p>You're making excellent progress on your Skill Buddy journey! Your profile is now {milestone}% complete.</p>
                    
                    <p>Keep going to unlock more features:</p>
                    <ul>
                        <li>✅ Enhanced career insights</li>
                        <li>✅ Better job matching</li>
                        <li>✅ Personalized recommendations</li>
                        <li>✅ Community features</li>
                    </ul>
                    
                    <p>Ready to complete your profile? Log in to Skill Buddy and take the next step!</p>
                    
                    <p>Best regards,<br>The Skill Buddy Team</p>
                </div>
                <div class="footer">
                    <p>This is an automated message. Please do not reply to this email.</p>
                    <p>&copy; 2024 Skill Buddy. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Milestone Achieved! - Skill Buddy
        
        Great job, {display_name}!
        
        🎉 Milestone Achieved! 🎯
        {milestone}% Profile Complete
        +{xp_earned} XP Earned!
        
        You're making excellent progress on your Skill Buddy journey! Your profile is now {milestone}% complete.
        
        Keep going to unlock more features:
        ✅ Enhanced career insights
        ✅ Better job matching
        ✅ Personalized recommendations
        ✅ Community features
        
        Ready to complete your profile? Log in to Skill Buddy and take the next step!
        
        Best regards,
        The Skill Buddy Team
        
        This is an automated message. Please do not reply to this email.
        """
        
        return self.send_email([user_email], subject, html_content, text_content)
    
    def test_connection(self) -> bool:
        """Test SMTP connection"""
        if not self.enabled:
            return False
        
        try:
            server = self._create_server()
            server.quit()
            logger.info("SMTP connection test successful")
            return True
        except Exception as e:
            logger.error(f"SMTP connection test failed: {e}")
            return False

# Global email service instance
email_service = EmailService()
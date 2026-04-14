import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiosmtplib
from app.core.config import get_settings

logger = logging.getLogger("event_api.email")

class EmailService:
    @staticmethod
    async def send_email(to_email: str, subject: str, html_content: str):
        settings = get_settings()
        
        if not all([settings.smtp_user, settings.smtp_password, settings.mail_from]):
            logger.warning("SMTP settings are not fully configured. Email sending skipped for %s", to_email)
            return False

        message = MIMEMultipart("alternative")
        message["From"] = f"{settings.mail_from_name} <{settings.mail_from}>"
        message["To"] = to_email
        message["Subject"] = subject
        
        message.attach(MIMEText(html_content, "html"))

        try:
            await aiosmtplib.send(
                message,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_user,
                password=settings.smtp_password,
                start_tls=True if settings.smtp_port == 587 else False,
                use_tls=True if settings.smtp_port == 465 else False,
            )
            logger.info("Email sent successfully to %s", to_email)
            return True
        except Exception as e:
            logger.error("Failed to send email to %s: %s", to_email, str(e))
            return False

    @staticmethod
    async def send_otp_email(to_email: str, otp_code: str):
        subject = f"{otp_code} is your verification code"
        html_content = f"""
        <html>
            <body>
                <h2>Verification Code</h2>
                <p>Hello,</p>
                <p>Your verification code for the Event Application is:</p>
                <h1 style="color: #4CAF50;">{otp_code}</h1>
                <p>This code will expire in {get_settings().otp_expire_minutes} minutes.</p>
                <p>If you did not request this code, please ignore this email.</p>
            </body>
        </html>
        """
        return await EmailService.send_email(to_email, subject, html_content)

    @staticmethod
    async def send_password_reset_email(to_email: str, otp_code: str):
        subject = "Reset your password"
        html_content = f"""
        <html>
            <body>
                <h2>Password Reset Request</h2>
                <p>Hello,</p>
                <p>We received a request to reset your password. Use the following code to proceed:</p>
                <h1 style="color: #2196F3;">{otp_code}</h1>
                <p>This code will expire in {get_settings().otp_expire_minutes} minutes.</p>
                <p>If you did not request a password reset, you can safely ignore this email.</p>
            </body>
        </html>
        """
        return await EmailService.send_email(to_email, subject, html_content)

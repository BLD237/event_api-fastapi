import asyncio
import sys
import os

# Add parent directory to sys.path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.email import EmailService
from app.core.config import get_settings

async def test_email():
    settings = get_settings()
    print(f"Testing SMTP with user: {settings.smtp_user}")
    print(f"Host: {settings.smtp_host}:{settings.smtp_port}")
    
    if not settings.smtp_user or not settings.smtp_password:
        print("ERROR: SMTP credentials not set in .env")
        return

    recipient = settings.smtp_user  # Send to self for testing
    print(f"Sending test OTP email to {recipient}...")
    
    success = await EmailService.send_otp_email(recipient, "123456")
    
    if success:
        print("SUCCESS: Email sent! Please check your inbox.")
    else:
        print("FAILURE: Email could not be sent. Check logs for details.")

if __name__ == "__main__":
    asyncio.run(test_email())

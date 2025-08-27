#!/usr/bin/env python3
"""
Test script to check email service functionality
"""
import sys
import asyncio
from pathlib import Path

# Add the parent directory (backend root) to Python path
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from app.services.email import get_email_service
from app.core.config import settings

async def test_email_service():
    """Test the email service configuration"""

    try:
        print("🔧 Testing email service configuration...")
        print(f"📧 FRONTEND_URL: {settings.FRONTEND_URL}")

        # Get email service instance
        email_service = get_email_service()
        print("✅ Email service instance created successfully")

        # Check email configuration
        config = email_service.config
        print(f"📧 MAIL_SERVER: {config.MAIL_SERVER}")
        print(f"📧 MAIL_PORT: {config.MAIL_PORT}")
        print(f"📧 MAIL_USERNAME: {config.MAIL_USERNAME}")
        print(f"📧 MAIL_FROM: {config.MAIL_FROM}")
        print(f"📧 USE_CREDENTIALS: {config.USE_CREDENTIALS}")

        # Test sending a verification email (same as registration)
        test_email = "tkajaluxshan@gmail.com"  # Use the configured email for testing
        print(f"📤 Attempting to send verification email to {test_email}...")

        success = await email_service.send_email_verification(
            email=test_email,
            first_name="Test User",
            verification_token="test_token_123"
        )

        if success:
            print("✅ Verification email sent successfully!")
            print("📧 Check your inbox (and spam folder) for the verification email.")
        else:
            print("❌ Failed to send verification email")
            print("🔍 Possible issues:")
            print("   - Gmail App Password: Gmail requires an App Password for SMTP, not your regular password")
            print("   - Firewall/Network: SMTP port 587 might be blocked")
            print("   - Gmail Security: Less secure app access might be disabled")
            print("   - Credentials: Username/password might be incorrect")

    except Exception as e:
        print(f"❌ Error testing email service: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🧪 Starting email service test...")
    asyncio.run(test_email_service())
    print("✅ Email service test completed.")

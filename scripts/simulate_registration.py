#!/usr/bin/env python3
"""
Test script to simulate the exact registration process
"""
import sys
import asyncio
import logging
from pathlib import Path

# Add the parent directory (backend root) to Python path
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

# Set up logging to see what's happening
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from app.services.email import get_email_service
from app.core.auth import generate_email_verification_token
from app.core.config import settings

async def simulate_registration_email():
    """Simulate the exact email sending process from registration"""

    try:
        print("🔧 Simulating registration email process...")

        # Simulate the exact data that would be used in registration
        email = "tkajaluxshan@gmail.com"
        first_name = "Test"
        last_name = "User"
        password = "testpassword123"

        # Generate verification token (same as in registration)
        verification_token = generate_email_verification_token()
        print(f"🔑 Generated verification token: {verification_token}")

        # Get email service (same as in registration)
        email_service = get_email_service()
        print("✅ Email service obtained")

        # Send email (same call as in registration)
        print(f"📤 Sending verification email to {email}...")
        email_sent = await email_service.send_email_verification(
            email=email,
            first_name=first_name,
            verification_token=verification_token
        )

        if email_sent:
            print("✅ Registration email simulation successful!")
            print("📧 Check your inbox for the verification email.")
        else:
            print("❌ Registration email simulation failed!")
            print("🔍 This indicates the issue is with the email service configuration.")

    except Exception as e:
        print(f"❌ Error in registration simulation: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🧪 Starting registration email simulation...")
    asyncio.run(simulate_registration_email())
    print("✅ Registration simulation completed.")

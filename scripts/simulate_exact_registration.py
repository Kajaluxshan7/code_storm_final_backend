#!/usr/bin/env python3
"""
Test script to simulate the exact registration process with email service
"""
import sys
import asyncio
import logging
from pathlib import Path
from datetime import date

# Add the parent directory (backend root) to Python path
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

# Set up logging to see what's happening
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from app.services.auth import AuthService
from app.core.database import SessionLocal
from app.core.auth import generate_email_verification_token

async def simulate_exact_registration():
    """Simulate the exact registration process that happens in the API"""

    try:
        print("🔧 Simulating exact registration process...")

        # Create database session
        db = SessionLocal()

        try:
            # Create auth service instance
            auth_service = AuthService(db)
            print("✅ Auth service created")

            # Simulate registration data
            email = "testuser2@example.com"
            password = "TestPassword123!"  # Updated to meet password requirements
            first_name = "Test"
            last_name = "User"
            date_of_birth = date(2000, 1, 1)

            print(f"📤 Attempting to register user {email}...")

            # Call the exact same method that's called in the API
            user, verification_token = await auth_service.register_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                date_of_birth=date_of_birth,
                request=None  # We don't have a real request object
            )

            print("✅ Registration completed successfully!")
            print(f"📧 User created: {user.email}")
            print(f"🔑 Verification token generated: {verification_token is not None}")
            print(f"📧 Email verified status: {user.is_email_verified}")

            # Check if user was actually saved to database
            db.refresh(user)
            print(f"💾 User in database: {user.email}")
            print(f"🔒 Password hash exists: {user.password_hash is not None}")
            print(f"🎯 Auth provider: {user.auth_provider}")
            print(f"📧 Verification token in DB: {user.email_verification_token is not None}")

        finally:
            db.close()

    except Exception as e:
        print(f"❌ Error in registration simulation: {str(e)}")
        import traceback
        traceback.print_exc()
        print(f"❌ Error in registration simulation: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🧪 Starting exact registration simulation...")
    asyncio.run(simulate_exact_registration())
    print("✅ Registration simulation completed.")

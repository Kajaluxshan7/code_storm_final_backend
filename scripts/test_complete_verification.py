#!/usr/bin/env python3
"""
Complete email verification flow test
"""
import sys
import asyncio
import requests
import json
from pathlib import Path

# Add the parent directory (backend root) to Python path
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from app.core.database import SessionLocal
from app.models.user import User

async def test_complete_verification_flow():
    """Test the complete email verification flow"""

    print("🔧 Testing complete email verification flow...")

    # Step 1: Register a new user
    register_url = "http://localhost:8000/api/v1/auth/register"
    user_data = {
        "email": "verifytest@example.com",
        "password": "TestPassword123!",
        "first_name": "Verify",
        "last_name": "Test",
        "date_of_birth": "2000-01-01"
    }

    print("📝 Step 1: Registering new user...")
    response = requests.post(register_url, json=user_data, headers={"Content-Type": "application/json"})

    if response.status_code != 201:
        print(f"❌ Registration failed: {response.status_code} - {response.text}")
        return

    print("✅ User registered successfully")

    # Step 2: Get the verification token from database
    print("🔑 Step 2: Retrieving verification token from database...")
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == user_data["email"]).first()
        if not user:
            print("❌ User not found in database")
            return

        if not user.email_verification_token:
            print("❌ No verification token found")
            return

        token = user.email_verification_token
        print(f"✅ Got verification token: {token[:20]}...")

    finally:
        db.close()

    # Step 3: Verify the email using the token
    print("📧 Step 3: Verifying email with token...")
    verify_url = "http://localhost:8000/api/v1/auth/verify-email"
    verify_data = {"token": token}

    response = requests.post(verify_url, json=verify_data, headers={"Content-Type": "application/json"})

    print(f"📊 Verification response status: {response.status_code}")
    print(f"📧 Verification response: {response.text}")

    if response.status_code == 200:
        print("✅ Email verification successful!")

        # Step 4: Check if user is now verified in database
        print("🔍 Step 4: Checking if user is verified in database...")
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == user_data["email"]).first()
            if user and user.is_email_verified:
                print("✅ User email is now verified in database!")
            else:
                print("❌ User email is still not verified in database")
        finally:
            db.close()
    else:
        print(f"❌ Email verification failed: {response.status_code} - {response.text}")

if __name__ == "__main__":
    print("🧪 Starting complete email verification flow test...")
    asyncio.run(test_complete_verification_flow())
    print("✅ Email verification flow test completed.")

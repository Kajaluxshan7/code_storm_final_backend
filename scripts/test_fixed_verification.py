#!/usr/bin/env python3
"""
Test the fixed email verification with a real token
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

async def test_fixed_verification():
    """Test email verification with the fixed frontend approach"""

    print("🔧 Testing fixed email verification...")

    # Step 1: Create a test user and get their verification token
    print("📝 Step 1: Creating test user...")
    register_url = "http://localhost:8000/api/v1/auth/register"
    user_data = {
        "email": "frontendtest@example.com",
        "password": "TestPassword123!",
        "first_name": "Frontend",
        "last_name": "Test",
        "date_of_birth": "2000-01-01"
    }

    response = requests.post(register_url, json=user_data, headers={"Content-Type": "application/json"})

    if response.status_code != 201:
        print(f"❌ Registration failed: {response.status_code} - {response.text}")
        return

    print("✅ User registered successfully")

    # Step 2: Get the verification token
    print("🔑 Step 2: Getting verification token...")
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == user_data["email"]).first()
        if not user or not user.email_verification_token:
            print("❌ No verification token found")
            return

        token = user.email_verification_token
        print(f"✅ Got token: {token[:20]}...")

    finally:
        db.close()

    # Step 3: Test the fixed frontend request
    print("🌐 Step 3: Testing fixed frontend request...")
    verify_url = "http://localhost:8000/api/v1/auth/verify-email"
    headers = {"Content-Type": "application/json"}
    data = {"token": token}

    response = requests.post(verify_url, json=data, headers=headers)

    print(f"📊 Status: {response.status_code}")
    print(f"📧 Response: {response.text}")

    if response.status_code == 200:
        print("✅ Fixed verification works!")
    else:
        print(f"❌ Still not working: {response.status_code}")

if __name__ == "__main__":
    print("🧪 Testing fixed email verification...")
    asyncio.run(test_fixed_verification())
    print("✅ Test completed.")

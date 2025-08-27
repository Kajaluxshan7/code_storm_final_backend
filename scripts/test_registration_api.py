#!/usr/bin/env python3
"""
Test script to test registration through the actual API endpoint
"""
import sys
import asyncio
import httpx
import json
from pathlib import Path

# Add the parent directory (backend root) to Python path
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

async def test_registration_api():
    """Test user registration through the API endpoint"""

    try:
        print("🔧 Testing registration through API endpoint...")

        # Registration data
        registration_data = {
            "email": "testuser@example.com",
            "password": "TestPassword123!",  # Updated to meet password requirements
            "first_name": "Test",
            "last_name": "User",
            "date_of_birth": "2000-01-01"
        }

        print(f"📤 Sending registration request for {registration_data['email']}...")

        # Make the API request
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/api/v1/auth/register",
                json=registration_data,
                headers={"Content-Type": "application/json"}
            )

            print(f"📊 Response status: {response.status_code}")

            if response.status_code == 201:
                print("✅ Registration successful!")
                response_data = response.json()
                print(f"📧 User created: {response_data.get('email', 'N/A')}")

                # Check if the user was actually created in the database
                from app.core.database import SessionLocal
                from app.models.user import User

                db = SessionLocal()
                try:
                    user = db.query(User).filter(User.email == registration_data['email']).first()
                    if user:
                        print(f"✅ User found in database: {user.email}")
                        print(f"📧 Email verified: {user.is_email_verified}")
                        print(f"🔑 Verification token: {user.email_verification_token is not None}")
                    else:
                        print("❌ User not found in database")
                finally:
                    db.close()

            else:
                print(f"❌ Registration failed: {response.text}")

    except httpx.RequestError as e:
        print(f"❌ Network error: {str(e)}")
        print("💡 Make sure the FastAPI server is running on http://localhost:8000")
    except Exception as e:
        print(f"❌ Error testing registration API: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🧪 Starting API registration test...")
    asyncio.run(test_registration_api())
    print("✅ API registration test completed.")

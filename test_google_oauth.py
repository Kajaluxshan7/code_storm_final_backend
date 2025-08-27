#!/usr/bin/env python3
"""
Test script to simulate Google OAuth callback flow
This helps test the backend logic without actual Google OAuth flow
"""
import requests
import json
from datetime import datetime, timedelta
from jose import jwt

# Configuration
BACKEND_URL = "http://localhost:8000"
SECRET_KEY = "edu_capture_application"  # From .env file
ALGORITHM = "HS256"

def create_test_token(google_id: str, email: str, first_name: str = "", last_name: str = "", existing_user_id: str = None):
    """Create a test token for Google OAuth completion"""
    
    token_data = {
        "google_id": google_id,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "profile_picture_url": "https://lh3.googleusercontent.com/test-picture",
        "exp": datetime.utcnow() + timedelta(minutes=30)
    }
    
    if existing_user_id:
        token_data["existing_user_id"] = existing_user_id
    
    token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
    return token

def test_google_complete_existing_user():
    """Test completing Google OAuth for existing user (account linking scenario)"""
    print("Testing Google OAuth completion for existing user...")
    
    # Create test token for existing user
    test_token = create_test_token(
        google_id="105501439271237378815",
        email="thavamkajan7777@gmail.com",
        first_name="Kajaluxshan",
        last_name="Thavalingam",
        existing_user_id="223da111-2308-4ad9-9c40-e4a6d3217b94"  # Actual user ID from database
    )
    
    # Test data
    data = {
        "google_token": test_token,
        "date_of_birth": "2000-03-20",
        "first_name": "Kajaluxshan",
        "last_name": "Thavalingam"
    }
    
    url = f"{BACKEND_URL}/api/v1/auth/google/complete"
    print(f"Calling: {url}")
    print(f"Data: {json.dumps(data, indent=2)}")
    
    try:
        response = requests.post(url, json=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ SUCCESS: Account linking worked!")
            return True
        else:
            print("❌ FAILED: Account linking failed")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_google_complete_new_user():
    """Test completing Google OAuth for new user"""
    print("\nTesting Google OAuth completion for NEW user...")
    
    # Create test token for new user
    test_token = create_test_token(
        google_id="999999999999999999999",
        email="newuser@gmail.com",
        first_name="New",
        last_name="User"
    )
    
    # Test data
    data = {
        "google_token": test_token,
        "date_of_birth": "1995-01-01",
        "first_name": "New",
        "last_name": "User"
    }
    
    url = f"{BACKEND_URL}/api/v1/auth/google/complete"
    print(f"Calling: {url}")
    print(f"Data: {json.dumps(data, indent=2)}")
    
    try:
        response = requests.post(url, json=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ SUCCESS: New user registration worked!")
            return True
        else:
            print("❌ FAILED: New user registration failed")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Testing Google OAuth Backend Flow")
    print("=" * 50)
    
    # Test 1: Existing user (account linking)
    success1 = test_google_complete_existing_user()
    
    # Test 2: New user
    success2 = test_google_complete_new_user()
    
    print("\n" + "=" * 50)
    print("📋 SUMMARY:")
    print(f"  Existing User Test: {'✅ PASS' if success1 else '❌ FAIL'}")
    print(f"  New User Test:      {'✅ PASS' if success2 else '❌ FAIL'}")
    
    if success1 and success2:
        print("\n🎉 All tests passed! Google OAuth flow is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")

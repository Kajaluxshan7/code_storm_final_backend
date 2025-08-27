#!/usr/bin/env python3
"""
Test the complete Google OAuth account linking flow
"""
import requests
import jwt
from datetime import datetime, timedelta

# Base URL for your API
BASE_URL = "http://localhost:8000"

def create_test_jwt():
    """Create a test JWT token with Google user data"""
    payload = {
        'email': 'thavamkajan7777@gmail.com',
        'google_id': '105501439271237378815',
        'existing_user_id': '223da111-2308-4ad9-9c40-e4a6d3217b94',  # Actual user ID
        'first_name': 'Thavam',
        'last_name': 'Kajan',
        'profile_picture_url': 'https://lh3.googleusercontent.com/test-flow',
        'exp': datetime.utcnow() + timedelta(hours=1),
        'iat': datetime.utcnow()
    }
    # Use your JWT secret (this should match your application's secret)
    secret = "your-secret-key-change-in-production-educapture-2024"
    return jwt.encode(payload, secret, algorithm='HS256')

def test_complete_google_registration():
    """Test the complete_google_registration endpoint"""
    print("🧪 Testing complete Google registration with account linking...")
    
    # Create the JWT token
    token = create_test_jwt()
    print(f"📝 Created JWT token: {token[:50]}...")
    
    # Make the API call
    url = f"{BASE_URL}/api/v1/auth/google/complete"
    headers = {
        'Content-Type': 'application/json'
    }
    data = {
        'google_token': token,
        'date_of_birth': '1990-01-01'
    }
    
    print(f"🚀 Making POST request to {url}")
    print(f"📊 Payload: {data}")
    
    try:
        response = requests.post(url, json=data, headers=headers)
        print(f"📈 Response Status: {response.status_code}")
        print(f"📋 Response Headers: {dict(response.headers)}")
        
        if response.headers.get('content-type', '').startswith('application/json'):
            print(f"📄 Response Body: {response.json()}")
        else:
            print(f"📄 Response Text: {response.text}")
            
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ Error making request: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Testing Google OAuth account linking flow...")
    print("=" * 60)
    
    success = test_complete_google_registration()
    
    print("=" * 60)
    if success:
        print("✅ Test completed successfully!")
    else:
        print("❌ Test failed!")

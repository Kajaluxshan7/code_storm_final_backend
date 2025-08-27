#!/usr/bin/env python3
"""
Test frontend-style email verification request
"""
import requests
import json

def test_frontend_verification_request():
    """Test the exact same request the frontend makes"""

    # This simulates the exact request from the frontend verify-email page
    url = "http://localhost:8000/api/v1/auth/verify-email"
    headers = {
        "Content-Type": "application/json",
        # Note: No credentials/cookies since this is a public endpoint
    }

    # Test with a valid token first (we'll get one from our test user)
    # For now, let's test with an invalid token to see the error response
    data = {"token": "invalid-test-token"}

    print("🌐 Testing frontend-style verification request...")
    print(f"📡 URL: {url}")
    print(f"📝 Data: {json.dumps(data, indent=2)}")
    print(f"📋 Headers: {json.dumps(headers, indent=2)}")

    try:
        response = requests.post(url, json=data, headers=headers)

        print(f"📊 Status: {response.status_code}")
        print(f"📧 Response: {response.text}")
        print(f"📋 Response Headers: {dict(response.headers)}")

        if response.status_code == 200:
            print("✅ Verification successful!")
        elif response.status_code == 400:
            print("⚠️  Bad Request (expected for invalid token)")
        elif response.status_code == 401:
            print("❌ Unauthorized - This suggests an authentication issue")
        elif response.status_code == 404:
            print("❌ Not Found - Endpoint doesn't exist")
        else:
            print(f"❓ Unexpected status: {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")

def test_cors_headers():
    """Test CORS preflight request"""
    print("\n🔍 Testing CORS preflight...")

    url = "http://localhost:8000/api/v1/auth/verify-email"
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type"
    }

    try:
        # OPTIONS request for CORS preflight
        response = requests.options(url, headers=headers)
        print(f"📊 CORS Preflight Status: {response.status_code}")
        print(f"📋 CORS Headers: {dict(response.headers)}")

        if 'access-control-allow-origin' in response.headers:
            print("✅ CORS is properly configured")
        else:
            print("⚠️  CORS headers missing")

    except Exception as e:
        print(f"❌ CORS test failed: {e}")

if __name__ == "__main__":
    test_frontend_verification_request()
    test_cors_headers()

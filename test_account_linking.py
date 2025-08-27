#!/usr/bin/env python3
"""Test account linking with debug logging"""
import requests
import json
from datetime import datetime, timedelta
from jose import jwt

# Configuration
BACKEND_URL = 'http://localhost:8000'
SECRET_KEY = 'edu_capture_application'
ALGORITHM = 'HS256'

# Create test token for existing user
token_data = {
    'google_id': '105501439271237378815',
    'email': 'thavamkajan7777@gmail.com',
    'first_name': 'Kajaluxshan',
    'last_name': 'Thavalingam',
    'profile_picture_url': 'https://lh3.googleusercontent.com/test-picture-debug',
    'exp': datetime.utcnow() + timedelta(minutes=30),
    'existing_user_id': '223da111-2308-4ad9-9c40-e4a6d3217b94'
}

test_token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

# Test data
data = {
    'google_token': test_token,
    'date_of_birth': '2000-03-20',
    'first_name': 'Kajaluxshan',
    'last_name': 'Thavalingam'
}

url = f'{BACKEND_URL}/api/v1/auth/google/complete'
print(f'Testing account linking with debug: {url}')

try:
    response = requests.post(url, json=data)
    print(f'Status: {response.status_code}')
    if response.status_code == 200:
        print('✅ Account linking successful!')
        # Show user data from response
        resp_data = response.json()
        user_data = resp_data.get('user', {})
        print(f'User ID: {user_data.get("id")}')
        print(f'Auth Provider: {user_data.get("auth_provider")}')
    else:
        print(f'❌ Failed: {response.text}')
        
except Exception as e:
    print(f'Error: {e}')

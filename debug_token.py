#!/usr/bin/env python3
"""Debug token parsing"""
from jose import jwt
from datetime import datetime, timedelta

SECRET_KEY = 'edu_capture_application'
ALGORITHM = 'HS256'

# Create test token
token_data = {
    'google_id': '105501439271237378815',
    'email': 'thavamkajan7777@gmail.com',
    'first_name': 'Kajaluxshan',
    'last_name': 'Thavalingam',
    'profile_picture_url': 'https://lh3.googleusercontent.com/test-picture-updated',
    'exp': datetime.utcnow() + timedelta(minutes=30),
    'existing_user_id': '223da111-2308-4ad9-9c40-e4a6d3217b94'
}

test_token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
print(f'Created token: {test_token[:50]}...')

# Decode and verify
decoded = jwt.decode(test_token, SECRET_KEY, algorithms=[ALGORITHM])
print('Decoded token data:')
for key, value in decoded.items():
    print(f'  {key}: {value}')
    
print()
print(f'Google ID from token: {decoded.get("google_id")}')
print(f'Existing user ID from token: {decoded.get("existing_user_id")}')

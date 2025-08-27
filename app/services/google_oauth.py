"""
Google OAuth Service
Google OAuth 2.0 integration for user authentication
"""
from typing import Dict, Any, Optional
import json
import httpx
from fastapi import HTTPException, status
from google.auth.transport import requests
from google.oauth2 import id_token
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class GoogleOAuthService:
    """Google OAuth service for handling Google Sign-In"""
    
    def __init__(self):
        # Ensure settings are loaded
        from app.core.config import settings
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_REDIRECT_URI
        
        # Debug logging
        logger.info(f"GoogleOAuthService initialized with client_id: {bool(self.client_id)}")
        
        # Google OAuth endpoints
        self.token_url = "https://oauth2.googleapis.com/token"
        self.userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        self.auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    
    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """Generate Google OAuth authorization URL"""
        
        logger.info(f"get_authorization_url called with client_id: {bool(self.client_id)}")
        
        if not self.client_id:
            logger.error("Google OAuth not configured - client_id is None")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google OAuth not configured"
            )
        
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "openid email profile",
            "response_type": "code",
            "access_type": "offline",
            "include_granted_scopes": "true"
        }
        
        if state:
            params["state"] = state
        
        # Build URL with parameters
        param_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.auth_url}?{param_string}"
    
    async def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access tokens"""
        
        if not self.client_id or not self.client_secret:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google OAuth not configured"
            )
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.token_url, data=data)
                response.raise_for_status()
                
                token_data = response.json()
                
                if "error" in token_data:
                    logger.error(f"Google OAuth token exchange error: {token_data}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Google OAuth error: {token_data.get('error_description', 'Unknown error')}"
                    )
                
                return token_data
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during Google OAuth token exchange: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange authorization code for tokens"
            )
        except Exception as e:
            logger.error(f"Unexpected error during Google OAuth token exchange: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error during OAuth process"
            )
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from Google using access token"""
        
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.userinfo_url, headers=headers)
                response.raise_for_status()
                
                user_info = response.json()
                return user_info
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during Google user info retrieval: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to retrieve user information from Google"
            )
        except Exception as e:
            logger.error(f"Unexpected error during Google user info retrieval: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error during user info retrieval"
            )
    
    def verify_id_token(self, id_token_string: str) -> Dict[str, Any]:
        """Verify Google ID token and extract user information"""
        
        if not self.client_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google OAuth not configured"
            )
        
        try:
            # Verify the token
            id_info = id_token.verify_oauth2_token(
                id_token_string, 
                requests.Request(), 
                self.client_id
            )
            
            # Check issuer
            if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Wrong issuer.')
            
            return id_info
            
        except ValueError as e:
            logger.error(f"ID token verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid ID token"
            )
        except Exception as e:
            logger.error(f"Unexpected error during ID token verification: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error during token verification"
            )
    
    async def complete_oauth_flow(self, code: str) -> Dict[str, Any]:
        """Complete OAuth flow and return user information"""
        
        # Exchange code for tokens
        token_data = await self.exchange_code_for_tokens(code)
        
        # Extract tokens
        access_token = token_data.get("access_token")
        id_token_string = token_data.get("id_token")
        
        if not access_token or not id_token_string:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required tokens from Google"
            )
        
        # Verify ID token and get user info
        id_info = self.verify_id_token(id_token_string)
        
        # Extract user information
        user_data = {
            "google_id": id_info.get("sub"),
            "email": id_info.get("email"),
            "first_name": id_info.get("given_name", ""),
            "last_name": id_info.get("family_name", ""),
            "profile_picture_url": id_info.get("picture"),
            "email_verified": id_info.get("email_verified", False)
        }
        
        # Validate required fields
        if not user_data["google_id"] or not user_data["email"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required user information from Google"
            )
        
        if not user_data["email_verified"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google email is not verified"
            )
        
        logger.info(f"Google OAuth completed for user: {user_data['email']}")
        return user_data


# Global Google OAuth service instance
google_oauth_service = GoogleOAuthService()

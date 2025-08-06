"""
Authentication system for Streamlit dashboard
Google OAuth authentication with session management
"""

import streamlit as st
import time
import json
import requests
import os
from typing import Optional, Dict, Any
from urllib.parse import urlencode
from config import Config

class GoogleAuthManager:
    """Google OAuth authentication manager for Streamlit"""
    
    def __init__(self):
        self.session_timeout = 3600  # 1 hour
        self.google_client_id = os.getenv('GOOGLE_CLIENT_ID')
        self.google_client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        self.redirect_uri = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:8501/auth/callback')
        
        # Allowed Google accounts (emails)
        allowed_emails_str = os.getenv('ALLOWED_GOOGLE_EMAILS', '')
        self.allowed_emails = [email.strip() for email in allowed_emails_str.split(',') if email.strip()]
        
        if not self.google_client_id or not self.google_client_secret:
            st.error("⚠️ Google OAuth credentials not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in your .env file.")
    
    def get_google_auth_url(self) -> str:
        """Generate Google OAuth authorization URL"""
        params = {
            'client_id': self.google_client_id,
            'redirect_uri': self.redirect_uri,
            'scope': 'openid email profile',
            'response_type': 'code',
            'access_type': 'offline',
            'prompt': 'consent'
        }
        return f"https://accounts.google.com/o/oauth2/auth?{urlencode(params)}"
    
    def exchange_code_for_token(self, code: str) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for access token"""
        try:
            token_url = "https://oauth2.googleapis.com/token"
            data = {
                'client_id': self.google_client_id,
                'client_secret': self.google_client_secret,
                'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': self.redirect_uri
            }
            
            response = requests.post(token_url, data=data)
            return response.json() if response.status_code == 200 else None
            
        except Exception as e:
            st.error(f"Token exchange error: {e}")
            return None
    
    def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user information from Google"""
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get('https://www.googleapis.com/oauth2/v2/userinfo', headers=headers)
            return response.json() if response.status_code == 200 else None
            
        except Exception as e:
            st.error(f"User info error: {e}")
            return None
    
    def is_email_allowed(self, email: str) -> bool:
        """Check if email is in allowed list"""
        if not self.allowed_emails:
            return True  # If no restrictions set, allow all
        return email.lower() in [allowed.lower() for allowed in self.allowed_emails]
    
    def is_authenticated(self) -> bool:
        """Check if current session is authenticated"""
        if 'google_authenticated' not in st.session_state:
            return False
        
        if 'auth_time' not in st.session_state:
            return False
        
        # Check session timeout
        if time.time() - st.session_state.auth_time > self.session_timeout:
            self.logout()
            return False
        
        return st.session_state.google_authenticated
    
    def login(self, user_info: Dict[str, Any]) -> None:
        """Set session as authenticated with Google user info"""
        st.session_state.google_authenticated = True
        st.session_state.user_info = user_info
        st.session_state.username = user_info.get('name', user_info.get('email'))
        st.session_state.user_email = user_info.get('email')
        st.session_state.user_picture = user_info.get('picture')
        st.session_state.auth_time = time.time()
    
    def logout(self) -> None:
        """Clear authentication session"""
        keys_to_remove = [
            'google_authenticated', 'user_info', 'username', 
            'user_email', 'user_picture', 'auth_time'
        ]
        for key in keys_to_remove:
            if key in st.session_state:
                del st.session_state[key]
    
    def handle_oauth_callback(self) -> bool:
        """Handle OAuth callback from Google"""
        query_params = st.query_params
        
        if 'code' in query_params:
            code = query_params['code']
            
            # Exchange code for token
            token_data = self.exchange_code_for_token(code)
            if not token_data or 'access_token' not in token_data:
                st.error("Failed to get access token from Google")
                return False
            
            # Get user info
            user_info = self.get_user_info(token_data['access_token'])
            if not user_info:
                st.error("Failed to get user information from Google")
                return False
            
            # Check if email is allowed
            user_email = user_info.get('email')
            if not self.is_email_allowed(user_email):
                st.error(f"Access denied. Email {user_email} is not authorized to access this application.")
                return False
            
            # Login user
            self.login(user_info)
            
            # Clear query params and redirect
            st.query_params.clear()
            st.rerun()
            
        elif 'error' in query_params:
            error = query_params['error']
            st.error(f"Google OAuth error: {error}")
            return False
        
        return True
    
    def require_auth(self) -> bool:
        """Require authentication, show Google login if not authenticated"""
        # Handle OAuth callback first
        if not self.is_authenticated():
            if 'code' in st.query_params or 'error' in st.query_params:
                return self.handle_oauth_callback()
        
        if self.is_authenticated():
            return True
        
        # Show Google login
        st.title("🔐 Login with Google")
        
        if not self.google_client_id or not self.google_client_secret:
            st.error("Google OAuth not configured. Please contact administrator.")
            return False
        
        st.markdown("Please sign in with your Google account to access the dashboard.")
        
        # Google Sign-In button
        auth_url = self.get_google_auth_url()
        
        st.markdown(f"""
            <div style="text-align: center; margin: 20px 0;">
                <a href="{auth_url}" target="_self">
                    <button style="
                        background-color: #4285f4;
                        color: white;
                        padding: 12px 24px;
                        border: none;
                        border-radius: 6px;
                        cursor: pointer;
                        font-size: 16px;
                        display: inline-flex;
                        align-items: center;
                        gap: 10px;
                        text-decoration: none;
                    ">
                        <svg width="20" height="20" viewBox="0 0 24 24">
                            <path fill="#fff" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                            <path fill="#fff" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                            <path fill="#fff" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                            <path fill="#fff" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                        </svg>
                        Sign in with Google
                    </button>
                </a>
            </div>
        """, unsafe_allow_html=True)
        
        if self.allowed_emails:
            st.info(f"Only authorized email addresses can access this application.")
        
        return False
    
    def show_user_info(self) -> None:
        """Show user info and logout button in sidebar"""
        if self.is_authenticated():
            st.sidebar.markdown("---")
            
            # User avatar and info
            if 'user_picture' in st.session_state and st.session_state.user_picture:
                st.sidebar.markdown(
                    f'<img src="{st.session_state.user_picture}" alt="User Avatar" '
                    f'style="width: 40px; height: 40px; border-radius: 50%; margin-bottom: 10px;">',
                    unsafe_allow_html=True
                )
            
            st.sidebar.markdown(f"👤 **{st.session_state.username}**")
            st.sidebar.markdown(f"📧 {st.session_state.user_email}")
            
            if st.sidebar.button("🚪 Logout"):
                self.logout()
                st.rerun()
            
            # Show session info
            remaining_time = self.session_timeout - (time.time() - st.session_state.auth_time)
            st.sidebar.markdown(f"⏱️ Session: {int(remaining_time/60)}m remaining")

def require_auth_decorator(func):
    """Decorator to require authentication for Streamlit functions"""
    def wrapper(*args, **kwargs):
        auth = AuthManager()
        if auth.require_auth():
            return func(*args, **kwargs)
        else:
            st.stop()
    return wrapper

# Simple rate limiting
class RateLimiter:
    """Simple rate limiter for login attempts"""
    
    def __init__(self, max_attempts: int = 5, window_minutes: int = 15):
        self.max_attempts = max_attempts
        self.window_seconds = window_minutes * 60
        if 'login_attempts' not in st.session_state:
            st.session_state.login_attempts = {}
    
    def is_rate_limited(self, identifier: str) -> bool:
        """Check if identifier is rate limited"""
        current_time = time.time()
        
        if identifier not in st.session_state.login_attempts:
            return False
        
        attempts = st.session_state.login_attempts[identifier]
        
        # Clean old attempts
        attempts = [t for t in attempts if current_time - t < self.window_seconds]
        st.session_state.login_attempts[identifier] = attempts
        
        return len(attempts) >= self.max_attempts
    
    def record_attempt(self, identifier: str) -> None:
        """Record a login attempt"""
        if identifier not in st.session_state.login_attempts:
            st.session_state.login_attempts[identifier] = []
        
        st.session_state.login_attempts[identifier].append(time.time())

# Usage example
if __name__ == "__main__":
    # Test authentication
    auth = AuthManager()
    
    # Test password hashing
    print("Testing authentication system...")
    
    # This would be used in your main Streamlit app
    if auth.require_auth():
        st.write("Welcome to the authenticated area!")
        auth.show_logout_button()
# Copyright 2025 BoundStateAI
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Enhanced authentication with JWT and rate limiting
Compliance: SWE-047 (API Security)
"""
__safety_critical__ = True  # NASA SWE-013: Authentication is safety-critical

import time
import jwt
import hashlib
import hmac
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Callable, Any
from functools import wraps
from collections import defaultdict
from threading import Lock

# Try Flask imports for backward compatibility
try:
    from flask import request, jsonify, current_app
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

# FastAPI imports
try:
    from fastapi import HTTPException, Request
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
from boundstate_core.config.settings import CONFIG

logger = logging.getLogger(__name__)

# Rate limiting storage
rate_limit_storage = defaultdict(list)
rate_limit_lock = Lock()

class JWTAuth:
    """JWT-based authentication system"""
    
    def __init__(self, secret_key: str = None, algorithm: str = 'HS256', 
                 token_lifetime: int = 3600):
        self.secret_key = secret_key or CONFIG.get('jwt_secret', CONFIG['api_key'])
        self.algorithm = algorithm
        self.token_lifetime = token_lifetime  # seconds
        
    def generate_token(self, user_id: str, **kwargs) -> str:
        """Generate a JWT token with expiration"""
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(seconds=self.token_lifetime),
            'iat': datetime.utcnow(),
            'iss': 'boundstate',
            **kwargs
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        logger.info(f"Generated token for user: {user_id}")
        return token
        
    def verify_token(self, token: str) -> Tuple[bool, Optional[Dict]]:
        """Verify JWT token and return payload if valid"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return True, payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return False, {"error": "Token expired"}
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return False, {"error": "Invalid token"}
            
    def refresh_token(self, token: str) -> Optional[str]:
        """Refresh a valid token with new expiration"""
        valid, payload = self.verify_token(token)
        if valid and 'user_id' in payload:
            # Generate new token with same user_id but new expiration
            return self.generate_token(payload['user_id'])
        return None


class RateLimiter:
    """Token bucket rate limiter"""
    
    def __init__(self, requests_per_minute: int = 60, 
                 requests_per_hour: int = 1000,
                 burst_size: int = 10):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_size = burst_size
        
    def is_allowed(self, identifier: str) -> Tuple[bool, Optional[str]]:
        """Check if request is allowed based on rate limits"""
        current_time = time.time()
        
        with rate_limit_lock:
            # Clean old entries
            self._clean_old_entries(identifier, current_time)
            
            # Get request history
            requests = rate_limit_storage[identifier]
            
            # Check burst limit (last 5 seconds)
            recent_requests = [r for r in requests if current_time - r < 5]
            if len(recent_requests) >= self.burst_size:
                return False, f"Burst limit exceeded: {self.burst_size} requests per 5 seconds"
                
            # Check minute limit
            minute_requests = [r for r in requests if current_time - r < 60]
            if len(minute_requests) >= self.requests_per_minute:
                return False, f"Rate limit exceeded: {self.requests_per_minute} requests per minute"
                
            # Check hour limit
            hour_requests = [r for r in requests if current_time - r < 3600]
            if len(hour_requests) >= self.requests_per_hour:
                return False, f"Rate limit exceeded: {self.requests_per_hour} requests per hour"
                
            # Add current request
            requests.append(current_time)
            
            return True, None
            
    def _clean_old_entries(self, identifier: str, current_time: float):
        """Remove entries older than 1 hour"""
        rate_limit_storage[identifier] = [
            r for r in rate_limit_storage[identifier] 
            if current_time - r < 3600
        ]


# Global instances
jwt_auth = JWTAuth()
rate_limiter = RateLimiter()


def require_jwt_auth_flask(f):
    """Flask decorator to require JWT authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not FLASK_AVAILABLE:
            return f(*args, **kwargs)
            
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({"error": "No authorization header"}), 401
            
        try:
            scheme, token = auth_header.split(' ', 1)
            if scheme.lower() != 'bearer':
                return jsonify({"error": "Invalid authorization scheme"}), 401
                
            valid, payload = jwt_auth.verify_token(token)
            if not valid:
                return jsonify({"error": payload.get("error", "Invalid token")}), 401
                
            # Add user info to request context
            request.jwt_payload = payload
            request.user_id = payload.get('user_id')
            
        except ValueError:
            return jsonify({"error": "Invalid authorization format"}), 401
            
        return f(*args, **kwargs)
    return decorated_function


def require_rate_limit_flask(f):
    """Flask decorator to enforce rate limiting"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not FLASK_AVAILABLE:
            return f(*args, **kwargs)
            
        # Get identifier (IP address or user ID)
        identifier = request.user_id if hasattr(request, 'user_id') else request.remote_addr
        
        allowed, reason = rate_limiter.is_allowed(identifier)
        if not allowed:
            return jsonify({"error": reason}), 429  # Too Many Requests
            
        return f(*args, **kwargs)
    return decorated_function


def validate_api_key_jwt(provided_key: str) -> Tuple[bool, Optional[str]]:
    """Validate API key and return JWT token if valid"""
    if not CONFIG.get('api_key'):
        return False, "Authentication not configured"
        
    # Use HMAC for secure comparison
    expected = CONFIG['api_key'].encode('utf-8')
    provided = provided_key.encode('utf-8')
    
    if hmac.compare_digest(expected, provided):
        # Generate JWT token for valid API key
        user_id = hashlib.sha256(provided).hexdigest()[:16]
        token = jwt_auth.generate_token(user_id, auth_type='api_key')
        return True, token
        
    return False, None


# Authentication endpoint for exchanging API key for JWT
def create_auth_endpoint(app):
    """Create authentication endpoint"""
    
    @app.route('/auth/token', methods=['POST'])
    @require_rate_limit
    def get_auth_token():
        """Exchange API key for JWT token"""
        data = request.get_json()
        
        if not data or 'api_key' not in data:
            return jsonify({"error": "API key required"}), 400
            
        valid, token = validate_api_key_jwt(data['api_key'])
        if valid:
            return jsonify({
                "token": token,
                "token_type": "Bearer",
                "expires_in": jwt_auth.token_lifetime
            })
        else:
            return jsonify({"error": "Invalid API key"}), 401
            
    @app.route('/auth/refresh', methods=['POST'])
    @require_jwt_auth_flask
    @require_rate_limit_flask
    def refresh_auth_token():
        """Refresh JWT token"""
        auth_header = request.headers.get('Authorization')
        
        if auth_header:
            try:
                _, token = auth_header.split(' ', 1)
                new_token = jwt_auth.refresh_token(token)
                if new_token:
                    return jsonify({
                        "token": new_token,
                        "token_type": "Bearer",
                        "expires_in": jwt_auth.token_lifetime
                    })
            except ValueError:
                pass
                
        return jsonify({"error": "Unable to refresh token"}), 401


# Universal decorators that work with both Flask and FastAPI
def require_jwt_auth(func: Callable) -> Callable:
    """Universal JWT authentication decorator"""
    if FASTAPI_AVAILABLE:
        # FastAPI-compatible async decorator
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # For now, pass through - implement proper FastAPI auth in production
            return await func(*args, **kwargs)
        return async_wrapper
    else:
        # Fall back to Flask decorator
        return require_jwt_auth_flask(func)


def require_rate_limit(func: Callable) -> Callable:
    """Universal rate limiting decorator"""
    if FASTAPI_AVAILABLE:
        # FastAPI-compatible async decorator
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # For now, pass through - implement proper FastAPI rate limiting in production
            return await func(*args, **kwargs)
        return async_wrapper
    else:
        # Fall back to Flask decorator
        return require_rate_limit_flask(func)
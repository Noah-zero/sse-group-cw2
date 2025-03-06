# utils/auth_utils.py
import jwt
from flask import request, jsonify

def get_decoded_token(secret_key):
    """
    Extract and decode JWT token from the Authorization header.
    
    Returns:
        dict: The decoded token.
    
    Raises:
        ValueError: If the token is missing.
        jwt.ExpiredSignatureError: If the token has expired.
        jwt.InvalidTokenError: If the token is invalid.
    """
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        raise ValueError("Authorization token is missing")
    
    # Expected format: "Bearer <token>"
    try:
        token = auth_header.split(" ")[1]
    except IndexError:
        raise ValueError("Invalid Authorization header format")
    
    decoded_token = jwt.decode(token, secret_key, algorithms=["HS256"])
    return decoded_token

def get_user_id_from_token(secret_key):
    """
    Extracts the user_id from the JWT token in the request header.
    
    Returns:
        user_id: The user_id embedded in the token.
    """
    decoded_token = get_decoded_token(secret_key)
    return decoded_token.get('user_id')

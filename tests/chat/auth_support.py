"""Identity fixture used only by the isolated pre-auth workflow tests."""
import secrets
from hashlib import sha256
from fastapi import Request, Response
from apps.api.auth import same_origin


def fixture_user(request: Request, response: Response):
    same_origin(request)
    if not request.cookies.get('asiatax_workspace') and request.url.path not in ('/api/session', '/api/auth/session'):
        return None
    token = request.cookies.get('asiatax_workspace') or secrets.token_hex(32)
    response.set_cookie('asiatax_workspace', token, httponly=True, samesite='strict')
    return {'id': sha256(token.encode()).hexdigest()[:36], 'email': 'fixture@example.test'}

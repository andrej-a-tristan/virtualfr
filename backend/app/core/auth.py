"""Bearer token auth for chat gateway (dev-friendly: CHAT_API_KEY env)."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core import get_settings

_security = HTTPBearer(auto_error=False)


async def require_chat_api_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(_security),
) -> str:
    """Require Authorization: Bearer <token> matching CHAT_API_KEY. Returns token for user_id."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )
    token = credentials.credentials
    expected = get_settings().chat_api_key
    if not expected or token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return token

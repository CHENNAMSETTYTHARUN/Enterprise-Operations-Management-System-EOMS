from typing import Generator, Callable
from fastapi import Depends, Header, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_token, hash_api_key
from app.core.exceptions import UnauthorizedException, ForbiddenException
from app.core.config import settings
from app.models.auth import User, Role, Permission
from app.models.infrastructure import ApiKey
from app.services.rate_limiter import rate_limiter

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token", auto_error=False)


def get_current_user(token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    if not token:
        raise UnauthorizedException(message="Not authenticated")
    try:
        payload = decode_token(token)
        token_type = payload.get("type")
        if token_type != "access":
            raise UnauthorizedException(message="Invalid token type")
        user_id = payload.get("sub")
        if user_id is None:
            raise UnauthorizedException(message="Could not validate credentials")
    except JWTError:
        raise UnauthorizedException(message="Could not validate credentials or token expired")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise UnauthorizedException(message="User not found")
    if not user.is_active:
        raise ForbiddenException(message="Inactive user account")
    return user


def get_current_active_superuser(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_superuser:
        raise ForbiddenException(message="The user does not have enough privileges")
    return current_user


def require_role(role_name: str) -> Callable:
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.is_superuser:
            return current_user
        user_roles = [r.name for r in current_user.roles]
        if role_name not in user_roles:
            raise ForbiddenException(message=f"Role '{role_name}' required")
        return current_user
    return role_checker


def require_permission(permission_code: str) -> Callable:
    def permission_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.is_superuser:
            return current_user
        user_perms = set()
        for r in current_user.roles:
            for p in r.permissions:
                user_perms.add(p.code)
        if permission_code not in user_perms:
            raise ForbiddenException(message=f"Permission '{permission_code}' required")
        return current_user
    return permission_checker


def get_api_key_user(x_api_key: str | None = Header(None, alias="X-API-Key"), db: Session = Depends(get_db)) -> User:
    if not x_api_key:
        raise UnauthorizedException(message="API Key missing")
    hashed = hash_api_key(x_api_key)
    key_record = db.query(ApiKey).filter(ApiKey.hashed_key == hashed, ApiKey.is_active == True).first()
    if not key_record:
        raise UnauthorizedException(message="Invalid or inactive API Key")
    return key_record.user


def get_current_user_optional(token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User | None:
    if not token:
        return None
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        user_id = payload.get("sub")
        if user_id is None:
            return None
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user or not user.is_active:
            return None
        return user
    except Exception:
        return None


def check_rate_limit(request: Request, current_user: User | None = Depends(get_current_user_optional)) -> bool:
    identifier = str(current_user.id) if current_user else (request.client.host if request.client else "anonymous")
    rate_limiter.check_rate_limit(identifier, request.url.path)
    return True

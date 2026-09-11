from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, status, Request, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token, decode_token
from app.core.exceptions import BadRequestException, UnauthorizedException, NotFoundException, ConflictException
from app.core.config import settings
from app.core.dependencies import get_current_user, get_current_active_superuser
from app.models.auth import User, Role, Permission, RefreshToken
from app.schemas.auth import (
    UserCreate, UserResponse, UserUpdate,
    RoleCreate, RoleResponse,
    PermissionCreate, PermissionResponse,
    LoginRequest, TokenResponse, RefreshTokenRequest
)
from app.schemas.common import MessageResponse
from app.services.audit import log_audit

router = APIRouter(prefix="/auth", tags=["Authentication & Access Control"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, request: Request, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user_in.email).first():
        raise ConflictException(message="A user with this email already exists")
    if db.query(User).filter(User.username == user_in.username).first():
        raise ConflictException(message="A user with this username already exists")

    roles = []
    if user_in.role_ids:
        roles = db.query(Role).filter(Role.id.in_(user_in.role_ids)).all()

    user = User(
        email=user_in.email,
        username=user_in.username,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        is_active=True,
        is_superuser=False,
        roles=roles
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    log_audit(db, action="CREATE", module="AUTH", entity="User", entity_id=str(user.id), user_id=user.id, ip_address=request.client.host if request.client else None, details=f"Registered user {user.username}")
    return user


@router.post("/token")
def login_for_access_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(
        (User.username == form_data.username) | (User.email == form_data.username)
    ).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
            headers={"WWW-Authenticate": "Bearer"}
        )

    access_token = create_access_token(subject=user.id)
    refresh_token_str = create_refresh_token(subject=user.id)

    rf_expiry = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token_rec = RefreshToken(
        token=refresh_token_str,
        user_id=user.id,
        expires_at=rf_expiry,
        is_revoked=False
    )
    db.add(refresh_token_rec)
    db.commit()

    log_audit(db, action="LOGIN", module="AUTH", entity="User", entity_id=str(user.id), user_id=user.id, ip_address=request.client.host if request.client else None, details="User login via OAuth2 token")

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.post("/login", response_model=TokenResponse)
def login(login_data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        (User.username == login_data.username_or_email) | (User.email == login_data.username_or_email)
    ).first()

    if not user or not verify_password(login_data.password, user.hashed_password):
        raise UnauthorizedException(message="Incorrect username/email or password")
    if not user.is_active:
        raise UnauthorizedException(message="User account is inactive")

    access_token = create_access_token(subject=user.id)
    refresh_token_str = create_refresh_token(subject=user.id)

    rf_expiry = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token_rec = RefreshToken(
        token=refresh_token_str,
        user_id=user.id,
        expires_at=rf_expiry,
        is_revoked=False
    )
    db.add(refresh_token_rec)
    db.commit()

    log_audit(db, action="LOGIN", module="AUTH", entity="User", entity_id=str(user.id), user_id=user.id, ip_address=request.client.host if request.client else None, details="User login successful")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_str,
        token_type="bearer",
        user=user
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(data: RefreshTokenRequest, db: Session = Depends(get_db)):
    token_record = db.query(RefreshToken).filter(
        RefreshToken.token == data.refresh_token,
        RefreshToken.is_revoked == False
    ).first()

    if not token_record:
        raise UnauthorizedException(message="Invalid or revoked refresh token")

    try:
        payload = decode_token(data.refresh_token)
        if payload.get("type") != "refresh":
            raise UnauthorizedException(message="Invalid token type")
        user_id = int(payload.get("sub"))
    except Exception:
        raise UnauthorizedException(message="Expired or corrupted refresh token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise UnauthorizedException(message="User no longer active")

    token_record.is_revoked = True
    new_access = create_access_token(subject=user.id)
    new_refresh = create_refresh_token(subject=user.id)
    rf_expiry = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    new_token_rec = RefreshToken(
        token=new_refresh,
        user_id=user.id,
        expires_at=rf_expiry,
        is_revoked=False
    )
    db.add(new_token_rec)
    db.commit()

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        token_type="bearer",
        user=user
    )


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/logout", response_model=MessageResponse)
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(RefreshToken).filter(RefreshToken.user_id == current_user.id).update({"is_revoked": True})
    db.commit()
    return MessageResponse(message="Successfully logged out")


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def create_role(role_in: RoleCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_superuser)):
    if db.query(Role).filter(Role.name == role_in.name).first():
        raise ConflictException(message="Role already exists")
    permissions = []
    if role_in.permission_ids:
        permissions = db.query(Permission).filter(Permission.id.in_(role_in.permission_ids)).all()
    role = Role(name=role_in.name, description=role_in.description, permissions=permissions)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@router.get("/roles", response_model=list[RoleResponse])
def list_roles(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Role).all()


@router.post("/permissions", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
def create_permission(perm_in: PermissionCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_superuser)):
    if db.query(Permission).filter(Permission.code == perm_in.code).first():
        raise ConflictException(message="Permission already exists")
    perm = Permission(code=perm_in.code, name=perm_in.name, description=perm_in.description)
    db.add(perm)
    db.commit()
    db.refresh(perm)
    return perm


@router.get("/permissions", response_model=list[PermissionResponse])
def list_permissions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Permission).all()

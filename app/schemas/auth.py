from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class PermissionBase(BaseModel):
    code: str
    name: str
    description: str | None = None


class PermissionCreate(PermissionBase):
    pass


class PermissionResponse(PermissionBase):
    id: int

    class Config:
        from_attributes = True


class RoleBase(BaseModel):
    name: str
    description: str | None = None


class RoleCreate(RoleBase):
    permission_ids: list[int] = []


class RoleResponse(RoleBase):
    id: int
    permissions: list[PermissionResponse] = []

    class Config:
        from_attributes = True


class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: str | None = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)
    role_ids: list[int] = []


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    password: str | None = None
    is_active: bool | None = None
    role_ids: list[int] | None = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    roles: list[RoleResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username_or_email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenPayload(BaseModel):
    sub: str
    exp: int
    type: str

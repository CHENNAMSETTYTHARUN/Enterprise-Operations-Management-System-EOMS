from datetime import datetime
from pydantic import BaseModel, EmailStr


class AuditLogResponse(BaseModel):
    id: int
    user_id: int | None = None
    action: str
    module: str
    entity: str
    entity_id: str | None = None
    ip_address: str | None = None
    details: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class OTPGenerateRequest(BaseModel):
    target: str
    purpose: str = "VERIFICATION"


class OTPVerifyRequest(BaseModel):
    target: str
    otp_code: str
    purpose: str = "VERIFICATION"


class ApiKeyCreate(BaseModel):
    name: str
    expires_in_days: int | None = None


class ApiKeyResponse(BaseModel):
    id: int
    name: str
    key_prefix: str
    is_active: bool
    expires_at: datetime | None = None
    created_at: datetime
    raw_key: str | None = None

    class Config:
        from_attributes = True


class WebhookCreate(BaseModel):
    target_url: str
    event_type: str
    secret_key: str | None = None


class WebhookResponse(WebhookCreate):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class WebhookLogResponse(BaseModel):
    id: int
    webhook_id: int
    payload: str
    response_status: int | None = None
    response_body: str | None = None
    is_success: bool
    attempts: int
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    type: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class EmailSendRequest(BaseModel):
    recipient: EmailStr
    subject: str
    body: str


class EmailLogResponse(BaseModel):
    id: int
    recipient: str
    subject: str
    body: str
    status: str
    attempts: int
    error_message: str | None = None
    sent_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ImportHistoryResponse(BaseModel):
    id: int
    imported_by_id: int
    entity_type: str
    file_name: str
    total_rows: int
    successful_rows: int
    failed_rows: int
    error_summary: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True

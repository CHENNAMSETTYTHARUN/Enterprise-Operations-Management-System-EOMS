from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(50), nullable=False, index=True)
    module = Column(String(100), nullable=False, index=True)
    entity = Column(String(100), nullable=False, index=True)
    entity_id = Column(String(100), nullable=True)
    ip_address = Column(String(50), nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    user = relationship("User")


class OTPRecord(Base):
    __tablename__ = "otp_records"

    id = Column(Integer, primary_key=True, index=True)
    target = Column(String(255), index=True, nullable=False)
    otp_code = Column(String(10), nullable=False)
    purpose = Column(String(50), default="VERIFICATION", nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    key_prefix = Column(String(15), index=True, nullable=False)
    hashed_key = Column(String(255), unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User")


class Webhook(Base):
    __tablename__ = "webhooks"

    id = Column(Integer, primary_key=True, index=True)
    target_url = Column(String(500), nullable=False)
    event_type = Column(String(100), nullable=False, index=True)
    secret_key = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    logs = relationship("WebhookLog", back_populates="webhook", cascade="all, delete-orphan")


class WebhookLog(Base):
    __tablename__ = "webhook_logs"

    id = Column(Integer, primary_key=True, index=True)
    webhook_id = Column(Integer, ForeignKey("webhooks.id", ondelete="CASCADE"), nullable=False, index=True)
    payload = Column(Text, nullable=False)
    response_status = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    is_success = Column(Boolean, default=False, nullable=False)
    attempts = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    webhook = relationship("Webhook", back_populates="logs")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), default="INFO", nullable=False)
    is_read = Column(Boolean, default=False, index=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User")


class EmailLog(Base):
    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True, index=True)
    recipient = Column(String(255), nullable=False, index=True)
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    status = Column(String(50), default="QUEUED", index=True, nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class DataImportHistory(Base):
    __tablename__ = "data_import_history"

    id = Column(Integer, primary_key=True, index=True)
    imported_by_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_type = Column(String(100), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    total_rows = Column(Integer, default=0, nullable=False)
    successful_rows = Column(Integer, default=0, nullable=False)
    failed_rows = Column(Integer, default=0, nullable=False)
    error_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", foreign_keys=[imported_by_id])

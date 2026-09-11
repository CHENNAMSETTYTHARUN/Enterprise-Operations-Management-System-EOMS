from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from app.core.database import Base


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False, index=True)
    status = Column(String(50), default="SCHEDULED", index=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    customer = relationship("Customer", back_populates="appointments")
    employee = relationship("Employee")


class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    resource_type = Column(String(100), nullable=False, index=True)
    location = Column(String(255), nullable=True)
    capacity = Column(Integer, default=1, nullable=False)
    is_available = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    bookings = relationship("ResourceBooking", back_populates="resource")


class ResourceBooking(Base):
    __tablename__ = "resource_bookings"

    id = Column(Integer, primary_key=True, index=True)
    resource_id = Column(Integer, ForeignKey("resources.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    purpose = Column(String(255), nullable=False)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False, index=True)
    status = Column(String(50), default="CONFIRMED", index=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    resource = relationship("Resource", back_populates="bookings")
    user = relationship("User")


class WaitingList(Base):
    __tablename__ = "waiting_lists"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    position = Column(Integer, default=1, nullable=False)
    status = Column(String(50), default="WAITING", index=True, nullable=False)
    promoted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User")


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    remind_at = Column(DateTime, nullable=False, index=True)
    status = Column(String(50), default="PENDING", index=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, default=0, nullable=False)
    mime_type = Column(String(100), nullable=False)
    uploaded_by_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(100), default="GENERAL", index=True, nullable=False)
    is_public = Column(Boolean, default=False, nullable=False)
    current_version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    uploader = relationship("User", foreign_keys=[uploaded_by_id])
    approvals = relationship("DocumentApproval", back_populates="document", cascade="all, delete-orphan")
    versions = relationship("DocumentVersion", back_populates="document", cascade="all, delete-orphan")


class DocumentApproval(Base):
    __tablename__ = "document_approvals"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(50), default="PENDING", index=True, nullable=False)
    remarks = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    document = relationship("Document", back_populates="approvals")
    reviewer = relationship("User", foreign_keys=[reviewer_id])


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, default=0, nullable=False)
    change_summary = Column(String(255), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    document = relationship("Document", back_populates="versions")
    creator = relationship("User", foreign_keys=[created_by_id])

from datetime import datetime, date, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from app.core.database import Base


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id = Column(Integer, primary_key=True, index=True)
    requester_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    request_type = Column(String(100), nullable=False, index=True)
    entity_id = Column(Integer, nullable=True)
    title = Column(String(255), nullable=False)
    details = Column(Text, nullable=True)
    amount = Column(Float, nullable=True)
    current_stage = Column(String(50), default="MANAGER", nullable=False)
    status = Column(String(50), default="PENDING", index=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    requester = relationship("User", foreign_keys=[requester_id])
    history = relationship("ApprovalHistory", back_populates="request", cascade="all, delete-orphan")


class ApprovalHistory(Base):
    __tablename__ = "approval_history"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("approval_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    stage = Column(String(50), nullable=False)
    action = Column(String(50), nullable=False)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    request = relationship("ApprovalRequest", back_populates="history")
    actor = relationship("User", foreign_keys=[actor_id])


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    amount = Column(Float, nullable=False)
    expense_date = Column(Date, default=date.today, nullable=False)
    status = Column(String(50), default="PENDING", index=True, nullable=False)
    approved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    receipt_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    employee = relationship("Employee", back_populates="expenses")
    approver = relationship("User", foreign_keys=[approved_by_id])
    reimbursement = relationship("Reimbursement", back_populates="expense", uselist=False)


class Reimbursement(Base):
    __tablename__ = "reimbursements"

    id = Column(Integer, primary_key=True, index=True)
    expense_id = Column(Integer, ForeignKey("expenses.id", ondelete="CASCADE"), unique=True, nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    status = Column(String(50), default="PENDING", index=True, nullable=False)
    payment_status = Column(String(50), default="UNPAID", index=True, nullable=False)
    payment_reference = Column(String(100), nullable=True)
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    expense = relationship("Expense", back_populates="reimbursement")
    employee = relationship("Employee", back_populates="reimbursements")


class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    asset_code = Column(String(100), unique=True, index=True, nullable=False)
    category = Column(String(100), nullable=False, index=True)
    serial_number = Column(String(100), unique=True, nullable=True)
    purchase_date = Column(Date, nullable=True)
    cost = Column(Float, default=0.0, nullable=False)
    status = Column(String(50), default="AVAILABLE", index=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    assignments = relationship("AssetAssignment", back_populates="asset")
    returns = relationship("AssetReturn", back_populates="asset")


class AssetAssignment(Base):
    __tablename__ = "asset_assignments"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_date = Column(Date, default=date.today, nullable=False)
    condition_notes = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    asset = relationship("Asset", back_populates="assignments")
    employee = relationship("Employee", back_populates="assigned_assets")


class AssetReturn(Base):
    __tablename__ = "asset_returns"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    return_date = Column(Date, default=date.today, nullable=False)
    has_damage = Column(Boolean, default=False, nullable=False)
    damage_details = Column(Text, nullable=True)
    damage_cost = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    asset = relationship("Asset", back_populates="returns")
    employee = relationship("Employee")


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True, index=True)
    ticket_number = Column(String(50), unique=True, index=True, nullable=False)
    creator_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(100), nullable=False, index=True)
    priority = Column(String(50), default="MEDIUM", index=True, nullable=False)
    status = Column(String(50), default="OPEN", index=True, nullable=False)
    escalated = Column(Boolean, default=False, nullable=False)
    resolution_time_minutes = Column(Integer, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    creator = relationship("User", foreign_keys=[creator_id])
    assignments = relationship("TicketAssignment", back_populates="ticket")
    escalations = relationship("TicketEscalation", back_populates="ticket")


class TicketAssignment(Base):
    __tablename__ = "ticket_assignments"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_by_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    assigned_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    ticket = relationship("SupportTicket", back_populates="assignments")
    agent = relationship("User", foreign_keys=[agent_id])
    assigner = relationship("User", foreign_keys=[assigned_by_id])


class TicketEscalation(Base):
    __tablename__ = "ticket_escalations"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    reason = Column(Text, nullable=False)
    escalated_to_role = Column(String(50), default="ADMIN", nullable=False)
    status = Column(String(50), default="ESCALATED", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    ticket = relationship("SupportTicket", back_populates="escalations")


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_to_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(50), default="PENDING", index=True, nullable=False)
    resolution_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    customer = relationship("Customer", back_populates="complaints")
    assignee = relationship("User", foreign_keys=[assigned_to_id])


class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    category = Column(String(100), nullable=False, index=True)
    rating = Column(Integer, default=5, nullable=False)
    feedback_text = Column(Text, nullable=False)
    admin_response = Column(Text, nullable=True)
    status = Column(String(50), default="SUBMITTED", index=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    customer = relationship("Customer", back_populates="feedbacks")

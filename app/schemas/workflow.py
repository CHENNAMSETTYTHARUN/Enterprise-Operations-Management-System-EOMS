from datetime import datetime, date
from pydantic import BaseModel


class ApprovalCreate(BaseModel):
    request_type: str
    entity_id: int | None = None
    title: str
    details: str | None = None
    amount: float | None = None


class ApprovalAction(BaseModel):
    action: str
    remarks: str | None = None


class ApprovalHistoryResponse(BaseModel):
    id: int
    actor_id: int
    stage: str
    action: str
    remarks: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ApprovalResponse(BaseModel):
    id: int
    requester_id: int
    request_type: str
    entity_id: int | None = None
    title: str
    details: str | None = None
    amount: float | None = None
    current_stage: str
    status: str
    created_at: datetime
    updated_at: datetime
    history: list[ApprovalHistoryResponse] = []

    class Config:
        from_attributes = True


class ExpenseCreate(BaseModel):
    category: str
    title: str
    description: str | None = None
    amount: float
    expense_date: date = date.today()
    receipt_url: str | None = None


class ExpenseAction(BaseModel):
    status: str


class ExpenseResponse(ExpenseCreate):
    id: int
    employee_id: int
    status: str
    approved_by_id: int | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ReimbursementCreate(BaseModel):
    expense_id: int


class ReimbursementAction(BaseModel):
    status: str
    payment_status: str | None = None
    payment_reference: str | None = None


class ReimbursementResponse(BaseModel):
    id: int
    expense_id: int
    employee_id: int
    amount: float
    status: str
    payment_status: str
    payment_reference: str | None = None
    processed_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class AssetBase(BaseModel):
    name: str
    asset_code: str
    category: str
    serial_number: str | None = None
    purchase_date: date | None = None
    cost: float = 0.0
    status: str = "AVAILABLE"


class AssetCreate(AssetBase):
    pass


class AssetUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    serial_number: str | None = None
    cost: float | None = None
    status: str | None = None


class AssetResponse(AssetBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class AssetAssign(BaseModel):
    employee_id: int
    condition_notes: str | None = None


class AssetAssignmentResponse(BaseModel):
    id: int
    asset_id: int
    employee_id: int
    assigned_date: date
    condition_notes: str | None = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AssetReturnCreate(BaseModel):
    has_damage: bool = False
    damage_details: str | None = None
    damage_cost: float = 0.0


class AssetReturnResponse(BaseModel):
    id: int
    asset_id: int
    employee_id: int
    return_date: date
    has_damage: bool
    damage_details: str | None = None
    damage_cost: float
    created_at: datetime

    class Config:
        from_attributes = True


class TicketCreate(BaseModel):
    title: str
    description: str
    category: str
    priority: str = "MEDIUM"


class TicketUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    category: str | None = None
    priority: str | None = None
    status: str | None = None


class TicketResponse(BaseModel):
    id: int
    ticket_number: str
    creator_id: int
    title: str
    description: str
    category: str
    priority: str
    status: str
    escalated: bool
    resolution_time_minutes: int | None = None
    closed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TicketAssign(BaseModel):
    agent_id: int


class TicketEscalate(BaseModel):
    reason: str
    escalated_to_role: str = "ADMIN"


class ComplaintCreate(BaseModel):
    customer_id: int
    subject: str
    description: str


class ComplaintResolve(BaseModel):
    resolution_notes: str


class ComplaintResponse(BaseModel):
    id: int
    customer_id: int
    assigned_to_id: int | None = None
    subject: str
    description: str
    status: str
    resolution_notes: str | None = None
    resolved_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class FeedbackCreate(BaseModel):
    customer_id: int | None = None
    category: str
    rating: int = 5
    feedback_text: str


class FeedbackRespond(BaseModel):
    admin_response: str


class FeedbackResponse(BaseModel):
    id: int
    customer_id: int | None = None
    category: str
    rating: int
    feedback_text: str
    admin_response: str | None = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

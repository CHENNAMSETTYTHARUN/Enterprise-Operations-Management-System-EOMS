from datetime import datetime
from pydantic import BaseModel


class AppointmentCreate(BaseModel):
    customer_id: int
    employee_id: int
    title: str
    description: str | None = None
    start_time: datetime
    end_time: datetime


class AppointmentResponse(AppointmentCreate):
    id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ResourceCreate(BaseModel):
    name: str
    resource_type: str
    location: str | None = None
    capacity: int = 1


class ResourceResponse(ResourceCreate):
    id: int
    is_available: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ResourceBookingCreate(BaseModel):
    resource_id: int
    purpose: str
    start_time: datetime
    end_time: datetime


class ResourceBookingResponse(ResourceBookingCreate):
    id: int
    user_id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class WaitingListCreate(BaseModel):
    entity_type: str
    entity_id: int


class WaitingListResponse(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    user_id: int
    position: int
    status: str
    promoted_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ReminderCreate(BaseModel):
    title: str
    description: str | None = None
    remind_at: datetime


class ReminderResponse(ReminderCreate):
    id: int
    user_id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentResponse(BaseModel):
    id: int
    title: str
    file_name: str
    file_path: str
    file_size: int
    mime_type: str
    uploaded_by_id: int
    category: str
    is_public: bool
    current_version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentApprovalAction(BaseModel):
    status: str
    remarks: str | None = None


class DocumentApprovalResponse(BaseModel):
    id: int
    document_id: int
    reviewer_id: int
    status: str
    remarks: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentVersionResponse(BaseModel):
    id: int
    document_id: int
    version_number: int
    file_name: str
    file_size: int
    change_summary: str | None = None
    created_by_id: int
    created_at: datetime

    class Config:
        from_attributes = True

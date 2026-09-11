import os
import shutil
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status, Query, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from app.core.database import get_db
from app.core.config import settings
from app.core.exceptions import NotFoundException, BadRequestException, ConflictException, ForbiddenException
from app.core.dependencies import get_current_user
from app.models.auth import User
from app.models.core_business import Customer, Employee
from app.models.advanced import (
    Appointment, Resource, ResourceBooking, WaitingList,
    Reminder, Document, DocumentApproval, DocumentVersion
)
from app.models.infrastructure import Notification, EmailLog, AuditLog
from app.schemas.advanced import (
    AppointmentCreate, AppointmentResponse,
    ResourceCreate, ResourceResponse,
    ResourceBookingCreate, ResourceBookingResponse,
    WaitingListCreate, WaitingListResponse,
    ReminderCreate, ReminderResponse,
    DocumentResponse, DocumentApprovalAction, DocumentApprovalResponse, DocumentVersionResponse
)
from app.schemas.infrastructure import NotificationResponse, EmailSendRequest, EmailLogResponse, AuditLogResponse
from app.schemas.common import MessageResponse, PaginatedResponse
from app.services.audit import log_audit
from app.services.email import send_email_background
from app.services.notifications import create_notification_background

router = APIRouter(prefix="", tags=["Phase 4 — Advanced Business Logic"])


@router.post("/appointments", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def create_appointment(app_in: AppointmentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if app_in.end_time <= app_in.start_time:
        raise BadRequestException(message="End time must be after start time")

    conflict = db.query(Appointment).filter(
        Appointment.employee_id == app_in.employee_id,
        Appointment.status != "CANCELLED",
        Appointment.start_time < app_in.end_time,
        Appointment.end_time > app_in.start_time
    ).first()
    if conflict:
        raise ConflictException(message="Selected time slot is already booked for this employee")

    appointment = Appointment(**app_in.model_dump(), status="SCHEDULED")
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    log_audit(db, action="CREATE", module="APPOINTMENT", entity="Appointment", entity_id=str(appointment.id), user_id=current_user.id, details="Scheduled new appointment")
    return appointment


@router.get("/appointments", response_model=list[AppointmentResponse])
def list_appointments(employee_id: int | None = None, customer_id: int | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Appointment)
    if employee_id:
        query = query.filter(Appointment.employee_id == employee_id)
    if customer_id:
        query = query.filter(Appointment.customer_id == customer_id)
    return query.order_by(Appointment.start_time.asc()).all()


@router.post("/appointments/{app_id}/cancel", response_model=AppointmentResponse)
def cancel_appointment(app_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    app_obj = db.query(Appointment).filter(Appointment.id == app_id).first()
    if not app_obj:
        raise NotFoundException(message="Appointment not found")
    app_obj.status = "CANCELLED"
    db.commit()
    db.refresh(app_obj)

    next_wait = db.query(WaitingList).filter(
        WaitingList.entity_type == "APPOINTMENT",
        WaitingList.status == "WAITING"
    ).order_by(WaitingList.position.asc()).first()
    if next_wait:
        next_wait.status = "PROMOTED"
        next_wait.promoted_at = datetime.now(timezone.utc)
        db.commit()

    return app_obj


@router.post("/resources", response_model=ResourceResponse, status_code=status.HTTP_201_CREATED)
def create_resource(res_in: ResourceCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    resource = Resource(**res_in.model_dump(), is_available=True)
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource


@router.get("/resources", response_model=list[ResourceResponse])
def list_resources(resource_type: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Resource)
    if resource_type:
        query = query.filter(Resource.resource_type.ilike(f"%{resource_type}%"))
    return query.all()


@router.post("/resources/book", response_model=ResourceBookingResponse, status_code=status.HTTP_201_CREATED)
def book_resource(booking_in: ResourceBookingCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if booking_in.end_time <= booking_in.start_time:
        raise BadRequestException(message="End time must be after start time")

    conflict = db.query(ResourceBooking).filter(
        ResourceBooking.resource_id == booking_in.resource_id,
        ResourceBooking.status == "CONFIRMED",
        ResourceBooking.start_time < booking_in.end_time,
        ResourceBooking.end_time > booking_in.start_time
    ).first()
    if conflict:
        raise ConflictException(message="Resource is already booked during this time window")

    booking = ResourceBooking(
        resource_id=booking_in.resource_id,
        user_id=current_user.id,
        purpose=booking_in.purpose,
        start_time=booking_in.start_time,
        end_time=booking_in.end_time,
        status="CONFIRMED"
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    log_audit(db, action="BOOK", module="RESOURCE", entity="ResourceBooking", entity_id=str(booking.id), user_id=current_user.id, details="Resource booked")
    return booking


@router.get("/resources/bookings", response_model=list[ResourceBookingResponse])
def list_resource_bookings(resource_id: int | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(ResourceBooking)
    if resource_id:
        query = query.filter(ResourceBooking.resource_id == resource_id)
    return query.order_by(ResourceBooking.start_time.asc()).all()


@router.post("/resources/bookings/{booking_id}/cancel", response_model=ResourceBookingResponse)
def cancel_resource_booking(booking_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    booking = db.query(ResourceBooking).filter(ResourceBooking.id == booking_id).first()
    if not booking:
        raise NotFoundException(message="Booking not found")
    booking.status = "CANCELLED"
    db.commit()
    db.refresh(booking)
    return booking


@router.post("/waiting-lists", response_model=WaitingListResponse, status_code=status.HTTP_201_CREATED)
def join_waiting_list(wait_in: WaitingListCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    current_count = db.query(WaitingList).filter(
        WaitingList.entity_type == wait_in.entity_type,
        WaitingList.entity_id == wait_in.entity_id,
        WaitingList.status == "WAITING"
    ).count()

    item = WaitingList(
        entity_type=wait_in.entity_type,
        entity_id=wait_in.entity_id,
        user_id=current_user.id,
        position=current_count + 1,
        status="WAITING"
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/waiting-lists", response_model=list[WaitingListResponse])
def list_waiting_lists(entity_type: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(WaitingList)
    if entity_type:
        query = query.filter(WaitingList.entity_type == entity_type)
    return query.order_by(WaitingList.position.asc()).all()


@router.delete("/waiting-lists/{wait_id}", response_model=MessageResponse)
def leave_waiting_list(wait_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = db.query(WaitingList).filter(WaitingList.id == wait_id).first()
    if not item:
        raise NotFoundException(message="Waiting list record not found")
    item.status = "CANCELLED"
    db.commit()
    return MessageResponse(message="Removed from waiting list")


@router.get("/notifications", response_model=list[NotificationResponse])
def get_user_notifications(unread_only: bool = False, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    if unread_only:
        query = query.filter(Notification.is_read == False)
    return query.order_by(Notification.created_at.desc()).all()


@router.post("/notifications/{notif_id}/read", response_model=NotificationResponse)
def mark_notification_read(notif_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    notif = db.query(Notification).filter(Notification.id == notif_id, Notification.user_id == current_user.id).first()
    if not notif:
        raise NotFoundException(message="Notification not found")
    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return notif


@router.post("/notifications/read-all", response_model=MessageResponse)
def mark_all_notifications_read(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db.query(Notification).filter(Notification.user_id == current_user.id, Notification.is_read == False).update({"is_read": True})
    db.commit()
    return MessageResponse(message="All notifications marked as read")


@router.get("/notifications/unread-count")
def get_unread_notification_count(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    count = db.query(Notification).filter(Notification.user_id == current_user.id, Notification.is_read == False).count()
    return {"unread_count": count}


@router.post("/emails/send", response_model=MessageResponse)
def queue_email(email_in: EmailSendRequest, bg_tasks: BackgroundTasks, current_user: User = Depends(get_current_user)):
    bg_tasks.add_task(send_email_background, email_in.recipient, email_in.subject, email_in.body)
    return MessageResponse(message=f"Email to {email_in.recipient} queued for delivery")


@router.get("/emails/logs", response_model=list[EmailLogResponse])
def get_email_logs(recipient: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(EmailLog)
    if recipient:
        query = query.filter(EmailLog.recipient.ilike(f"%{recipient}%"))
    return query.order_by(EmailLog.created_at.desc()).all()


@router.post("/reminders", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
def create_reminder(rem_in: ReminderCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    reminder = Reminder(
        user_id=current_user.id,
        title=rem_in.title,
        description=rem_in.description,
        remind_at=rem_in.remind_at,
        status="PENDING"
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder


@router.get("/reminders", response_model=list[ReminderResponse])
def list_reminders(status_filter: str | None = Query(None, alias="status"), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Reminder).filter(Reminder.user_id == current_user.id)
    if status_filter:
        query = query.filter(Reminder.status == status_filter)
    return query.order_by(Reminder.remind_at.asc()).all()


@router.post("/documents/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_document(
    title: str = Form(...),
    category: str = Form("GENERAL"),
    is_public: bool = Form(False),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    save_filename = f"{int(datetime.now(timezone.utc).timestamp())}_{file.filename}"
    file_dest = os.path.join(settings.UPLOAD_DIR, save_filename)
    with open(file_dest, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(file_dest)
    doc = Document(
        title=title,
        file_name=file.filename or save_filename,
        file_path=file_dest,
        file_size=file_size,
        mime_type=file.content_type or "application/octet-stream",
        uploaded_by_id=current_user.id,
        category=category,
        is_public=is_public,
        current_version=1
    )
    db.add(doc)
    db.flush()

    ver = DocumentVersion(
        document_id=doc.id,
        version_number=1,
        file_name=doc.file_name,
        file_path=doc.file_path,
        file_size=file_size,
        change_summary="Initial upload",
        created_by_id=current_user.id
    )
    db.add(ver)
    db.commit()
    db.refresh(doc)
    log_audit(db, action="UPLOAD", module="DOCUMENT", entity="Document", entity_id=str(doc.id), user_id=current_user.id, details=f"Uploaded document {doc.title}")
    return doc


@router.get("/documents", response_model=list[DocumentResponse])
def list_documents(category: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Document).filter(or_(Document.uploaded_by_id == current_user.id, Document.is_public == True, current_user.is_superuser == True))
    if category:
        query = query.filter(Document.category == category)
    return query.all()


@router.get("/documents/{doc_id}/download")
def download_document(doc_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise NotFoundException(message="Document not found")
    if not doc.is_public and doc.uploaded_by_id != current_user.id and not current_user.is_superuser:
        raise ForbiddenException(message="You do not have permission to download this document")
    if not os.path.exists(doc.file_path):
        raise NotFoundException(message="File on disk not found")
    return FileResponse(doc.file_path, filename=doc.file_name, media_type=doc.mime_type)


@router.delete("/documents/{doc_id}", response_model=MessageResponse)
def delete_document(doc_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise NotFoundException(message="Document not found")
    if doc.uploaded_by_id != current_user.id and not current_user.is_superuser:
        raise ForbiddenException(message="Not authorized to delete this document")
    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception:
            pass
    db.delete(doc)
    db.commit()
    return MessageResponse(message="Document deleted successfully")


@router.post("/documents/{doc_id}/submit-approval", response_model=DocumentApprovalResponse)
def submit_document_approval(doc_id: int, reviewer_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    rev = db.query(User).filter(User.id == reviewer_id).first()
    if not doc or not rev:
        raise NotFoundException(message="Document or Reviewer user not found")

    approval = DocumentApproval(
        document_id=doc.id,
        reviewer_id=rev.id,
        status="PENDING"
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)
    return approval


@router.post("/documents/approvals/{approval_id}/review", response_model=DocumentApprovalResponse)
def review_document(approval_id: int, action_in: DocumentApprovalAction, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    appr = db.query(DocumentApproval).filter(DocumentApproval.id == approval_id).first()
    if not appr:
        raise NotFoundException(message="Document approval not found")
    if appr.reviewer_id != current_user.id and not current_user.is_superuser:
        raise ForbiddenException(message="Only assigned reviewer can perform this action")

    appr.status = action_in.status
    appr.remarks = action_in.remarks
    appr.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(appr)
    return appr


@router.post("/documents/{doc_id}/new-version", response_model=DocumentResponse)
def upload_document_version(
    doc_id: int,
    change_summary: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise NotFoundException(message="Document not found")

    new_ver_num = doc.current_version + 1
    save_filename = f"v{new_ver_num}_{int(datetime.now(timezone.utc).timestamp())}_{file.filename}"
    file_dest = os.path.join(settings.UPLOAD_DIR, save_filename)
    with open(file_dest, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(file_dest)
    doc.file_name = file.filename or save_filename
    doc.file_path = file_dest
    doc.file_size = file_size
    doc.current_version = new_ver_num
    doc.mime_type = file.content_type or "application/octet-stream"

    ver = DocumentVersion(
        document_id=doc.id,
        version_number=new_ver_num,
        file_name=doc.file_name,
        file_path=doc.file_path,
        file_size=file_size,
        change_summary=change_summary,
        created_by_id=current_user.id
    )
    db.add(ver)
    db.commit()
    db.refresh(doc)
    return doc


@router.get("/documents/{doc_id}/versions", response_model=list[DocumentVersionResponse])
def get_document_versions(doc_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(DocumentVersion).filter(DocumentVersion.document_id == doc_id).order_by(DocumentVersion.version_number.desc()).all()


@router.get("/audit-logs", response_model=PaginatedResponse[AuditLogResponse])
def list_audit_logs(
    module: str | None = None,
    action: str | None = None,
    user_id: int | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(AuditLog)
    if module:
        query = query.filter(AuditLog.module == module)
    if action:
        query = query.filter(AuditLog.action == action)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)

    total = query.count()
    items = query.order_by(AuditLog.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    total_pages = (total + limit - 1) // limit if total > 0 else 1
    return PaginatedResponse(total=total, page=page, limit=limit, total_pages=total_pages, data=items)

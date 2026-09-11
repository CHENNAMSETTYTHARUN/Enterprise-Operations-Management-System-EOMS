from datetime import datetime, date, timezone
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.core.database import get_db
from app.core.exceptions import NotFoundException, BadRequestException, ForbiddenException
from app.core.dependencies import get_current_user
from app.models.auth import User
from app.models.core_business import Employee, Customer
from app.models.workflow import (
    ApprovalRequest, ApprovalHistory, Expense, Reimbursement,
    Asset, AssetAssignment, AssetReturn, SupportTicket,
    TicketAssignment, TicketEscalation, Complaint, Feedback
)
from app.schemas.workflow import (
    ApprovalCreate, ApprovalAction, ApprovalResponse,
    ExpenseCreate, ExpenseAction, ExpenseResponse,
    ReimbursementCreate, ReimbursementAction, ReimbursementResponse,
    AssetCreate, AssetUpdate, AssetResponse, AssetAssign, AssetAssignmentResponse, AssetReturnCreate, AssetReturnResponse,
    TicketCreate, TicketUpdate, TicketResponse, TicketAssign, TicketEscalate,
    ComplaintCreate, ComplaintResolve, ComplaintResponse,
    FeedbackCreate, FeedbackRespond, FeedbackResponse
)
from app.schemas.common import MessageResponse
from app.services.audit import log_audit

router = APIRouter(prefix="", tags=["Phase 2 — Workflow-Based APIs"])


@router.post("/approvals", response_model=ApprovalResponse, status_code=status.HTTP_201_CREATED)
def submit_approval_request(req_in: ApprovalCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    approval = ApprovalRequest(
        requester_id=current_user.id,
        request_type=req_in.request_type,
        entity_id=req_in.entity_id,
        title=req_in.title,
        details=req_in.details,
        amount=req_in.amount,
        current_stage="MANAGER",
        status="PENDING"
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)

    hist = ApprovalHistory(
        request_id=approval.id,
        actor_id=current_user.id,
        stage="INITIATED",
        action="SUBMITTED",
        remarks="Submitted request for approval"
    )
    db.add(hist)
    db.commit()
    db.refresh(approval)

    log_audit(db, action="SUBMIT", module="APPROVAL", entity="ApprovalRequest", entity_id=str(approval.id), user_id=current_user.id, details="Submitted multi-level approval request")
    return approval


@router.get("/approvals", response_model=list[ApprovalResponse])
def list_approvals(status_filter: str | None = Query(None, alias="status"), stage: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(ApprovalRequest)
    if status_filter:
        query = query.filter(ApprovalRequest.status == status_filter)
    if stage:
        query = query.filter(ApprovalRequest.current_stage == stage)
    return query.order_by(ApprovalRequest.created_at.desc()).all()


@router.get("/approvals/{req_id}", response_model=ApprovalResponse)
def get_approval(req_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    req = db.query(ApprovalRequest).filter(ApprovalRequest.id == req_id).first()
    if not req:
        raise NotFoundException(message="Approval request not found")
    return req


@router.post("/approvals/{req_id}/action", response_model=ApprovalResponse)
def process_approval_action(req_id: int, action_in: ApprovalAction, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    req = db.query(ApprovalRequest).filter(ApprovalRequest.id == req_id).first()
    if not req:
        raise NotFoundException(message="Approval request not found")
    if req.status in ["APPROVED", "REJECTED"]:
        raise BadRequestException(message=f"Request is already finalized with status: {req.status}")

    user_roles = [r.name.upper() for r in current_user.roles]
    is_admin = current_user.is_superuser or ("ADMIN" in user_roles)
    is_manager = "MANAGER" in user_roles or is_admin

    if req.current_stage == "MANAGER":
        if not is_manager:
            raise ForbiddenException(message="Manager role required to review this stage")
        if action_in.action == "APPROVE":
            req.current_stage = "ADMIN"
            req.status = "IN_PROGRESS"
        elif action_in.action == "REJECT":
            req.status = "REJECTED"
        else:
            raise BadRequestException(message="Action must be APPROVE or REJECT")

    elif req.current_stage == "ADMIN":
        if not is_admin:
            raise ForbiddenException(message="Admin role required to review this stage")
        if action_in.action == "APPROVE":
            req.status = "APPROVED"
        elif action_in.action == "REJECT":
            req.status = "REJECTED"
        else:
            raise BadRequestException(message="Action must be APPROVE or REJECT")

    hist = ApprovalHistory(
        request_id=req.id,
        actor_id=current_user.id,
        stage=req.current_stage,
        action=action_in.action,
        remarks=action_in.remarks
    )
    db.add(hist)
    db.commit()
    db.refresh(req)

    log_audit(db, action=action_in.action, module="APPROVAL", entity="ApprovalRequest", entity_id=str(req.id), user_id=current_user.id, details=f"Action {action_in.action} on stage {req.current_stage}")
    return req


@router.post("/expenses", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def submit_expense(exp_in: ExpenseCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    emp = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not emp:
        raise BadRequestException(message="User is not registered as an employee")

    expense = Expense(employee_id=emp.id, **exp_in.model_dump())
    db.add(expense)
    db.commit()
    db.refresh(expense)
    log_audit(db, action="CREATE", module="EXPENSE", entity="Expense", entity_id=str(expense.id), user_id=current_user.id, details=f"Submitted expense {expense.title}")
    return expense


@router.get("/expenses", response_model=list[ExpenseResponse])
def list_expenses(status_filter: str | None = Query(None, alias="status"), employee_id: int | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Expense)
    if status_filter:
        query = query.filter(Expense.status == status_filter)
    if employee_id:
        query = query.filter(Expense.employee_id == employee_id)
    return query.order_by(Expense.created_at.desc()).all()


@router.get("/expenses/{expense_id}", response_model=ExpenseResponse)
def get_expense(expense_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    exp = db.query(Expense).filter(Expense.id == expense_id).first()
    if not exp:
        raise NotFoundException(message="Expense not found")
    return exp


@router.post("/expenses/{expense_id}/action", response_model=ExpenseResponse)
def handle_expense_action(expense_id: int, action_in: ExpenseAction, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    exp = db.query(Expense).filter(Expense.id == expense_id).first()
    if not exp:
        raise NotFoundException(message="Expense not found")
    if exp.status != "PENDING":
        raise BadRequestException(message=f"Expense is already {exp.status}")

    exp.status = action_in.status
    exp.approved_by_id = current_user.id
    db.commit()
    db.refresh(exp)
    log_audit(db, action=action_in.status, module="EXPENSE", entity="Expense", entity_id=str(exp.id), user_id=current_user.id, details=f"Expense marked {action_in.status}")
    return exp


@router.post("/reimbursements", response_model=ReimbursementResponse, status_code=status.HTTP_201_CREATED)
def create_reimbursement(reimb_in: ReimbursementCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    expense = db.query(Expense).filter(Expense.id == reimb_in.expense_id).first()
    if not expense:
        raise NotFoundException(message="Associated expense not found")
    if expense.status != "APPROVED":
        raise BadRequestException(message="Expense must be approved before requesting reimbursement")
    if db.query(Reimbursement).filter(Reimbursement.expense_id == reimb_in.expense_id).first():
        raise BadRequestException(message="Reimbursement already filed for this expense")

    reimb = Reimbursement(
        expense_id=expense.id,
        employee_id=expense.employee_id,
        amount=expense.amount,
        status="PENDING",
        payment_status="UNPAID"
    )
    db.add(reimb)
    db.commit()
    db.refresh(reimb)
    log_audit(db, action="CREATE", module="REIMBURSEMENT", entity="Reimbursement", entity_id=str(reimb.id), user_id=current_user.id, details="Created reimbursement request")
    return reimb


@router.get("/reimbursements", response_model=list[ReimbursementResponse])
def list_reimbursements(status_filter: str | None = Query(None, alias="status"), employee_id: int | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Reimbursement)
    if status_filter:
        query = query.filter(Reimbursement.status == status_filter)
    if employee_id:
        query = query.filter(Reimbursement.employee_id == employee_id)
    return query.order_by(Reimbursement.created_at.desc()).all()


@router.post("/reimbursements/{reimb_id}/action", response_model=ReimbursementResponse)
def handle_reimbursement_action(reimb_id: int, action_in: ReimbursementAction, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    reimb = db.query(Reimbursement).filter(Reimbursement.id == reimb_id).first()
    if not reimb:
        raise NotFoundException(message="Reimbursement not found")

    reimb.status = action_in.status
    if action_in.payment_status:
        reimb.payment_status = action_in.payment_status
    if action_in.payment_reference:
        reimb.payment_reference = action_in.payment_reference
    if action_in.payment_status == "PAID":
        reimb.processed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(reimb)
    return reimb


@router.post("/assets", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
def create_asset(asset_in: AssetCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if db.query(Asset).filter(Asset.asset_code == asset_in.asset_code).first():
        raise BadRequestException(message="Asset code already exists")
    asset = Asset(**asset_in.model_dump())
    db.add(asset)
    db.commit()
    db.refresh(asset)
    log_audit(db, action="CREATE", module="ASSET", entity="Asset", entity_id=str(asset.id), user_id=current_user.id, details=f"Registered asset {asset.name}")
    return asset


@router.get("/assets", response_model=list[AssetResponse])
def list_assets(status_filter: str | None = Query(None, alias="status"), category: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Asset)
    if status_filter:
        query = query.filter(Asset.status == status_filter)
    if category:
        query = query.filter(Asset.category.ilike(f"%{category}%"))
    return query.all()


@router.get("/assets/{asset_id}", response_model=AssetResponse)
def get_asset(asset_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise NotFoundException(message="Asset not found")
    return asset


@router.put("/assets/{asset_id}", response_model=AssetResponse)
def update_asset(asset_id: int, asset_in: AssetUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise NotFoundException(message="Asset not found")
    for k, v in asset_in.model_dump(exclude_unset=True).items():
        setattr(asset, k, v)
    db.commit()
    db.refresh(asset)
    return asset


@router.post("/assets/{asset_id}/assign", response_model=AssetAssignmentResponse)
def assign_asset(asset_id: int, assign_in: AssetAssign, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    emp = db.query(Employee).filter(Employee.id == assign_in.employee_id).first()
    if not asset or not emp:
        raise NotFoundException(message="Asset or Employee not found")
    if asset.status != "AVAILABLE":
        raise BadRequestException(message=f"Asset is currently {asset.status} and cannot be assigned")

    assignment = AssetAssignment(
        asset_id=asset.id,
        employee_id=emp.id,
        condition_notes=assign_in.condition_notes,
        is_active=True
    )
    asset.status = "ASSIGNED"
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    log_audit(db, action="ASSIGN", module="ASSET", entity="AssetAssignment", entity_id=str(assignment.id), user_id=current_user.id, details=f"Assigned asset {asset.asset_code} to employee {emp.id}")
    return assignment


@router.post("/assets/{asset_id}/return", response_model=AssetReturnResponse)
def return_asset(asset_id: int, return_in: AssetReturnCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise NotFoundException(message="Asset not found")

    active_assignment = db.query(AssetAssignment).filter(AssetAssignment.asset_id == asset_id, AssetAssignment.is_active == True).first()
    if not active_assignment:
        raise BadRequestException(message="No active assignment found for this asset")

    active_assignment.is_active = False
    ret = AssetReturn(
        asset_id=asset.id,
        employee_id=active_assignment.employee_id,
        return_date=date.today(),
        has_damage=return_in.has_damage,
        damage_details=return_in.damage_details,
        damage_cost=return_in.damage_cost
    )
    asset.status = "DAMAGED" if return_in.has_damage else "AVAILABLE"
    db.add(ret)
    db.commit()
    db.refresh(ret)
    log_audit(db, action="RETURN", module="ASSET", entity="AssetReturn", entity_id=str(ret.id), user_id=current_user.id, details=f"Returned asset {asset.asset_code}")
    return ret


@router.post("/tickets", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
def create_support_ticket(ticket_in: TicketCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    t_num = f"TICK-{int(datetime.now(timezone.utc).timestamp())}"
    ticket = SupportTicket(
        ticket_number=t_num,
        creator_id=current_user.id,
        title=ticket_in.title,
        description=ticket_in.description,
        category=ticket_in.category,
        priority=ticket_in.priority,
        status="OPEN"
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    log_audit(db, action="CREATE", module="TICKET", entity="SupportTicket", entity_id=str(ticket.id), user_id=current_user.id, details=f"Created support ticket {ticket.ticket_number}")
    return ticket


@router.get("/tickets", response_model=list[TicketResponse])
def list_support_tickets(
    status_filter: str | None = Query(None, alias="status"),
    priority: str | None = None,
    category: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(SupportTicket)
    if status_filter:
        query = query.filter(SupportTicket.status == status_filter)
    if priority:
        query = query.filter(SupportTicket.priority == priority)
    if category:
        query = query.filter(SupportTicket.category == category)
    return query.order_by(SupportTicket.created_at.desc()).all()


@router.get("/tickets/{ticket_id}", response_model=TicketResponse)
def get_ticket(ticket_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not ticket:
        raise NotFoundException(message="Ticket not found")
    return ticket


@router.put("/tickets/{ticket_id}", response_model=TicketResponse)
def update_ticket(ticket_id: int, ticket_in: TicketUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not ticket:
        raise NotFoundException(message="Ticket not found")

    for k, v in ticket_in.model_dump(exclude_unset=True).items():
        setattr(ticket, k, v)

    if ticket_in.status == "CLOSED" and not ticket.closed_at:
        ticket.closed_at = datetime.now(timezone.utc)
        diff = ticket.closed_at.replace(tzinfo=None) - ticket.created_at.replace(tzinfo=None)
        ticket.resolution_time_minutes = int(diff.total_seconds() / 60)

    db.commit()
    db.refresh(ticket)
    return ticket


@router.post("/tickets/{ticket_id}/assign", response_model=TicketResponse)
def assign_ticket(ticket_id: int, assign_in: TicketAssign, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    agent = db.query(User).filter(User.id == assign_in.agent_id).first()
    if not ticket or not agent:
        raise NotFoundException(message="Ticket or Agent user not found")

    db.query(TicketAssignment).filter(TicketAssignment.ticket_id == ticket_id).update({"is_active": False})
    assignment = TicketAssignment(
        ticket_id=ticket.id,
        agent_id=agent.id,
        assigned_by_id=current_user.id,
        is_active=True
    )
    ticket.status = "IN_PROGRESS"
    db.add(assignment)
    db.commit()
    db.refresh(ticket)
    log_audit(db, action="ASSIGN", module="TICKET", entity="SupportTicket", entity_id=str(ticket.id), user_id=current_user.id, details=f"Assigned ticket {ticket.ticket_number} to agent {agent.id}")
    return ticket


@router.post("/tickets/{ticket_id}/escalate", response_model=TicketResponse)
def escalate_ticket(ticket_id: int, esc_in: TicketEscalate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not ticket:
        raise NotFoundException(message="Ticket not found")

    ticket.escalated = True
    ticket.priority = "URGENT"
    escalation = TicketEscalation(
        ticket_id=ticket.id,
        reason=esc_in.reason,
        escalated_to_role=esc_in.escalated_to_role,
        status="ESCALATED"
    )
    db.add(escalation)
    db.commit()
    db.refresh(ticket)
    log_audit(db, action="ESCALATE", module="TICKET", entity="SupportTicket", entity_id=str(ticket.id), user_id=current_user.id, details=f"Escalated ticket {ticket.ticket_number}")
    return ticket


@router.post("/complaints", response_model=ComplaintResponse, status_code=status.HTTP_201_CREATED)
def register_complaint(comp_in: ComplaintCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    cust = db.query(Customer).filter(Customer.id == comp_in.customer_id).first()
    if not cust:
        raise NotFoundException(message="Customer not found")

    complaint = Complaint(
        customer_id=comp_in.customer_id,
        subject=comp_in.subject,
        description=comp_in.description,
        status="PENDING"
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)
    log_audit(db, action="CREATE", module="COMPLAINT", entity="Complaint", entity_id=str(complaint.id), user_id=current_user.id, details="Registered complaint")
    return complaint


@router.get("/complaints", response_model=list[ComplaintResponse])
def list_complaints(status_filter: str | None = Query(None, alias="status"), customer_id: int | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Complaint)
    if status_filter:
        query = query.filter(Complaint.status == status_filter)
    if customer_id:
        query = query.filter(Complaint.customer_id == customer_id)
    return query.order_by(Complaint.created_at.desc()).all()


@router.post("/complaints/{comp_id}/resolve", response_model=ComplaintResponse)
def resolve_complaint(comp_id: int, resolve_in: ComplaintResolve, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    comp = db.query(Complaint).filter(Complaint.id == comp_id).first()
    if not comp:
        raise NotFoundException(message="Complaint not found")

    comp.status = "RESOLVED"
    comp.resolution_notes = resolve_in.resolution_notes
    comp.resolved_at = datetime.now(timezone.utc)
    comp.assigned_to_id = current_user.id
    db.commit()
    db.refresh(comp)
    log_audit(db, action="RESOLVE", module="COMPLAINT", entity="Complaint", entity_id=str(comp.id), user_id=current_user.id, details="Resolved customer complaint")
    return comp


@router.post("/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
def submit_feedback(fb_in: FeedbackCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    fb = Feedback(
        customer_id=fb_in.customer_id,
        category=fb_in.category,
        rating=fb_in.rating,
        feedback_text=fb_in.feedback_text,
        status="SUBMITTED"
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    log_audit(db, action="SUBMIT", module="FEEDBACK", entity="Feedback", entity_id=str(fb.id), user_id=current_user.id, details="Customer submitted feedback")
    return fb


@router.get("/feedback", response_model=list[FeedbackResponse])
def list_feedbacks(category: str | None = None, status_filter: str | None = Query(None, alias="status"), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Feedback)
    if category:
        query = query.filter(Feedback.category == category)
    if status_filter:
        query = query.filter(Feedback.status == status_filter)
    return query.order_by(Feedback.created_at.desc()).all()


@router.post("/feedback/{fb_id}/respond", response_model=FeedbackResponse)
def respond_feedback(fb_id: int, resp_in: FeedbackRespond, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    fb = db.query(Feedback).filter(Feedback.id == fb_id).first()
    if not fb:
        raise NotFoundException(message="Feedback not found")

    fb.admin_response = resp_in.admin_response
    fb.status = "RESPONDED"
    db.commit()
    db.refresh(fb)
    return fb

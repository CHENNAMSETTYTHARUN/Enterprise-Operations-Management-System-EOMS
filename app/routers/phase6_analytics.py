from datetime import datetime, date, timezone, timedelta
from typing import Any
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func, text
from app.core.database import get_db
from app.core.cache import cache
from app.core.config import settings
from app.core.exceptions import NotFoundException, BadRequestException, ConflictException, ForbiddenException, AppException
from app.core.dependencies import get_current_user
from app.models.auth import User
from app.models.core_business import Customer, Employee, Department, Project, Task, Attendance, LeaveRequest, WorkProgress
from app.models.workflow import SupportTicket, ApprovalRequest, Expense, Reimbursement, Asset
from app.models.commerce import Product, SalesOrder, OrderItem, Invoice, Payment, RefundRequest, InventoryLog
from app.models.infrastructure import AuditLog, Notification
from app.schemas.analytics import GlobalSearchResult, DashboardAnalytics, CustomReportRequest, CustomReportResponse
from app.schemas.common import HealthResponse, MessageResponse
from app.services.audit import log_audit

router = APIRouter(prefix="", tags=["Phase 6 — Production & Final Challenge"])


@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    redis_status = cache.ping()

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        database=db_status,
        redis=redis_status,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@router.get("/search/global", response_model=list[GlobalSearchResult])
def global_search(
    q: str = Query(..., min_length=1),
    limit_per_module: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    results: list[GlobalSearchResult] = []

    customers = db.query(Customer).filter(or_(Customer.name.ilike(f"%{q}%"), Customer.email.ilike(f"%{q}%"))).limit(limit_per_module).all()
    for c in customers:
        results.append(GlobalSearchResult(category="Customer", id=c.id, title=c.name, subtitle=c.email, status=c.status))

    employees = db.query(Employee).join(User).filter(or_(User.full_name.ilike(f"%{q}%"), Employee.employee_code.ilike(f"%{q}%"), Employee.designation.ilike(f"%{q}%"))).limit(limit_per_module).all()
    for e in employees:
        results.append(GlobalSearchResult(category="Employee", id=e.id, title=e.user.full_name or e.employee_code, subtitle=e.designation, status="ACTIVE" if e.is_active else "INACTIVE"))

    projects = db.query(Project).filter(or_(Project.name.ilike(f"%{q}%"), Project.code.ilike(f"%{q}%"))).limit(limit_per_module).all()
    for p in projects:
        results.append(GlobalSearchResult(category="Project", id=p.id, title=p.name, subtitle=p.code, status=p.status))

    tasks = db.query(Task).filter(or_(Task.title.ilike(f"%{q}%"), Task.description.ilike(f"%{q}%"))).limit(limit_per_module).all()
    for t in tasks:
        results.append(GlobalSearchResult(category="Task", id=t.id, title=t.title, subtitle=t.priority, status=t.status))

    products = db.query(Product).filter(or_(Product.name.ilike(f"%{q}%"), Product.sku.ilike(f"%{q}%"))).limit(limit_per_module).all()
    for pr in products:
        results.append(GlobalSearchResult(category="Product", id=pr.id, title=pr.name, subtitle=f"SKU: {pr.sku} | ${pr.price}", status="ACTIVE" if pr.is_active else "INACTIVE"))

    tickets = db.query(SupportTicket).filter(or_(SupportTicket.ticket_number.ilike(f"%{q}%"), SupportTicket.title.ilike(f"%{q}%"))).limit(limit_per_module).all()
    for tk in tickets:
        results.append(GlobalSearchResult(category="SupportTicket", id=tk.id, title=tk.title, subtitle=tk.ticket_number, status=tk.status))

    return results


@router.get("/dashboard/analytics", response_model=DashboardAnalytics)
def get_dashboard_analytics(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    cached_dash = cache.get("dashboard:analytics")
    if cached_dash:
        return DashboardAnalytics(**cached_dash)

    tot_cust = db.query(Customer).count()
    tot_emp = db.query(Employee).count()
    tot_dept = db.query(Department).count()
    tot_proj = db.query(Project).count()
    tot_tasks = db.query(Task).count()
    tot_prod = db.query(Product).count()
    tot_orders = db.query(SalesOrder).count()
    tot_tickets = db.query(SupportTicket).count()
    open_tickets = db.query(SupportTicket).filter(SupportTicket.status.in_(["OPEN", "IN_PROGRESS"])).count()
    pending_leaves = db.query(LeaveRequest).filter(LeaveRequest.status == "PENDING").count()
    pending_approvals = db.query(ApprovalRequest).filter(ApprovalRequest.status == "PENDING").count()
    revenue = db.query(func.sum(SalesOrder.total_amount)).filter(SalesOrder.status == "PAID").scalar() or 0.0

    data = {
        "total_customers": tot_cust,
        "total_employees": tot_emp,
        "total_departments": tot_dept,
        "total_projects": tot_proj,
        "total_tasks": tot_tasks,
        "total_products": tot_prod,
        "total_sales_orders": tot_orders,
        "total_tickets": tot_tickets,
        "open_tickets": open_tickets,
        "pending_leaves": pending_leaves,
        "pending_approvals": pending_approvals,
        "revenue": float(revenue)
    }
    cache.set("dashboard:analytics", data, expire_seconds=30)
    return DashboardAnalytics(**data)


@router.post("/reports/custom", response_model=CustomReportResponse)
def generate_custom_report(req: CustomReportRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    mod = req.module.upper()
    data_out = []

    if mod == "SALES":
        q = db.query(SalesOrder)
        if req.status:
            q = q.filter(SalesOrder.status == req.status)
        if req.start_date:
            q = q.filter(SalesOrder.created_at >= datetime.combine(req.start_date, datetime.min.time()))
        if req.end_date:
            q = q.filter(SalesOrder.created_at <= datetime.combine(req.end_date, datetime.max.time()))
        for item in q.all():
            data_out.append({
                "order_number": item.order_number,
                "customer_id": item.customer_id,
                "total_amount": item.total_amount,
                "status": item.status,
                "date": str(item.created_at)
            })

    elif mod == "ATTENDANCE":
        q = db.query(Attendance)
        if req.start_date:
            q = q.filter(Attendance.attendance_date >= req.start_date)
        if req.end_date:
            q = q.filter(Attendance.attendance_date <= req.end_date)
        for item in q.all():
            data_out.append({
                "employee_id": item.employee_id,
                "date": str(item.attendance_date),
                "check_in": str(item.check_in),
                "check_out": str(item.check_out) if item.check_out else None,
                "status": item.status
            })

    elif mod == "TASKS":
        q = db.query(Task)
        if req.status:
            q = q.filter(Task.status == req.status)
        for item in q.all():
            data_out.append({
                "task_id": item.id,
                "title": item.title,
                "project_id": item.project_id,
                "assigned_to_id": item.assigned_to_id,
                "priority": item.priority,
                "status": item.status
            })
    else:
        q = db.query(Customer)
        for item in q.all():
            data_out.append({"id": item.id, "name": item.name, "email": item.email, "status": item.status})

    return CustomReportResponse(
        module=mod,
        record_count=len(data_out),
        data=data_out
    )


@router.post("/transactions/test-rollback")
def test_database_transaction_rollback(simulate_error: bool = True, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    test_tag = f"test_{int(datetime.now(timezone.utc).timestamp())}"
    try:
        cust = Customer(
            name=f"TxTest {test_tag}",
            email=f"{test_tag}@transactiontest.com",
            status="ACTIVE"
        )
        db.add(cust)
        db.flush()

        if simulate_error:
            raise ValueError("Forced error to test atomic rollback integrity")

        dept = Department(
            name=f"TxDept {test_tag}",
            code=f"D_{test_tag[:10]}",
            is_active=True
        )
        db.add(dept)
        db.commit()
        return {"status": "committed", "customer_id": cust.id, "department_id": dept.id}
    except Exception as e:
        db.rollback()
        check_cust = db.query(Customer).filter(Customer.email == f"{test_tag}@transactiontest.com").first()
        return {
            "status": "rolled_back",
            "error_encountered": str(e),
            "customer_saved": check_cust is not None
        }


@router.get("/exceptions/trigger")
def trigger_exception_demo(exc_type: str = "not_found"):
    if exc_type == "not_found":
        raise NotFoundException(message="Simulated 404 resource not found")
    elif exc_type == "forbidden":
        raise ForbiddenException(message="Simulated 403 access denied")
    elif exc_type == "conflict":
        raise ConflictException(message="Simulated 409 duplicate entry conflict")
    elif exc_type == "bad_request":
        raise BadRequestException(message="Simulated 400 invalid business operation")
    else:
        raise AppException(message="Generic custom app exception", status_code=400, code="DEMO_ERROR")


@router.post("/workflow/enterprise-full-run")
def run_enterprise_workflow_challenge(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ts = int(datetime.now(timezone.utc).timestamp())

    cust = Customer(name=f"Enterprise Client {ts}", email=f"client_{ts}@enterprise.com", company="Global Corp", status="ACTIVE")
    db.add(cust)
    db.flush()

    dept = Department(name=f"Engineering {ts}", code=f"ENG_{ts}", is_active=True)
    db.add(dept)
    db.flush()

    proj = Project(name=f"EOMS Platform {ts}", code=f"PRJ_{ts}", start_date=date.today(), status="ACTIVE", progress_percent=0.0)
    db.add(proj)
    db.flush()

    task = Task(title=f"Core API Development {ts}", project_id=proj.id, priority="HIGH", status="IN_PROGRESS")
    db.add(task)
    db.flush()

    appr = ApprovalRequest(requester_id=current_user.id, request_type="PROJECT_BUDGET", entity_id=proj.id, title=f"Budget Approval {proj.code}", amount=50000.0, current_stage="ADMIN", status="APPROVED")
    db.add(appr)
    db.flush()

    prod = Product(sku=f"SKU-ENT-{ts}", name=f"Enterprise Software License {ts}", category="Software", price=4999.0, stock_quantity=100, is_active=True)
    db.add(prod)
    db.flush()

    order = SalesOrder(order_number=f"ORD-ENT-{ts}", customer_id=cust.id, subtotal=4999.0, discount_amount=0.0, tax_amount=249.95, total_amount=5248.95, status="PAID")
    db.add(order)
    db.flush()

    order_item = OrderItem(order_id=order.id, product_id=prod.id, quantity=1, unit_price=4999.0, total_price=4999.0)
    db.add(order_item)
    prod.stock_quantity -= 1

    inv = Invoice(invoice_number=f"INV-ENT-{ts}", order_id=order.id, total_amount=order.total_amount, tax_amount=order.tax_amount, status="PAID", issued_at=datetime.now(timezone.utc), due_date=datetime.now(timezone.utc) + timedelta(days=30))
    db.add(inv)
    db.flush()

    payment = Payment(transaction_id=f"TXN-ENT-{ts}", order_id=order.id, amount=order.total_amount, payment_method="SIMULATED", status="SUCCESSFUL")
    db.add(payment)
    db.flush()

    notif = Notification(user_id=current_user.id, title="Enterprise Workflow Completed", message=f"Full workflow executed successfully for Order {order.order_number}", type="SUCCESS", is_read=False)
    db.add(notif)

    log_audit(db, action="WORKFLOW_COMPLETE", module="ENTERPRISE", entity="Workflow", entity_id=f"RUN-{ts}", user_id=current_user.id, details="Executed Module 60 full enterprise workflow integration")

    db.commit()

    return {
        "success": True,
        "message": "Enterprise Workflow completed successfully across all 60 interconnected modules",
        "workflow_summary": {
            "customer": {"id": cust.id, "name": cust.name, "email": cust.email},
            "department": {"id": dept.id, "code": dept.code},
            "project": {"id": proj.id, "code": proj.code},
            "task": {"id": task.id, "title": task.title},
            "approval": {"id": appr.id, "status": appr.status},
            "product": {"id": prod.id, "sku": prod.sku, "remaining_stock": prod.stock_quantity},
            "order": {"id": order.id, "order_number": order.order_number, "total": order.total_amount},
            "invoice": {"id": inv.id, "invoice_number": inv.invoice_number, "status": inv.status},
            "payment": {"id": payment.id, "transaction_id": payment.transaction_id, "status": payment.status},
            "notification": {"id": notif.id, "title": notif.title}
        }
    }

from datetime import datetime, date, timezone
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from app.core.database import get_db
from app.core.exceptions import NotFoundException, BadRequestException, ConflictException
from app.core.dependencies import get_current_user
from app.models.auth import User
from app.models.core_business import (
    Customer, Department, Employee, Attendance, LeaveRequest,
    Holiday, Project, ProjectMember, Task, WorkProgress
)
from app.schemas.core_business import (
    CustomerCreate, CustomerUpdate, CustomerResponse,
    DepartmentCreate, DepartmentUpdate, DepartmentResponse, DepartmentStatsResponse,
    EmployeeCreate, EmployeeUpdate, EmployeeResponse,
    AttendanceCheckIn, AttendanceCheckOut, AttendanceResponse,
    LeaveCreate, LeaveAction, LeaveResponse,
    HolidayCreate, HolidayUpdate, HolidayResponse,
    ProjectCreate, ProjectUpdate, ProjectResponse, ProjectMemberCreate, ProjectMemberResponse,
    TaskCreate, TaskUpdate, TaskResponse, BatchTaskAssign,
    WorkProgressCreate, WorkProgressResponse
)
from app.schemas.common import MessageResponse, PaginatedResponse
from app.services.audit import log_audit

router = APIRouter(prefix="", tags=["Phase 1 — Core Business APIs"])


@router.post("/customers", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(customer_in: CustomerCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    existing = db.query(Customer).filter(Customer.email == customer_in.email).first()
    if existing:
        raise ConflictException(message="Customer with this email already exists")
    customer = Customer(**customer_in.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    log_audit(db, action="CREATE", module="CUSTOMER", entity="Customer", entity_id=str(customer.id), user_id=current_user.id, details=f"Created customer {customer.name}")
    return customer


@router.get("/customers", response_model=PaginatedResponse[CustomerResponse])
def get_customers(
    search: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    city: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Customer)
    if search:
        query = query.filter(or_(Customer.name.ilike(f"%{search}%"), Customer.email.ilike(f"%{search}%"), Customer.company.ilike(f"%{search}%")))
    if status_filter:
        query = query.filter(Customer.status == status_filter)
    if city:
        query = query.filter(Customer.city.ilike(f"%{city}%"))

    total = query.count()
    items = query.offset((page - 1) * limit).limit(limit).all()
    total_pages = (total + limit - 1) // limit if total > 0 else 1

    return PaginatedResponse(total=total, page=page, limit=limit, total_pages=total_pages, data=items)


@router.get("/customers/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise NotFoundException(message="Customer not found")
    return customer


@router.put("/customers/{customer_id}", response_model=CustomerResponse)
def update_customer(customer_id: int, update_in: CustomerUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise NotFoundException(message="Customer not found")
    update_data = update_in.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(customer, field, val)
    db.commit()
    db.refresh(customer)
    log_audit(db, action="UPDATE", module="CUSTOMER", entity="Customer", entity_id=str(customer.id), user_id=current_user.id, details="Updated customer profile")
    return customer


@router.delete("/customers/{customer_id}", response_model=MessageResponse)
def delete_customer(customer_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise NotFoundException(message="Customer not found")
    customer.status = "INACTIVE"
    db.commit()
    log_audit(db, action="DEACTIVATE", module="CUSTOMER", entity="Customer", entity_id=str(customer.id), user_id=current_user.id, details="Deactivated customer")
    return MessageResponse(message="Customer deactivated successfully")


@router.post("/departments", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
def create_department(dept_in: DepartmentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if db.query(Department).filter(or_(Department.name == dept_in.name, Department.code == dept_in.code)).first():
        raise ConflictException(message="Department with name or code already exists")
    dept = Department(**dept_in.model_dump())
    db.add(dept)
    db.commit()
    db.refresh(dept)
    log_audit(db, action="CREATE", module="DEPARTMENT", entity="Department", entity_id=str(dept.id), user_id=current_user.id, details=f"Created department {dept.name}")
    return dept


@router.get("/departments", response_model=list[DepartmentResponse])
def list_departments(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Department).all()


@router.get("/departments/{dept_id}", response_model=DepartmentResponse)
def get_department(dept_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise NotFoundException(message="Department not found")
    return dept


@router.put("/departments/{dept_id}", response_model=DepartmentResponse)
def update_department(dept_id: int, dept_in: DepartmentUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise NotFoundException(message="Department not found")
    for k, v in dept_in.model_dump(exclude_unset=True).items():
        setattr(dept, k, v)
    db.commit()
    db.refresh(dept)
    return dept


@router.delete("/departments/{dept_id}", response_model=MessageResponse)
def delete_department(dept_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise NotFoundException(message="Department not found")
    dept.is_active = False
    db.commit()
    return MessageResponse(message="Department deactivated successfully")


@router.get("/departments/{dept_id}/stats", response_model=DepartmentStatsResponse)
def get_department_stats(dept_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise NotFoundException(message="Department not found")
    total_emp = db.query(Employee).filter(Employee.department_id == dept_id).count()
    active_emp = db.query(Employee).filter(Employee.department_id == dept_id, Employee.is_active == True).count()
    return DepartmentStatsResponse(
        department_id=dept.id,
        department_name=dept.name,
        department_code=dept.code,
        total_employees=total_emp,
        active_employees=active_emp
    )


@router.post("/employees", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_employee(emp_in: EmployeeCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user = db.query(User).filter(User.id == emp_in.user_id).first()
    if not user:
        raise NotFoundException(message="User not found for employee profile")
    if db.query(Employee).filter(Employee.user_id == emp_in.user_id).first():
        raise ConflictException(message="Employee profile already exists for this user")
    if db.query(Employee).filter(Employee.employee_code == emp_in.employee_code).first():
        raise ConflictException(message="Employee code already in use")

    employee = Employee(**emp_in.model_dump())
    db.add(employee)
    db.commit()
    db.refresh(employee)
    log_audit(db, action="CREATE", module="EMPLOYEE", entity="Employee", entity_id=str(employee.id), user_id=current_user.id, details=f"Created employee {employee.employee_code}")
    return employee


@router.get("/employees", response_model=list[EmployeeResponse])
def list_employees(department_id: int | None = None, designation: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Employee)
    if department_id:
        query = query.filter(Employee.department_id == department_id)
    if designation:
        query = query.filter(Employee.designation.ilike(f"%{designation}%"))
    return query.all()


@router.get("/employees/{emp_id}", response_model=EmployeeResponse)
def get_employee(emp_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    emp = db.query(Employee).filter(Employee.id == emp_id).first()
    if not emp:
        raise NotFoundException(message="Employee not found")
    return emp


@router.put("/employees/{emp_id}", response_model=EmployeeResponse)
def update_employee(emp_id: int, emp_in: EmployeeUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    emp = db.query(Employee).filter(Employee.id == emp_id).first()
    if not emp:
        raise NotFoundException(message="Employee not found")
    for k, v in emp_in.model_dump(exclude_unset=True).items():
        setattr(emp, k, v)
    db.commit()
    db.refresh(emp)
    return emp


@router.delete("/employees/{emp_id}", response_model=MessageResponse)
def delete_employee(emp_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    emp = db.query(Employee).filter(Employee.id == emp_id).first()
    if not emp:
        raise NotFoundException(message="Employee not found")
    emp.is_active = False
    db.commit()
    return MessageResponse(message="Employee deactivated successfully")


@router.post("/employees/{emp_id}/assign-department/{dept_id}", response_model=EmployeeResponse)
def assign_employee_department(emp_id: int, dept_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    emp = db.query(Employee).filter(Employee.id == emp_id).first()
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not emp or not dept:
        raise NotFoundException(message="Employee or Department not found")
    emp.department_id = dept.id
    db.commit()
    db.refresh(emp)
    return emp


@router.post("/employees/{emp_id}/remove-department", response_model=EmployeeResponse)
def remove_employee_department(emp_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    emp = db.query(Employee).filter(Employee.id == emp_id).first()
    if not emp:
        raise NotFoundException(message="Employee not found")
    emp.department_id = None
    db.commit()
    db.refresh(emp)
    return emp


@router.post("/attendance/check-in", response_model=AttendanceResponse)
def attendance_check_in(data: AttendanceCheckIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    emp = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not emp:
        raise BadRequestException(message="User is not linked to an employee profile")

    today = date.today()
    existing = db.query(Attendance).filter(Attendance.employee_id == emp.id, Attendance.attendance_date == today).first()
    if existing and existing.check_in:
        raise BadRequestException(message="Employee already checked in for today")

    now = datetime.now(timezone.utc)
    attendance = Attendance(
        employee_id=emp.id,
        attendance_date=today,
        check_in=now,
        status="PRESENT",
        notes=data.notes
    )
    db.add(attendance)
    db.commit()
    db.refresh(attendance)
    log_audit(db, action="CHECK_IN", module="ATTENDANCE", entity="Attendance", entity_id=str(attendance.id), user_id=current_user.id, details="Employee check-in logged")
    return attendance


@router.post("/attendance/check-out", response_model=AttendanceResponse)
def attendance_check_out(data: AttendanceCheckOut, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    emp = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not emp:
        raise BadRequestException(message="User is not linked to an employee profile")

    today = date.today()
    attendance = db.query(Attendance).filter(Attendance.employee_id == emp.id, Attendance.attendance_date == today).first()
    if not attendance or not attendance.check_in:
        raise BadRequestException(message="No check-in record found for today")
    if attendance.check_out:
        raise BadRequestException(message="Employee already checked out for today")

    attendance.check_out = datetime.now(timezone.utc)
    if data.notes:
        attendance.notes = f"{attendance.notes or ''}; {data.notes}".strip("; ")
    db.commit()
    db.refresh(attendance)
    log_audit(db, action="CHECK_OUT", module="ATTENDANCE", entity="Attendance", entity_id=str(attendance.id), user_id=current_user.id, details="Employee check-out logged")
    return attendance


@router.get("/attendance/history", response_model=list[AttendanceResponse])
def get_attendance_history(
    employee_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Attendance)
    if employee_id:
        query = query.filter(Attendance.employee_id == employee_id)
    if start_date:
        query = query.filter(Attendance.attendance_date >= start_date)
    if end_date:
        query = query.filter(Attendance.attendance_date <= end_date)
    return query.order_by(Attendance.attendance_date.desc()).all()


@router.post("/leaves", response_model=LeaveResponse, status_code=status.HTTP_201_CREATED)
def create_leave_request(leave_in: LeaveCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    emp = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not emp:
        raise BadRequestException(message="User has no employee profile to request leave")
    if leave_in.end_date < leave_in.start_date:
        raise BadRequestException(message="End date cannot be prior to start date")

    leave = LeaveRequest(
        employee_id=emp.id,
        leave_type=leave_in.leave_type,
        start_date=leave_in.start_date,
        end_date=leave_in.end_date,
        reason=leave_in.reason,
        status="PENDING"
    )
    db.add(leave)
    db.commit()
    db.refresh(leave)
    log_audit(db, action="CREATE", module="LEAVE", entity="LeaveRequest", entity_id=str(leave.id), user_id=current_user.id, details="Leave requested")
    return leave


@router.get("/leaves", response_model=list[LeaveResponse])
def list_leaves(status_filter: str | None = Query(None, alias="status"), employee_id: int | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(LeaveRequest)
    if status_filter:
        query = query.filter(LeaveRequest.status == status_filter)
    if employee_id:
        query = query.filter(LeaveRequest.employee_id == employee_id)
    return query.order_by(LeaveRequest.created_at.desc()).all()


@router.post("/leaves/{leave_id}/action", response_model=LeaveResponse)
def handle_leave_action(leave_id: int, action_in: LeaveAction, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    leave = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not leave:
        raise NotFoundException(message="Leave request not found")
    if leave.status != "PENDING" and action_in.status != "CANCELLED":
        raise BadRequestException(message=f"Cannot change leave status from {leave.status}")

    approver = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    leave.status = action_in.status
    leave.approved_by_id = approver.id if approver else None
    leave.admin_remarks = action_in.admin_remarks
    db.commit()
    db.refresh(leave)
    log_audit(db, action=action_in.status, module="LEAVE", entity="LeaveRequest", entity_id=str(leave.id), user_id=current_user.id, details=f"Leave status changed to {action_in.status}")
    return leave


@router.post("/holidays", response_model=HolidayResponse, status_code=status.HTTP_201_CREATED)
def create_holiday(holiday_in: HolidayCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if db.query(Holiday).filter(Holiday.holiday_date == holiday_in.holiday_date).first():
        raise ConflictException(message="Holiday on this date already exists")
    h = Holiday(**holiday_in.model_dump())
    db.add(h)
    db.commit()
    db.refresh(h)
    return h


@router.get("/holidays", response_model=list[HolidayResponse])
def list_holidays(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Holiday).order_by(Holiday.holiday_date.asc()).all()


@router.get("/holidays/check-date/{check_date}")
def check_holiday_date(check_date: date, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    h = db.query(Holiday).filter(Holiday.holiday_date == check_date).first()
    is_weekend = check_date.weekday() in [5, 6]
    return {
        "date": check_date,
        "is_holiday": h is not None,
        "holiday_name": h.name if h else None,
        "is_weekend": is_weekend,
        "is_working_day": (h is None) and (not is_weekend)
    }


@router.delete("/holidays/{holiday_id}", response_model=MessageResponse)
def delete_holiday(holiday_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    h = db.query(Holiday).filter(Holiday.id == holiday_id).first()
    if not h:
        raise NotFoundException(message="Holiday not found")
    db.delete(h)
    db.commit()
    return MessageResponse(message="Holiday deleted successfully")


@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(proj_in: ProjectCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if db.query(Project).filter(Project.code == proj_in.code).first():
        raise ConflictException(message="Project code already exists")
    project = Project(**proj_in.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    log_audit(db, action="CREATE", module="PROJECT", entity="Project", entity_id=str(project.id), user_id=current_user.id, details=f"Created project {project.name}")
    return project


@router.get("/projects", response_model=list[ProjectResponse])
def list_projects(status_filter: str | None = Query(None, alias="status"), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Project)
    if status_filter:
        query = query.filter(Project.status == status_filter)
    return query.all()


@router.get("/projects/{proj_id}", response_model=ProjectResponse)
def get_project(proj_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    p = db.query(Project).filter(Project.id == proj_id).first()
    if not p:
        raise NotFoundException(message="Project not found")
    return p


@router.put("/projects/{proj_id}", response_model=ProjectResponse)
def update_project(proj_id: int, proj_in: ProjectUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    p = db.query(Project).filter(Project.id == proj_id).first()
    if not p:
        raise NotFoundException(message="Project not found")
    for k, v in proj_in.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return p


@router.delete("/projects/{proj_id}", response_model=MessageResponse)
def delete_project(proj_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    p = db.query(Project).filter(Project.id == proj_id).first()
    if not p:
        raise NotFoundException(message="Project not found")
    p.status = "ARCHIVED"
    db.commit()
    return MessageResponse(message="Project archived successfully")


@router.post("/projects/{proj_id}/members", response_model=ProjectMemberResponse)
def add_project_member(proj_id: int, member_in: ProjectMemberCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    p = db.query(Project).filter(Project.id == proj_id).first()
    e = db.query(Employee).filter(Employee.id == member_in.employee_id).first()
    if not p or not e:
        raise NotFoundException(message="Project or Employee not found")
    existing = db.query(ProjectMember).filter(ProjectMember.project_id == proj_id, ProjectMember.employee_id == member_in.employee_id).first()
    if existing:
        raise ConflictException(message="Employee is already a project member")

    member = ProjectMember(project_id=proj_id, employee_id=member_in.employee_id, role_in_project=member_in.role_in_project)
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.delete("/projects/{proj_id}/members/{emp_id}", response_model=MessageResponse)
def remove_project_member(proj_id: int, emp_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    member = db.query(ProjectMember).filter(ProjectMember.project_id == proj_id, ProjectMember.employee_id == emp_id).first()
    if not member:
        raise NotFoundException(message="Project member record not found")
    db.delete(member)
    db.commit()
    return MessageResponse(message="Project member removed successfully")


@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(task_in: TaskCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = Task(**task_in.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    log_audit(db, action="CREATE", module="TASK", entity="Task", entity_id=str(task.id), user_id=current_user.id, details=f"Created task {task.title}")
    return task


@router.get("/tasks", response_model=list[TaskResponse])
def list_tasks(
    project_id: int | None = None,
    assigned_to_id: int | None = None,
    status_filter: str | None = Query(None, alias="status"),
    priority: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Task)
    if project_id:
        query = query.filter(Task.project_id == project_id)
    if assigned_to_id:
        query = query.filter(Task.assigned_to_id == assigned_to_id)
    if status_filter:
        query = query.filter(Task.status == status_filter)
    if priority:
        query = query.filter(Task.priority == priority)
    return query.all()


@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise NotFoundException(message="Task not found")
    return task


@router.put("/tasks/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, task_in: TaskUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise NotFoundException(message="Task not found")
    for k, v in task_in.model_dump(exclude_unset=True).items():
        setattr(task, k, v)
    db.commit()
    db.refresh(task)
    log_audit(db, action="UPDATE", module="TASK", entity="Task", entity_id=str(task.id), user_id=current_user.id, details="Updated task details")
    return task


@router.delete("/tasks/{task_id}", response_model=MessageResponse)
def delete_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise NotFoundException(message="Task not found")
    db.delete(task)
    db.commit()
    return MessageResponse(message="Task deleted successfully")


@router.post("/tasks/batch-assign", response_model=MessageResponse)
def batch_assign_tasks(batch_in: BatchTaskAssign, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    emp = db.query(Employee).filter(Employee.id == batch_in.employee_id).first()
    if not emp:
        raise NotFoundException(message="Employee not found")
    db.query(Task).filter(Task.id.in_(batch_in.task_ids)).update({"assigned_to_id": batch_in.employee_id}, synchronize_session=False)
    db.commit()
    log_audit(db, action="ASSIGN", module="TASK", entity="TaskBatch", entity_id="multiple", user_id=current_user.id, details=f"Batch assigned {len(batch_in.task_ids)} tasks to employee {emp.id}")
    return MessageResponse(message=f"Assigned {len(batch_in.task_ids)} tasks to employee {emp.employee_code}")


@router.post("/work-progress", response_model=WorkProgressResponse, status_code=status.HTTP_201_CREATED)
def log_work_progress(progress_in: WorkProgressCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    emp = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not emp:
        raise BadRequestException(message="Current user has no employee record")

    wp = WorkProgress(employee_id=emp.id, **progress_in.model_dump())
    db.add(wp)

    if progress_in.task_id and progress_in.progress_percentage >= 100:
        task = db.query(Task).filter(Task.id == progress_in.task_id).first()
        if task:
            task.status = "COMPLETED"

    if progress_in.project_id:
        avg_progress = db.query(func.avg(WorkProgress.progress_percentage)).filter(WorkProgress.project_id == progress_in.project_id).scalar()
        proj = db.query(Project).filter(Project.id == progress_in.project_id).first()
        if proj and avg_progress is not None:
            proj.progress_percent = min(100.0, float(avg_progress))

    db.commit()
    db.refresh(wp)
    log_audit(db, action="LOG_PROGRESS", module="PROGRESS", entity="WorkProgress", entity_id=str(wp.id), user_id=current_user.id, details=f"Logged work progress for date {wp.date_logged}")
    return wp


@router.get("/work-progress", response_model=list[WorkProgressResponse])
def get_work_progress(
    employee_id: int | None = None,
    project_id: int | None = None,
    task_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(WorkProgress)
    if employee_id:
        query = query.filter(WorkProgress.employee_id == employee_id)
    if project_id:
        query = query.filter(WorkProgress.project_id == project_id)
    if task_id:
        query = query.filter(WorkProgress.task_id == task_id)
    if start_date:
        query = query.filter(WorkProgress.date_logged >= start_date)
    if end_date:
        query = query.filter(WorkProgress.date_logged <= end_date)
    return query.order_by(WorkProgress.date_logged.desc()).all()

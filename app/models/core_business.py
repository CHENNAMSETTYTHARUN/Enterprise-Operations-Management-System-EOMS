from datetime import datetime, date, time, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Time, ForeignKey, Text, Float, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(50), nullable=True)
    company = Column(String(255), nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    status = Column(String(50), default="ACTIVE", index=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    sales_orders = relationship("SalesOrder", back_populates="customer")
    appointments = relationship("Appointment", back_populates="customer")
    feedbacks = relationship("Feedback", back_populates="customer")
    complaints = relationship("Complaint", back_populates="customer")


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    code = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    manager_id = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    employees = relationship("Employee", back_populates="department", foreign_keys="Employee.department_id")


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True)
    employee_code = Column(String(50), unique=True, index=True, nullable=False)
    designation = Column(String(100), nullable=False, index=True)
    phone = Column(String(50), nullable=True)
    join_date = Column(Date, default=date.today, nullable=False)
    salary = Column(Float, default=0.0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="employee")
    department = relationship("Department", back_populates="employees", foreign_keys=[department_id])
    attendances = relationship("Attendance", back_populates="employee")
    leaves = relationship("LeaveRequest", back_populates="employee", foreign_keys="LeaveRequest.employee_id")
    assigned_tasks = relationship("Task", back_populates="assignee", foreign_keys="Task.assigned_to_id")
    progress_logs = relationship("WorkProgress", back_populates="employee")
    expenses = relationship("Expense", back_populates="employee")
    reimbursements = relationship("Reimbursement", back_populates="employee")
    assigned_assets = relationship("AssetAssignment", back_populates="employee")


class Attendance(Base):
    __tablename__ = "attendances"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    attendance_date = Column(Date, default=date.today, nullable=False, index=True)
    check_in = Column(DateTime, nullable=False)
    check_out = Column(DateTime, nullable=True)
    status = Column(String(50), default="PRESENT", nullable=False)
    notes = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    employee = relationship("Employee", back_populates="attendances")


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    leave_type = Column(String(50), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(50), default="PENDING", index=True, nullable=False)
    approved_by_id = Column(Integer, ForeignKey("employees.id", ondelete="SET NULL"), nullable=True)
    admin_remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    employee = relationship("Employee", back_populates="leaves", foreign_keys=[employee_id])
    approver = relationship("Employee", foreign_keys=[approved_by_id])


class Holiday(Base):
    __tablename__ = "holidays"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    holiday_date = Column(Date, unique=True, index=True, nullable=False)
    description = Column(String(255), nullable=True)
    is_recurring = Column(Boolean, default=False, nullable=False)


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    deadline = Column(Date, nullable=True)
    progress_percent = Column(Float, default=0.0, nullable=False)
    status = Column(String(50), default="ACTIVE", index=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="project")
    progress_updates = relationship("WorkProgress", back_populates="project")


class ProjectMember(Base):
    __tablename__ = "project_members"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    role_in_project = Column(String(100), default="Member", nullable=False)
    joined_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    project = relationship("Project", back_populates="members")
    employee = relationship("Employee")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    assigned_to_id = Column(Integer, ForeignKey("employees.id", ondelete="SET NULL"), nullable=True, index=True)
    priority = Column(String(50), default="MEDIUM", index=True, nullable=False)
    status = Column(String(50), default="TODO", index=True, nullable=False)
    due_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    project = relationship("Project", back_populates="tasks")
    assignee = relationship("Employee", back_populates="assigned_tasks", foreign_keys=[assigned_to_id])
    progress_entries = relationship("WorkProgress", back_populates="task")


class WorkProgress(Base):
    __tablename__ = "work_progress"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True)
    date_logged = Column(Date, default=date.today, nullable=False, index=True)
    hours_spent = Column(Float, default=0.0, nullable=False)
    progress_percentage = Column(Float, default=0.0, nullable=False)
    work_description = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    employee = relationship("Employee", back_populates="progress_logs")
    project = relationship("Project", back_populates="progress_updates")
    task = relationship("Task", back_populates="progress_entries")

from datetime import datetime, date
from pydantic import BaseModel, EmailStr


class CustomerBase(BaseModel):
    name: str
    email: EmailStr
    phone: str | None = None
    company: str | None = None
    address: str | None = None
    city: str | None = None
    country: str | None = None
    status: str = "ACTIVE"


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    company: str | None = None
    address: str | None = None
    city: str | None = None
    country: str | None = None
    status: str | None = None


class CustomerResponse(CustomerBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DepartmentBase(BaseModel):
    name: str
    code: str
    description: str | None = None
    manager_id: int | None = None
    is_active: bool = True


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    description: str | None = None
    manager_id: int | None = None
    is_active: bool | None = None


class DepartmentResponse(DepartmentBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class DepartmentStatsResponse(BaseModel):
    department_id: int
    department_name: str
    department_code: str
    total_employees: int
    active_employees: int


class EmployeeBase(BaseModel):
    employee_code: str
    designation: str
    department_id: int | None = None
    phone: str | None = None
    join_date: date = date.today()
    salary: float = 0.0
    is_active: bool = True


class EmployeeCreate(EmployeeBase):
    user_id: int


class EmployeeUpdate(BaseModel):
    designation: str | None = None
    department_id: int | None = None
    phone: str | None = None
    salary: float | None = None
    is_active: bool | None = None


class EmployeeResponse(EmployeeBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class AttendanceCheckIn(BaseModel):
    notes: str | None = None


class AttendanceCheckOut(BaseModel):
    notes: str | None = None


class AttendanceResponse(BaseModel):
    id: int
    employee_id: int
    attendance_date: date
    check_in: datetime
    check_out: datetime | None = None
    status: str
    notes: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class LeaveCreate(BaseModel):
    leave_type: str
    start_date: date
    end_date: date
    reason: str


class LeaveAction(BaseModel):
    status: str
    admin_remarks: str | None = None


class LeaveResponse(BaseModel):
    id: int
    employee_id: int
    leave_type: str
    start_date: date
    end_date: date
    reason: str
    status: str
    approved_by_id: int | None = None
    admin_remarks: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class HolidayBase(BaseModel):
    name: str
    holiday_date: date
    description: str | None = None
    is_recurring: bool = False


class HolidayCreate(HolidayBase):
    pass


class HolidayUpdate(BaseModel):
    name: str | None = None
    holiday_date: date | None = None
    description: str | None = None
    is_recurring: bool | None = None


class HolidayResponse(HolidayBase):
    id: int

    class Config:
        from_attributes = True


class ProjectBase(BaseModel):
    name: str
    code: str
    description: str | None = None
    start_date: date
    end_date: date | None = None
    deadline: date | None = None
    status: str = "ACTIVE"


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    deadline: date | None = None
    progress_percent: float | None = None
    status: str | None = None


class ProjectResponse(ProjectBase):
    id: int
    progress_percent: float
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectMemberCreate(BaseModel):
    employee_id: int
    role_in_project: str = "Member"


class ProjectMemberResponse(BaseModel):
    id: int
    project_id: int
    employee_id: int
    role_in_project: str
    joined_at: datetime

    class Config:
        from_attributes = True


class TaskBase(BaseModel):
    title: str
    description: str | None = None
    project_id: int | None = None
    assigned_to_id: int | None = None
    priority: str = "MEDIUM"
    status: str = "TODO"
    due_date: date | None = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    project_id: int | None = None
    assigned_to_id: int | None = None
    priority: str | None = None
    status: str | None = None
    due_date: date | None = None


class TaskResponse(TaskBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BatchTaskAssign(BaseModel):
    task_ids: list[int]
    employee_id: int


class WorkProgressCreate(BaseModel):
    project_id: int | None = None
    task_id: int | None = None
    date_logged: date = date.today()
    hours_spent: float
    progress_percentage: float
    work_description: str


class WorkProgressResponse(WorkProgressCreate):
    id: int
    employee_id: int
    created_at: datetime

    class Config:
        from_attributes = True

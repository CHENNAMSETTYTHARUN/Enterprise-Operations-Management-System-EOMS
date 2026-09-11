from datetime import date
from typing import Any
from pydantic import BaseModel


class GlobalSearchResult(BaseModel):
    category: str
    id: int
    title: str
    subtitle: str | None = None
    status: str | None = None


class DashboardAnalytics(BaseModel):
    total_customers: int
    total_employees: int
    total_departments: int
    total_projects: int
    total_tasks: int
    total_products: int
    total_sales_orders: int
    total_tickets: int
    open_tickets: int
    pending_leaves: int
    pending_approvals: int
    revenue: float


class CustomReportRequest(BaseModel):
    module: str
    start_date: date | None = None
    end_date: date | None = None
    status: str | None = None
    department_id: int | None = None
    user_id: int | None = None


class CustomReportResponse(BaseModel):
    module: str
    record_count: int
    data: list[dict[str, Any]]

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    validation_exception_handler,
    integrity_exception_handler,
    sqlalchemy_exception_handler,
    general_exception_handler
)
from app.core.middleware import LoggingAndCorrelationMiddleware
from app.core.scheduler import start_scheduler, shutdown_scheduler
from app.seed.seed_data import init_db
from app.routers import (
    auth_router,
    phase1_router,
    phase2_router,
    phase3_router,
    phase4_router,
    phase5_router,
    phase6_router
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        init_db(db)
    finally:
        db.close()
    start_scheduler()
    yield
    shutdown_scheduler()


tags_metadata = [
    {"name": "Authentication & Access Control", "description": "JWT authentication, tokens, roles, and permissions"},
    {"name": "Phase 1 — Core Business APIs", "description": "Modules 1-10: Customers, Employees, Departments, Attendance, Leaves, Holidays, Tasks, Projects, Assignments, Work Progress"},
    {"name": "Phase 2 — Workflow-Based APIs", "description": "Modules 11-20: Approvals, Expenses, Reimbursements, Assets, Returns, Tickets, Escalations, Complaints, Feedback"},
    {"name": "Phase 3 — Commerce & Transactions", "description": "Modules 21-30: Products, Inventory, Suppliers, Purchase Orders, Orders, Cart, Coupons, Invoices, Payments, Refunds"},
    {"name": "Phase 4 — Advanced Business Logic", "description": "Modules 31-40: Appointments, Resources, Waiting Lists, Notifications, Email Service, Reminders, Documents, Approvals, Versioning, Audit Trail"},
    {"name": "Phase 5 — Advanced Backend Features", "description": "Modules 41-50: OTP, API Keys, Webhooks, External API, Redis Cache, Rate Limiting, Background Jobs, Scheduled Jobs, Data Import/Export"},
    {"name": "Phase 6 — Production & Final Challenge", "description": "Modules 51-60: Global Search, Dashboard Analytics, Custom Reports, Performance, Transactions, Exception Architecture, Health, Full Enterprise Workflow"}
]

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_tags=tags_metadata,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(LoggingAndCorrelationMiddleware)

app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(IntegrityError, integrity_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(phase1_router, prefix=settings.API_V1_STR)
app.include_router(phase2_router, prefix=settings.API_V1_STR)
app.include_router(phase3_router, prefix=settings.API_V1_STR)
app.include_router(phase4_router, prefix=settings.API_V1_STR)
app.include_router(phase5_router, prefix=settings.API_V1_STR)
app.include_router(phase6_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Health & Status"])
def root():
    return {
        "success": True,
        "service": settings.PROJECT_NAME,
        "version": "1.0.0",
        "docs_url": "/docs",
        "health_check": f"{settings.API_V1_STR}/health"
    }

import secrets
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, status, Query, UploadFile, File, BackgroundTasks
from fastapi.responses import Response
from sqlalchemy.orm import Session
import httpx
from app.core.database import get_db
from app.core.security import generate_api_key_pair
from app.core.cache import cache
from app.core.exceptions import NotFoundException, BadRequestException, ConflictException, UnauthorizedException
from app.core.dependencies import get_current_user, get_api_key_user, check_rate_limit
from app.core.scheduler import cleanup_expired_otps_job, cleanup_expired_coupons_job, auto_escalate_tickets_job, process_reminders_job
from app.models.auth import User
from app.models.core_business import Customer, Employee, Department
from app.models.commerce import Product, SalesOrder
from app.models.infrastructure import OTPRecord, ApiKey, Webhook, WebhookLog, DataImportHistory
from app.schemas.infrastructure import (
    OTPGenerateRequest, OTPVerifyRequest,
    ApiKeyCreate, ApiKeyResponse,
    WebhookCreate, WebhookResponse, WebhookLogResponse,
    ImportHistoryResponse
)
from app.schemas.common import MessageResponse
from app.services.external import external_client
from app.services.export_import import export_data_to_csv, export_data_to_excel, import_customers_file, import_products_file
from app.services.audit import log_audit

router = APIRouter(prefix="", tags=["Phase 5 — Advanced Backend Features"])


@router.post("/otp/generate", response_model=MessageResponse)
def generate_otp(otp_in: OTPGenerateRequest, db: Session = Depends(get_db)):
    code = f"{secrets.randbelow(900000) + 100000}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

    record = OTPRecord(
        target=otp_in.target,
        otp_code=code,
        purpose=otp_in.purpose,
        attempts=0,
        max_attempts=3,
        is_verified=False,
        expires_at=expires_at
    )
    db.add(record)
    db.commit()
    return MessageResponse(message=f"OTP generated successfully. (Dev code: {code})")


@router.post("/otp/resend", response_model=MessageResponse)
def resend_otp(otp_in: OTPGenerateRequest, db: Session = Depends(get_db)):
    db.query(OTPRecord).filter(
        OTPRecord.target == otp_in.target,
        OTPRecord.purpose == otp_in.purpose,
        OTPRecord.is_verified == False
    ).update({"expires_at": datetime.now(timezone.utc) - timedelta(seconds=1)})

    code = f"{secrets.randbelow(900000) + 100000}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

    record = OTPRecord(
        target=otp_in.target,
        otp_code=code,
        purpose=otp_in.purpose,
        attempts=0,
        max_attempts=3,
        is_verified=False,
        expires_at=expires_at
    )
    db.add(record)
    db.commit()
    return MessageResponse(message=f"OTP resent successfully. (Dev code: {code})")


@router.post("/otp/verify", response_model=MessageResponse)
def verify_otp(verify_in: OTPVerifyRequest, db: Session = Depends(get_db)):
    record = db.query(OTPRecord).filter(
        OTPRecord.target == verify_in.target,
        OTPRecord.purpose == verify_in.purpose,
        OTPRecord.is_verified == False
    ).order_by(OTPRecord.id.desc()).first()

    if not record:
        raise NotFoundException(message="No active OTP found for this target")

    now = datetime.now(timezone.utc)
    exp = record.expires_at if record.expires_at.tzinfo else record.expires_at.replace(tzinfo=timezone.utc)
    if now > exp:
        raise BadRequestException(message="OTP has expired")

    if record.attempts >= record.max_attempts:
        raise BadRequestException(message="Maximum OTP verification attempts exceeded")

    record.attempts += 1
    if record.otp_code != verify_in.otp_code:
        db.commit()
        raise BadRequestException(message=f"Invalid OTP. Remaining attempts: {record.max_attempts - record.attempts}")

    record.is_verified = True
    db.commit()
    return MessageResponse(message="OTP successfully verified")


@router.post("/api-keys", response_model=ApiKeyResponse, status_code=status.HTTP_201_CREATED)
def generate_api_key(key_in: ApiKeyCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    raw_key, prefix, hashed = generate_api_key_pair()
    exp = datetime.now(timezone.utc) + timedelta(days=key_in.expires_in_days) if key_in.expires_in_days else None

    api_key = ApiKey(
        user_id=current_user.id,
        name=key_in.name,
        key_prefix=prefix,
        hashed_key=hashed,
        is_active=True,
        expires_at=exp
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    resp = ApiKeyResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        is_active=api_key.is_active,
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
        raw_key=raw_key
    )
    return resp


@router.get("/api-keys", response_model=list[ApiKeyResponse])
def list_api_keys(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(ApiKey).filter(ApiKey.user_id == current_user.id).all()


@router.delete("/api-keys/{key_id}", response_model=MessageResponse)
def revoke_api_key(key_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    key_obj = db.query(ApiKey).filter(ApiKey.id == key_id, ApiKey.user_id == current_user.id).first()
    if not key_obj:
        raise NotFoundException(message="API key not found")
    key_obj.is_active = False
    db.commit()
    return MessageResponse(message="API Key revoked successfully")


@router.get("/api-keys/test-auth")
def test_api_key_access(auth_user: User = Depends(get_api_key_user)):
    return {
        "success": True,
        "message": f"Successfully authenticated via API Key as {auth_user.username}",
        "user_id": auth_user.id
    }


@router.post("/webhooks", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
def register_webhook(hook_in: WebhookCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    hook = Webhook(**hook_in.model_dump(), is_active=True)
    db.add(hook)
    db.commit()
    db.refresh(hook)
    return hook


@router.get("/webhooks", response_model=list[WebhookResponse])
def list_webhooks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Webhook).all()


@router.post("/webhooks/{webhook_id}/trigger", response_model=WebhookLogResponse)
async def trigger_webhook(webhook_id: int, event_payload: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    hook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not hook:
        raise NotFoundException(message="Webhook not found")

    status_code = None
    resp_text = None
    success = False
    attempts = 0
    max_retries = 3

    for attempt in range(1, max_retries + 1):
        attempts = attempt
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(hook.target_url, json=event_payload)
                status_code = res.status_code
                resp_text = res.text[:500]
                success = 200 <= res.status_code < 300
                if success:
                    break
        except Exception as e:
            resp_text = f"Delivery attempt {attempt} failed: {str(e)}"

    log = WebhookLog(
        webhook_id=hook.id,
        payload=str(event_payload),
        response_status=status_code,
        response_body=resp_text,
        is_success=success,
        attempts=attempts
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.post("/webhooks/logs/{log_id}/retry", response_model=WebhookLogResponse)
async def retry_webhook_delivery(log_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    log = db.query(WebhookLog).filter(WebhookLog.id == log_id).first()
    if not log:
        raise NotFoundException(message="Webhook log not found")
    hook = db.query(Webhook).filter(Webhook.id == log.webhook_id).first()
    if not hook:
        raise NotFoundException(message="Webhook configuration not found")

    import json
    try:
        payload_data = json.loads(log.payload.replace("'", '"'))
    except Exception:
        payload_data = {"raw_payload": log.payload}

    status_code = None
    resp_text = None
    success = False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.post(hook.target_url, json=payload_data)
            status_code = res.status_code
            resp_text = res.text[:500]
            success = 200 <= res.status_code < 300
    except Exception as e:
        resp_text = f"Manual retry failed: {str(e)}"

    log.response_status = status_code
    log.response_body = resp_text
    log.is_success = success
    log.attempts += 1
    db.commit()
    db.refresh(log)
    return log


@router.get("/webhooks/{webhook_id}/logs", response_model=list[WebhookLogResponse])
def get_webhook_logs(webhook_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(WebhookLog).filter(WebhookLog.webhook_id == webhook_id).order_by(WebhookLog.created_at.desc()).all()


@router.get("/external/data")
async def get_external_third_party_data(current_user: User = Depends(get_current_user)):
    return await external_client.fetch_external_data()


@router.get("/cache/test")
def test_caching(key: str = "demo_key", val: str = "demo_value"):
    cached_val = cache.get(key)
    if cached_val is None:
        cache.set(key, {"cached_data": val, "saved_at": str(datetime.now(timezone.utc))}, expire_seconds=60)
        return {"source": "fresh_set", "value": val}
    return {"source": "cache", "data": cached_val}


@router.delete("/cache/invalidate")
def invalidate_cache(key: str):
    cache.delete(key)
    return {"message": f"Cache key '{key}' invalidated"}


@router.get("/rate-limiting/test", dependencies=[Depends(check_rate_limit)])
def test_rate_limiting():
    return {"message": "Rate limit check passed"}


@router.post("/jobs/heavy-processing", response_model=MessageResponse)
def trigger_heavy_background_job(job_name: str, bg_tasks: BackgroundTasks, current_user: User = Depends(get_current_user)):
    def simulate_heavy_computation(name: str):
        import time
        time.sleep(1)

    bg_tasks.add_task(simulate_heavy_computation, job_name)
    return MessageResponse(message=f"Background job '{job_name}' dispatched successfully")


@router.post("/jobs/scheduler/run-manual", response_model=MessageResponse)
def trigger_scheduled_jobs_manual(job_type: str = "ALL", current_user: User = Depends(get_current_user)):
    if job_type in ["OTP", "ALL"]:
        cleanup_expired_otps_job()
    if job_type in ["COUPONS", "ALL"]:
        cleanup_expired_coupons_job()
    if job_type in ["TICKETS", "ALL"]:
        auto_escalate_tickets_job()
    if job_type in ["REMINDERS", "ALL"]:
        process_reminders_job()
    return MessageResponse(message=f"Scheduled jobs for '{job_type}' executed successfully")


@router.post("/import/customers")
async def import_customers(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await import_customers_file(db, file, current_user.id)


@router.post("/import/products")
async def import_products(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await import_products_file(db, file, current_user.id)


@router.get("/import/history", response_model=list[ImportHistoryResponse])
def get_import_history(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(DataImportHistory).order_by(DataImportHistory.created_at.desc()).all()


@router.get("/export/customers")
def export_customers(format_type: str = "csv", status_filter: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Customer)
    if status_filter:
        query = query.filter(Customer.status == status_filter)
    customers = query.all()
    data = [{"id": c.id, "name": c.name, "email": c.email, "phone": c.phone, "company": c.company, "status": c.status} for c in customers]

    if format_type.lower() == "excel":
        excel_io = export_data_to_excel(data)
        return Response(content=excel_io.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=customers.xlsx"})
    csv_io = export_data_to_csv(data)
    return Response(content=csv_io.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=customers.csv"})


@router.get("/export/products")
def export_products(format_type: str = "csv", category: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Product)
    if category:
        query = query.filter(Product.category == category)
    products = query.all()
    data = [{"id": p.id, "sku": p.sku, "name": p.name, "category": p.category, "price": p.price, "stock_quantity": p.stock_quantity} for p in products]

    if format_type.lower() == "excel":
        excel_io = export_data_to_excel(data)
        return Response(content=excel_io.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=products.xlsx"})
    csv_io = export_data_to_csv(data)
    return Response(content=csv_io.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=products.csv"})

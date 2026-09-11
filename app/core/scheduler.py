from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.core.database import SessionLocal


def cleanup_expired_otps_job():
    from app.models.infrastructure import OTPRecord
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        db.query(OTPRecord).filter(OTPRecord.expires_at < now).delete()
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def cleanup_expired_coupons_job():
    from app.models.commerce import Coupon
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        db.query(Coupon).filter(Coupon.valid_until < now, Coupon.is_active == True).update({"is_active": False})
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def auto_escalate_tickets_job():
    from app.models.workflow import SupportTicket, TicketEscalation
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        tickets = db.query(SupportTicket).filter(
            SupportTicket.status.in_(["OPEN", "IN_PROGRESS"]),
            SupportTicket.priority.in_(["URGENT", "HIGH"]),
            SupportTicket.escalated == False
        ).all()
        for ticket in tickets:
            ticket.escalated = True
            escalation = TicketEscalation(
                ticket_id=ticket.id,
                reason="Auto escalated due to urgent SLA threshold",
                escalated_to_role="ADMIN",
                status="ESCALATED",
                created_at=now
            )
            db.add(escalation)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def process_reminders_job():
    from app.models.advanced import Reminder
    from app.models.infrastructure import Notification
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        reminders = db.query(Reminder).filter(
            Reminder.remind_at <= now,
            Reminder.status == "PENDING"
        ).all()
        for r in reminders:
            r.status = "COMPLETED"
            notif = Notification(
                user_id=r.user_id,
                title=f"Reminder: {r.title}",
                message=r.description or "You have a scheduled reminder",
                type="REMINDER",
                is_read=False,
                created_at=now
            )
            db.add(notif)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


scheduler = BackgroundScheduler(daemon=True)


def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(cleanup_expired_otps_job, IntervalTrigger(minutes=15), id="cleanup_otps", replace_existing=True)
        scheduler.add_job(cleanup_expired_coupons_job, IntervalTrigger(minutes=30), id="cleanup_coupons", replace_existing=True)
        scheduler.add_job(auto_escalate_tickets_job, IntervalTrigger(minutes=10), id="auto_escalate", replace_existing=True)
        scheduler.add_job(process_reminders_job, IntervalTrigger(minutes=5), id="process_reminders", replace_existing=True)
        scheduler.start()


def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)

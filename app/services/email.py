from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.infrastructure import EmailLog


def send_email_background(recipient: str, subject: str, body: str):
    db: Session = SessionLocal()
    try:
        log = EmailLog(
            recipient=recipient,
            subject=subject,
            body=body,
            status="SENT",
            attempts=1,
            sent_at=datetime.now(timezone.utc)
        )
        db.add(log)
        db.commit()
    except Exception as e:
        db.rollback()
        try:
            err_log = EmailLog(
                recipient=recipient,
                subject=subject,
                body=body,
                status="FAILED",
                attempts=1,
                error_message=str(e)
            )
            db.add(err_log)
            db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()

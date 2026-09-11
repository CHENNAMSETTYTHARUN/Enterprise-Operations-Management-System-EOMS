from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.infrastructure import Notification


def create_notification_background(user_id: int, title: str, message: str, notif_type: str = "INFO"):
    db: Session = SessionLocal()
    try:
        notif = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=notif_type,
            is_read=False,
            created_at=datetime.now(timezone.utc)
        )
        db.add(notif)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()

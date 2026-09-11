from sqlalchemy.orm import Session
from app.models.infrastructure import AuditLog


def log_audit(
    db: Session,
    action: str,
    module: str,
    entity: str,
    entity_id: str | None = None,
    user_id: int | None = None,
    ip_address: str | None = None,
    details: str | None = None
) -> AuditLog:
    entry = AuditLog(
        user_id=user_id,
        action=action,
        module=module,
        entity=entity,
        entity_id=str(entity_id) if entity_id is not None else None,
        ip_address=ip_address,
        details=details
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry

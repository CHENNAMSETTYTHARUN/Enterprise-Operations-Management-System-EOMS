import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.core.security import create_access_token
from app.models.auth import User


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def admin_headers():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "admin").first()
        token = create_access_token(subject=user.id)
        return {"Authorization": f"Bearer {token}"}
    finally:
        db.close()


@pytest.fixture(scope="session")
def manager_headers():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "manager").first()
        token = create_access_token(subject=user.id)
        return {"Authorization": f"Bearer {token}"}
    finally:
        db.close()


@pytest.fixture(scope="session")
def employee_headers():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "employee").first()
        token = create_access_token(subject=user.id)
        return {"Authorization": f"Bearer {token}"}
    finally:
        db.close()

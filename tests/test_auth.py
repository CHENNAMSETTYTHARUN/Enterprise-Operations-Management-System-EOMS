import uuid


def test_auth_login_success(client):
    res = client.post("/api/v1/auth/login", json={"username_or_email": "admin", "password": "admin123"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["username"] == "admin"


def test_oauth2_token_endpoint(client):
    res = client.post("/api/v1/auth/token", data={"username": "admin", "password": "admin123"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    res_err = client.post("/api/v1/auth/token", data={"username": "admin", "password": "wrong"})
    assert res_err.status_code == 401


def test_auth_login_invalid_password(client):
    res = client.post("/api/v1/auth/login", json={"username_or_email": "admin", "password": "wrongpassword"})
    assert res.status_code == 401
    assert res.json()["success"] is False


def test_auth_register_and_profile(client, admin_headers):
    uid = uuid.uuid4().hex[:8]
    payload = {
        "email": f"newuser_{uid}@enterprise.com",
        "username": f"user_{uid}",
        "password": "Password123!",
        "full_name": "Test User"
    }
    reg_res = client.post("/api/v1/auth/register", json=payload)
    assert reg_res.status_code == 201
    user_id = reg_res.json()["id"]

    login_res = client.post("/api/v1/auth/login", json={"username_or_email": payload["username"], "password": payload["password"]})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    refresh_token = login_res.json()["refresh_token"]

    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["id"] == user_id

    refresh_res = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_res.status_code == 200
    assert "access_token" in refresh_res.json()


def test_roles_and_permissions(client, admin_headers):
    perm_code = f"perm_{uuid.uuid4().hex[:6]}"
    perm_res = client.post("/api/v1/auth/permissions", json={"code": perm_code, "name": "Custom Perm"}, headers=admin_headers)
    assert perm_res.status_code == 201
    perm_id = perm_res.json()["id"]

    role_name = f"ROLE_{uuid.uuid4().hex[:6]}"
    role_res = client.post("/api/v1/auth/roles", json={"name": role_name, "permission_ids": [perm_id]}, headers=admin_headers)
    assert role_res.status_code == 201

    list_res = client.get("/api/v1/auth/roles", headers=admin_headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

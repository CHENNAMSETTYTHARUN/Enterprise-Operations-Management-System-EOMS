import io
import uuid


def test_module_41_42_otp_and_apikey(client, admin_headers):
    tag = uuid.uuid4().hex[:6]
    target = f"user_{tag}@enterprise.com"

    gen_res = client.post("/api/v1/otp/generate", json={"target": target, "purpose": "VERIFICATION"})
    assert gen_res.status_code == 200

    # Module 41: Test OTP resend
    resend_res = client.post("/api/v1/otp/resend", json={"target": target, "purpose": "VERIFICATION"})
    assert resend_res.status_code == 200
    msg = resend_res.json()["message"]
    otp_code = msg.split("Dev code: ")[1].replace(")", "").strip()

    ver_res = client.post("/api/v1/otp/verify", json={"target": target, "otp_code": otp_code, "purpose": "VERIFICATION"})
    assert ver_res.status_code == 200

    key_res = client.post("/api/v1/api-keys", json={"name": "Dev Pipeline Key", "expires_in_days": 30}, headers=admin_headers)
    assert key_res.status_code == 201
    raw_key = key_res.json()["raw_key"]

    auth_test = client.get("/api/v1/api-keys/test-auth", headers={"X-API-Key": raw_key})
    assert auth_test.status_code == 200


def test_module_43_44_45_46_webhooks_external_cache_ratelimit(client, admin_headers):
    hook_res = client.post("/api/v1/webhooks", json={"target_url": "https://httpbin.org/post", "event_type": "ORDER_CREATED"}, headers=admin_headers)
    assert hook_res.status_code == 201
    hook_id = hook_res.json()["id"]

    # Module 43: Trigger webhook and test manual retry
    trig_res = client.post(f"/api/v1/webhooks/{hook_id}/trigger", json={"event": "order_placed", "order_id": 123}, headers=admin_headers)
    assert trig_res.status_code == 200
    log_id = trig_res.json()["id"]
    assert trig_res.json()["attempts"] >= 1

    retry_res = client.post(f"/api/v1/webhooks/logs/{log_id}/retry", headers=admin_headers)
    assert retry_res.status_code == 200
    assert retry_res.json()["attempts"] >= 2

    ext_res = client.get("/api/v1/external/data", headers=admin_headers)
    assert ext_res.status_code == 200

    c_res1 = client.get("/api/v1/cache/test?key=k1&val=v1")
    assert c_res1.status_code == 200

    c_res2 = client.get("/api/v1/cache/test?key=k1&val=v1")
    assert c_res2.status_code == 200
    assert c_res2.json()["source"] == "cache"

    # Module 46: Test rate limiting both with and without auth
    rl_auth = client.get("/api/v1/rate-limiting/test", headers=admin_headers)
    assert rl_auth.status_code == 200

    rl_unauth = client.get("/api/v1/rate-limiting/test")
    assert rl_unauth.status_code == 200


def test_module_47_48_49_50_jobs_import_export(client, admin_headers):
    job_res = client.post("/api/v1/jobs/heavy-processing?job_name=AnnualReportGen", headers=admin_headers)
    assert job_res.status_code == 200

    sched_res = client.post("/api/v1/jobs/scheduler/run-manual?job_type=ALL", headers=admin_headers)
    assert sched_res.status_code == 200

    import secrets
    tag = secrets.token_hex(4)
    csv_content = f"name,email,company,phone\nImported Corp {tag},imported_{tag}@corp.com,Imported LLC,+1-555-9000\n".encode("utf-8")
    files = {"file": ("customers.csv", io.BytesIO(csv_content), "text/csv")}
    imp_res = client.post("/api/v1/import/customers", files=files, headers=admin_headers)
    assert imp_res.status_code == 200
    assert imp_res.json()["successful_rows"] == 1

    exp_res = client.get("/api/v1/export/customers?format_type=csv", headers=admin_headers)
    assert exp_res.status_code == 200
    assert "text/csv" in exp_res.headers["content-type"]

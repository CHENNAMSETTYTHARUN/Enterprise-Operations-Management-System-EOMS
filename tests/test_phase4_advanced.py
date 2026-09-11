import io
from datetime import datetime, timezone, timedelta


def test_module_31_32_33_booking_and_waitlist(client, admin_headers):
    import secrets
    cust = client.get("/api/v1/customers", headers=admin_headers).json()["data"][0]
    emp = client.get("/api/v1/employees", headers=admin_headers).json()[0]

    offset_hours = secrets.randbelow(10000) + 50
    st = datetime.now(timezone.utc) + timedelta(hours=offset_hours)
    et = st + timedelta(hours=1)
    app_res = client.post("/api/v1/appointments", json={"customer_id": cust["id"], "employee_id": emp["id"], "title": "Client Strategy Session", "start_time": st.isoformat(), "end_time": et.isoformat()}, headers=admin_headers)
    assert app_res.status_code == 201
    app_id = app_res.json()["id"]

    res_res = client.post("/api/v1/resources", json={"name": f"Boardroom {secrets.token_hex(3)}", "resource_type": "ROOM", "capacity": 20}, headers=admin_headers)
    assert res_res.status_code == 201
    resource_id = res_res.json()["id"]

    book_res = client.post("/api/v1/resources/book", json={"resource_id": resource_id, "purpose": "Quarterly Review", "start_time": st.isoformat(), "end_time": et.isoformat()}, headers=admin_headers)
    assert book_res.status_code == 201

    wait_res = client.post("/api/v1/waiting-lists", json={"entity_type": "RESOURCE", "entity_id": resource_id}, headers=admin_headers)
    assert wait_res.status_code == 201


def test_module_34_35_36_notifications_emails_reminders(client, admin_headers, employee_headers):
    notif_cnt = client.get("/api/v1/notifications/unread-count", headers=employee_headers)
    assert notif_cnt.status_code == 200

    mail_res = client.post("/api/v1/emails/send", json={"recipient": "tester@enterprise.com", "subject": "Automated Report", "body": "Report generated."}, headers=admin_headers)
    assert mail_res.status_code == 200

    rem_time = datetime.now(timezone.utc) + timedelta(hours=5)
    rem_res = client.post("/api/v1/reminders", json={"title": "Submit Weekly Timesheet", "remind_at": rem_time.isoformat()}, headers=employee_headers)
    assert rem_res.status_code == 201


def test_module_37_38_39_40_documents_and_audit(client, admin_headers, employee_headers):
    file_content = b"Sample enterprise legal agreement content."
    files = {"file": ("agreement.txt", io.BytesIO(file_content), "text/plain")}
    data = {"title": "Vendor Contract 2026", "category": "LEGAL", "is_public": "true"}

    doc_res = client.post("/api/v1/documents/upload", data=data, files=files, headers=admin_headers)
    assert doc_res.status_code == 201
    doc_id = doc_res.json()["id"]

    down_res = client.get(f"/api/v1/documents/{doc_id}/download", headers=admin_headers)
    assert down_res.status_code == 200
    assert down_res.content == file_content

    admin_user = client.get("/api/v1/auth/me", headers=admin_headers).json()
    sub_appr = client.post(f"/api/v1/documents/{doc_id}/submit-approval?reviewer_id={admin_user['id']}", headers=admin_headers)
    assert sub_appr.status_code == 200

    audit_res = client.get("/api/v1/audit-logs", headers=admin_headers)
    assert audit_res.status_code == 200
    assert audit_res.json()["total"] >= 1

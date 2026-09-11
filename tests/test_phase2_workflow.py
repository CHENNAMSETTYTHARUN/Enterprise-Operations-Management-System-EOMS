import uuid


def test_module_11_multilevel_approval(client, employee_headers, manager_headers, admin_headers):
    sub_res = client.post("/api/v1/approvals", json={"request_type": "BUDGET_INCREASE", "title": "Server Upgrades", "amount": 2500.0}, headers=employee_headers)
    assert sub_res.status_code == 201
    req_id = sub_res.json()["id"]
    assert sub_res.json()["current_stage"] == "MANAGER"

    mgr_res = client.post(f"/api/v1/approvals/{req_id}/action", json={"action": "APPROVE", "remarks": "Approved by manager"}, headers=manager_headers)
    assert mgr_res.status_code == 200
    assert mgr_res.json()["current_stage"] == "ADMIN"

    adm_res = client.post(f"/api/v1/approvals/{req_id}/action", json={"action": "APPROVE", "remarks": "Final executive signoff"}, headers=admin_headers)
    assert adm_res.status_code == 200
    assert adm_res.json()["status"] == "APPROVED"


def test_module_12_and_13_expense_and_reimbursement(client, employee_headers, admin_headers):
    exp_res = client.post("/api/v1/expenses", json={"category": "TRAVEL", "title": "Flight to Client site", "amount": 650.0}, headers=employee_headers)
    assert exp_res.status_code == 201
    exp_id = exp_res.json()["id"]

    act_res = client.post(f"/api/v1/expenses/{exp_id}/action", json={"status": "APPROVED"}, headers=admin_headers)
    assert act_res.status_code == 200

    reimb_res = client.post("/api/v1/reimbursements", json={"expense_id": exp_id}, headers=employee_headers)
    assert reimb_res.status_code == 201
    reimb_id = reimb_res.json()["id"]

    pay_res = client.post(f"/api/v1/reimbursements/{reimb_id}/action", json={"status": "PAID", "payment_status": "PAID", "payment_reference": "WIRE-9988"}, headers=admin_headers)
    assert pay_res.status_code == 200
    assert pay_res.json()["payment_status"] == "PAID"


def test_module_14_and_15_asset_management_and_return(client, admin_headers):
    tag = uuid.uuid4().hex[:6]
    asset_res = client.post("/api/v1/assets", json={"name": f"Laptop {tag}", "asset_code": f"AST-{tag}", "category": "Hardware", "cost": 1500.0}, headers=admin_headers)
    assert asset_res.status_code == 201
    asset_id = asset_res.json()["id"]

    emp = client.get("/api/v1/employees", headers=admin_headers).json()[0]
    assign_res = client.post(f"/api/v1/assets/{asset_id}/assign", json={"employee_id": emp["id"], "condition_notes": "Brand new condition"}, headers=admin_headers)
    assert assign_res.status_code == 200

    return_res = client.post(f"/api/v1/assets/{asset_id}/return", json={"has_damage": False}, headers=admin_headers)
    assert return_res.status_code == 200

    chk = client.get(f"/api/v1/assets/{asset_id}", headers=admin_headers)
    assert chk.json()["status"] == "AVAILABLE"


def test_module_16_17_18_support_tickets_escalation(client, employee_headers, admin_headers):
    t_res = client.post("/api/v1/tickets", json={"title": "VPN connection drops", "description": "Unable to connect to internal db", "category": "IT", "priority": "HIGH"}, headers=employee_headers)
    assert t_res.status_code == 201
    t_id = t_res.json()["id"]

    admin_me = client.get("/api/v1/auth/me", headers=admin_headers).json()
    assign_res = client.post(f"/api/v1/tickets/{t_id}/assign", json={"agent_id": admin_me["id"]}, headers=admin_headers)
    assert assign_res.status_code == 200

    esc_res = client.post(f"/api/v1/tickets/{t_id}/escalate", json={"reason": "SLA critical threshold reached"}, headers=admin_headers)
    assert esc_res.status_code == 200
    assert esc_res.json()["escalated"] is True


def test_module_19_and_20_complaints_and_feedback(client, admin_headers):
    cust = client.get("/api/v1/customers", headers=admin_headers).json()["data"][0]

    comp_res = client.post("/api/v1/complaints", json={"customer_id": cust["id"], "subject": "Late delivery", "description": "Package delayed by 3 days"}, headers=admin_headers)
    assert comp_res.status_code == 201
    comp_id = comp_res.json()["id"]

    res_res = client.post(f"/api/v1/complaints/{comp_id}/resolve", json={"resolution_notes": "Courier refunded shipment fee"}, headers=admin_headers)
    assert res_res.status_code == 200
    assert res_res.json()["status"] == "RESOLVED"

    fb_res = client.post("/api/v1/feedback", json={"customer_id": cust["id"], "category": "SUPPORT", "rating": 5, "feedback_text": "Great turnaround time"}, headers=admin_headers)
    assert fb_res.status_code == 201
    fb_id = fb_res.json()["id"]

    resp_res = client.post(f"/api/v1/feedback/{fb_id}/respond", json={"admin_response": "Thank you for your business!"}, headers=admin_headers)
    assert resp_res.status_code == 200
    assert resp_res.json()["status"] == "RESPONDED"

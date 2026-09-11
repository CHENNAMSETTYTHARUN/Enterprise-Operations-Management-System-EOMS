import uuid
from datetime import date, timedelta


def test_module_1_customer_management(client, admin_headers):
    tag = uuid.uuid4().hex[:6]
    payload = {
        "name": f"Customer {tag}",
        "email": f"cust_{tag}@corp.com",
        "company": "Tech Corp",
        "phone": "+1-800-555-1234",
        "city": "Austin",
        "country": "USA",
        "status": "ACTIVE"
    }
    create_res = client.post("/api/v1/customers", json=payload, headers=admin_headers)
    assert create_res.status_code == 201
    cust_id = create_res.json()["id"]

    get_res = client.get(f"/api/v1/customers/{cust_id}", headers=admin_headers)
    assert get_res.status_code == 200
    assert get_res.json()["email"] == payload["email"]

    update_res = client.put(f"/api/v1/customers/{cust_id}", json={"company": "New Corp"}, headers=admin_headers)
    assert update_res.status_code == 200
    assert update_res.json()["company"] == "New Corp"

    list_res = client.get(f"/api/v1/customers?search={tag}", headers=admin_headers)
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1

    del_res = client.delete(f"/api/v1/customers/{cust_id}", headers=admin_headers)
    assert del_res.status_code == 200


def test_module_2_and_3_department_and_employee(client, admin_headers):
    tag = uuid.uuid4().hex[:6]
    dept_res = client.post("/api/v1/departments", json={"name": f"Dept {tag}", "code": f"D_{tag}"}, headers=admin_headers)
    assert dept_res.status_code == 201
    dept_id = dept_res.json()["id"]

    user_res = client.post("/api/v1/auth/register", json={"email": f"emp_{tag}@company.com", "username": f"emp_{tag}", "password": "Password123!"}, headers=admin_headers)
    assert user_res.status_code == 201
    user_id = user_res.json()["id"]

    emp_res = client.post("/api/v1/employees", json={"user_id": user_id, "department_id": dept_id, "employee_code": f"EMP-{tag}", "designation": "Staff Engineer", "salary": 80000.0}, headers=admin_headers)
    assert emp_res.status_code == 201
    emp_id = emp_res.json()["id"]

    stats_res = client.get(f"/api/v1/departments/{dept_id}/stats", headers=admin_headers)
    assert stats_res.status_code == 200
    assert stats_res.json()["total_employees"] == 1


def test_module_4_attendance_system(client, employee_headers):
    in_res = client.post("/api/v1/attendance/check-in", json={"notes": "Morning checkin"}, headers=employee_headers)
    assert in_res.status_code in [200, 400]

    out_res = client.post("/api/v1/attendance/check-out", json={"notes": "Evening checkout"}, headers=employee_headers)
    assert out_res.status_code in [200, 400]

    hist_res = client.get("/api/v1/attendance/history", headers=employee_headers)
    assert hist_res.status_code == 200


def test_module_5_leave_management(client, employee_headers, admin_headers):
    import secrets
    offset = secrets.randbelow(1000) + 10
    start = date.today() + timedelta(days=offset)
    end = date.today() + timedelta(days=offset + 2)
    leave_res = client.post("/api/v1/leaves", json={"leave_type": "ANNUAL", "start_date": str(start), "end_date": str(end), "reason": "Family vacation"}, headers=employee_headers)
    assert leave_res.status_code == 201
    leave_id = leave_res.json()["id"]

    appr_res = client.post(f"/api/v1/leaves/{leave_id}/action", json={"status": "APPROVED", "admin_remarks": "Enjoy your time off"}, headers=admin_headers)
    assert appr_res.status_code == 200
    assert appr_res.json()["status"] == "APPROVED"


def test_module_6_holiday_management(client, admin_headers):
    import secrets
    h_date = date.today() + timedelta(days=secrets.randbelow(2000) + 200)
    h_res = client.post("/api/v1/holidays", json={"name": f"Founders Day {secrets.token_hex(2)}", "holiday_date": str(h_date)}, headers=admin_headers)
    assert h_res.status_code == 201
    h_id = h_res.json()["id"]

    chk_res = client.get(f"/api/v1/holidays/check-date/{str(h_date)}", headers=admin_headers)
    assert chk_res.status_code == 200
    assert chk_res.json()["is_holiday"] is True


def test_module_7_8_9_10_projects_tasks_assignments_progress(client, admin_headers, employee_headers):
    tag = uuid.uuid4().hex[:6]
    proj_res = client.post("/api/v1/projects", json={"name": f"Project {tag}", "code": f"PRJ-{tag}", "start_date": str(date.today())}, headers=admin_headers)
    assert proj_res.status_code == 201
    proj_id = proj_res.json()["id"]

    task_res = client.post("/api/v1/tasks", json={"title": f"Task {tag}", "project_id": proj_id, "priority": "HIGH"}, headers=admin_headers)
    assert task_res.status_code == 201
    task_id = task_res.json()["id"]

    emp = client.get("/api/v1/employees", headers=admin_headers).json()[0]
    batch_res = client.post("/api/v1/tasks/batch-assign", json={"task_ids": [task_id], "employee_id": emp["id"]}, headers=admin_headers)
    assert batch_res.status_code == 200

    prog_res = client.post("/api/v1/work-progress", json={"project_id": proj_id, "task_id": task_id, "hours_spent": 4.5, "progress_percentage": 100.0, "work_description": "Finished feature implementation"}, headers=employee_headers)
    assert prog_res.status_code == 201

    t_chk = client.get(f"/api/v1/tasks/{task_id}", headers=admin_headers)
    assert t_chk.status_code == 200
    assert t_chk.json()["status"] == "COMPLETED"

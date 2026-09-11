def test_module_60_end_to_end_enterprise_workflow(client, admin_headers):
    res = client.post("/api/v1/workflow/enterprise-full-run", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    summary = data["workflow_summary"]
    assert "customer" in summary
    assert "department" in summary
    assert "project" in summary
    assert "task" in summary
    assert "approval" in summary
    assert "product" in summary
    assert "order" in summary
    assert "invoice" in summary
    assert "payment" in summary
    assert "notification" in summary
    assert summary["order"]["total"] > 0
    assert summary["invoice"]["status"] == "PAID"
    assert summary["payment"]["status"] == "SUCCESSFUL"

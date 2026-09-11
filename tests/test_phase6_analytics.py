def test_module_51_to_59_analytics_search_transactions_health(client, admin_headers):
    health_res = client.get("/api/v1/health")
    assert health_res.status_code == 200
    assert "status" in health_res.json()

    search_res = client.get("/api/v1/search/global?q=Acme", headers=admin_headers)
    assert search_res.status_code == 200
    assert len(search_res.json()) >= 1

    dash_res = client.get("/api/v1/dashboard/analytics", headers=admin_headers)
    assert dash_res.status_code == 200
    assert "total_customers" in dash_res.json()

    rep_res = client.post("/api/v1/reports/custom", json={"module": "CUSTOMERS"}, headers=admin_headers)
    assert rep_res.status_code == 200
    assert rep_res.json()["record_count"] >= 1

    rollback_test = client.post("/api/v1/transactions/test-rollback?simulate_error=true", headers=admin_headers)
    assert rollback_test.status_code == 200
    assert rollback_test.json()["status"] == "rolled_back"
    assert rollback_test.json()["customer_saved"] is False

    exc_404 = client.get("/api/v1/exceptions/trigger?exc_type=not_found")
    assert exc_404.status_code == 404
    assert exc_404.json()["error"]["code"] == "NOT_FOUND"

    exc_403 = client.get("/api/v1/exceptions/trigger?exc_type=forbidden")
    assert exc_403.status_code == 403
    assert exc_403.json()["error"]["code"] == "FORBIDDEN"

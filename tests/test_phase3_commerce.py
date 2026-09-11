import uuid
from datetime import datetime, timezone, timedelta


def test_module_21_22_23_24_product_inventory_supplier_po(client, admin_headers):
    tag = uuid.uuid4().hex[:6]
    prod_res = client.post("/api/v1/products", json={"sku": f"SKU-{tag}", "name": f"Product {tag}", "category": "Hardware", "price": 199.99, "stock_quantity": 20, "low_stock_threshold": 5}, headers=admin_headers)
    assert prod_res.status_code == 201
    prod_id = prod_res.json()["id"]

    adj_res = client.post("/api/v1/inventory/adjust", json={"product_id": prod_id, "change_type": "STOCK_IN", "quantity": 10, "reason": "Restock batch"}, headers=admin_headers)
    assert adj_res.status_code == 200
    assert adj_res.json()["new_stock"] == 30

    sup_res = client.post("/api/v1/suppliers", json={"name": f"Supplier {tag}", "email": f"sup_{tag}@supply.com"}, headers=admin_headers)
    assert sup_res.status_code == 201
    sup_id = sup_res.json()["id"]

    # Module 23: Test product-supplier relationship
    link_res = client.post(f"/api/v1/suppliers/{sup_id}/products", json={"product_id": prod_id, "supply_price": 115.0, "lead_time_days": 5}, headers=admin_headers)
    assert link_res.status_code == 201
    assert link_res.json()["supply_price"] == 115.0

    sup_prods = client.get(f"/api/v1/suppliers/{sup_id}/products", headers=admin_headers)
    assert sup_prods.status_code == 200
    assert len(sup_prods.json()) == 1

    po_res = client.post("/api/v1/purchase-orders", json={"supplier_id": sup_id, "items": [{"product_id": prod_id, "quantity": 5, "unit_price": 120.0}]}, headers=admin_headers)
    assert po_res.status_code == 201
    po_id = po_res.json()["id"]

    appr_po = client.post(f"/api/v1/purchase-orders/{po_id}/approve", headers=admin_headers)
    assert appr_po.status_code == 200
    assert appr_po.json()["approval_status"] == "APPROVED"

    del_sp = client.delete(f"/api/v1/suppliers/{sup_id}/products/{prod_id}", headers=admin_headers)
    assert del_sp.status_code == 200


def test_module_25_26_27_28_29_30_cart_orders_invoices_payments_refunds(client, admin_headers, employee_headers):
    prod = client.get("/api/v1/products", headers=admin_headers).json()["data"][0]
    cust = client.get("/api/v1/customers", headers=admin_headers).json()["data"][0]

    cart_add = client.post("/api/v1/cart/items", json={"product_id": prod["id"], "quantity": 2}, headers=employee_headers)
    assert cart_add.status_code == 200
    assert len(cart_add.json()["items"]) >= 1

    cart_view = client.get("/api/v1/cart", headers=employee_headers)
    assert cart_view.status_code == 200

    order_res = client.post("/api/v1/orders", json={"customer_id": cust["id"], "items": [{"product_id": prod["id"], "quantity": 1}], "coupon_code": "WELCOME10"}, headers=admin_headers)
    assert order_res.status_code == 201
    order_id = order_res.json()["id"]
    assert order_res.json()["discount_amount"] > 0

    inv_res = client.post(f"/api/v1/orders/{order_id}/generate-invoice", headers=admin_headers)
    assert inv_res.status_code == 200
    assert "invoice_number" in inv_res.json()

    pay_res = client.post("/api/v1/payments", json={"order_id": order_id, "amount": order_res.json()["total_amount"], "payment_method": "SIMULATED"}, headers=admin_headers)
    assert pay_res.status_code == 200
    assert pay_res.json()["status"] == "SUCCESSFUL"
    pay_id = pay_res.json()["id"]

    ref_res = client.post("/api/v1/refunds", json={"payment_id": pay_id, "amount": 10.0, "reason": "Customer goodwill discount"}, headers=admin_headers)
    assert ref_res.status_code == 201
    ref_id = ref_res.json()["id"]

    appr_ref = client.post(f"/api/v1/refunds/{ref_id}/action", json={"status": "APPROVED"}, headers=admin_headers)
    assert appr_ref.status_code == 200
    assert appr_ref.json()["status"] == "APPROVED"

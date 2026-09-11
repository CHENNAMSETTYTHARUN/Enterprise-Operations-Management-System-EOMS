import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.core.database import get_db
from app.core.exceptions import NotFoundException, BadRequestException, ConflictException
from app.core.dependencies import get_current_user
from app.models.auth import User
from app.models.core_business import Customer
from app.models.commerce import (
    Product, InventoryLog, Supplier, SupplierProduct,
    PurchaseOrder, PurchaseOrderItem, SalesOrder, OrderItem,
    Cart, CartItem, Coupon, CouponUsage, Invoice, Payment, RefundRequest
)
from app.schemas.commerce import (
    ProductCreate, ProductUpdate, ProductResponse,
    InventoryAdjustment, InventoryLogResponse,
    SupplierCreate, SupplierResponse, SupplierProductCreate, SupplierProductResponse,
    POCreate, POResponse,
    SalesOrderCreate, SalesOrderResponse,
    CartItemAdd, CartItemUpdate, CartResponse, CartItemResponse,
    CouponCreate, CouponResponse,
    InvoiceResponse, PaymentCreate, PaymentResponse,
    RefundCreate, RefundAction, RefundResponse
)
from app.schemas.common import MessageResponse, PaginatedResponse
from app.services.audit import log_audit

router = APIRouter(prefix="", tags=["Phase 3 — Commerce & Transactions"])


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(prod_in: ProductCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if db.query(Product).filter(Product.sku == prod_in.sku).first():
        raise ConflictException(message="Product with this SKU already exists")
    product = Product(**prod_in.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    log_audit(db, action="CREATE", module="PRODUCT", entity="Product", entity_id=str(product.id), user_id=current_user.id, details=f"Created product {product.name}")
    return product


@router.get("/products", response_model=PaginatedResponse[ProductResponse])
def list_products(
    search: str | None = None,
    category: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    low_stock_only: bool = False,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Product).filter(Product.is_active == True)
    if search:
        query = query.filter(or_(Product.name.ilike(f"%{search}%"), Product.sku.ilike(f"%{search}%")))
    if category:
        query = query.filter(Product.category.ilike(f"%{category}%"))
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    if low_stock_only:
        query = query.filter(Product.stock_quantity <= Product.low_stock_threshold)

    total = query.count()
    items = query.offset((page - 1) * limit).limit(limit).all()
    total_pages = (total + limit - 1) // limit if total > 0 else 1
    return PaginatedResponse(total=total, page=page, limit=limit, total_pages=total_pages, data=items)


@router.get("/products/{prod_id}", response_model=ProductResponse)
def get_product(prod_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    prod = db.query(Product).filter(Product.id == prod_id).first()
    if not prod:
        raise NotFoundException(message="Product not found")
    return prod


@router.put("/products/{prod_id}", response_model=ProductResponse)
def update_product(prod_id: int, prod_in: ProductUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    prod = db.query(Product).filter(Product.id == prod_id).first()
    if not prod:
        raise NotFoundException(message="Product not found")
    for k, v in prod_in.model_dump(exclude_unset=True).items():
        setattr(prod, k, v)
    db.commit()
    db.refresh(prod)
    return prod


@router.delete("/products/{prod_id}", response_model=MessageResponse)
def delete_product(prod_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    prod = db.query(Product).filter(Product.id == prod_id).first()
    if not prod:
        raise NotFoundException(message="Product not found")
    prod.is_active = False
    db.commit()
    return MessageResponse(message="Product deactivated successfully")


@router.post("/inventory/adjust", response_model=InventoryLogResponse)
def adjust_inventory(adj: InventoryAdjustment, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    prod = db.query(Product).filter(Product.id == adj.product_id).first()
    if not prod:
        raise NotFoundException(message="Product not found")

    prev = prod.stock_quantity
    change = adj.quantity

    if adj.change_type == "STOCK_IN":
        new_qty = prev + change
    elif adj.change_type == "STOCK_OUT":
        if prev < change:
            raise BadRequestException(message=f"Insufficient stock. Available: {prev}, Requested: {change}")
        new_qty = prev - change
    elif adj.change_type == "ADJUSTMENT":
        new_qty = change
    else:
        raise BadRequestException(message="Invalid change_type. Must be STOCK_IN, STOCK_OUT, or ADJUSTMENT")

    prod.stock_quantity = new_qty
    log = InventoryLog(
        product_id=prod.id,
        change_type=adj.change_type,
        quantity=change,
        previous_stock=prev,
        new_stock=new_qty,
        reason=adj.reason
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    log_audit(db, action="INVENTORY_ADJUST", module="INVENTORY", entity="Product", entity_id=str(prod.id), user_id=current_user.id, details=f"Inventory adjusted: {prev} -> {new_qty}")
    return log


@router.get("/inventory/logs", response_model=list[InventoryLogResponse])
def get_inventory_logs(product_id: int | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(InventoryLog)
    if product_id:
        query = query.filter(InventoryLog.product_id == product_id)
    return query.order_by(InventoryLog.created_at.desc()).all()


@router.get("/inventory/low-stock", response_model=list[ProductResponse])
def get_low_stock_products(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Product).filter(Product.stock_quantity <= Product.low_stock_threshold, Product.is_active == True).all()


@router.post("/suppliers", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
def create_supplier(sup_in: SupplierCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if db.query(Supplier).filter(Supplier.email == sup_in.email).first():
        raise ConflictException(message="Supplier with this email already exists")
    supplier = Supplier(**sup_in.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


@router.get("/suppliers", response_model=list[SupplierResponse])
def list_suppliers(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Supplier).filter(Supplier.is_active == True).all()


@router.post("/suppliers/{supplier_id}/products", response_model=SupplierProductResponse, status_code=status.HTTP_201_CREATED)
def link_supplier_product(supplier_id: int, sp_in: SupplierProductCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sup = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    prod = db.query(Product).filter(Product.id == sp_in.product_id).first()
    if not sup or not prod:
        raise NotFoundException(message="Supplier or Product not found")

    existing = db.query(SupplierProduct).filter(SupplierProduct.supplier_id == supplier_id, SupplierProduct.product_id == sp_in.product_id).first()
    if existing:
        existing.supply_price = sp_in.supply_price
        existing.lead_time_days = sp_in.lead_time_days
        db.commit()
        db.refresh(existing)
        return existing

    sp = SupplierProduct(
        supplier_id=supplier_id,
        product_id=sp_in.product_id,
        supply_price=sp_in.supply_price,
        lead_time_days=sp_in.lead_time_days
    )
    db.add(sp)
    db.commit()
    db.refresh(sp)
    log_audit(db, action="LINK_PRODUCT", module="SUPPLIER", entity="SupplierProduct", entity_id=str(sp.id), user_id=current_user.id, details=f"Linked product {prod.name} to supplier {sup.name}")
    return sp


@router.get("/suppliers/{supplier_id}/products", response_model=list[SupplierProductResponse])
def list_supplier_products(supplier_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sup = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not sup:
        raise NotFoundException(message="Supplier not found")
    return db.query(SupplierProduct).filter(SupplierProduct.supplier_id == supplier_id).all()


@router.delete("/suppliers/{supplier_id}/products/{product_id}", response_model=MessageResponse)
def remove_supplier_product(supplier_id: int, product_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sp = db.query(SupplierProduct).filter(SupplierProduct.supplier_id == supplier_id, SupplierProduct.product_id == product_id).first()
    if not sp:
        raise NotFoundException(message="Supplier product relationship not found")
    db.delete(sp)
    db.commit()
    return MessageResponse(message="Product removed from supplier successfully")


@router.post("/purchase-orders", response_model=POResponse, status_code=status.HTTP_201_CREATED)
def create_purchase_order(po_in: POCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sup = db.query(Supplier).filter(Supplier.id == po_in.supplier_id).first()
    if not sup:
        raise NotFoundException(message="Supplier not found")
    if not po_in.items:
        raise BadRequestException(message="Purchase order must contain at least one item")

    po_num = f"PO-{int(datetime.now(timezone.utc).timestamp())}"
    po = PurchaseOrder(
        po_number=po_num,
        supplier_id=sup.id,
        total_amount=0.0,
        status="DRAFT",
        approval_status="PENDING"
    )
    db.add(po)
    db.flush()

    total = 0.0
    for it in po_in.items:
        prod = db.query(Product).filter(Product.id == it.product_id).first()
        if not prod:
            raise NotFoundException(message=f"Product id {it.product_id} not found")
        item_tot = it.quantity * it.unit_price
        total += item_tot
        line = PurchaseOrderItem(
            purchase_order_id=po.id,
            product_id=it.product_id,
            quantity=it.quantity,
            unit_price=it.unit_price,
            total_price=item_tot
        )
        db.add(line)

    po.total_amount = total
    db.commit()
    db.refresh(po)
    log_audit(db, action="CREATE", module="PURCHASE_ORDER", entity="PurchaseOrder", entity_id=str(po.id), user_id=current_user.id, details=f"Created PO {po.po_number}")
    return po


@router.get("/purchase-orders", response_model=list[POResponse])
def list_purchase_orders(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(PurchaseOrder).order_by(PurchaseOrder.created_at.desc()).all()


@router.post("/purchase-orders/{po_id}/approve", response_model=POResponse)
def approve_purchase_order(po_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise NotFoundException(message="Purchase order not found")

    po.approval_status = "APPROVED"
    po.status = "ORDERED"
    for line in po.items:
        prod = db.query(Product).filter(Product.id == line.product_id).first()
        if prod:
            prod.stock_quantity += line.quantity
            inv = InventoryLog(
                product_id=prod.id,
                change_type="STOCK_IN",
                quantity=line.quantity,
                previous_stock=prod.stock_quantity - line.quantity,
                new_stock=prod.stock_quantity,
                reason=f"Received PO {po.po_number}"
            )
            db.add(inv)

    db.commit()
    db.refresh(po)
    log_audit(db, action="APPROVE", module="PURCHASE_ORDER", entity="PurchaseOrder", entity_id=str(po.id), user_id=current_user.id, details=f"Approved and stocked PO {po.po_number}")
    return po


@router.get("/cart", response_model=CartResponse)
def get_user_cart(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    cart = db.query(Cart).filter(Cart.user_id == current_user.id).first()
    if not cart:
        cart = Cart(user_id=current_user.id)
        db.add(cart)
        db.commit()
        db.refresh(cart)

    items_out = []
    subtotal = 0.0
    for it in cart.items:
        line_sub = it.quantity * it.product.price
        subtotal += line_sub
        items_out.append(CartItemResponse(
            id=it.id,
            product_id=it.product_id,
            quantity=it.quantity,
            product_name=it.product.name,
            unit_price=it.product.price,
            subtotal=line_sub
        ))

    return CartResponse(
        id=cart.id,
        user_id=current_user.id,
        items=items_out,
        subtotal=subtotal,
        total=subtotal
    )


@router.post("/cart/items", response_model=CartResponse)
def add_to_cart(item_in: CartItemAdd, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    prod = db.query(Product).filter(Product.id == item_in.product_id).first()
    if not prod or not prod.is_active:
        raise NotFoundException(message="Product not available")

    cart = db.query(Cart).filter(Cart.user_id == current_user.id).first()
    if not cart:
        cart = Cart(user_id=current_user.id)
        db.add(cart)
        db.flush()

    existing = db.query(CartItem).filter(CartItem.cart_id == cart.id, CartItem.product_id == item_in.product_id).first()
    if existing:
        existing.quantity += item_in.quantity
    else:
        new_item = CartItem(cart_id=cart.id, product_id=item_in.product_id, quantity=item_in.quantity)
        db.add(new_item)

    db.commit()
    return get_user_cart(db, current_user)


@router.put("/cart/items/{cart_item_id}", response_model=CartResponse)
def update_cart_item(cart_item_id: int, item_in: CartItemUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    cart = db.query(Cart).filter(Cart.user_id == current_user.id).first()
    if not cart:
        raise NotFoundException(message="Cart not found")

    item = db.query(CartItem).filter(CartItem.id == cart_item_id, CartItem.cart_id == cart.id).first()
    if not item:
        raise NotFoundException(message="Cart item not found")

    if item_in.quantity <= 0:
        db.delete(item)
    else:
        item.quantity = item_in.quantity
    db.commit()
    return get_user_cart(db, current_user)


@router.delete("/cart/items/{cart_item_id}", response_model=CartResponse)
def remove_from_cart(cart_item_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    cart = db.query(Cart).filter(Cart.user_id == current_user.id).first()
    if not cart:
        raise NotFoundException(message="Cart not found")
    item = db.query(CartItem).filter(CartItem.id == cart_item_id, CartItem.cart_id == cart.id).first()
    if item:
        db.delete(item)
        db.commit()
    return get_user_cart(db, current_user)


@router.post("/coupons", response_model=CouponResponse, status_code=status.HTTP_201_CREATED)
def create_coupon(coup_in: CouponCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if db.query(Coupon).filter(Coupon.code == coup_in.code).first():
        raise ConflictException(message="Coupon code already exists")
    coup = Coupon(**coup_in.model_dump())
    db.add(coup)
    db.commit()
    db.refresh(coup)
    return coup


@router.get("/coupons/{code}/validate")
def validate_coupon(code: str, order_amount: float = 0.0, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    coupon = db.query(Coupon).filter(Coupon.code == code).first()
    if not coupon or not coupon.is_active:
        raise BadRequestException(message="Coupon is invalid or inactive")

    v_from = coupon.valid_from if coupon.valid_from.tzinfo else coupon.valid_from.replace(tzinfo=timezone.utc)
    v_until = coupon.valid_until if coupon.valid_until.tzinfo else coupon.valid_until.replace(tzinfo=timezone.utc)

    if now < v_from or now > v_until:
        raise BadRequestException(message="Coupon is expired or not yet active")
    if coupon.times_used >= coupon.usage_limit:
        raise BadRequestException(message="Coupon usage limit reached")
    if order_amount < coupon.min_order_amount:
        raise BadRequestException(message=f"Minimum order amount of {coupon.min_order_amount} required")

    discount = (order_amount * (coupon.discount_value / 100.0)) if coupon.discount_type == "PERCENTAGE" else coupon.discount_value
    if coupon.max_discount_amount:
        discount = min(discount, coupon.max_discount_amount)

    return {
        "valid": True,
        "code": coupon.code,
        "discount_type": coupon.discount_type,
        "discount_value": coupon.discount_value,
        "calculated_discount": discount
    }


@router.post("/orders", response_model=SalesOrderResponse, status_code=status.HTTP_201_CREATED)
def create_sales_order(order_in: SalesOrderCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    cust = db.query(Customer).filter(Customer.id == order_in.customer_id).first()
    if not cust:
        raise NotFoundException(message="Customer not found")
    if not order_in.items:
        raise BadRequestException(message="Order must have at least one item")

    subtotal = 0.0
    for it in order_in.items:
        prod = db.query(Product).filter(Product.id == it.product_id).first()
        if not prod or not prod.is_active:
            raise BadRequestException(message=f"Product {it.product_id} not available")
        if prod.stock_quantity < it.quantity:
            raise BadRequestException(message=f"Insufficient stock for {prod.name}. Available: {prod.stock_quantity}")
        subtotal += prod.price * it.quantity

    discount = 0.0
    if order_in.coupon_code:
        c_res = validate_coupon(order_in.coupon_code, order_amount=subtotal, db=db, current_user=current_user)
        discount = c_res.get("calculated_discount", 0.0)

    tax = (subtotal - discount) * 0.05
    total = max(0.0, (subtotal - discount) + tax)

    ord_num = f"ORD-{int(datetime.now(timezone.utc).timestamp())}"
    order = SalesOrder(
        order_number=ord_num,
        customer_id=cust.id,
        subtotal=subtotal,
        discount_amount=discount,
        tax_amount=tax,
        total_amount=total,
        status="PENDING",
        coupon_code=order_in.coupon_code
    )
    db.add(order)
    db.flush()

    for it in order_in.items:
        prod = db.query(Product).filter(Product.id == it.product_id).first()
        line = OrderItem(
            order_id=order.id,
            product_id=prod.id,
            quantity=it.quantity,
            unit_price=prod.price,
            total_price=prod.price * it.quantity
        )
        prod.stock_quantity -= it.quantity
        inv = InventoryLog(
            product_id=prod.id,
            change_type="STOCK_OUT",
            quantity=it.quantity,
            previous_stock=prod.stock_quantity + it.quantity,
            new_stock=prod.stock_quantity,
            reason=f"Sold in order {order.order_number}"
        )
        db.add(line)
        db.add(inv)

    if order_in.coupon_code:
        coup = db.query(Coupon).filter(Coupon.code == order_in.coupon_code).first()
        if coup:
            coup.times_used += 1
            usage = CouponUsage(coupon_id=coup.id, user_id=current_user.id, order_id=order.id)
            db.add(usage)

    db.commit()
    db.refresh(order)
    log_audit(db, action="CREATE", module="ORDER", entity="SalesOrder", entity_id=str(order.id), user_id=current_user.id, details=f"Created order {order.order_number}")
    return order


@router.get("/orders", response_model=list[SalesOrderResponse])
def list_sales_orders(customer_id: int | None = None, status_filter: str | None = Query(None, alias="status"), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(SalesOrder)
    if customer_id:
        query = query.filter(SalesOrder.customer_id == customer_id)
    if status_filter:
        query = query.filter(SalesOrder.status == status_filter)
    return query.order_by(SalesOrder.created_at.desc()).all()


@router.get("/orders/{order_id}", response_model=SalesOrderResponse)
def get_sales_order(order_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
    if not order:
        raise NotFoundException(message="Sales order not found")
    return order


@router.post("/orders/{order_id}/generate-invoice", response_model=InvoiceResponse)
def generate_invoice(order_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
    if not order:
        raise NotFoundException(message="Sales order not found")

    existing = db.query(Invoice).filter(Invoice.order_id == order_id).first()
    if existing:
        return existing

    inv_num = f"INV-{order.order_number}"
    now = datetime.now(timezone.utc)
    due = now + timedelta(days=30)
    invoice = Invoice(
        invoice_number=inv_num,
        order_id=order.id,
        total_amount=order.total_amount,
        tax_amount=order.tax_amount,
        status="ISSUED",
        issued_at=now,
        due_date=due
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    log_audit(db, action="CREATE", module="INVOICE", entity="Invoice", entity_id=str(invoice.id), user_id=current_user.id, details=f"Generated invoice {invoice.invoice_number}")
    return invoice


@router.get("/invoices", response_model=list[InvoiceResponse])
def list_invoices(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Invoice).order_by(Invoice.issued_at.desc()).all()


@router.post("/payments", response_model=PaymentResponse)
def process_payment(pay_in: PaymentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    order = db.query(SalesOrder).filter(SalesOrder.id == pay_in.order_id).first()
    if not order:
        raise NotFoundException(message="Order not found")

    tx_id = f"TXN-{uuid.uuid4().hex[:12].upper()}"
    p_status = "FAILED" if pay_in.simulate_failure else "SUCCESSFUL"

    payment = Payment(
        transaction_id=tx_id,
        order_id=order.id,
        amount=pay_in.amount,
        payment_method=pay_in.payment_method,
        status=p_status
    )
    db.add(payment)

    if p_status == "SUCCESSFUL":
        order.status = "PAID"
        inv = db.query(Invoice).filter(Invoice.order_id == order.id).first()
        if inv:
            inv.status = "PAID"

    db.commit()
    db.refresh(payment)
    log_audit(db, action="PAYMENT", module="PAYMENT", entity="Payment", entity_id=str(payment.id), user_id=current_user.id, details=f"Payment {p_status} for order {order.order_number}")
    return payment


@router.get("/payments", response_model=list[PaymentResponse])
def list_payments(order_id: int | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Payment)
    if order_id:
        query = query.filter(Payment.order_id == order_id)
    return query.order_by(Payment.created_at.desc()).all()


@router.post("/refunds", response_model=RefundResponse, status_code=status.HTTP_201_CREATED)
def request_refund(ref_in: RefundCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    payment = db.query(Payment).filter(Payment.id == ref_in.payment_id).first()
    if not payment:
        raise NotFoundException(message="Payment not found")
    if payment.status != "SUCCESSFUL":
        raise BadRequestException(message="Only successful payments can be refunded")
    if ref_in.amount > payment.amount:
        raise BadRequestException(message="Refund amount cannot exceed paid amount")

    refund = RefundRequest(
        payment_id=payment.id,
        amount=ref_in.amount,
        reason=ref_in.reason,
        status="PENDING"
    )
    db.add(refund)
    db.commit()
    db.refresh(refund)
    log_audit(db, action="CREATE", module="REFUND", entity="RefundRequest", entity_id=str(refund.id), user_id=current_user.id, details="Refund requested")
    return refund


@router.get("/refunds", response_model=list[RefundResponse])
def list_refunds(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(RefundRequest).order_by(RefundRequest.created_at.desc()).all()


@router.post("/refunds/{refund_id}/action", response_model=RefundResponse)
def handle_refund_action(refund_id: int, action_in: RefundAction, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    refund = db.query(RefundRequest).filter(RefundRequest.id == refund_id).first()
    if not refund:
        raise NotFoundException(message="Refund request not found")

    refund.status = action_in.status
    refund.approved_by_id = current_user.id
    if action_in.status == "APPROVED":
        refund.payment.status = "REFUNDED"
        refund.payment.order.status = "REFUNDED"

    db.commit()
    db.refresh(refund)
    log_audit(db, action=action_in.status, module="REFUND", entity="RefundRequest", entity_id=str(refund.id), user_id=current_user.id, details=f"Refund request {action_in.status}")
    return refund

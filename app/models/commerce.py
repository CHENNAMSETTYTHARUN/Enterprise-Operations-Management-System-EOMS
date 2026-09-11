from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from app.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(255), index=True, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), index=True, nullable=False)
    price = Column(Float, nullable=False)
    cost_price = Column(Float, default=0.0, nullable=False)
    stock_quantity = Column(Integer, default=0, nullable=False)
    low_stock_threshold = Column(Integer, default=10, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    inventory_logs = relationship("InventoryLog", back_populates="product")
    order_items = relationship("OrderItem", back_populates="product")
    cart_items = relationship("CartItem", back_populates="product")
    suppliers = relationship("SupplierProduct", back_populates="product")


class InventoryLog(Base):
    __tablename__ = "inventory_logs"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    change_type = Column(String(50), nullable=False)
    quantity = Column(Integer, nullable=False)
    previous_stock = Column(Integer, nullable=False)
    new_stock = Column(Integer, nullable=False)
    reason = Column(String(255), nullable=True)
    reference_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    product = relationship("Product", back_populates="inventory_logs")


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    contact_person = Column(String(100), nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    products = relationship("SupplierProduct", back_populates="supplier")
    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")


class SupplierProduct(Base):
    __tablename__ = "supplier_products"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    supply_price = Column(Float, nullable=False)
    lead_time_days = Column(Integer, default=7, nullable=False)

    supplier = relationship("Supplier", back_populates="products")
    product = relationship("Product", back_populates="suppliers")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    po_number = Column(String(100), unique=True, index=True, nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False, index=True)
    total_amount = Column(Float, default=0.0, nullable=False)
    status = Column(String(50), default="DRAFT", index=True, nullable=False)
    approval_status = Column(String(50), default="PENDING", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    supplier = relationship("Supplier", back_populates="purchase_orders")
    items = relationship("PurchaseOrderItem", back_populates="purchase_order", cascade="all, delete-orphan")


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    id = Column(Integer, primary_key=True, index=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)

    purchase_order = relationship("PurchaseOrder", back_populates="items")
    product = relationship("Product")


class SalesOrder(Base):
    __tablename__ = "sales_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(100), unique=True, index=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    subtotal = Column(Float, default=0.0, nullable=False)
    discount_amount = Column(Float, default=0.0, nullable=False)
    tax_amount = Column(Float, default=0.0, nullable=False)
    total_amount = Column(Float, default=0.0, nullable=False)
    status = Column(String(50), default="PENDING", index=True, nullable=False)
    coupon_code = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    customer = relationship("Customer", back_populates="sales_orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    invoice = relationship("Invoice", back_populates="order", uselist=False)
    payments = relationship("Payment", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("sales_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)

    order = relationship("SalesOrder", back_populates="items")
    product = relationship("Product", back_populates="order_items")


class Cart(Base):
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey("carts.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    cart = relationship("Cart", back_populates="items")
    product = relationship("Product", back_populates="cart_items")


class Coupon(Base):
    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    discount_type = Column(String(20), default="PERCENTAGE", nullable=False)
    discount_value = Column(Float, nullable=False)
    min_order_amount = Column(Float, default=0.0, nullable=False)
    max_discount_amount = Column(Float, nullable=True)
    usage_limit = Column(Integer, default=100, nullable=False)
    times_used = Column(Integer, default=0, nullable=False)
    valid_from = Column(DateTime, nullable=False)
    valid_until = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    usages = relationship("CouponUsage", back_populates="coupon")


class CouponUsage(Base):
    __tablename__ = "coupon_usages"

    id = Column(Integer, primary_key=True, index=True)
    coupon_id = Column(Integer, ForeignKey("coupons.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("sales_orders.id", ondelete="CASCADE"), nullable=False)
    used_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    coupon = relationship("Coupon", back_populates="usages")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String(100), unique=True, index=True, nullable=False)
    order_id = Column(Integer, ForeignKey("sales_orders.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    total_amount = Column(Float, nullable=False)
    tax_amount = Column(Float, default=0.0, nullable=False)
    status = Column(String(50), default="ISSUED", index=True, nullable=False)
    issued_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    due_date = Column(DateTime, nullable=False)

    order = relationship("SalesOrder", back_populates="invoice")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String(100), unique=True, index=True, nullable=False)
    order_id = Column(Integer, ForeignKey("sales_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    payment_method = Column(String(50), default="SIMULATED", nullable=False)
    status = Column(String(50), default="PENDING", index=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    order = relationship("SalesOrder", back_populates="payments")
    refunds = relationship("RefundRequest", back_populates="payment")


class RefundRequest(Base):
    __tablename__ = "refund_requests"

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey("payments.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(50), default="PENDING", index=True, nullable=False)
    approved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    payment = relationship("Payment", back_populates="refunds")
    approver = relationship("User", foreign_keys=[approved_by_id])

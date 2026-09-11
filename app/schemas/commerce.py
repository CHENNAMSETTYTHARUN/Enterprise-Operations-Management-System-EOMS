from datetime import datetime
from pydantic import BaseModel


class ProductBase(BaseModel):
    sku: str
    name: str
    description: str | None = None
    category: str
    price: float
    cost_price: float = 0.0
    stock_quantity: int = 0
    low_stock_threshold: int = 10
    is_active: bool = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None
    price: float | None = None
    cost_price: float | None = None
    stock_quantity: int | None = None
    low_stock_threshold: int | None = None
    is_active: bool | None = None


class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InventoryAdjustment(BaseModel):
    product_id: int
    change_type: str
    quantity: int
    reason: str | None = None


class InventoryLogResponse(BaseModel):
    id: int
    product_id: int
    change_type: str
    quantity: int
    previous_stock: int
    new_stock: int
    reason: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class SupplierBase(BaseModel):
    name: str
    contact_person: str | None = None
    email: str
    phone: str | None = None
    address: str | None = None
    is_active: bool = True


class SupplierCreate(SupplierBase):
    pass


class SupplierResponse(SupplierBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class SupplierProductCreate(BaseModel):
    product_id: int
    supply_price: float
    lead_time_days: int = 7


class SupplierProductResponse(BaseModel):
    id: int
    supplier_id: int
    product_id: int
    supply_price: float
    lead_time_days: int

    class Config:
        from_attributes = True


class POItemCreate(BaseModel):
    product_id: int
    quantity: int
    unit_price: float


class POItemResponse(POItemCreate):
    id: int
    total_price: float

    class Config:
        from_attributes = True


class POCreate(BaseModel):
    supplier_id: int
    items: list[POItemCreate]


class POResponse(BaseModel):
    id: int
    po_number: str
    supplier_id: int
    total_amount: float
    status: str
    approval_status: str
    created_at: datetime
    items: list[POItemResponse] = []

    class Config:
        from_attributes = True


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int


class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    unit_price: float
    total_price: float

    class Config:
        from_attributes = True


class SalesOrderCreate(BaseModel):
    customer_id: int
    items: list[OrderItemCreate]
    coupon_code: str | None = None


class SalesOrderResponse(BaseModel):
    id: int
    order_number: str
    customer_id: int
    subtotal: float
    discount_amount: float
    tax_amount: float
    total_amount: float
    status: str
    coupon_code: str | None = None
    created_at: datetime
    items: list[OrderItemResponse] = []

    class Config:
        from_attributes = True


class CartItemAdd(BaseModel):
    product_id: int
    quantity: int = 1


class CartItemUpdate(BaseModel):
    quantity: int


class CartItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    product_name: str
    unit_price: float
    subtotal: float


class CartResponse(BaseModel):
    id: int
    user_id: int
    items: list[CartItemResponse] = []
    subtotal: float
    total: float


class CouponCreate(BaseModel):
    code: str
    discount_type: str = "PERCENTAGE"
    discount_value: float
    min_order_amount: float = 0.0
    max_discount_amount: float | None = None
    usage_limit: int = 100
    valid_from: datetime
    valid_until: datetime
    is_active: bool = True


class CouponResponse(CouponCreate):
    id: int
    times_used: int

    class Config:
        from_attributes = True


class InvoiceResponse(BaseModel):
    id: int
    invoice_number: str
    order_id: int
    total_amount: float
    tax_amount: float
    status: str
    issued_at: datetime
    due_date: datetime

    class Config:
        from_attributes = True


class PaymentCreate(BaseModel):
    order_id: int
    amount: float
    payment_method: str = "SIMULATED"
    simulate_failure: bool = False


class PaymentResponse(BaseModel):
    id: int
    transaction_id: str
    order_id: int
    amount: float
    payment_method: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class RefundCreate(BaseModel):
    payment_id: int
    amount: float
    reason: str


class RefundAction(BaseModel):
    status: str


class RefundResponse(BaseModel):
    id: int
    payment_id: int
    amount: float
    reason: str
    status: str
    approved_by_id: int | None = None
    created_at: datetime

    class Config:
        from_attributes = True

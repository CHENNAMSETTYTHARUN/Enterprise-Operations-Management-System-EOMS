from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine, Base
from app.core.security import get_password_hash
from app.models.auth import User, Role, Permission
from app.models.core_business import Department, Employee, Customer
from app.models.commerce import Product, Coupon
from datetime import datetime, timezone, timedelta


def init_db(db: Session):
    Base.metadata.create_all(bind=engine)

    perms_data = [
        ("user:read", "Read Users"),
        ("user:write", "Write Users"),
        ("admin:all", "Admin Full Access"),
        ("employee:read", "Read Employees"),
        ("employee:write", "Write Employees"),
        ("finance:manage", "Manage Finances")
    ]
    perm_objs = {}
    for code, name in perms_data:
        p = db.query(Permission).filter(Permission.code == code).first()
        if not p:
            p = Permission(code=code, name=name)
            db.add(p)
            db.flush()
        perm_objs[code] = p

    roles_data = {
        "ADMIN": ["admin:all", "user:read", "user:write", "employee:read", "employee:write", "finance:manage"],
        "MANAGER": ["user:read", "employee:read", "employee:write"],
        "EMPLOYEE": ["employee:read"]
    }
    role_objs = {}
    for r_name, p_codes in roles_data.items():
        r = db.query(Role).filter(Role.name == r_name).first()
        if not r:
            r = Role(name=r_name, description=f"{r_name} role", permissions=[perm_objs[c] for c in p_codes])
            db.add(r)
            db.flush()
        role_objs[r_name] = r

    admin_user = db.query(User).filter(User.username == "admin").first()
    if not admin_user:
        admin_user = User(
            email="admin@enterprise.com",
            username="admin",
            hashed_password=get_password_hash("admin123"),
            full_name="System Administrator",
            is_active=True,
            is_superuser=True,
            roles=[role_objs["ADMIN"], role_objs["MANAGER"]]
        )
        db.add(admin_user)
        db.flush()

    manager_user = db.query(User).filter(User.username == "manager").first()
    if not manager_user:
        manager_user = User(
            email="manager@enterprise.com",
            username="manager",
            hashed_password=get_password_hash("manager123"),
            full_name="Operations Manager",
            is_active=True,
            is_superuser=False,
            roles=[role_objs["MANAGER"]]
        )
        db.add(manager_user)
        db.flush()

    employee_user = db.query(User).filter(User.username == "employee").first()
    if not employee_user:
        employee_user = User(
            email="employee@enterprise.com",
            username="employee",
            hashed_password=get_password_hash("employee123"),
            full_name="John Doe",
            is_active=True,
            is_superuser=False,
            roles=[role_objs["EMPLOYEE"]]
        )
        db.add(employee_user)
        db.flush()

    dept = db.query(Department).filter(Department.code == "ENG-01").first()
    if not dept:
        dept = Department(name="Engineering", code="ENG-01", description="Software Development & DevOps", is_active=True)
        db.add(dept)
        db.flush()

    emp = db.query(Employee).filter(Employee.user_id == employee_user.id).first()
    if not emp:
        emp = Employee(
            user_id=employee_user.id,
            department_id=dept.id,
            employee_code="EMP-1001",
            designation="Senior Software Engineer",
            phone="+1-555-0100",
            salary=95000.0,
            is_active=True
        )
        db.add(emp)
        db.flush()

    cust = db.query(Customer).filter(Customer.email == "acme@corporation.com").first()
    if not cust:
        cust = Customer(
            name="Acme Corporation",
            email="acme@corporation.com",
            phone="+1-555-0200",
            company="Acme Corp",
            address="100 Innovation Way",
            city="New York",
            country="USA",
            status="ACTIVE"
        )
        db.add(cust)
        db.flush()

    prod = db.query(Product).filter(Product.sku == "PROD-CLOUD-01").first()
    if not prod:
        prod = Product(
            sku="PROD-CLOUD-01",
            name="Enterprise Cloud Suite",
            description="Enterprise operational license",
            category="Software",
            price=2999.0,
            cost_price=1200.0,
            stock_quantity=50,
            low_stock_threshold=5,
            is_active=True
        )
        db.add(prod)
        db.flush()

    coupon = db.query(Coupon).filter(Coupon.code == "WELCOME10").first()
    if not coupon:
        now = datetime.now(timezone.utc)
        coupon = Coupon(
            code="WELCOME10",
            discount_type="PERCENTAGE",
            discount_value=10.0,
            min_order_amount=100.0,
            usage_limit=500,
            times_used=0,
            valid_from=now - timedelta(days=1),
            valid_until=now + timedelta(days=365),
            is_active=True
        )
        db.add(coupon)
        db.flush()

    db.commit()


if __name__ == "__main__":
    db = SessionLocal()
    try:
        init_db(db)
    finally:
        db.close()

import io
import csv
import pandas as pd
from typing import Any
from fastapi import UploadFile
from sqlalchemy.orm import Session
from app.models.core_business import Customer
from app.models.commerce import Product
from app.models.infrastructure import DataImportHistory


def export_data_to_csv(data: list[dict[str, Any]]) -> io.StringIO:
    output = io.StringIO()
    if not data:
        return output
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    output.seek(0)
    return output


def export_data_to_excel(data: list[dict[str, Any]]) -> io.BytesIO:
    output = io.BytesIO()
    df = pd.DataFrame(data)
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return output


async def import_customers_file(db: Session, file: UploadFile, user_id: int) -> dict[str, Any]:
    content = await file.read()
    filename = file.filename or "import.csv"

    if filename.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(content))
    else:
        df = pd.read_excel(io.BytesIO(content))

    total_rows = len(df)
    successful = 0
    failed = 0
    errors = []

    for idx, row in df.iterrows():
        try:
            name = str(row.get("name", "")).strip()
            email = str(row.get("email", "")).strip()
            if not name or not email or "@" not in email:
                raise ValueError("Valid name and email are required")

            existing = db.query(Customer).filter(Customer.email == email).first()
            if existing:
                raise ValueError(f"Customer with email {email} already exists")

            cust = Customer(
                name=name,
                email=email,
                phone=str(row.get("phone", "")) if pd.notna(row.get("phone")) else None,
                company=str(row.get("company", "")) if pd.notna(row.get("company")) else None,
                status="ACTIVE"
            )
            db.add(cust)
            db.commit()
            successful += 1
        except Exception as e:
            db.rollback()
            failed += 1
            errors.append(f"Row {idx + 1}: {str(e)}")

    history = DataImportHistory(
        imported_by_id=user_id,
        entity_type="CUSTOMERS",
        file_name=filename,
        total_rows=total_rows,
        successful_rows=successful,
        failed_rows=failed,
        error_summary="; ".join(errors[:10]) if errors else None
    )
    db.add(history)
    db.commit()
    db.refresh(history)

    return {
        "history_id": history.id,
        "total_rows": total_rows,
        "successful_rows": successful,
        "failed_rows": failed,
        "errors": errors
    }


async def import_products_file(db: Session, file: UploadFile, user_id: int) -> dict[str, Any]:
    content = await file.read()
    filename = file.filename or "products.csv"

    if filename.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(content))
    else:
        df = pd.read_excel(io.BytesIO(content))

    total_rows = len(df)
    successful = 0
    failed = 0
    errors = []

    for idx, row in df.iterrows():
        try:
            sku = str(row.get("sku", "")).strip()
            name = str(row.get("name", "")).strip()
            price = float(row.get("price", 0))
            category = str(row.get("category", "General")).strip()

            if not sku or not name or price <= 0:
                raise ValueError("Valid SKU, Name, and positive Price are required")

            existing = db.query(Product).filter(Product.sku == sku).first()
            if existing:
                raise ValueError(f"Product with SKU {sku} already exists")

            prod = Product(
                sku=sku,
                name=name,
                category=category,
                price=price,
                stock_quantity=int(row.get("stock_quantity", 0)) if pd.notna(row.get("stock_quantity")) else 0,
                is_active=True
            )
            db.add(prod)
            db.commit()
            successful += 1
        except Exception as e:
            db.rollback()
            failed += 1
            errors.append(f"Row {idx + 1}: {str(e)}")

    history = DataImportHistory(
        imported_by_id=user_id,
        entity_type="PRODUCTS",
        file_name=filename,
        total_rows=total_rows,
        successful_rows=successful,
        failed_rows=failed,
        error_summary="; ".join(errors[:10]) if errors else None
    )
    db.add(history)
    db.commit()
    db.refresh(history)

    return {
        "history_id": history.id,
        "total_rows": total_rows,
        "successful_rows": successful,
        "failed_rows": failed,
        "errors": errors
    }

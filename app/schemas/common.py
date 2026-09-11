from typing import Generic, TypeVar, Any
from pydantic import BaseModel, Field

T = TypeVar("T")


class MessageResponse(BaseModel):
    success: bool = True
    message: str


class DataResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T
    message: str | None = None


class PaginatedResponse(BaseModel, Generic[T]):
    success: bool = True
    total: int
    page: int
    limit: int
    total_pages: int
    data: list[T]


class HealthResponse(BaseModel):
    status: str
    database: str
    redis: dict[str, Any]
    timestamp: str

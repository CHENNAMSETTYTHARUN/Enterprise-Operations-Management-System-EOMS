from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError


class AppException(Exception):
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST, code: str = "BAD_REQUEST", details: dict | list | None = None):
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details
        super().__init__(message)


class NotFoundException(AppException):
    def __init__(self, message: str = "Resource not found", details: dict | list | None = None):
        super().__init__(message=message, status_code=status.HTTP_404_NOT_FOUND, code="NOT_FOUND", details=details)


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Could not validate credentials", details: dict | list | None = None):
        super().__init__(message=message, status_code=status.HTTP_401_UNAUTHORIZED, code="UNAUTHORIZED", details=details)


class ForbiddenException(AppException):
    def __init__(self, message: str = "Permission denied", details: dict | list | None = None):
        super().__init__(message=message, status_code=status.HTTP_403_FORBIDDEN, code="FORBIDDEN", details=details)


class BadRequestException(AppException):
    def __init__(self, message: str = "Bad request", details: dict | list | None = None):
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST, code="BAD_REQUEST", details=details)


class ConflictException(AppException):
    def __init__(self, message: str = "Conflict with existing resource", details: dict | list | None = None):
        super().__init__(message=message, status_code=status.HTTP_409_CONFLICT, code="CONFLICT", details=details)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request parameters",
                "details": exc.errors()
            }
        }
    )


async def integrity_exception_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "error": {
                "code": "DATABASE_INTEGRITY_ERROR",
                "message": "Database constraint violation occurred",
                "details": str(exc.orig) if hasattr(exc, "orig") else str(exc)
            }
        }
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "DATABASE_ERROR",
                "message": "Database operation failed",
                "details": None
            }
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred on the server",
                "details": str(exc)
            }
        }
    )

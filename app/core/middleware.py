import time
import uuid
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

logger = logging.getLogger("eoms")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [request_id=%(name)s] %(message)s"
)


class LoggingAndCorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.time()
        logger.info(f"Incoming request {request.method} {request.url.path} ID: {request_id}")

        try:
            response = await call_next(request)
            process_time = (time.time() - start_time) * 1000
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"
            logger.info(f"Completed request {request.method} {request.url.path} with status {response.status_code} in {process_time:.2f}ms")
            return response
        except Exception as exc:
            process_time = (time.time() - start_time) * 1000
            logger.error(f"Error handling request {request.method} {request.url.path} after {process_time:.2f}ms: {exc}")
            raise exc

import time
from app.core.cache import cache
from app.core.exceptions import AppException


class RateLimiter:
    def __init__(self, requests_limit: int = 60, window_seconds: int = 60):
        self.requests_limit = requests_limit
        self.window_seconds = window_seconds

    def check_rate_limit(self, identifier: str, endpoint: str):
        key = f"rate_limit:{identifier}:{endpoint}"
        current_data = cache.get(key)
        now = time.time()

        if current_data is None:
            cache.set(key, {"count": 1, "start_time": now}, expire_seconds=self.window_seconds)
            return True

        count = current_data.get("count", 0)
        start_time = current_data.get("start_time", now)

        if now - start_time > self.window_seconds:
            cache.set(key, {"count": 1, "start_time": now}, expire_seconds=self.window_seconds)
            return True

        if count >= self.requests_limit:
            retry_after = int(self.window_seconds - (now - start_time))
            raise AppException(
                message=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                status_code=429,
                code="RATE_LIMIT_EXCEEDED",
                details={"retry_after": retry_after}
            )

        cache.set(key, {"count": count + 1, "start_time": start_time}, expire_seconds=int(self.window_seconds - (now - start_time)) + 1)
        return True


rate_limiter = RateLimiter(requests_limit=120, window_seconds=60)

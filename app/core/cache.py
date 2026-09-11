import json
import time
import socket
from typing import Any
import redis
from app.core.config import settings


def is_port_open(host: str, port: int, timeout: float = 0.05) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


class CacheService:
    def __init__(self):
        self.memory_store: dict[str, tuple[str, float | None]] = {}
        self._redis_client = None
        self._redis_available = False

    def _get_redis(self):
        if not self._redis_available:
            if is_port_open(settings.REDIS_HOST, settings.REDIS_PORT, timeout=0.05):
                try:
                    client = redis.Redis(
                        host=settings.REDIS_HOST,
                        port=settings.REDIS_PORT,
                        db=settings.REDIS_DB,
                        decode_responses=True,
                        socket_timeout=0.2,
                        socket_connect_timeout=0.2
                    )
                    client.ping()
                    self._redis_client = client
                    self._redis_available = True
                except Exception:
                    self._redis_client = None
                    self._redis_available = False
            else:
                self._redis_client = None
                self._redis_available = False
        return self._redis_client if self._redis_available else None

    def get(self, key: str) -> Any | None:
        client = self._get_redis()
        if client:
            try:
                val = client.get(key)
                if val is not None:
                    return json.loads(val)
            except Exception:
                self._redis_available = False

        if key in self.memory_store:
            data_str, expiry = self.memory_store[key]
            if expiry is None or time.time() < expiry:
                return json.loads(data_str)
            else:
                del self.memory_store[key]
        return None

    def set(self, key: str, value: Any, expire_seconds: int | None = 300) -> bool:
        val_str = json.dumps(value, default=str)
        client = self._get_redis()
        if client:
            try:
                if expire_seconds:
                    client.setex(key, expire_seconds, val_str)
                else:
                    client.set(key, val_str)
                return True
            except Exception:
                self._redis_available = False

        expiry = time.time() + expire_seconds if expire_seconds else None
        self.memory_store[key] = (val_str, expiry)
        return True

    def delete(self, key: str) -> bool:
        client = self._get_redis()
        if client:
            try:
                client.delete(key)
            except Exception:
                self._redis_available = False

        if key in self.memory_store:
            del self.memory_store[key]
        return True

    def delete_pattern(self, pattern: str) -> bool:
        client = self._get_redis()
        if client:
            try:
                keys = client.keys(pattern)
                if keys:
                    client.delete(*keys)
            except Exception:
                self._redis_available = False

        prefix = pattern.replace("*", "")
        keys_to_delete = [k for k in self.memory_store if k.startswith(prefix)]
        for k in keys_to_delete:
            del self.memory_store[k]
        return True

    def ping(self) -> dict[str, Any]:
        client = self._get_redis()
        if client:
            try:
                if client.ping():
                    return {"status": "connected", "type": "redis"}
            except Exception as e:
                self._redis_available = False
                return {"status": "fallback", "type": "in_memory", "error": str(e)}
        return {"status": "connected", "type": "in_memory"}


cache = CacheService()

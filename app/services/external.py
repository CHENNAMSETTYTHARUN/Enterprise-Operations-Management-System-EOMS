import httpx
from app.core.config import settings


class ExternalApiClient:
    def __init__(self):
        self.base_url = settings.EXTERNAL_API_URL
        self.timeout = 5.0

    async def fetch_external_data(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.base_url)
                if response.status_code == 200:
                    return {
                        "status": "success",
                        "source": self.base_url,
                        "data": response.json()
                    }
                return {
                    "status": "warning",
                    "message": f"External API returned {response.status_code}",
                    "data": {"mock_key": "mock_value_fallback"}
                }
        except Exception as e:
            return {
                "status": "fallback",
                "message": f"External API unavailable: {str(e)}",
                "data": {"id": 1, "title": "Fallback data", "body": "External service is temporarily unreachable"}
            }


external_client = ExternalApiClient()

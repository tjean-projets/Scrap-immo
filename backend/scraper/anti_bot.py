from __future__ import annotations

import asyncio
import random

import httpx
import structlog

logger = structlog.get_logger()

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
]

VIEWPORTS = [
    (1920, 1080),
    (1440, 900),
    (1366, 768),
    (1536, 864),
    (1280, 720),
]


class AntiBotManager:
    def __init__(self, min_delay: float = 2.0, max_delay: float = 6.0, max_retries: int = 3):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.max_retries = max_retries

    def random_ua(self) -> str:
        return random.choice(USER_AGENTS)

    def random_viewport(self) -> tuple[int, int]:
        return random.choice(VIEWPORTS)

    def base_headers(self) -> dict[str, str]:
        return {
            "User-Agent": self.random_ua(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    async def delay(self):
        wait = random.uniform(self.min_delay, self.max_delay)
        await asyncio.sleep(wait)

    def create_client(self, **kwargs) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            headers=self.base_headers(),
            follow_redirects=True,
            timeout=30.0,
            **kwargs,
        )

    async def fetch_with_retry(
        self, client: httpx.AsyncClient, url: str
    ) -> httpx.Response | None:
        for attempt in range(self.max_retries):
            try:
                await self.delay()
                response = await client.get(url)
                if response.status_code == 200:
                    return response
                if response.status_code in (429, 503):
                    backoff = 10 * (2**attempt) + random.uniform(0, 5)
                    logger.warning(
                        "rate_limited",
                        url=url,
                        status=response.status_code,
                        backoff=backoff,
                    )
                    await asyncio.sleep(backoff)
                    client.headers["User-Agent"] = self.random_ua()
                    continue
                logger.warning("http_error", url=url, status=response.status_code)
                return None
            except httpx.HTTPError as e:
                logger.error("request_failed", url=url, error=str(e), attempt=attempt)
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(5 * (attempt + 1))
        return None

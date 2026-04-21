"""
Simple rate limiter for Groq free tier.
Enforces a minimum delay between consecutive API calls to stay
within 30 RPM / 6,000 TPM limits.
"""

import asyncio
import time
import logging

logger = logging.getLogger(__name__)


class GroqRateLimiter:
    """
    Enforces a minimum delay between Groq API calls.
    
    Default 2.5s delay → max ~24 calls/min (safely under 30 RPM).
    """

    def __init__(self, min_delay: float = 2.5):
        self.min_delay = min_delay
        self._last_call: float = 0.0

    async def wait(self) -> None:
        """Wait until enough time has passed since the last call."""
        now = time.time()
        elapsed = now - self._last_call
        if elapsed < self.min_delay:
            wait_time = self.min_delay - elapsed
            logger.debug("Rate limiter: waiting %.1fs", wait_time)
            await asyncio.sleep(wait_time)
        self._last_call = time.time()

    def wait_sync(self) -> None:
        """Synchronous version for non-async contexts."""
        now = time.time()
        elapsed = now - self._last_call
        if elapsed < self.min_delay:
            wait_time = self.min_delay - elapsed
            logger.debug("Rate limiter: waiting %.1fs", wait_time)
            time.sleep(wait_time)
        self._last_call = time.time()


# Singleton instance shared across all nodes
rate_limiter = GroqRateLimiter()

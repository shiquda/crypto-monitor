"""
Reconnect strategy for WebSocket connections.
"""

import random
from typing import Optional

class ReconnectStrategy:
    """
    Exponential backoff reconnection strategy.
    Implements jitter to prevent thundering herd problem.
    """

    def __init__(self, initial_delay: float = 1.0, max_delay: float = 30.0,
                 backoff_factor: float = 2.0, max_retries: Optional[int] = None):
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.max_retries = max_retries
        self.retry_count = 0

    def next_delay(self) -> float:
        """Get the next retry delay with exponential backoff and jitter."""
        if self.retry_count == 0:
            delay = self.initial_delay
        else:
            delay = min(
                self.initial_delay * (self.backoff_factor ** self.retry_count),
                self.max_delay
            )

        # Add jitter (±25% random variation)
        jitter = delay * 0.25 * random.random()
        delay += jitter if random.random() > 0.5 else -jitter

        self.retry_count += 1
        return max(delay, self.initial_delay)

    def reset(self):
        """Reset retry counter."""
        self.retry_count = 0

    def should_retry(self) -> bool:
        """Check if retry attempts are still within limits."""
        if self.max_retries is None:
            return True
        return self.retry_count < self.max_retries

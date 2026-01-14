"""
Rate Limiter - Token bucket implementation for respectful scraping
Thread-safe with adaptive delay based on server responses
"""
import time
import threading
from typing import Optional


class RateLimiter:
    """
    Token bucket rate limiter
    - Ensures minimum delay between requests
    - Thread-safe for concurrent scraping
    - Supports adaptive delay increase on 429 responses
    """
    
    def __init__(self, min_delay: float = 1.0, max_delay: float = 10.0):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.current_delay = min_delay
        self.last_request_time: Optional[float] = None
        self._lock = threading.Lock()
    
    def wait(self) -> float:
        """
        Wait until next request is allowed
        Returns the actual wait time
        """
        with self._lock:
            now = time.time()
            
            if self.last_request_time is None:
                self.last_request_time = now
                return 0.0
            
            elapsed = now - self.last_request_time
            wait_time = max(0, self.current_delay - elapsed)
            
            if wait_time > 0:
                time.sleep(wait_time)
            
            self.last_request_time = time.time()
            return wait_time
    
    def increase_delay(self, factor: float = 2.0):
        """Increase delay on rate limit response (429)"""
        with self._lock:
            self.current_delay = min(self.current_delay * factor, self.max_delay)
    
    def decrease_delay(self, factor: float = 0.9):
        """Gradually decrease delay on successful responses"""
        with self._lock:
            self.current_delay = max(self.current_delay * factor, self.min_delay)
    
    def reset(self):
        """Reset to minimum delay"""
        with self._lock:
            self.current_delay = self.min_delay
            self.last_request_time = None
    
    @property
    def delay(self) -> float:
        """Current delay value"""
        return self.current_delay


class AdaptiveRateLimiter(RateLimiter):
    """
    Adaptive rate limiter that adjusts based on response patterns
    - Tracks success/failure rates
    - Automatically adjusts delay
    """
    
    def __init__(self, min_delay: float = 1.0, max_delay: float = 10.0, window_size: int = 10):
        super().__init__(min_delay, max_delay)
        self.window_size = window_size
        self.success_history: list = []
    
    def record_success(self):
        """Record successful request"""
        with self._lock:
            self.success_history.append(True)
            if len(self.success_history) > self.window_size:
                self.success_history.pop(0)
            
            # If all recent requests successful, try decreasing delay
            if len(self.success_history) == self.window_size and all(self.success_history):
                self.current_delay = max(self.current_delay * 0.95, self.min_delay)
    
    def record_failure(self):
        """Record failed request (rate limited or error)"""
        with self._lock:
            self.success_history.append(False)
            if len(self.success_history) > self.window_size:
                self.success_history.pop(0)
            
            # Increase delay on failure
            self.current_delay = min(self.current_delay * 1.5, self.max_delay)
    
    def get_success_rate(self) -> float:
        """Get recent success rate (0.0 to 1.0)"""
        if not self.success_history:
            return 1.0
        return sum(self.success_history) / len(self.success_history)

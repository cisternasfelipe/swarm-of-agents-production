import time
import threading
from collections import deque

from config import RATE_LIMIT_REQUESTS_PER_MINUTE


class RateLimiter:
    def __init__(self, max_requests: int = RATE_LIMIT_REQUESTS_PER_MINUTE):
        self._max = max_requests
        self._timestamps = deque()
        self._lock = threading.Lock()

    def wait(self):
        with self._lock:
            now = time.time()
            while self._timestamps and self._timestamps[0] < now - 60:
                self._timestamps.popleft()
            if len(self._timestamps) >= self._max:
                sleep_time = 60 - (now - self._timestamps[0])
                if sleep_time > 0:
                    time.sleep(sleep_time)
                return self.wait()
            self._timestamps.append(time.time())

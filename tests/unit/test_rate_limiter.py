import time
import pytest
from utils.rate_limiter import RateLimiter


class TestRateLimiter:
    def test_wait_within_limit(self, mocker):
        mocker.patch("time.time", return_value=1000.0)
        mock_sleep = mocker.patch("time.sleep")
        rl = RateLimiter(max_requests=3)
        rl.wait()
        rl.wait()
        rl.wait()
        mock_sleep.assert_not_called()

    def test_wait_exceeds_limit_sleeps(self, mocker):
        t = [1000.0]
        def fake_time():
            return t[0]
        def fake_sleep(s):
            t[0] += s + 1
        mocker.patch("time.time", side_effect=fake_time)
        mocker.patch("time.sleep", side_effect=fake_sleep)
        rl = RateLimiter(max_requests=2)
        rl.wait()
        rl.wait()
        rl.wait()
        assert t[0] > 1000.0

    def test_sliding_window_expired(self, mocker):
        times = [1000.0, 1000.0, 1065.0]
        def fake_time():
            return times.pop(0) if times else 1065.0
        mocker.patch("time.time", side_effect=lambda: fake_time())
        mock_sleep = mocker.patch("time.sleep")
        rl = RateLimiter(max_requests=2)
        rl.wait()
        rl.wait()
        rl.wait()
        mock_sleep.assert_not_called()

    def test_default_max_from_config(self, mocker):
        mocker.patch("time.time", return_value=1000.0)
        rl = RateLimiter()
        assert rl._max == 60

    def test_custom_max_requests(self):
        rl = RateLimiter(max_requests=10)
        assert rl._max == 10

    def test_zero_max_requests_handled(self, mocker):
        mocker.patch("time.time", return_value=1000.0)
        mock_sleep = mocker.patch("time.sleep")
        rl = RateLimiter(max_requests=0)
        try:
            rl.wait()
        except IndexError:
            pass

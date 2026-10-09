"""
Custom throttles (rate limiting) for sensitive endpoints.

Currently only the login endpoint uses a dedicated, strict throttle.
The global anon/user rates are set in settings.REST_FRAMEWORK.
"""
from rest_framework.throttling import AnonRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """5 attempts/minute per IP for login attempts."""
    scope = "login"

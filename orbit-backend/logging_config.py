import logging
import os

_configured = False


def configure_logging() -> logging.Logger:
    """
    Call once at startup. Bootstrap-time warnings (missing secret key,
    missing CORS config) still use plain print() so they're impossible to
    miss even before logging is configured — everything else (failed
    logins, lockouts, revocations, rate limit hits, email failures) goes
    through this logger so it can be redirected to a file or an
    observability tool later without touching call sites.
    """
    global _configured
    logger = logging.getLogger("orbit")
    if _configured:
        return logger

    level = os.environ.get("ORBIT_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
    )
    logger.setLevel(level)
    _configured = True
    return logger


logger = configure_logging()

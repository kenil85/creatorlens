import time
import re
import hashlib
from collections import defaultdict
from fastapi import Request, HTTPException
from app.core.config import get_settings

# ── Token bucket rate limiter ─────────────────────────────────────────────────
class TokenBucketLimiter:
    """
    Per-IP token bucket rate limiter.
    Each IP gets `capacity` tokens; 1 token consumed per request.
    Tokens refill at `refill_rate` per second.
    """
    def __init__(self, capacity: int = 10, refill_rate: float = 1.0):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._buckets: dict[str, dict] = defaultdict(
            lambda: {"tokens": capacity, "last_refill": time.monotonic()}
        )

    def _refill(self, bucket: dict):
        now = time.monotonic()
        elapsed = now - bucket["last_refill"]
        bucket["tokens"] = min(
            self.capacity,
            bucket["tokens"] + elapsed * self.refill_rate
        )
        bucket["last_refill"] = now

    def consume(self, ip: str) -> tuple[bool, float]:
        bucket = self._buckets[ip]
        self._refill(bucket)
        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            return True, bucket["tokens"]
        wait = (1 - bucket["tokens"]) / self.refill_rate
        return False, wait


_limiter = TokenBucketLimiter(
    capacity=get_settings().rate_limit_per_minute,
    refill_rate=get_settings().rate_limit_per_minute / 60.0,
)


async def rate_limit(request: Request):
    ip = request.client.host if request.client else "unknown"
    allowed, info = _limiter.consume(ip)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={"error": "rate_limited", "retry_after_seconds": round(info, 2)},
        )


# ── Prompt injection defense ──────────────────────────────────────────────────
INJECTION_PATTERNS = [
    r"ignore\s+(previous|all|above|prior)\s+instructions?",
    r"disregard\s+(previous|all|above|prior)",
    r"you\s+are\s+now",
    r"act\s+as\s+(if\s+you\s+are|a\s+)",
    r"jailbreak",
    r"system\s+prompt",
    r"forget\s+(everything|instructions?|all)",
    r"new\s+instructions?:",
    r"override\s+(previous|safety|all)",
    r"do\s+anything\s+now",
    r"dan\s+mode",
    r"developer\s+mode",
    r"<\s*script",
    r"eval\s*\(",
    r"exec\s*\(",
]

_INJECTION_RE = re.compile(
    "|".join(INJECTION_PATTERNS),
    re.IGNORECASE,
)


def detect_injection(text: str) -> tuple[bool, str | None]:
    """Returns (is_injection, matched_pattern)"""
    match = _INJECTION_RE.search(text)
    if match:
        return True, match.group(0)
    return False, None


def sanitize_input(text: str, max_length: int = 2000) -> str:
    """Remove dangerous characters and truncate."""
    text = text[:max_length]
    # Strip null bytes and control characters
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # Strip HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


# ── URL validation ────────────────────────────────────────────────────────────
ALLOWED_VIDEO_HOSTS = {
    "youtube.com", "www.youtube.com", "youtu.be",
    "m.youtube.com", "music.youtube.com",
    "vimeo.com", "www.vimeo.com",
}

def validate_video_url(url: str) -> bool:
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        return (
            parsed.scheme in {"http", "https"}
            and parsed.netloc in ALLOWED_VIDEO_HOSTS
        )
    except Exception:
        return False


# ── Request fingerprinting ────────────────────────────────────────────────────
def fingerprint_request(request: Request) -> str:
    parts = [
        request.client.host if request.client else "",
        request.headers.get("user-agent", ""),
    ]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]

"""审批链接：带签名，防止别人伪造。

注意：签名只能证明「链接是系统发出的」，不能证明「点击的人是你」。
正式使用请把审批网页放在 HTTPS 和公司统一登录之后。
"""

import hashlib
import hmac
from urllib.parse import urlencode

from weekly_agent import config


def sign(thread: str) -> str:
    secret = config.env("APPROVAL_SECRET")
    if not secret:
        raise KeyError("APPROVAL_SECRET")
    return hmac.new(secret.encode(), thread.encode(), hashlib.sha256).hexdigest()[:32]


def verify(thread: str, sig: str) -> bool:
    return hmac.compare_digest(sign(thread), sig or "")


def review_url(thread: str) -> str:
    base = config.env("APPROVAL_BASE_URL", "http://localhost:8000").rstrip("/")
    return f"{base}/review?" + urlencode({"thread": thread, "sig": sign(thread)})

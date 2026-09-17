"""Tiny helpers reused by the newsletter router without circular imports."""
import secrets
import string


def gen_code(prefix: str = "", length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    body = "".join(secrets.choice(alphabet) for _ in range(length))
    return f"{prefix}{body}" if not prefix else f"{prefix}-{body}"

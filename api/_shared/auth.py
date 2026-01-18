"""Authentication middleware for Vercel serverless functions."""

from .config import AUTH_PASSWORD, ALLOWED_EMAILS


def check_auth(password: str, email: str) -> tuple[bool, str]:
    """
    Check if the provided credentials are valid.

    Requires BOTH:
    - Password matches AUTH_PASSWORD env var
    - Email is in ALLOWED_EMAILS env var list

    Args:
        password: The password to check
        email: The email to check

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not AUTH_PASSWORD:
        return False, "Server auth not configured"

    if not password:
        return False, "Password required"

    if password != AUTH_PASSWORD:
        return False, "Invalid password"

    if not email:
        return False, "Email required"

    email_lower = email.strip().lower()
    if email_lower not in ALLOWED_EMAILS:
        return False, "Email not authorized"

    return True, ""


def get_auth_from_headers(headers: dict) -> tuple[str, str]:
    """
    Extract auth credentials from request headers.

    Args:
        headers: Request headers dict

    Returns:
        Tuple of (password, email)
    """
    password = headers.get("x-auth-password", "") or headers.get("X-Auth-Password", "")
    email = headers.get("x-auth-email", "") or headers.get("X-Auth-Email", "")
    return password, email

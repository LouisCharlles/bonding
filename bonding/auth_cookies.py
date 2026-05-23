from django.conf import settings


def _cookie_common(*, max_age: int, httponly: bool = True):
    return {
        "max_age": max_age,
        "secure": settings.AUTH_COOKIE_SECURE,
        "httponly": httponly,
        "samesite": settings.AUTH_COOKIE_SAMESITE,
        "domain": settings.AUTH_COOKIE_DOMAIN or None,
    }


def set_access_cookie(response, access_token: str) -> None:
    response.set_cookie(
        settings.AUTH_ACCESS_COOKIE_NAME,
        access_token,
        path="/",
        **_cookie_common(max_age=settings.AUTH_ACCESS_COOKIE_MAX_AGE),
    )


def set_refresh_cookie(response, refresh_token: str) -> None:
    response.set_cookie(
        settings.AUTH_REFRESH_COOKIE_NAME,
        refresh_token,
        path=settings.AUTH_REFRESH_COOKIE_PATH,
        **_cookie_common(max_age=settings.AUTH_REFRESH_COOKIE_MAX_AGE),
    )


def clear_auth_cookies(response) -> None:
    response.delete_cookie(
        settings.AUTH_ACCESS_COOKIE_NAME,
        path="/",
        domain=settings.AUTH_COOKIE_DOMAIN or None,
        samesite=settings.AUTH_COOKIE_SAMESITE,
    )
    response.delete_cookie(
        settings.AUTH_REFRESH_COOKIE_NAME,
        path=settings.AUTH_REFRESH_COOKIE_PATH,
        domain=settings.AUTH_COOKIE_DOMAIN or None,
        samesite=settings.AUTH_COOKIE_SAMESITE,
    )

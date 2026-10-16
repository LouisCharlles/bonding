from django.conf import settings


def _samesite(cross_site: bool) -> str:
    # SameSite=None exige Secure — sem HTTPS (dev local) o navegador recusaria
    # o cookie, entao cai no SameSite configurado.
    if cross_site and settings.AUTH_COOKIE_SECURE:
        return "None"
    return settings.AUTH_COOKIE_SAMESITE


def _cookie_common(*, max_age: int, httponly: bool = True, cross_site: bool = False):
    return {
        "max_age": max_age,
        "secure": settings.AUTH_COOKIE_SECURE,
        "httponly": httponly,
        "samesite": _samesite(cross_site),
        "domain": settings.AUTH_COOKIE_DOMAIN or None,
    }


def set_access_cookie(response, access_token: str, *, cross_site: bool = False) -> None:
    response.set_cookie(
        settings.AUTH_ACCESS_COOKIE_NAME,
        access_token,
        path="/",
        **_cookie_common(max_age=settings.AUTH_ACCESS_COOKIE_MAX_AGE, cross_site=cross_site),
    )


def set_refresh_cookie(response, refresh_token: str, *, cross_site: bool = False) -> None:
    """cross_site=True (usuario aceitou cookies de terceiros no login) usa
    SameSite=None para o cookie seguir no refresh quando frontend e backend
    estao em sites diferentes (ex.: vercel.app -> onrender.com), mantendo a
    sessao apos recarregar a pagina."""
    response.set_cookie(
        settings.AUTH_REFRESH_COOKIE_NAME,
        refresh_token,
        path=settings.AUTH_REFRESH_COOKIE_PATH,
        **_cookie_common(max_age=settings.AUTH_REFRESH_COOKIE_MAX_AGE, cross_site=cross_site),
    )


def clear_auth_cookies(response) -> None:
    # Remove com SameSite=None (quando ha HTTPS) para que a remocao tambem
    # funcione em resposta cross-site, cobrindo cookies criados com qualquer
    # uma das duas opcoes.
    samesite = _samesite(cross_site=True)
    response.delete_cookie(
        settings.AUTH_ACCESS_COOKIE_NAME,
        path="/",
        domain=settings.AUTH_COOKIE_DOMAIN or None,
        samesite=samesite,
    )
    response.delete_cookie(
        settings.AUTH_REFRESH_COOKIE_NAME,
        path=settings.AUTH_REFRESH_COOKIE_PATH,
        domain=settings.AUTH_COOKIE_DOMAIN or None,
        samesite=samesite,
    )

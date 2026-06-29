"""URL and metadata-key safety helpers for acquisition handoffs."""

from __future__ import annotations

from urllib.parse import SplitResult, parse_qsl, urlencode, urlsplit, urlunsplit


PUBLIC_URL_SCHEMES = {"http", "https", "magnet"}
SENSITIVE_KEY_MARKERS = (
    "api_key",
    "apikey",
    "auth_key",
    "authkey",
    "authheader",
    "authorization",
    "bearer",
    "credential",
    "csrf",
    "cookie",
    "jwt",
    "pass_key",
    "passkey",
    "password",
    "private_key",
    "privatekey",
    "rss_key",
    "rsskey",
    "secret",
    "sessioncookie",
    "sid",
    "token",
)


def looks_sensitive_key(key: str) -> bool:
    normalized = key.replace("-", "_").casefold()
    return any(marker in normalized for marker in SENSITIVE_KEY_MARKERS)


def is_public_url(parsed: SplitResult) -> bool:
    return parsed.scheme in PUBLIC_URL_SCHEMES


def split_url(value: str) -> SplitResult:
    return urlsplit(value)


def url_has_credentials(parsed: SplitResult) -> bool:
    return bool(parsed.username or parsed.password)


def sensitive_url_query_keys(parsed: SplitResult) -> tuple[str, ...]:
    if not is_public_url(parsed):
        return ()
    return tuple(
        key
        for key, _ in parse_qsl(parsed.query, keep_blank_values=True)
        if looks_sensitive_key(key)
    )


def sensitive_url_fragment_keys(parsed: SplitResult) -> tuple[str, ...]:
    if not is_public_url(parsed) or "=" not in parsed.fragment:
        return ()
    return tuple(
        key
        for key, _ in parse_qsl(parsed.fragment, keep_blank_values=True)
        if looks_sensitive_key(key)
    )


def strip_sensitive_url_parts(value: str) -> str:
    try:
        parsed = split_url(value)
    except ValueError:
        return value
    if not is_public_url(parsed):
        return value
    netloc = parsed.netloc.rsplit("@", 1)[-1] if "@" in parsed.netloc else parsed.netloc
    fragment = _strip_sensitive_url_fragment(parsed.fragment)
    if not parsed.query:
        if netloc == parsed.netloc and fragment == parsed.fragment:
            return value
        return urlunsplit(
            (
                parsed.scheme,
                netloc,
                parsed.path,
                parsed.query,
                fragment,
            )
        )
    query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
    public_pairs = [
        (key, item_value)
        for key, item_value in query_pairs
        if not looks_sensitive_key(key)
    ]
    if len(public_pairs) == len(query_pairs) and netloc == parsed.netloc and fragment == parsed.fragment:
        return value
    return urlunsplit(
        (
            parsed.scheme,
            netloc,
            parsed.path,
            urlencode(public_pairs, doseq=True),
            fragment,
        )
    )


def _strip_sensitive_url_fragment(fragment: str) -> str:
    if not fragment or "=" not in fragment:
        return fragment
    fragment_pairs = parse_qsl(fragment, keep_blank_values=True)
    public_pairs = [
        (key, item_value)
        for key, item_value in fragment_pairs
        if not looks_sensitive_key(key)
    ]
    if len(public_pairs) == len(fragment_pairs):
        return fragment
    return urlencode(public_pairs, doseq=True)

"""The provider documents of Ilta-Pulu: manifest.json, sites.json, rules.json and data.json.

The shapes follow Paatti's provider resolver (src/provider.js) and docs/providers.md.

The documents name the address of the request, not the address in the settings, so the provider works when a
browser reaches the server by any host: a container name, or the address of another machine. The site's origin
has no port, so it matches the server on any port.
"""

from urllib.parse import urlsplit

from fastapi import Request

from .layout import site_rules
from .pool import rahti_entry, updated_at

SCHEMA_VERSION = "0.1.0"
CAPTURE_REL = "x-paatti-dev-capture"


def request_origin(request: Request) -> str:
    """The scheme and authority that the client used, e.g. "http://172.17.0.2:3000"."""
    return str(request.base_url).rstrip("/")


def request_netloc(request: Request) -> str:
    """The host and port that the client used, in lowercase: a Host header is case-insensitive, and Suola
    matches a rule's domain against this."""
    return urlsplit(request_origin(request)).netloc.lower()


def links(origin: str) -> list[dict]:
    """The manifest links. The capture link has no `title`: the options page shows a titled link of an unknown rel."""
    return [
        {"rel": "privacy-policy", "href": f"{origin}/privacy", "title": "Ilta-Pulu privacy notice"},
        {"rel": CAPTURE_REL, "href": f"{origin}/api/capture"},
    ]


def manifest(settings, origin: str) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "name": "Ilta-Pulu (dev server)",
        "updated": updated_at(settings.pool_seed),
        "links": links(origin),
        "resources": [
            {"type": "suola-rules", "href": "rules.json", "description": "Signs Ilta-Pulu article links"},
            {"type": "site-configs", "href": "sites.json"},
            {"type": "rahti-data", "href": "data.json"},
            {"type": "x-paatti-dev", "href": "ignored.json",
             "description": "An unknown resource type, which Paatti must ignore and not fetch"},
        ],
    }


def sites(settings, origin: str) -> dict:
    """The site document, keyed and scoped by the host of `origin`."""
    parsed = urlsplit(origin)
    # A URL writes an IPv6 literal with brackets, and the site key and its origin pattern must use that spelling.
    host = f"[{parsed.hostname}]" if ":" in parsed.hostname else parsed.hostname
    rules = [{"description": rule["description"], "container": rule["container"], "link": rule["link"],
              "title": rule["title"]} for _, rule in site_rules(settings.features.blocks)]
    return {
        "schema_version": SCHEMA_VERSION,
        "sites": {
            host: {
                "name": "Ilta-Pulu",
                "description": "The fake news site of the Paatti development server",
                "enabled": True,
                "origins": [f"{parsed.scheme}://{host}/*"],
                "links": [{"rel": "x-publisher-policy", "href": f"{origin}/privacy",
                           "title": "Ilta-Pulu publishing policy"}],
                "rules": rules,
            }
        },
    }


def rules_tests(state, origin: str) -> list[dict]:
    """Suola `tests` for the rules: a few articles in two href variants, and an id of the wrong length."""
    tests = []
    for article in state.pool[:3]:
        url = f"{origin}{article.path}"
        tests += [
            {"url": url, "signature": state.signs[article.id]},
            {"url": f"{url}/?utm_source=x", "signature": state.signs[article.id]},
        ]
    tests.append({"url": f"{origin}/news/a/0123", "xfail": True})
    return tests


def data(state) -> dict:
    updated = updated_at(state.settings.pool_seed)
    return {
        "status": "ok",
        "updated": updated,
        "schema_version": SCHEMA_VERSION,
        "entries": [rahti_entry(article, state.signs[article.id], updated)
                    for article in state.pool if article.has_entry],
    }


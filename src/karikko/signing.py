"""URL signatures, made by the same Suola rules that the extension uses.

The extension signs a link to a host that a provider supplies with the provider's named rule set: the provider's
rules before the base rules, so that a provider rule wins against a base rule with the same domain and weight
(`defineRules` in suola/docs/api.md). `append_rules()` puts the rules after the base rules, so `Signer` builds the
same sequence from the packaged `base_rules.yaml` instead. The base rules and the wheel have the same suola tag
(pyproject.toml), so the copy follows the signed suola version. Suola compares a rule's domain with
`host:port`, so the Ilta-Pulu document carries the port of the request.

The base rules carry the named rules of the published sites. Suola signs only a host that a rule matches, so a
provider that must sign any host adds a catch-all (`domain: ""`) rule: the captured-sites provider has one, and
Ilta-Pulu has none, because it serves only its own site.

An instance is safe to share between threads, which FastAPI needs because it runs `def` endpoints in a thread pool.
"""

import functools
import json
import tempfile
from pathlib import Path

import yaml
from suola import InvalidURLError, Suola

BASE_RULES = Path(__file__).parent / "base_rules.yaml"

ARTICLE_PATTERN = r"^/(?P<Section>[A-Za-z]+)/a/(?P<ArticleID>[0-9a-f]{12})"
ARTICLE_TEMPLATE = "http://localhost/{{ .Section }}/a/{{ .ArticleID }}"


def ilta_pulu_rules(netloc: str, tests: list[dict] | None = None) -> dict:
    """The Suola rules of Ilta-Pulu for a server at `netloc` (`localhost:3000`, or `localhost` on port 80).

    `netloc` is only the domain that the rule matches. The template normalizes an article to a fixed URL, so a
    request at any address signs to the same value. The pool therefore signs once, at startup.
    """
    return {
        "sites": [{
            "domain": netloc,
            "templates": [{
                "pattern": ARTICLE_PATTERN,
                "template": ARTICLE_TEMPLATE,
                "transform": {"Section": "lowercase"},
            }],
            "tests": tests or [],
        }]
    }


@functools.cache
def base_sites() -> list[dict]:
    """The sites of the base rules, without the test cases, which Suola does not use."""
    sites = yaml.safe_load(BASE_RULES.read_text())["sites"]
    return [{key: value for key, value in site.items() if key != "tests"} for site in sites]


class Signer:
    """One Suola instance: the base rules, or a rule set before the base rules, or a rule set alone.

    Raises `suola.InvalidRulesError` when Suola refuses the rule set.
    """

    def __init__(self, rules: dict | None = None, over_base: bool = True):
        if rules is None:
            self._suola = Suola()
            return
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rules.json"
            path.write_text(json.dumps({"sites": rules["sites"] + (base_sites() if over_base else [])}))
            self._suola = Suola(custom_rules=path)

    def sign(self, url: str) -> str | None:
        """The signature of `url`, or None when Suola cannot sign it, for example because it has no host."""
        try:
            return self._suola(url)
        except InvalidURLError:
            return None

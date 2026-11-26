"""Secrets in untrusted text: known token formats, credentials, and how to redact them.

Every pattern uses bounded quantifiers and every input is cut to MAX_VALUE characters first,
so matching stays linear on adversarial input. Custom token formats from a config file are
structured (prefix, charset, length) and compiled to one fixed shape, never taken as regexes.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from .limits import MAX_VALUE

# Known token formats. The left boundary keeps words such as "task-management-..." from
# matching, and the bounded quantifiers keep matching linear on adversarial input.
BOUNDARY = r"(?<![A-Za-z0-9_\-])"
TOKENS = (r"sk-(?:ant|proj|svcacct|admin|ak)-[A-Za-z0-9_\-]{20,400}|sk-[A-Za-z0-9]{40,400}|"  # sk-ak-: Zapier MCP
          r"gh[pousr]_[A-Za-z0-9]{30,400}|github_pat_[A-Za-z0-9_]{40,400}|xox[abprs]-[A-Za-z0-9\-]{10,400}|"
          r"AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|glpat-[A-Za-z0-9_\-]{20,400}|AIza[0-9A-Za-z_\-]{35}|"
          r"(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{20,400}|npm_[A-Za-z0-9]{36}|pypi-[A-Za-z0-9_\-]{50,400}|hf_[A-Za-z0-9]{30,400}|"
          r"ntn_[A-Za-z0-9]{40,400}|secret_[A-Za-z0-9]{43}(?![A-Za-z0-9])|"  # Notion integration tokens, new and old
          r"eyJ[A-Za-z0-9_\-]{10,800}\.eyJ[A-Za-z0-9_\-]{10,2000}\.[A-Za-z0-9_\-]{10,800}|"
          r"https://hooks\.slack\.com/services/T[A-Z0-9]{6,20}/B[A-Z0-9]{6,20}/[A-Za-z0-9]{20,64}|"  # Slack webhook
          # A PEM private key with its key material (raw, or with \\n escapes inside a JSON string)
          r"-----BEGIN [A-Z ]{0,40}PRIVATE KEY-----(?:[\sA-Za-z0-9+/=]|\\n){20,4000}|"
          # A Google Cloud service-account key file, inline: its type, then a private_key with a value
          r"\\?\"type\\?\"[ \t]{0,20}:[ \t]{0,20}\\?\"service_account\\?\""
          r"(?=[\s\S]{0,4000}?private_key\\?\"[ \t]{0,20}:[ \t]{0,20}\\?\"[^\"\\<$]{20})")
TOKEN_PREFIX_WORD = re.compile(r"^[A-Za-z]{1,40}[-_]")  # `ghp_`, `sk-`: left out when judging a token's variety
RUNS = re.compile(r"[A-Za-z0-9+=]{16,}")  # runs of letters and digits that opaque() inspects
TEST_KEY = re.compile(r"(?:sk|rk)_test_")  # a Stripe test key: still a secret, but say so
# A credential header value, alone or with its header name (`Authorization: Bearer ...`,
# `X-Api-Key: ...`), as written in an env value, a header or a --header argument.
CREDENTIAL = r"[A-Za-z0-9._~+/\-]{20,2000}=*"
KEY_HEADER = r"(?:X-)?(?:Api-?Key|Auth-?Token|Access-?Token)"
BEARER = re.compile(rf"^(?:(?:Proxy-)?Authorization[ \t]*:[ \t]*)?(?:Bearer|Basic|token)[ \t]+{CREDENTIAL}$|"
                    rf"^{KEY_HEADER}[ \t]*:[ \t]*(?:Bearer[ \t]+)?{CREDENTIAL}$", re.I)
BEARER_ANYWHERE = re.compile(rf"\b((?:Bearer|Basic)[ \t]+|{KEY_HEADER}[ \t]*:[ \t]*){CREDENTIAL}", re.I)
# A name that says its value is a credential (--api-key, BRAVE_API_KEY, X-API-Key, ?token=,
# PGPASSWORD), judged by its words: one word is a secret word, or ends with a long one
# (`apikey`, `authtoken`, `pgpassword`), and no word says the value is public (PUBLIC_KEY,
# STRIPE_PUBLISHABLE_KEY). A name whose last word says the value is something else (TOKEN_FILE,
# AUTH_URL, KEY_ID, PRIMARY_KEY_COLUMN) is not a credential. The value must look like one: 16 or
# more characters mixing letters and digits, or, under a password-like name (passw, password,
# pass, pwd, passphrase, secret), any 8 or more printable characters; never a reference to a
# secret kept elsewhere (${VAR}, $VAR, %VAR%, {{...}}, env:..., op://...), a URL or a file path.
NAME_WORD = re.compile(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+")  # `DB_SECRET_ARN`, `tokenFile`: words of a name
SECRET_WORDS = frozenset(("key", "keys", "pass", "pwd", "auth", "authorization", "cred", "creds", "passw"))
SECRET_ENDINGS = ("token", "tokens", "secret", "secrets", "password", "passwords", "passwd", "passphrase",
                  "credential", "credentials", "apikey", "accesskey", "privatekey", "secretkey", "authkey", "oauth")
PASSWORD_PARTS = ("pass", "pwd")         # a password-like name: a word holding one of these (pgpassword),
PASSWORD_ENDINGS = ("secret", "secrets")  # or ending with one of these
PUBLIC_WORDS = frozenset(("public", "publishable"))
NOT_SECRET_NAME = frozenset((
    "path", "file", "dir", "url", "uri", "host", "endpoint", "name", "id", "mode", "type", "region", "version",
    "format", "prefix", "scheme", "header", "length", "size", "count", "ttl", "expiry", "expires", "arn", "alias",
    "domain", "fingerprint", "server", "issuer", "audience", "realm", "algorithm", "column", "layout", "schema",
    "strategy", "method"))  # last word of a name, lowercased
SECRET_VALUE = re.compile(r"^(?=[^/.~$%])(?=[^\s]{0,2000}?\d)(?=[^\s]{0,2000}?[A-Za-z])[A-Za-z0-9_\-+/=.:]{16,2000}$")
PASSWORD_VALUE = re.compile(r"^(?=[^$%])[!-~][ -~]{6,2000}[!-~]$")  # 8+ printable ASCII characters, no edge spaces
REFERENCE = re.compile(r"^(?:env|secret|secrets|op|vault|file|keychain|ref|arn)[:.]|\$\{|\{\{|%[A-Za-z_]\w{0,60}%|://", re.I)
FILE_PATH = re.compile(r"^[\w.\-]{0,200}(?:/[\w.\-]{1,200}){1,20}\.[A-Za-z]{1,6}$")
FLAG_ASSIGN = re.compile(r"(?<![\w-])(--?[A-Za-z][\w-]{0,60})=([^\s\"',]{8,2000})")
# `NAME=value`: an environment assignment (`-e API_TOKEN=...`) or a URL query parameter (`?api_key=...`).
NAME_ASSIGN = re.compile(r"(?<![\w.\-])([A-Za-z_][\w.\-]{0,60})=([^\s\"',&#;]{8,2000})")
PLACEHOLDER = re.compile(r"your[-_ ]|example|placeholder|change[-_ ]?me|replace[-_ ]?me|dummy|insert|[-_]here\b|todo|"
                         r"xxx|<[^<>]{0,200}>|\$\{|\{\{|\*{6,}|0{12,}", re.I)
# Values that point at a secret kept elsewhere or at a place, not a credential: an absolute
# path (`/workspace/project1`, `~/x`, `C:\\x`) or a GCP Secret Manager name.
NOT_A_CREDENTIAL = re.compile(r"^(?:/|~/|[A-Za-z]:\\)|^projects/[^/\s]{1,200}/secrets/")
NOT_SECRET_NAMES = frozenset(("pwd", "oldpwd"))  # the shell's working directories
LIST_WORDS = frozenset(("through", "list", "names", "vars"))  # PASS_THROUGH_ENV, SECRET_NAMES: names, not values
# A path segment of a URL that is a credential (`https://mcp.zapier.com/api/mcp/s/<token>/mcp`):
# 32 or more base64url characters; commit and digest SHAs (40 or 64 hex) are not.
URL_SEGMENT = re.compile(r"^[A-Za-z0-9_-]{32,400}$")
HEX_SHA = re.compile(r"^(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})$")

# The user-info part of a URL (`https://user:password@host`). Shown as <redacted> everywhere;
# a password in it is a literal credential. Bounded, so matching stays linear.
# Passwords in URLs that are documentation, not credentials (`postgresql://user:password@localhost`).
URL_PASSWORD_PLACEHOLDERS = frozenset(("password", "passwd", "pass", "pwd", "secret", "changeme", "example",
                                       "your-password", "your_password", "yourpassword"))
URL_USERINFO = re.compile(r"\b([A-Za-z][A-Za-z0-9+.\-]{0,30}://)([^/\s@:?#]{0,256})(?::([^/\s@?#]{1,256}))?@")

# Character classes a configured token may use. Config never supplies a regex.
CHARSETS = {"alnum": "A-Za-z0-9", "alnum-dash": "A-Za-z0-9_\\-", "hex": "0-9a-fA-F", "base64": "A-Za-z0-9+/=_\\-"}
TOKEN_PREFIX = re.compile(r"^[A-Za-z0-9_\-.]{2,40}$")


@dataclass(frozen=True)
class TokenSpec:
    """A custom token format: a literal prefix followed by min..max characters of one charset."""
    name: str
    prefix: str
    charset: str
    min: int
    max: int

    def pattern(self) -> str:
        """The fixed, linear-time shape every custom token compiles to."""
        return f"{re.escape(self.prefix)}[{CHARSETS[self.charset]}]{{{self.min},{self.max}}}"


class Secrets:
    """Finds and redacts secrets: the built-in token formats plus any configured TokenSpecs."""

    def __init__(self, extra: tuple[TokenSpec, ...] = ()):
        alternatives = "|".join([TOKENS] + [t.pattern() for t in extra])
        self.any = re.compile(f"{BOUNDARY}(?:{alternatives})")

    def redact(self, s: str) -> str:
        s = URL_USERINFO.sub(r"\1<redacted>@", s)
        s = BEARER_ANYWHERE.sub(r"\1<redacted>", s)
        for rx in (FLAG_ASSIGN, NAME_ASSIGN):
            s = rx.sub(lambda m: f"{m.group(1)}=<redacted>" if named_secret(m.group(1), m.group(2)) else m.group(0), s)
        return self.any.sub("<redacted>", s)

    def secret_in(self, v) -> bool:
        """Whether a value holds a literal credential: a known token format or a bearer
        credential (not an obvious placeholder), a secret-named `--flag=value`, `NAME=value` or
        URL query parameter, or a URL password. Every rule that looks for secrets asks this."""
        v = str(v)[:MAX_VALUE]
        return self.known_format(v) or url_password(v) or any(
            named_secret(m.group(1), m.group(2)) for rx in (FLAG_ASSIGN, NAME_ASSIGN) for m in rx.finditer(v))

    def secret_pair(self, name, value) -> bool:
        """secret_in for a named value (an env var, a header, a setting): also true when the name
        says it is a credential and the value looks like one (`"BRAVE_API_KEY": "BSA..."`)."""
        return self.secret_in(value) or named_secret(name, value)

    def secret_in_command(self, args) -> bool:
        """secret_in for a command line: any argument, or the value after a secret-named flag
        written as two arguments (`--token VALUE`)."""
        args = [str(a)[:MAX_VALUE] for a in args]
        return any(self.secret_in(a) for a in args) or any(
            a.startswith("-") and "=" not in a and named_secret(a, b) for a, b in zip(args, args[1:]))

    def known_format(self, v) -> bool:
        """A known token format or a bearer credential, alone or inside a longer value (a headers
        JSON string, `Authorization=Bearer ...`, a curl command), excluding obvious placeholders."""
        v = str(v)[:MAX_VALUE]
        found = (self.any.search(v), BEARER.search(v), *BEARER_ANYWHERE.finditer(v))
        return any(m and not placeholder_token(m.group(0)) for m in found)


DEFAULT = Secrets()


def placeholder_token(token: str) -> bool:
    """A matched token or credential that is an obvious placeholder (`Bearer YOUR_TOKEN_HERE...`,
    `sk-xxxxxxxx...`): a placeholder word, or a body of at most two distinct characters."""
    body = TOKEN_PREFIX_WORD.sub("", token.split()[-1])
    return bool(PLACEHOLDER.search(token)) or len(set(body)) <= 2


def name_words(name) -> list[str]:
    return [w.lower() for w in NAME_WORD.findall(str(name)[:100])]


def secret_name(name) -> bool:
    """A name that says its value is a credential (see NAME_WORD): `API_KEY`, `authToken`,
    `--client-secret`, `MYSQL_PASS`, `PGPASSWORD`; not `PUBLIC_KEY` or `KEYBOARD_LAYOUT`."""
    words = name_words(name)
    return not PUBLIC_WORDS.intersection(words) and any(
        w in SECRET_WORDS or w.endswith(SECRET_ENDINGS) for w in words)


def not_secret_name(name: str) -> bool:
    """A secret-sounding name whose last word says the value is something else: TOKEN_FILE,
    AUTH_URL, KEY_ID, DB_SECRET_ARN, AUTH0_DOMAIN, ENCRYPTION_KEY_ALIAS, PRIMARY_KEY_COLUMN."""
    words = name_words(name)
    return bool(words) and words[-1] in NOT_SECRET_NAME


def named_secret(name, value) -> bool:
    """The one judgement of a (name, value) pair, for flags (--api-key VALUE), env vars, headers,
    query parameters and `NAME=value`: a secret name and a value that looks like a credential (any
    8+ printable characters under a password-like name), not a placeholder, a reference to a
    secret kept elsewhere, a URL or a file path."""
    name, value = str(name)[:100].strip("-_ "), str(value)[:MAX_VALUE]
    if not secret_name(name) or not_secret_name(name) or name.lower() in NOT_SECRET_NAMES \
            or LIST_WORDS.intersection(name_words(name)):
        return False
    password = any(w.endswith(PASSWORD_ENDINGS) or any(p in w for p in PASSWORD_PARTS) for w in name_words(name))
    return bool((PASSWORD_VALUE if password else SECRET_VALUE).match(value) and not PLACEHOLDER.search(value)
                and not REFERENCE.search(value) and not FILE_PATH.match(value) and not NOT_A_CREDENTIAL.search(value))


def secret_kind(v) -> str:
    """A note for secrets that are real but lower risk: Stripe test keys."""
    return " (a test key)" if TEST_KEY.search(str(v)[:MAX_VALUE]) else ""


def opaque(s: str) -> bool:
    """Looks like a credential rather than a package name: a run of 16 or more letters and
    digits (no word separators) with at least three digits and some letters."""
    return any(sum(c.isdigit() for c in run) >= 3 and any(c.isalpha() for c in run)
               for run in RUNS.findall(s[:MAX_VALUE]))


def random_token(s: str) -> bool:
    """Looks generated rather than named: 16 or more letters and digits with no separator,
    mixing upper case, lower case and a digit (`Zq9fPqLmZtRvWbNcHdJsKkXyTn`)."""
    s = s[:MAX_VALUE]
    return len(s) >= 16 and s.isascii() and s.isalnum() and not s.isdigit() and any(c.isdigit() for c in s) \
        and any(c.isupper() for c in s) and any(c.islower() for c in s)


def url_path_secret(url) -> bool:
    """Whether a URL's path holds a credential segment (see URL_SEGMENT): 32 or more base64url
    characters that look generated (random_token, separators aside), not a hex SHA."""
    try:
        path = urlsplit(str(url)[:MAX_VALUE].strip()).path
    except ValueError:
        return False
    return any(URL_SEGMENT.match(seg) and not HEX_SHA.match(seg) and random_token(seg.replace("-", "").replace("_", ""))
               for seg in path.split("/"))


def url_password(v) -> bool:
    """Whether a string holds a URL with a literal password (`scheme://user:password@host`)."""
    for m in URL_USERINFO.finditer(str(v)[:MAX_VALUE]):
        password = m.group(3)
        if password and not PLACEHOLDER.search(password) and not password.startswith("$") \
                and password.lower() not in URL_PASSWORD_PLACEHOLDERS:
            return True
    return False


def redact_command(args, secrets: Secrets = DEFAULT) -> list[str]:
    """A command line that is safe to keep (the host map stores it): an argument that holds or
    looks like a credential becomes <redacted>, and so does the value after a secret-named flag
    (`--token VALUE`, whatever VALUE looks like); `KEY=value` with a secret-named key keeps its key."""
    out, hide = [], False
    for a in map(str, args):
        key, eq, _ = a.partition("=")
        if hide:
            out.append("<redacted>")
        elif eq and secret_name(key):
            out.append(key + "=<redacted>")
        elif secrets.secret_in(a) or (opaque(a) and not a.startswith(("-", "/", ".", "@"))):
            out.append("<redacted>")
        else:
            out.append(secrets.redact(a))
        hide = not hide and not eq and a.startswith("-") and secret_name(a)
    return out

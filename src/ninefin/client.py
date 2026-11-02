"""9fin's APIs, and their stand-in.

9fin (9fin.com; its public API documentation at console.9fin.com, one
OpenAPI file per API) answers `GET` requests at `https://api.9fin.com` with
JSON. The plugin asks two of its APIs, and nothing else:

- Instruments (Bonds & Loans) 0.10.1:
  `/v0/instruments/bonds-and-loans?<field>__in=...` -- the instruments whose
  Rule 144A, Regulation S or other ISIN is one the deployment lists, and
  `/v0/instruments/bonds-and-loans/{nf_id}`;
- Entity 0.5.7: `/v0/entity/{nf_id}` -- an issuer, its SEC CIK among its
  identifiers.

**The credential.** 9fin's APIs take an OAuth2 bearer token from the client
credentials grant: a client ID and secret made in 9fin's developer portal,
the plugin's two secret settings, exchanged at the token address 9fin's
OpenAPI files name (`https://api.9fin.com/oauth/token`, HTTP Basic) for a
token of about an hour, asked again before it lapses. 9fin's authentication
guide names another token address (`authkit.9fin.com`); which is current is
asked of 9fin. Neither secret, nor the token, is ever in an answer, a log,
an error or a page.

**Pacing is the plugin's** (ruling 1028). 9fin publishes 1,000 requests a
minute and 10,000 an hour for Instruments and Entity; the plugin asks one
request at a time, at most five a second, and waits out a 429 a minute,
reading `X-RateLimit-Remaining-minute` and `-hour` for the Connection page.

`SyntheticNineFin` answers from the answers committed under sample/, made
in the shape of 9fin's public documentation's field examples, so the
plugin's tests and sample data run offline, the same on any day.
"""

from __future__ import annotations

import asyncio
import base64
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from importlib import resources
from typing import Any, Protocol

BASE = "https://api.9fin.com"
TOKEN_URL = "https://api.9fin.com/oauth/token"
INSTRUMENTS = "/v0/instruments/bonds-and-loans"
ENTITY = "/v0/entity"
USER_AGENT = "meridian-9fin (+https://github.com/open-meridian/plugin-9fin)"
TIMEOUT = 60.0
MOST_BYTES = 32 * 1024 * 1024
SPACING = 0.2
RETRY_SECONDS = 60.0
#: A token is asked again this long before it lapses, in seconds.
EARLY = 120.0


class Unreachable(Exception):  # noqa: N818 - what 9fin was
    """9fin could not be asked: no answer, or not in time."""


class NoCredential(Exception):  # noqa: N818 - what the plugin lacks
    """No client ID and secret are set, so 9fin is not asked."""


@dataclass(frozen=True)
class Fetched:
    path: str
    status: int
    body: str
    fetched_at: datetime

    @property
    def ok(self) -> bool:
        return self.status == 200

    @property
    def error(self) -> str:
        if self.status == 401:
            return "9fin refused the client's credentials"
        if self.status == 403:
            return f"{self.path}: the client is not entitled to this API"
        try:
            said = json.loads(self.body)
        except ValueError:
            said = None
        if isinstance(said, dict) and said.get("message"):
            return f"{self.path} answered {self.status}: {str(said['message'])[:200]}"
        return f"{self.path} answered {self.status}"


class NineFin(Protocol):
    mode: str
    calls: int
    rate_limited: int
    failed: str
    last_call_at: str
    remaining: str

    def today(self, now: datetime) -> date: ...

    async def get(self, path: str) -> Fetched: ...


def utc_now() -> datetime:
    return datetime.now(UTC)


def redacted(text: str, *secrets: str) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***")
    return text


def _request(
    url: str, headers: dict[str, str], data: bytes | None = None
) -> tuple[int, bytes, dict[str, str]]:
    request = urllib.request.Request(url, data=data, headers=headers,
                                     method="POST" if data is not None else "GET")  # fmt: skip
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as answer:  # noqa: S310 - 9fin's https address
            raw = answer.read(MOST_BYTES + 1)
            return answer.status, raw, {k.lower(): v for k, v in answer.headers.items()}
    except urllib.error.HTTPError as refused:
        raw = refused.read(MOST_BYTES + 1) if refused.fp else b""
        return refused.code, raw, {k.lower(): v for k, v in (refused.headers or {}).items()}
    except (urllib.error.URLError, TimeoutError, OSError) as failed:
        reason = getattr(failed, "reason", failed)
        raise Unreachable(
            f"{urllib.parse.urlsplit(url).netloc}: {type(reason).__name__}"
        ) from failed


@dataclass
class LiveNineFin:
    """9fin itself, asked with the client's credentials (see the module)."""

    client_id: str = field(repr=False)
    client_secret: str = field(repr=False)
    now: Callable[[], datetime] = utc_now
    mode: str = "live"
    calls: int = 0
    rate_limited: int = 0
    failed: str = ""
    last_call_at: str = ""
    remaining: str = ""
    _token: str = field(default="", repr=False)
    _token_until: float = 0.0
    _last: float = 0.0
    _not_before: float = 0.0
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def today(self, now: datetime) -> date:
        return now.date()

    def _secrets(self) -> tuple[str, ...]:
        return (self.client_id, self.client_secret, self._token)

    def _new_token(self) -> str:
        basic = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        status, raw, _ = _request(
            TOKEN_URL,
            {"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded",
             "Accept": "application/json", "User-Agent": USER_AGENT},
            urllib.parse.urlencode({"grant_type": "client_credentials"}).encode(),
        )  # fmt: skip
        if status != 200:
            raise PermissionError(f"9fin's token address answered {status}")
        said = json.loads(raw)
        self._token = str(said.get("access_token", ""))
        self._token_until = time.monotonic() + float(said.get("expires_in", 3600)) - EARLY
        return self._token

    def _get(self, path: str) -> Fetched:
        try:
            token = self._token if time.monotonic() < self._token_until else self._new_token()
        except PermissionError as refused:
            return Fetched(path, 401, json.dumps({"message": str(refused)}), self.now())
        status, raw, headers = _request(
            BASE + path, {"Authorization": f"Bearer {token}", "Accept": "application/json",
                          "User-Agent": USER_AGENT})  # fmt: skip
        if status == 401:
            self._token_until = 0.0
        if len(raw) > MOST_BYTES:
            raise Unreachable(f"{BASE}{path}: answered more than {MOST_BYTES} bytes")
        minute = headers.get("x-ratelimit-remaining-minute", "")
        hour = headers.get("x-ratelimit-remaining-hour", "")
        if minute or hour:
            self.remaining = f"{minute or '?'} this minute, {hour or '?'} this hour"
        text = redacted(raw.decode("utf-8", errors="replace"), *self._secrets())
        return Fetched(path, status, text, self.now())

    async def get(self, path: str) -> Fetched:
        if not (self.client_id and self.client_secret):
            raise NoCredential("no 9fin client ID and secret are set")
        async with self._lock:
            wait = max(self._last + SPACING, self._not_before) - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
            self.calls += 1
            self.last_call_at = self.now().isoformat(timespec="seconds")
            try:
                got = await asyncio.to_thread(self._get, path)
            except Unreachable as failed:
                self.failed = str(failed)
                raise
            finally:
                self._last = time.monotonic()
        if got.status == 429:
            self.rate_limited += 1
            self._not_before = time.monotonic() + RETRY_SECONDS
        self.failed = "" if got.ok else got.error
        return got


class SyntheticNineFin:
    """The answers committed under sample/ (sample/answers.json): an
    instrument by its 9fin ID, or those whose ISINs a list names; an entity
    by its 9fin ID; anything else 9fin's 404."""

    mode = "synthetic"
    remaining = ""

    def __init__(self, now: Callable[[], datetime] = utc_now) -> None:
        self._now = now
        held = resources.files(__package__).joinpath("sample")
        recorded = json.loads(held.joinpath("answers.json").read_text(encoding="utf-8"))
        self.today_is = date.fromisoformat(recorded["today"])
        self.instruments: dict[str, dict[str, Any]] = recorded["instruments"]
        self.entities: dict[str, dict[str, Any]] = recorded["entities"]
        self.asked: list[str] = []
        self.calls = 0
        self.rate_limited = 0
        self.failed = ""
        self.last_call_at = ""

    def today(self, now: datetime) -> date:
        return self.today_is

    def _answer(self, path: str) -> tuple[int, Any]:
        route, _, query = path.partition("?")
        if route == INSTRUMENTS:
            asked = dict(urllib.parse.parse_qsl(query))
            items = []
            for name, value in asked.items():
                if name.endswith("__in"):
                    wanted = set(value.split(","))
                    field_name = name.removesuffix("__in")
                    items += [i for i in self.instruments.values() if i.get(field_name) in wanted]
            return 200, {"items": items, "next_cursor": None}
        if route.startswith(INSTRUMENTS + "/"):
            found = self.instruments.get(route.rsplit("/", 1)[1])
            return (200, found) if found else (404, {"message": "Not found"})
        if route.startswith(ENTITY + "/"):
            found = self.entities.get(route.rsplit("/", 1)[1].lower())
            return (200, found) if found else (404, {"message": "Not found"})
        return 404, {"message": "Not found"}

    async def get(self, path: str) -> Fetched:
        self.calls += 1
        self.last_call_at = self._now().isoformat(timespec="seconds")
        self.asked.append(path)
        status, said = self._answer(path)
        return Fetched(path, status, json.dumps(said), self._now())


def ninefin(
    synthetic: bool, client_id: str, client_secret: str, now: Callable[[], datetime] = utc_now
) -> NineFin:
    if synthetic:
        return SyntheticNineFin(now)
    return LiveNineFin(client_id, client_secret, now)

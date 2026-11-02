"""9fin's APIs as the plugin asks them: the client's credentials, a token,
a 429, and the stand-in's answers."""

from __future__ import annotations

import asyncio
import json

import pytest

from ninefin import client
from ninefin.client import LiveNineFin, NoCredential

from conftest import AT, NOTE_144A, source


def test_no_credential_asks_nothing() -> None:
    with pytest.raises(NoCredential):
        asyncio.run(LiveNineFin("", "").get(client.INSTRUMENTS))


def test_the_token_is_asked_once_and_never_kept_in_an_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    live = LiveNineFin("id-1", "secret-1", lambda: AT)
    asked: list[str] = []

    def request(url: str, headers: dict[str, str], data: bytes | None = None):  # type: ignore[no-untyped-def]
        asked.append(url)
        if url == client.TOKEN_URL:
            assert headers["Authorization"].startswith("Basic ")
            return 200, json.dumps({"access_token": "tok-1", "expires_in": 3600}).encode(), {}
        assert headers["Authorization"] == "Bearer tok-1"
        body = json.dumps({"items": [], "echo": "tok-1 secret-1"}).encode()
        return 200, body, {"x-ratelimit-remaining-minute": "999"}

    monkeypatch.setattr(client, "_request", request)
    first = asyncio.run(live.get(client.INSTRUMENTS))
    asyncio.run(live.get(client.INSTRUMENTS))
    assert asked.count(client.TOKEN_URL) == 1
    assert "tok-1" not in first.body and "secret-1" not in first.body
    assert live.remaining.startswith("999")


def test_a_refused_client_is_said(monkeypatch: pytest.MonkeyPatch) -> None:
    live = LiveNineFin("id", "secret", lambda: AT)
    monkeypatch.setattr(client, "_request", lambda url, headers, data=None: (401, b"{}", {}))
    got = asyncio.run(live.get(client.INSTRUMENTS))
    assert got.status == 401 and live.failed == "9fin refused the client's credentials"


def test_the_stand_in_answers_a_list_by_isin() -> None:
    got = asyncio.run(source().get(f"{client.INSTRUMENTS}?reg_144a_isin__in={NOTE_144A}&limit=200"))
    assert json.loads(got.body)["items"][0]["reg_144a_isin"] == NOTE_144A

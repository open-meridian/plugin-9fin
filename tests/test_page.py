"""The two pages under Manage, and their read tools."""

from __future__ import annotations

import asyncio

import pytest
from meridian.suites import Recorder
from meridian.testing import PageClient

from ninefin.page import figures, hold, pages

from conftest import APPLE, holding, lake


@pytest.fixture
def client() -> PageClient:
    recorder = Recorder("ninefin")
    holding(recorder)
    work = lake(recorder)
    asyncio.run(work.check())
    hold(work)
    return PageClient(pages, recorder.plugin, roles=("data", "reference"))


def test_each_page_is_managed_alone(client: PageClient) -> None:
    served = {(r.page.path, r.level): r.response.status for r in client.every_page()}
    assert {level: status for (_, level), status in served.items()} == {
        "admin": 200, "write": 403, "read": 403,
    }  # fmt: skip
    client.assert_no_account_data("99.812", "99.5", "98.75")


def test_connection_lists_the_bonds_and_what_is_not_recorded(client: PageClient) -> None:
    text = client.get("/", "admin").text
    assert "4 of 5 resolved" in text and APPLE in text and "a loan: no template" in text
    assert '<th scope="row">Not recorded</th>' in text and "Price talk" in text


def test_the_tools_answer_what_the_pages_show(client: PageClient) -> None:
    connection = client.call_tool("read_connection").data
    assert [c["label"] for c in connection["credentials"]] == ["9fin client ID",
                                                               "9fin client secret"]  # fmt: skip
    assert len(connection["securities"]) == 5
    datasets = client.call_tool("read_datasets").data
    assert [s["dataset"] for s in datasets["served"]] == ["ninefin:new_issue_prices"]


def test_the_figures_are_the_role_s() -> None:
    labels = [f.label for f in figures(lake(Recorder("ninefin")))]
    assert labels[:2] == ["Connection", "Entitled at the vendor"]

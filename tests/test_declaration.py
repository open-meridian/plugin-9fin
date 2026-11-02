"""The catalogue and settings, from code, as the deployment approves them."""

from __future__ import annotations

from ninefin.declaration import DECLARATION
from ninefin.settings import config_from


def test_one_dataset_of_new_issue_prices() -> None:
    [prices] = DECLARATION.catalogue
    assert prices.key == "new_issue_prices" and prices.vendor == "9fin"
    assert list(prices.data_types) == ["meridian.v1.Price"]
    assert prices.price_source_class == "traded"
    assert prices.licence_default is None


def test_the_securities_are_isins() -> None:
    rows = [{"security": "us30161naa17"}, {"security": "037833ER7"}]
    config = config_from({"client_id": " a ", "client_secret": "b", "securities": rows})
    assert (config.client_id, config.client_secret) == ("a", "b")
    assert config.securities == ("US30161NAA17",)

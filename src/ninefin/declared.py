"""What this version declares beside its roles: its catalogue (W10.1).

**One dataset** (its name proposed in the pull request):
`new_issue_prices`, each listed bond's issue (reoffer) price, a `Price` of
kind `last` per 100 of face dated its pricing date (prices.py; 910, 965),
the dataset's class `traded` (906); pushed by the daily check and pulled on
a want; its day UTC.

**Not declared, so not presented** until the contract has their kinds (the
content wave, 944): 9fin's covenants, distressed situations, private
credit, CLOs, BDCs, asset-based finance and news (910); and its loans until
a loan template exists (964). Its price talk is free text, not recorded
(prices.py). **Terms** are the deployment's to settle with 9fin (rulings
1030 to 1032): no default licence is declared; docs/terms.md describes 9fin's
published terms in plain words.
"""

from __future__ import annotations

from meridian import DatasetDeclaration

from .prices import KEY

VENDOR = "9fin"

NEW_ISSUE_PRICES = DatasetDeclaration(
    key=KEY,
    vendor=VENDOR,
    data_types=["meridian.v1.Price"],
    modes=["push", "pull"],
    cadence=86_400,
    day_time_zone="Etc/UTC",
    price_source_class="traded",
)

CATALOGUE = [NEW_ISSUE_PRICES]

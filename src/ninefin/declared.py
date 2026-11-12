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
1030 to 1032): the dataset describes 9fin's published terms in plain words
(`terms_and_pricing`, contract 30), as docs/terms.md does, never a licence.
**A gap** is recovered by `backfill` (`gap_recovery`): 9fin serves each
bond's issue price again, so the lake asks again through its want.
"""

from __future__ import annotations

from meridian import DatasetDeclaration

from .prices import KEY

VENDOR = "9fin"
#: 9fin's published terms in plain words (contract 30, ruling 1032), as read
#: on 30 October 2026: docs/terms.md, shortened.
TERMS = (
    "9fin's data comes from its own analysts and journalists (ratings at issuance are the "
    "rating agencies'), under your agreement or order form with 9fin. Its published terms "
    "of service (v1.0, effective 12 May 2026) grant a non-exclusive, non-transferable, "
    "personal licence for authorised users at an authorised team, location or site; small "
    "portions for internal use; no dissemination to third parties without 9fin's consent, "
    "except 9fin data clearly marked as 9fin's in client materials; no derivative works "
    "beyond that and no AI model training; automated access limited to what a person could "
    "reasonably make unless an API order form sets the API's limits; trials for internal "
    "evaluation only, their data deleted within 30 days. Pricing is not published."
)

NEW_ISSUE_PRICES = DatasetDeclaration(
    key=KEY,
    vendor=VENDOR,
    data_types=["meridian.v1.Price"],
    modes=["push", "pull"],
    cadence=86_400,
    day_time_zone="Etc/UTC",
    price_source_class="traded",
    terms_and_pricing=TERMS,
    gap_recovery="backfill",
)

CATALOGUE = [NEW_ISSUE_PRICES]

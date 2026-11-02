"""9fin's new-issue prices, as the lake's prices (rulings 910, 965).

**The issue (reoffer) price** is a `Price` of kind `last`, its basis
`percent_of_par`, in the bond's currency, dated its pricing date (9fin's
`price_date`): the price at which the deal's primary allocations print, as
TRACE marks them primary market (965). 9fin states no reoffer yield or
spread, so none is beside it. Its key names the tranche's ISIN, so a
correction of 9fin's is the same row's next version. The dataset's class is
`traded` (906): the price a new issue traded at.

**Price talk is not recorded.** 965 records each stage of talk (initial
price thoughts, guidance, launch) as a `mid` at the range's midpoint; 9fin
states talk as free text (`price_talk`) that may cover several tranches of
a deal and may be truncated, naming no stage, so a stage read from it would
be a guess. Not presented, asked of 9fin.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

import meridian
from meridian.plugin.v1 import operations_pb2 as ops

from . import read

KEY = "new_issue_prices"


def _ns(day: date) -> int:
    return int(datetime(day.year, day.month, day.day, tzinfo=UTC).timestamp()) * 1_000_000_000


def issue_price(
    item: dict[str, Any], isin: str, subject: str, dataset: str, raw: ops.RawRecordRef
) -> meridian.Price | None:
    """A tranche's issue price, or None where 9fin states no price, date or
    currency for it."""
    price = read.number(item.get("issue_price"))
    priced = read.day(item.get("price_date"))
    currency = read.text(item.get("currency_ref_code"))
    if price is None or priced is None or not currency:
        return None
    meta = meridian.ObservationMeta(
        row_key=f"9fin:issue:{isin}",
        subjects=[meridian.SubjectRef(entity_id=subject)],
        source=ops.Source(dataset=dataset),
        valid_from_ns=_ns(priced),
        valid_until_ns=_ns(priced + timedelta(days=1)),
        business_date=priced,
        raw=raw,
    )
    return meridian.Price(
        meta=meta, kind="last", price=meridian.Money(price, currency_code=currency),
        basis="percent_of_par",
    )  # fmt: skip

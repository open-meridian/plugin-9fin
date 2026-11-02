"""The data role's work on the sample: issue prices, loans said, wants."""

from __future__ import annotations

import asyncio
from decimal import Decimal

from meridian.operations import as_decimal
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.suites import Recorder

from conftest import APPLE, LISTED, LOAN, holding, lake, want


def test_the_check_records_each_bond_s_issue_price_and_no_loan() -> None:
    recorder = Recorder("ninefin")
    holding(recorder)
    work = lake(recorder)
    asyncio.run(work.check())
    [sent] = recorder.on("RecordPrices")
    assert len(sent.prices) == 4
    apple = next(p for p in sent.prices if p.meta.row_key == f"9fin:issue:{APPLE}")
    assert apple.kind == ops.PRICE_KIND_LAST and apple.basis == ops.PRICE_BASIS_PERCENT_OF_PAR
    assert as_decimal(apple.price.amount) == Decimal("99.812000000")
    assert apple.meta.business_date == "2026-02-02"
    assert work.status.securities[LOAN]["record"] == "a loan: no template in v29"
    assert len(recorder.on("OfferTemplateFields")) == 4
    # Read once a day.
    asyncio.run(work.check())
    assert len(recorder.on("RecordPrices")) == 1
    assert sorted(work.records) == sorted(i for i in LISTED if i != LOAN)


def test_a_want_for_another_date_is_source_silent() -> None:
    recorder = Recorder("ninefin")
    holding(recorder)
    work = lake(recorder, securities=(APPLE,))
    asyncio.run(work.check())
    record = work.records[APPLE]
    asyncio.run(work.on_observations_wanted(want("w-1", "new_issue_prices", [record],
                                                 day="2026-10-28")))  # fmt: skip
    [declined] = recorder.on("DeclineWant")
    assert declined.reason == ops.UNANSWERED_REASON_SOURCE_SILENT


def test_an_unknown_issuer_is_said_and_asked_again() -> None:
    import meridian

    recorder = Recorder("ninefin")
    holding(recorder)

    def refuse(_: object) -> ops.ResolveCompanyResult:
        raise meridian.MeridianError("ResolveCompany: identifiers: pending the platform's review")

    recorder.answer("ResolveCompany", refuse)
    work = lake(recorder, securities=(APPLE,))
    asyncio.run(work.check())
    assert work.status.securities[APPLE]["issuer"] == "CIK not resolved yet"

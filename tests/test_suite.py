"""The data suite and the reference suite (meridian.suites, contract v29),
each case 9fin presents mapped to the plugin's own conversion of the sample
answers, each it never presents named with why.

**Data, presented:** an exact price, a want recorded against and a subject
another source resolved (a bond's issue price, kind `last`); an asset that
does not resolve; a subject declined; a standing want withdrawn; its
datasets' licences; and the cases the SDK answers. **Not presented:** a
close and a forming day (9fin states issue prices, never a close), a
venue's price (a new issue has none), a feed delay (9fin states no
publication time), and every kind it never publishes.

**Reference, presented:** a template filled, a licensed vendor's value kept
as an offer, a person's value never offered over, the record read first, a
security resolved by its identifiers; not presented, calendars and
settlement dates.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from meridian.plugin.v1 import operations_pb2 as ops
from meridian.suites import ANSWERED_BY_SDK, Recorder, run, suite

from conftest import APPLE, holding, lake, want

Producer = Callable[[Recorder], Awaitable[None]]

NEVER_KINDS = {
    "closes": "9fin states a new issue's price, never a close",
    "bars": "9fin states no bars",
    "a currency's rate against another currency": "9fin states no currency's rate",
    "a crypto asset's price": "9fin states no crypto asset",
    "prices on a venue": "a new issue's price is no venue's",
    "trades": "9fin states no trades",
    "quotes": "9fin states no quotes",
    "outcomes": "9fin states no event contract",
    "disputed outcomes": "9fin states no event contract",
    "rates": "9fin states no rates",
    "option chains": "9fin states no option",
    "filings": "9fin's documents have no lake kind yet (the content wave)",
    "holdings": "9fin's BDC holdings have no lake kind yet (the content wave)",
    "corporate actions": "9fin states no corporate action this plugin records",
    "ratings": "ratings at issuance are a rating agency's, not recorded from 9fin",
    "derived series": "it publishes no figure of its own",
    "factors": "9fin states no pool's or class's factor",
    "streams": "9fin is asked daily; it streams nothing",
    "publication times": "9fin states no publication time for an issue price",
    "calendars": "it records what 9fin states; it reads no calendar",
    "settlement dates": "it records what 9fin states; it asks no settlement date",
}
PRESENTED = {"an-exact-price", "a-want-recorded-against"}
NOT_PRESENTED = {
    case.name: NEVER_KINDS[case.about]
    for role in ("data", "reference")
    for case in suite(role).cases
    if case.about in NEVER_KINDS and case.name not in ANSWERED_BY_SDK and case.name not in PRESENTED
}


async def checked(recorder: Recorder) -> None:
    holding(recorder)
    await lake(recorder, securities=(APPLE,)).check()


async def wanted(recorder: Recorder) -> None:
    holding(recorder)
    work = lake(recorder, securities=(APPLE,))
    await work.check()
    record = work.records[APPLE]
    heard = want("w-1", "new_issue_prices", [record], day="2026-02-02")
    recorder.answer("ObservationsWanted", lambda _: heard.message)
    await recorder.hear(work, "ObservationsWanted")


async def elsewhere(recorder: Recorder) -> None:
    recorder.answer("ResolveInstrument", lambda p: ops.ResolveInstrumentResult(
        found=True, instrument=ops.InstrumentRecord(instrument_id=p.instrument_id, identifiers=[
            ops.Identifier(scheme="cusip", value="037833ER7"),
            ops.Identifier(scheme="symbol", value="AAPL36", source="custodian")])))  # fmt: skip
    work = lake(recorder, securities=())
    heard = want("w-1", "new_issue_prices", ["LCL-CUSTODIAN"])
    recorder.answer("ObservationsWanted", lambda _: heard.message)
    await recorder.hear(work, "ObservationsWanted")


async def ambiguous(recorder: Recorder) -> None:
    recorder.answer("ResolveIdentifier", lambda _: ops.ResolveIdentifierResult(
        found=False, miss_reason=ops.MISS_REASON_AMBIGUOUS))  # fmt: skip
    await lake(recorder, securities=(APPLE,)).check()


async def declined(recorder: Recorder) -> None:
    recorder.answer("ResolveInstrument", lambda _: ops.ResolveInstrumentResult(found=False))
    work = lake(recorder, securities=())
    recorder.answer("ObservationsWanted",
                    lambda _: want("w-1", "new_issue_prices", ["not-a-bond"]).message)  # fmt: skip
    await recorder.hear(work, "ObservationsWanted")


async def withdrawn(recorder: Recorder) -> None:
    work = lake(recorder, securities=())
    recorder.answer("WantWithdrawn", lambda _: ops.WantWithdrawnEvent(
        want_id="w-1", dataset="ninefin:new_issue_prices"))  # fmt: skip
    await recorder.hear(work, "WantWithdrawn")


async def licences(recorder: Recorder) -> None:
    await lake(recorder, securities=()).wants.read_licences()


def filled(person_set: tuple[str, ...] = ()) -> Producer:
    async def produce(recorder: Recorder) -> None:
        holding(recorder, person_set=person_set)
        await lake(recorder, securities=(APPLE,)).check()

    return produce


DATA: dict[str, Producer] = {
    "an-exact-price": checked,
    "a-want-recorded-against": wanted,
    "a-subject-another-source-resolved": elsewhere,
    "an-asset-that-does-not-resolve": ambiguous,
    "a-subject-declined": declined,
    "a-standing-want-withdrawn": withdrawn,
    "reads-its-datasets-licences": licences,
}
REFERENCE: dict[str, Producer] = {
    "fills-a-template": filled(),
    "licensed-vendor-value-stays": filled(),
    "offers-never-overwrite-a-person": filled(("description",)),
    "reads-the-record-it-fills": filled(),
    "resolves-a-security-it-reconciles": filled(),
}


def test_the_data_suite_passes() -> None:
    data_never = {
        k: v for k, v in NOT_PRESENTED.items() if k in {c.name for c in suite("data").cases}
    }
    report = run("data", DATA, not_presented=data_never, instance_id="ninefin")
    assert report.passed, report.failures
    assert set(report.passed_cases) == set(DATA) | set(ANSWERED_BY_SDK)


def test_the_reference_suite_passes() -> None:
    names = {c.name for c in suite("reference").cases}
    never = {k: v for k, v in NOT_PRESENTED.items() if k in names}
    report = run("reference", REFERENCE, not_presented=never, instance_id="ninefin")
    assert report.passed, report.failures
    assert set(report.passed_cases) == set(REFERENCE) | set(ANSWERED_BY_SDK)

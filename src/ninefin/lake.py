"""The plugin's `data` role class: 9fin's new-issue prices into the lake,
and the bonds a deployment lists resolved -- their issuers by CIK -- and
handed to the `reference` role class for their terms.

**What it reads, and when** (`check`, at start and daily, or at once when
the settings change): the listed bonds, by ISIN, from 9fin's Instruments
API (by each tranche's ISIN, a hundred at a time), and each one's issuer
from its Entity API. Each bond is resolved with what 9fin states of it, its
issuer's CIK resolved to the `ENT-` company record (W3.32), its terms
offered by the reference role (terms.py), and its issue price recorded
(`new_issue_prices`, prices.py). A loan has no template in v29 (964): it is
said, and nothing of it is recorded or offered.

**What the lake wants** (`on_observations_wanted`): a bond's price --
answered with its issue price, recorded against the want, where the want
asks for its pricing date or none; a date with no issue price is declined
`source_silent`; a subject 9fin does not cover `not_covered`.

It mints nothing: what the deployment does not hold is a miss.
"""

from __future__ import annotations

import logging
import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

import meridian
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.roles import data

from . import prices, read
from .client import ENTITY, INSTRUMENTS, NineFin, NoCredential, Unreachable, ninefin
from .terms import Reference, Terms, terms

log = logging.getLogger("ninefin")

KEYS = (prices.KEY,)
SOURCE = "9fin"
#: How many ISINs one list request names.
BATCH = 100
ISIN_FIELDS = ("reg_144a_isin", "reg_s_isin", "other_isin")


@dataclass
class Status:
    checked_at: str = ""
    last_error: str = ""
    securities: dict[str, dict[str, str]] = field(default_factory=dict)
    unread: dict[str, int] = field(default_factory=dict)
    refused: dict[str, str] = field(default_factory=dict)

    def said(self, what: str) -> None:
        self.unread[what] = self.unread.get(what, 0) + 1


class Lake(data.Role):
    """The data role's class (see the module)."""

    def __init__(
        self,
        source: NineFin | None = None,
        reference: Reference | None = None,
        *,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        super().__init__()
        self.source: NineFin = source or ninefin(False, "", "")
        self.reference = reference or Reference()
        self.now = now
        self.wants = data.Wants(self, KEYS, clock_ns=self.clock_ns)
        self.securities: tuple[str, ...] = ()
        self.has_credential = False
        self.status = Status()
        #: Each bond held, by its record: its ISIN; and each ISIN's record.
        self.held: dict[str, str] = {}
        self.records: dict[str, str] = {}
        #: Each issuer read, by its 9fin ID: its name and CIK.
        self.entities: dict[str, tuple[str, str]] = {}
        self.daily: tuple[date, tuple[str, ...]] | None = None

    def clock_ns(self) -> int:
        return int(self.now().timestamp() * 1e9)

    def use(self, source: NineFin, securities: tuple[str, ...], has_credential: bool) -> None:
        self.source = source
        self.securities = securities
        self.has_credential = has_credential

    def today(self) -> date:
        return self.source.today(self.now())

    def raw(self, key: str) -> ops.RawRecordRef:
        held: ops.RawRecordRef = self.plugin.raw_record(key[:256])
        return held

    async def ask(self, path: str) -> dict[str, Any] | None:
        try:
            got = await self.source.get(path)
        except NoCredential:
            return None
        except Unreachable as failed:
            self.status.last_error = str(failed)
            return None
        if not got.ok:
            if got.status != 404:
                self.status.last_error = got.error
            return None
        return read.parse(got.body)

    # ── 9fin ─────────────────────────────────────────────────────────────

    async def instruments(self, isins: list[str]) -> dict[str, dict[str, Any]]:
        """The instruments whose tranches the ISINs name, by ISIN."""
        found: dict[str, dict[str, Any]] = {}
        wanted = {i.upper() for i in isins}
        for start in range(0, len(isins), BATCH):
            asked = ",".join(isins[start : start + BATCH])
            for name in ISIN_FIELDS:
                query = urllib.parse.urlencode({f"{name}__in": asked, "limit": 200})
                answer = await self.ask(f"{INSTRUMENTS}?{query}")
                for item in (answer or {}).get("items") or []:
                    isin = read.text(item.get(name)).upper() if isinstance(item, dict) else ""
                    if isin in wanted:
                        found[isin] = item
        return found

    async def entity(self, nf_id: str) -> tuple[str, str]:
        """An issuer's name and CIK, read once."""
        if not nf_id:
            return "", ""
        if nf_id not in self.entities:
            answer = await self.ask(f"{ENTITY}/{urllib.parse.quote(nf_id, safe='')}") or {}
            name = read.text(answer.get("full_name")) or read.text(answer.get("short_name"))
            self.entities[nf_id] = (name, read.cik(answer.get("cik")))
        return self.entities[nf_id]

    # ── Records ──────────────────────────────────────────────────────────

    async def issuer(self, cik: str) -> str:
        """The issuer's `ENT-` company record by its CIK; empty where the
        deployment has none yet."""
        if not cik:
            return ""
        try:
            found = await self.resolve_company(
                identifiers=[ops.Identifier(scheme="cik", value=cik)], as_of_ns=self.clock_ns()
            )
        except meridian.MeridianError as refused:
            log.info("the issuer %s is not resolved yet: %s", cik, refused)
            return ""
        return str(found.company_id)

    async def security(self, held: Terms) -> str:
        known = self.records.get(held.isin)
        if known:
            return known
        named = held.identifiers()
        found = await self.resolve_identifier(
            identifiers=named, as_of_ns=self.clock_ns(), stated_asset_class="debt",
            stated_instrument_type="bond", stated_currency=held.currency,
            stated_description=held.description,
        )  # fmt: skip
        row = self.status.securities.setdefault(held.isin, {})
        if found.found and found.instrument_id:
            self.records[held.isin] = str(found.instrument_id)
            self.held[str(found.instrument_id)] = held.isin
            return str(found.instrument_id)
        row["record"] = ops.MissReason.Name(found.miss_reason or 1)
        await self.report_missing_instrument(
            source=SOURCE, asset_class="debt", identifiers=named, as_of_ns=self.clock_ns(),
            reason=found.miss_reason or ops.MISS_REASON_NOT_FOUND,
        )  # fmt: skip
        return ""

    # ── The check ────────────────────────────────────────────────────────

    async def check(self) -> None:
        """The listed bonds read, resolved, offered and priced."""
        if not self.has_credential and self.source.mode != "synthetic":
            return
        today = self.today()
        if self.daily == (today, self.securities):
            return
        found = await self.instruments(list(self.securities))
        rows: list[meridian.Price] = []
        for isin in self.securities:
            row = self.status.securities.setdefault(isin, {})
            item = found.get(isin)
            if item is None:
                row["record"] = "not covered by 9fin"
                continue
            name, cik = await self.entity(read.text(item.get("entity_nf_id")))
            held = terms(item, isin, name)
            if held is None:
                continue
            row["description"] = held.description
            if held.loan:
                row["record"] = "a loan: no template in v29"
                self.status.said("a loan, not recorded until a loan template exists (964)")
                continue
            for said in held.unmapped:
                self.status.said(f"terms: {said}")
            subject = await self.security(held)
            if not subject:
                continue
            row["record"] = subject
            company = await self.issuer(cik)
            row["issuer"] = company or ("CIK not resolved yet" if cik else "no CIK stated")
            raw = self.raw(f"instruments/{held.nf_id}")
            offered = await self.reference.offer(subject, held, company, raw)
            row["offered"] = str(offered.offered)
            if offered.refused:
                row["refused"] = offered.refused
            price = prices.issue_price(item, isin, subject, self.wants.dataset(prices.KEY), raw)
            if price is not None:
                rows.append(price)
        try:
            await self.wants.record("prices", rows, prices.KEY)
            self.status.refused.pop("new issue prices", None)
        except meridian.MeridianError as refused:
            self.status.refused["new issue prices"] = str(refused)[:300]
        self.daily = (today, self.securities)
        self.status.checked_at = self.now().isoformat(timespec="seconds")
        log.info("checked: %d recorded in all", self.wants.counts.recorded)

    # ── Wants ────────────────────────────────────────────────────────────

    async def on_observations_wanted(
        self, heard: meridian.Heard[ops.ObservationsWantedEvent]
    ) -> None:
        await self.wants.hear(heard, self.answer)

    async def on_want_withdrawn(self, heard: meridian.Heard[ops.WantWithdrawnEvent]) -> None:
        self.wants.withdraw(heard.message.want_id)

    async def isin_for(self, subject: str) -> str:
        if subject in self.held:
            return self.held[subject]
        found = await self.resolve_instrument(instrument_id=subject, as_of_ns=self.clock_ns())
        if not found.found:
            return ""
        named: dict[str, str] = {i.scheme: i.value for i in found.instrument.identifiers}
        isin = named.get("isin", "")
        if not isin and named.get("cusip"):
            isin = _isin_of(named["cusip"])
        return isin.upper()

    async def answer(
        self,
        want: ops.ObservationsWantedEvent,
        key: str,
        subjects: list[str],
        kinds: tuple[int, ...],
    ) -> dict[str, str]:
        declined: dict[str, str] = {}
        rows: list[meridian.Price] = []
        if key != prices.KEY:
            return {s: "not_covered" for s in subjects}
        dataset = self.wants.dataset(prices.KEY)
        for s in subjects:
            isin = await self.isin_for(s)
            item = (await self.instruments([isin])).get(isin) if isin else None
            if item is None or read.text(item.get("instrument_type")) == "Loan":
                declined[s] = "not_covered"
                continue
            price = prices.issue_price(item, isin, s, dataset, self.raw(f"instruments/{isin}"))
            priced = str(price.meta.business_date) if price and price.meta else ""
            if price is None or (want.business_date and priced != want.business_date):
                declined[s] = "source_silent"
                continue
            rows.append(price)
        await self.wants.record("prices", rows, key, want.want_id)
        if want.standing:
            self.wants.stand(want, [s for s in subjects if s not in declined], kinds)
        return declined


def _isin_of(cusip: str, country: str = "US") -> str:
    """The ISIN of a CUSIP (ISO 6166), for a record another source keyed by
    its CUSIP alone."""
    cusip = cusip.strip().upper()
    if len(cusip) != 9 or not cusip.isalnum():
        return ""
    body = country + cusip
    digits = "".join(str(int(c, 36)) for c in body)
    total = 0
    for i, c in enumerate(reversed(digits)):
        n = int(c)
        if i % 2 == 0:
            n = n * 2 - 9 if n * 2 > 9 else n * 2
        total += n
    return body + str((10 - total % 10) % 10)

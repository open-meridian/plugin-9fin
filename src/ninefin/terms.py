"""9fin's instruments, as offers of a bond's template fields (the
`reference` role, W3.23; contract v29's `bond` template; rulings 909, 910,
964, 966).

**One 9fin instrument, up to three securities.** 9fin states a bond once,
with the ISIN and FIGI of its Rule 144A tranche, its Regulation S tranche,
or neither (`other_`). Each is its own security, its own record in the
deployment; the plugin offers a record the terms of the tranche the listed
ISIN names: `rule_144a` true and `reg_s` false for the 144A tranche, the
reverse for Regulation S, both false for any other.

**What 9fin states, mapped** (9fin's field, then the template's), the rest
of the bond's terms (day count, coupon frequency, call schedules) left to
the deployment's other reference sources (910):

- `currency_ref_code` currency; `instrument_type` Bond the instrument type
  `bond` -- a Loan has no template in v29 and is not offered (964);
- the entity's SEC CIK -> `issuer_company_id`, the issuer's `ENT-` company
  record it resolves to (W3.32);
- `issue_date`, `maturity` maturity date; `amount` original issue amount;
- `coupon` coupon rate and a fixed coupon type, where no `benchmark` is
  stated; a floater's coupon type floating, its coupon not offered (9fin
  states no spread or index record for it);
- `debt_security_ref_name` seniority, by CDM's three values (966): a lien
  or a secured note secured; a subordinated or junior note subordinated; a
  senior note senior; the lien's position kept in the raw record;
- the description, by a named rule: the issuer's name, the coupon and the
  maturity (`EXAMPLE CORP 5.5% 2027-01-30`), 9fin stating no name.

Offers, never decisions: a person's value is never offered over, and a
value is in force once a person accepts it (W3.10). The offer's mechanics
-- read the record and its template, offer each field the template has, its
own fields and its groups apart -- are the same as plugin-terrapin's; they
are role logic every reference plugin repeats, proposed for the SDK.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from typing import Any

import meridian
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.replacements import TemplateCatalogue
from meridian.roles import reference

from . import read

SOURCE = "9fin"
TRANCHES = (("reg_144a", True, False), ("reg_s", False, True), ("other", False, False))


@dataclass(frozen=True)
class Offer:
    path: str
    value: str
    rule: str = ""

    @property
    def top(self) -> str:
        return self.path.split(".", 1)[0].split("[", 1)[0]

    @property
    def grouped(self) -> bool:
        return self.top != self.path


@dataclass
class Terms:
    """A bond tranche's terms as 9fin states them, mapped."""

    isin: str
    figi: str
    nf_id: str
    currency: str
    description: str
    entity: str
    loan: bool = False
    offers: list[Offer] = field(default_factory=list)
    unmapped: list[str] = field(default_factory=list)

    def identifiers(self) -> list[ops.Identifier]:
        named = [ops.Identifier(scheme="isin", value=self.isin)]
        if self.isin[:2] in ("US", "CA") and len(self.isin) == 12:
            named.append(ops.Identifier(scheme="cusip", value=self.isin[2:11]))
        if self.figi:
            named.insert(0, ops.Identifier(scheme="figi", value=self.figi))
        return named


def _decimal(value: Any) -> str:
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def seniority(name: str) -> str | None:
    """CDM's DebtSeniorityEnum for 9fin's ranking (966), or None."""
    said = name.lower()
    if "unsecured" not in said and ("lien" in said or "secured" in said):
        return "SENIORITY_SECURED"
    if "subordinated" in said or "junior" in said:
        return "SENIORITY_SUBORDINATED"
    if "senior" in said:
        return "SENIORITY_SENIOR"
    return None


def tranche_of(item: dict[str, Any], isin: str) -> tuple[str, bool, bool] | None:
    """Which of the instrument's tranches an ISIN names: its prefix, and
    whether it is Rule 144A and Regulation S."""
    for prefix, is_144a, is_s in TRANCHES:
        if read.text(item.get(f"{prefix}_isin")).upper() == isin.upper():
            return prefix, is_144a, is_s
    return None


def terms(item: dict[str, Any], isin: str, issuer_name: str = "") -> Terms | None:
    """One 9fin instrument's tranche named by `isin`, as its terms; None
    where the instrument names no such tranche."""
    tranche = tranche_of(item, isin)
    if tranche is None:
        return None
    prefix, is_144a, is_s = tranche
    coupon = read.number(item.get("coupon"))
    maturity = read.day(item.get("maturity"))
    floating = bool(read.text(item.get("benchmark")))
    name = issuer_name.upper()
    parts = [name] if name else []
    if coupon is not None and not floating:
        parts.append(f"{_decimal(coupon)}%")
    elif floating:
        parts.append(f"{read.text(item.get('benchmark'))} FRN")
    if maturity is not None:
        parts.append(maturity.isoformat())
    held = Terms(
        isin=isin.upper(),
        figi=read.text(item.get(f"{prefix}_figi")),
        nf_id=read.text(item.get("nf_id")),
        currency=read.text(item.get("currency_ref_code")),
        description=" ".join(parts),
        entity=read.text(item.get("entity_nf_id")),
        loan=read.text(item.get("instrument_type")) == "Loan",
    )
    if held.loan:
        return held
    offers = held.offers
    if held.description:
        offers.append(Offer("description", held.description, "issuer, coupon and maturity"))
    if held.currency:
        offers.append(Offer("currency", held.currency))
    offers.append(Offer("instrument_type", "INSTRUMENT_TYPE_BOND", "instrument_type Bond"))
    for source, path in (("issue_date", "issue_date"), ("maturity", "maturity_date")):
        when = read.day(item.get(source))
        if when is not None:
            offers.append(Offer(path, when.isoformat()))
    if floating:
        offers.append(Offer("coupon_type", "COUPON_TYPE_FLOATING", "a benchmark stated"))
    elif coupon is not None:
        offers.append(Offer("coupon_rate", _decimal(coupon)))
        offers.append(Offer("coupon_type", "COUPON_TYPE_FIXED", "a coupon and no benchmark"))
    amount = read.number(item.get("amount"))
    if amount is not None:
        offers.append(Offer("original_issue_amount", _decimal(amount)))
    ranking = read.text(item.get("debt_security_ref_name"))
    found = seniority(ranking) if ranking else None
    if found:
        offers.append(Offer("seniority", found, f"debt_security_ref_name {ranking}"))
    elif ranking:
        held.unmapped.append(f"ranking {ranking}")
    offers.append(Offer("rule_144a", "true" if is_144a else "false", f"the {prefix} tranche"))
    offers.append(Offer("reg_s", "true" if is_s else "false", f"the {prefix} tranche"))
    return held


@dataclass(frozen=True)
class Offered:
    instrument_id: str
    isin: str
    template: str
    offered: int
    skipped: int
    refused: str = ""
    version: int = 0


def person_set(record: ops.InstrumentRecord) -> set[str]:
    """The fields a person set or accepted, by the template's paths."""
    return {
        ops.InstrumentField.Name(source.field).removeprefix("INSTRUMENT_FIELD_").lower()
        for source in record.sources
        if source.person
    }


class Reference(reference.Role):
    """The plugin's `reference` role class: reads the template catalogue on
    start, and offers a held bond's fields from 9fin's terms (`offer`)."""

    def __init__(self) -> None:
        super().__init__()
        self.catalogue = TemplateCatalogue()
        self.offered: dict[str, Offered] = {}

    async def on_start(self) -> None:
        with contextlib.suppress(meridian.MeridianError):
            await self.catalogue.load(self, asset_class="debt")

    async def offer(
        self, instrument_id: str, held: Terms, issuer_company_id: str, raw: ops.RawRecordRef
    ) -> Offered:
        found = await self.resolve_instrument(instrument_id=instrument_id)
        record = found.instrument
        if not found.found or not record.template_id:
            done = Offered(instrument_id, held.isin, "", 0, 0, "no template named on the record")
            self.offered[instrument_id] = done
            return done
        template = await self.catalogue.template(self, record.template_id, record.template_version)
        if template is None:
            done = Offered(instrument_id, held.isin, record.template_id, 0, 0,
                           "the store holds no such template")  # fmt: skip
            self.offered[instrument_id] = done
            return done
        paths = {f.path for f in template.fields}
        offers = list(held.offers)
        if issuer_company_id:
            offers.append(
                Offer("issuer_company_id", issuer_company_id, "the issuer's CIK, resolved")
            )
        taken = person_set(record)
        kept = [o for o in offers if o.top in paths and o.top not in taken]
        version, refused = record.version, ""
        for part in ([o for o in kept if not o.grouped], [o for o in kept if o.grouped]):
            if not part:
                continue
            try:
                answer = await self.offer_template_fields(
                    instrument_id=record.instrument_id,
                    template_id=template.template_id,
                    template_version=template.template_version,
                    fields=[_field(o, raw) for o in part],
                )
            except meridian.MeridianError as failed:
                refused = str(failed)[:300]
                continue
            if answer.HasField("instrument"):
                version = answer.instrument.version
        named = f"{template.template_id} v{template.template_version}"
        done = Offered(instrument_id, held.isin, named, len(kept), len(offers) - len(kept),
                       refused, version)  # fmt: skip
        self.offered[instrument_id] = done
        return done


def _field(offer: Offer, raw: ops.RawRecordRef) -> meridian.TemplateFieldValue:
    return meridian.TemplateFieldValue(
        path=offer.path,
        value=offer.value,
        provenance=meridian.Provenance(
            field=offer.path,
            kind="derived" if offer.rule else "reported",
            raw_record=raw,
            source=SOURCE,
            rule=offer.rule[:200],
        ),
    )


def by_path(offers: list[Offer]) -> dict[str, str]:
    return {o.path: o.value for o in offers}

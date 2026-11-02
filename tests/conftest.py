"""Shared stand-ins: the sample answers (src/ninefin/sample/), a fixed
clock, the deployment's records as a recorder answers them, and the lake's
wants as the sidecar delivers them."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from meridian.plugin.v1 import operations_pb2 as ops
from meridian.receive import Heard
from meridian.suites import Recorder

from ninefin.client import SyntheticNineFin
from ninefin.lake import Lake
from ninefin.terms import Reference

#: The sample's day, 30 October 2026.
AT = datetime(2026, 10, 30, 22, 0, tzinfo=UTC)
INSTANCE = "ninefin"
#: The sample's bonds: a corporate (its FIGI one the harness mints from),
#: the 144A and Regulation S tranches of a high-yield note, a floating
#: second-lien note, and a term loan.
APPLE = "US037833ER75"
NOTE_144A = "US30161NAA17"
NOTE_REG_S = "USU3016NAA43"
FLOATER = "US30161NAB99"
LOAN = "US30161NAC72"
LISTED = (APPLE, NOTE_144A, NOTE_REG_S, FLOATER, LOAN)
BOND_TEMPLATE = "TPL-bond"


def source() -> SyntheticNineFin:
    return SyntheticNineFin(lambda: AT)


def lake(recorder: Recorder, *, securities: tuple[str, ...] = LISTED, ninefin: Any = None) -> Lake:
    """The data role's class and the reference role's, bound to `recorder`
    as `meridian.run` registers them."""
    reference = recorder.bind(Reference())
    made = recorder.bind(Lake(ninefin or source(), reference, now=lambda: AT))
    made.use(made.source, securities, True)
    return made


def template(template_id: str = BOND_TEMPLATE) -> ops.SecurityTemplate:
    """The bond template's first version, as the platform publishes it."""
    fields = [
        ("identifiers", "mint"), ("description", "mint"), ("currency", "mint"),
        ("instrument_type", "mint"), ("security_type", "mint"), ("issuer_company_id", "mint"),
        ("issuer_type", "mint"), ("issue_date", "mint"), ("maturity_date", "mint"),
        ("coupon_rate", "mint"), ("coupon_type", "mint"), ("coupon_frequency", "mint"),
        ("day_count", "mint"), ("calls", "complete"), ("original_issue_amount", "optional"),
        ("seniority", "optional"), ("rule_144a", "optional"), ("reg_s", "optional"),
    ]  # fmt: skip
    return ops.SecurityTemplate(
        template_id=template_id,
        template_version="1",
        asset_class=ops.ASSET_CLASS_DEBT,
        fields=[
            ops.TemplateField(
                path=path,
                requirement=getattr(ops, f"FIELD_REQUIREMENT_{level.upper()}"),
                repeated=path == "calls",
            )
            for path, level in fields
        ],
        match_rule=["figi"],
    )


def holding(
    recorder: Recorder,
    *,
    template_id: str = BOND_TEMPLATE,
    person_set: tuple[str, ...] = (),
) -> None:
    """The deployment's records as the store answers them: a bond's
    `INS-debt-n`, read back naming its template, `person_set` the fields a
    person set; the template read at its version."""
    resolved: list[str] = []

    def resolve(params: Any) -> ops.ResolveIdentifierResult:
        own = False
        resolved.append("ref" if own else "debt")
        made = f"INS-{resolved[-1]}-{len(resolved)}"
        return ops.ResolveIdentifierResult(found=True, instrument_id=made)

    def record(params: Any) -> ops.ResolveInstrumentResult:
        if params.instrument_id.startswith("INS-ref-"):
            return ops.ResolveInstrumentResult(
                found=True,
                instrument=ops.InstrumentRecord(
                    instrument_id=params.instrument_id,
                    asset_class=ops.ASSET_CLASS_REFERENTIAL,
                    instrument_type=ops.INSTRUMENT_TYPE_RATE_CURVE,
                ),
            )
        return ops.ResolveInstrumentResult(
            found=True,
            instrument=ops.InstrumentRecord(
                instrument_id=params.instrument_id,
                asset_class=ops.ASSET_CLASS_DEBT,
                template_id=template_id,
                template_version="1",
                version=1,
                sources=[
                    ops.InstrumentValueSource(
                        field=getattr(ops, f"INSTRUMENT_FIELD_{f.upper()}"), person="person:alice"
                    )
                    for f in person_set
                ],
            ),
        )

    recorder.answer("ResolveIdentifier", resolve)
    recorder.answer("ResolveInstrument", record)
    recorder.answer(
        "ReadTemplate", lambda p: ops.ReadTemplateResult(template=template(p.template_id))
    )


def want(
    want_id: str,
    dataset: str,
    subjects: list[str],
    *,
    data_type: str = "meridian.v1.Price",
    day: str = "",
    standing: bool = False,
) -> Heard[ops.ObservationsWantedEvent]:
    return Heard(
        row="ObservationsWanted",
        message=ops.ObservationsWantedEvent(
            want_id=want_id,
            dataset=f"{INSTANCE}:{dataset}",
            data_type=data_type,
            subjects=[ops.SubjectRef(entity_id=s) for s in subjects],
            business_date=day,
            standing=standing,
        ),
    )

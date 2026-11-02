"""9fin's instruments as the bond template's fields: one instrument, a
tranche a record; the ranking as CDM's seniority; loans never offered."""

from __future__ import annotations

import asyncio
from importlib import resources

from meridian.plugin.v1 import operations_pb2 as ops
from meridian.suites import Recorder

from ninefin import read, terms

from conftest import APPLE, FLOATER, LOAN, NOTE_144A, NOTE_REG_S, holding, lake

SAMPLE = read.parse(
    resources.files("ninefin").joinpath("sample/answers.json").read_text(encoding="utf-8")
)
BY_ISIN = {
    read.text(item.get(name)): item
    for item in SAMPLE["instruments"].values()
    for name in ("reg_144a_isin", "reg_s_isin", "other_isin")
    if read.text(item.get(name))
}


def held(isin: str, issuer: str = "EXAMPLE CORP HOLDINGS") -> terms.Terms:
    made = terms.terms(BY_ISIN[isin], isin, issuer)
    assert made is not None
    return made


def test_a_registered_corporate() -> None:
    apple = held(APPLE, "APPLE INC")
    said = terms.by_path(apple.offers)
    assert apple.figi == "BBG01BOND0001"
    assert said["description"] == "APPLE INC 4.875% 2036-02-05"
    assert said["coupon_rate"] == "4.875" and said["coupon_type"] == "COUPON_TYPE_FIXED"
    assert said["maturity_date"] == "2036-02-05" and said["issue_date"] == "2026-02-05"
    assert said["original_issue_amount"] == "1500000000"
    assert said["seniority"] == "SENIORITY_SENIOR"
    assert said["rule_144a"] == "false" and said["reg_s"] == "false"
    # Terrapin stays the source for these (ruling 910).
    assert not {"day_count", "coupon_frequency", "calls"} & set(said)


def test_each_tranche_its_own_flags() -> None:
    rule_144a = terms.by_path(held(NOTE_144A).offers)
    reg_s = terms.by_path(held(NOTE_REG_S).offers)
    assert (rule_144a["rule_144a"], rule_144a["reg_s"]) == ("true", "false")
    assert (reg_s["rule_144a"], reg_s["reg_s"]) == ("false", "true")
    assert held(NOTE_144A).figi == "BBG01EXMP144" and held(NOTE_REG_S).figi == "BBG01EXMPREG"
    assert rule_144a["seniority"] == "SENIORITY_SECURED"


def test_a_floater_and_a_lien() -> None:
    floater = terms.by_path(held(FLOATER).offers)
    assert floater["coupon_type"] == "COUPON_TYPE_FLOATING" and "coupon_rate" not in floater
    assert floater["seniority"] == "SENIORITY_SECURED"  # 2nd Lien Notes (966)


def test_a_loan_is_never_offered() -> None:
    loan = held(LOAN)
    assert loan.loan and not loan.offers


def test_seniority_by_ranking() -> None:
    assert terms.seniority("Senior Unsecured Notes") == "SENIORITY_SENIOR"
    assert terms.seniority("Senior Secured Notes") == "SENIORITY_SECURED"
    assert terms.seniority("1st Lien Term Loan") == "SENIORITY_SECURED"
    assert terms.seniority("Junior Subordinated Notes") == "SENIORITY_SUBORDINATED"
    assert terms.seniority("Notes") is None


def test_the_offer_s_provenance_and_issuer() -> None:
    recorder = Recorder("ninefin")
    holding(recorder)
    asyncio.run(lake(recorder, securities=(APPLE,)).check())
    [own] = recorder.on("OfferTemplateFields")
    paths = {f.path: f for f in own.fields}
    assert paths["issuer_company_id"].value.startswith("ENT-")
    assert paths["coupon_rate"].provenance.kind == ops.PROVENANCE_KIND_REPORTED
    assert paths["coupon_rate"].provenance.source == "9fin"
    assert paths["description"].provenance.kind == ops.PROVENANCE_KIND_DERIVED
    [company] = recorder.on("ResolveCompany")
    assert [(i.scheme, i.value) for i in company.identifiers] == [("cik", "0000320193")]

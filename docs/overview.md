# Overview

## What it is

9fin (9fin.com) publishes credit intelligence through APIs: bonds and
loans, their issuers, new issues, covenants, distressed situations, CLOs,
private credit and news. This plugin reads two of them -- Instruments
(Bonds & Loans) and Entity -- with the deployment's own 9fin API client,
and holds two roles, `data` and `reference`.

## What it records and offers

- **`reference`** -- offers the terms of the bonds you list to your
  deployment's instrument records: the currency, issue and maturity dates,
  the coupon (fixed, or floating where 9fin names a benchmark), the amount
  issued, the seniority (secured, senior or subordinated, from 9fin's
  ranking), Rule 144A or Regulation S by the tranche you list, a
  description, and the issuer, its SEC CIK resolved to your company record.
  The day count, coupon frequency and call schedules come from another
  reference source.
- **`data`** -- records each listed bond's **issue (reoffer) price**, per
  100 of face, dated its pricing date (`new_issue_prices`).

An offer is never a decision: a value is used once a person accepts it at
the Instruments page, and a value a person set is never offered over.

## What it does not record

- **Price talk**: 9fin states it as free text that may cover several
  tranches and may be truncated, naming no stage; reading a stage from it
  would be a guess.
- **Loans**: there is no loan template yet; a listed loan is said, not
  offered.
- **Covenants, distressed situations, private credit, CLOs, BDCs,
  asset-based finance and news**: no kind of the lake holds them yet.
- **Ratings at issuance**: a rating agency's, not recorded from 9fin.

It never mints a record: a bond is resolved by the FIGI of its tranche
where 9fin states one, else its ISIN (and a US ISIN's CUSIP, kept on your
deployment's record and never sent).

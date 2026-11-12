# Changelog

## 0.2.0

On open-meridian 0.36.0, contract 30, on core aae501d's harness (chart
0.1.538); `meridian` 0.1.60 in the check. What the plugin records is
unchanged.

- **9fin's terms in words** (ruling 1032): the dataset's
  `terms_and_pricing` summarises 9fin's published terms of service as
  docs/terms.md does (a personal, non-transferable licence for authorised
  users, internal use, no dissemination without consent, no derivative
  works or AI training, pricing not published), shown on Data sources and
  in the Datasets page's row details. The plugin still declares no licence.
- **A gap recovered by backfill** (`gap_recovery`): 9fin serves each
  bond's issue price again on a want. No `sessions_calendar_id`: an issue
  price is dated its pricing day, in no session.
- **Row keys checked against the lake's rule 5** (ruled 2026-11-12): an
  issue price is keyed by the tranche's ISIN (`9fin:issue:<ISIN>`) and valid
  on its pricing date, so a correction of the price is the same row's next
  version; a correction of 9fin's `price_date` would restate the key under
  another valid time. A price has no cancellation, so the key is unchanged
  and the case is listed for step 3d.
- `meridian plugin migrate --to 0.36.0` moved the pins (the base by
  digest, `meridian` 0.1.60); the test of the absent licence reads the
  words instead.
- Core's runtime and harness images at `aae501d`, by digest.

## 0.1.0

The first version, on open-meridian 0.35.3 (contract v29), built from 9fin's
public API documentation (rulings 868, 909 to 911, 1059).

- `reference`: the listed bonds' terms offered to the deployment's records
  under the `bond` template -- currency, dates, coupon, amount issued,
  seniority from 9fin's ranking (CDM's three values, 966), Rule 144A or
  Regulation S by tranche, a description -- the issuer's SEC CIK resolved to
  its `ENT-` record; the day count, frequency and calls left to Terrapin
  (910).
- `data`: `new_issue_prices`, each bond's issue (reoffer) price, kind `last`,
  per 100 of face, dated its pricing date, class `traded` (965, 906).
- Not presented: price talk (free text, no stage stated), loans (964),
  covenants, distressed, private credit, CLOs, BDCs, asset-based finance and
  news (910).
- No default licence declared (rulings 1030 to 1032).

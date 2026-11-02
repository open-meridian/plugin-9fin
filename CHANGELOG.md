# Changelog

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

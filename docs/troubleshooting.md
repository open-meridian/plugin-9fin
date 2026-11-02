# Troubleshooting

## Connection

| What you see | What it means | What to do |
|---|---|---|
| **No key** | No 9fin client ID and secret are set | Enter both in Settings |
| **9fin refused the client's credentials** | The ID or secret is wrong, or revoked | Make a new client in 9fin's developer portal |
| **Not entitled to this API** | The client lacks the Instruments or Entity API | Ask 9fin to entitle it |
| Calls **rate-limited** | 9fin answered 429; the plugin waited a minute | Nothing |

## Records and terms

| What you see | What it means | What to do |
|---|---|---|
| **Not covered by 9fin** | No 9fin instrument names that ISIN | Check the tranche's ISIN |
| **A loan: no template in v29** | 9fin's instrument is a loan | Nothing yet: loans wait for a loan template |
| **CIK not resolved yet** | The platform has not answered for the issuer's CIK | Nothing: asked again at the next daily read |
| A term **not offered** | 9fin's ranking maps to no seniority, or 9fin states no coupon | Set it at the Instruments page |

## Wants

| What you see | What it means | What to do |
|---|---|---|
| A date declined, *source silent* | 9fin's issue price is dated its pricing date, not that one | Ask for the pricing date, or none |
| Datasets: **Not licensed yet** | No deployment admin has licensed the dataset | Ask a deployment admin to license it |

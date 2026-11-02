# Setup

## Before launching

You need a 9fin API client -- a client ID and secret made in 9fin's
developer portal -- entitled to the Instruments and Entity APIs, under the
agreement your use calls for (see [Terms](terms.md)).

## Launching it

Launch the plugin and approve its two roles, `data` and `reference`. In the
dashboard's Settings form:

- **9fin client ID** and **9fin client secret** -- secrets: never shown
  again, logged or put on a page. The plugin exchanges them for an hour's
  token and asks again before it lapses.
- **Securities** -- the bonds whose terms are offered and whose issue prices
  are recorded, one ISIN a row (the tranche you hold: Rule 144A, Regulation
  S or another), up to 500.
- **Sample data**, on a deployment installed for development only: answers
  committed with the plugin, in the shape of 9fin's public documentation,
  in place of 9fin.

It reads 9fin at once and daily after, or at once when the list changes.

## Its dataset and records

On the **Data sources** page, license `<instance>:new_issue_prices` on the
terms your 9fin agreement gives you, and entitle the plugins that read it.
Each bond's offered terms wait at the **Instruments** page for a person to
accept.

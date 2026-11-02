# meridian-9fin

9fin's bond data in an [Open Meridian](https://open-meridian.dev)
deployment: an Apache-2.0 plugin, in Python on the open-meridian SDK 0.35.3
(contract v29), built from 9fin's public API documentation.

It holds two roles:

- **`reference`** -- the terms and issuers of the bonds a deployment lists,
  offered to its instrument records under the `bond` template;
- **`data`** -- their new-issue (reoffer) prices, into the lake.

Price talk, loans and 9fin's content (covenants, distressed situations,
private credit, CLOs, BDCs, asset-based finance, news) are not recorded in
this version; see [docs/overview.md](docs/overview.md). You need a 9fin API
client; the terms are yours and 9fin's to settle ([docs/terms.md](docs/terms.md)).

## Developing it

`AGENTS.md` is the plugin's guide for people and coding agents alike.

    make ci-remote     # lint and tests, in a container
    make check         # meridian plugin check --verified --run-tests
    make e2e           # the plugin on the plugin harness, on sample data
    make preview SHOTS=<dir>   # its pages in a browser, at 375, 582 and 1280 px

Changes land through a pull request; CI (`ci`, `check`, `e2e`) is the gate.

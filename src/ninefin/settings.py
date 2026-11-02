"""The plugin's settings, declared to the SDK, and what it makes of them.

In the data role's order: no `environment` (9fin has one API host); the
credentials; the plugin's own; then the role's sample data. On a plugin
holding two roles, each setting names the roles it serves (contract v15):
every one serves both, the credentials and the bonds listed reading 9fin's
terms and prices alike.

- `client_id` and `client_secret` -- the deployment's 9fin API client,
  made in 9fin's developer portal, both secrets. Without them nothing is
  asked of 9fin.
- `securities` -- the bonds whose terms are offered to the deployment's
  records and whose issue prices are recorded: a typed table, one column,
  each an ISIN (a Rule 144A, a Regulation S or another tranche's).
- `sample_data` -- a developer's setting: the answers committed under
  sample/ in place of 9fin.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import meridian

CLIENT_ID = "client_id"
CLIENT_SECRET = "client_secret"
SECURITIES = "securities"
SECURITY_COLUMN = "security"
SAMPLE_DATA = "sample_data"
MOST_SECURITIES = 500
BOTH = ("data", "reference")


@meridian.settings
class Declared:
    """The settings as declared, in the data role's order."""

    client_id: str = meridian.setting(
        "9fin client ID",
        secret=True,
        description="The deployment's 9fin API client's ID, made in 9fin's developer portal.",
        roles=BOTH,
    )
    client_secret: str = meridian.setting(
        "9fin client secret",
        secret=True,
        description=(
            "That client's secret. With the ID, it is exchanged for an hour's token; "
            "without both the plugin asks 9fin nothing."
        ),
        roles=BOTH,
    )
    securities: list = meridian.setting(  # type: ignore[type-arg]
        "Securities",
        description=(
            "The bonds whose terms 9fin offers to the deployment's records, and whose "
            "issue prices are recorded."
        ),
        columns=[
            meridian.Column(
                SECURITY_COLUMN,
                kind="text",
                label="ISIN",
                required=True,
                description="The bond tranche's ISIN",
            )
        ],
        most_rows=MOST_SECURITIES,
        roles=BOTH,
    )
    sample_data: bool = meridian.sample_data(
        description=(
            "Serve the answers committed with the plugin, made in the shape of 9fin's public "
            "documentation, instead of asking 9fin. No credentials needed. Development "
            "deployments only."
        ),
        roles=BOTH,
    )


DECLARED = Declared


@dataclass(frozen=True)
class Config:
    client_id: str = field(default="", repr=False)
    client_secret: str = field(default="", repr=False)
    securities: tuple[str, ...] = ()
    sample_data: bool = False


def _securities(rows: object) -> tuple[str, ...]:
    held: list[str] = []
    if not isinstance(rows, Sequence) or isinstance(rows, str):
        return ()
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        said = str(row.get(SECURITY_COLUMN, "")).strip().upper()
        if len(said) == 12 and said.isalnum() and said not in held:
            held.append(said)
    return tuple(held)


def config_from(values: Mapping[str, object]) -> Config:
    client_id, secret = values.get(CLIENT_ID), values.get(CLIENT_SECRET)
    return Config(
        client_id=client_id.strip() if isinstance(client_id, str) else "",
        client_secret=secret.strip() if isinstance(secret, str) else "",
        securities=_securities(values.get(SECURITIES)),
        sample_data=values.get(SAMPLE_DATA) is True,
    )

"""The plugin's pages, as an admin of the plugin sees them through the
deployment's dashboard: the data role's common pages
(spec/plugin-pages-follow-their-role), built on `meridian.roles.data`, at
`admin` of the `data` role (contract v15: a person's level is granted per
role).

- Connection (/): "Key", "Limits and use" and "Stream", from
  `ConnectionRead`; 9fin's own rows in "Key": "Securities", each listed
  bond's record, its issuer's company record and the terms offered; and
  "Not recorded", what 9fin offers that this version records nothing of.
- Datasets (/datasets): "Served", "Wants" and "Subjects", from
  `DatasetsRead`, with a notice of what was stated but not recorded.

Each page declares the record it renders (`answers=`), so it is also a read
tool on the deployment's MCP surface: `read_connection` and
`read_datasets`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import meridian
from meridian.roles import data

if TYPE_CHECKING:
    from .lake import Lake

TITLE = "9fin"
#: What this version records nothing of, and why (910, 964, 965).
NOT_RECORDED = (
    "Price talk (free text, no stage stated); loans (no template until a loan template); "
    "covenants, distressed, private credit, CLOs, BDCs, asset-based finance and news (no "
    "kinds until the content wave)."
)

pages = meridian.Pages(TITLE, templates=Path(__file__).parent / "templates")

running: list[Lake] = []


def hold(lake: Lake) -> None:
    running[:] = [lake]


@dataclass(frozen=True)
class SecurityRead:
    security: str
    description: str = ""
    record: str = ""
    miss: str = ""
    issuer: str = ""
    offered: int = 0
    refused: str = ""


@dataclass(frozen=True)
class ConnectionRead(data.ConnectionRead):
    securities: list[SecurityRead] = field(default_factory=list)
    not_recorded: str = ""
    checked_at: str = ""


@dataclass(frozen=True)
class DatasetsRead(data.DatasetsRead):
    served: list[data.Served] = field(default_factory=list)
    wants: list[data.WantHeard] = field(default_factory=list)  # type: ignore[assignment]
    not_recorded: list[str] = field(default_factory=list)


def mode(lake: Lake) -> str:
    if lake.source.mode == "synthetic":
        return "Sample data"
    return "Live" if lake.has_credential else "No key"


def _held(record: str) -> str:
    return record if record.startswith(("INS-", "LCL-")) else ""


def connection_read(lake: Lake) -> ConnectionRead:
    source = lake.source
    return ConnectionRead(
        mode=mode(lake),
        credentials=[
            data.Credential("9fin client ID", lake.has_credential),
            data.Credential("9fin client secret", lake.has_credential),
        ],
        entitled_at_vendor=f"{len(lake.securities)} securities listed",
        limit="1,000 a minute, 10,000 an hour" + (f"; {source.remaining} left"
                                                  if source.remaining else ""),
        calls=source.calls,
        rate_limited=source.rate_limited,
        last_call_at=source.last_call_at,
        last_error=source.failed or lake.status.last_error,
        sessions=None,
        securities=[
            SecurityRead(
                security=isin,
                description=row.get("description", ""),
                record=_held(row.get("record", "")),
                miss="" if _held(row.get("record", "")) else row.get("record", ""),
                issuer=row.get("issuer", ""),
                offered=int(row.get("offered", "0") or 0),
                refused=row.get("refused", ""),
            )
            for isin, row in sorted(lake.status.securities.items())
        ],
        not_recorded=NOT_RECORDED,
        checked_at=lake.status.checked_at,
    )  # fmt: skip


def datasets_read(lake: Lake) -> DatasetsRead:
    from .declaration import DECLARATION

    instance = lake.plugin.identity.instance_id if lake._role_plugin is not None else ""
    said = [f"{what} ({n})" for what, n in sorted(lake.status.unread.items())]
    said += [f"{what}: {why}" for what, why in sorted(lake.status.refused.items())]
    return DatasetsRead(
        served=data.served(DECLARATION.catalogue, instance, lake.wants,
                           f"{len(lake.securities)} securities listed"),
        wants=list(data.want_rows(lake.wants)),
        not_recorded=said,
    )  # fmt: skip


def _lake() -> Lake:
    if running:
        return running[0]
    from .lake import Lake

    return Lake()


@pages.page(
    "/", "Connection", levels="admin", roles=["data"], answers=ConnectionRead,
    name="read_connection",
)  # fmt: skip
async def connection(request: meridian.Request) -> meridian.Response:
    """Whether 9fin answers, and each listed bond's record and terms."""
    return pages.answer("connection.html", connection_read(_lake()))


@pages.page(
    "/datasets", "Datasets", levels="admin", roles=["data"], answers=DatasetsRead,
    name="read_datasets",
)  # fmt: skip
async def datasets(request: meridian.Request) -> meridian.Response:
    """The dataset this plugin serves the lake, whether it is licensed, and
    the wants it answered."""
    return pages.answer("datasets.html", datasets_read(_lake()))


def figures(lake: Lake) -> list[meridian.Figure]:
    source = lake.source
    return data.figures(
        connection=mode(lake) if mode(lake) != "Live" else (
            "Not answering" if source.failed else "Answering"),
        entitled_at_vendor=f"{len(lake.securities)} securities listed",
        stream="Does not stream",
        last_recorded=lake.status.checked_at or "None yet",
        rate_use=f"{source.calls} calls",
    )  # fmt: skip

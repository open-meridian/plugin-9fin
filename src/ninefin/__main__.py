"""9fin as an Open Meridian data and reference plugin (rulings 909 to 911,
964 to 966, 1059): the new-issue prices of the bonds a deployment lists into
its lake, and their terms and issuers offered to its records.

It runs two role classes with `meridian.run` on the sidecar it is launched
beside (SDK 0.35, multi-role by composition): `Running`, the data role's
(lake.py, with its lifecycle here), and `Reference`, the reference role's
(terms.py), which the data role's class hands each listed security's
terms. `meridian.run` delivers the settings, serves the two pages
(page.py), hands it what the lake wants, and sets the data role's figures
on each heartbeat. It reads 9fin at start and daily, and its
datasets' licences every minute. It holds nothing else: a restart reads
9fin again, and the lake answers what it recorded before unchanged.

Everything it says to the deployment goes through the sidecar; everything
it reads comes from 9fin's APIs, with the client the deployment's Settings
hold, or with sample data from the answers committed with it.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any

import meridian

from .client import ninefin
from .declaration import DECLARATION, PORT
from .lake import Lake
from .page import figures, hold, pages
from .settings import config_from
from .terms import Reference

log = logging.getLogger("ninefin")

#: How often the check runs, in seconds: hourly, reading 9fin once a day.
CHECK_SECONDS = 3600
#: How often the datasets' licences are read again.
LICENCES_SECONDS = 60


class Running(Lake):
    """The data role's class with its lifecycle: `meridian.run` delivers
    each settings to `on_settings` -- the first before anything is heard --
    and starts `run`, again after a backoff should it fail."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.wake = asyncio.Event()

    async def on_settings(self, delivered: Any) -> None:
        """Apply each delivery of the settings: the client, the securities
        listed, sample data on or off; read again at once."""
        config = config_from(delivered.values)
        source = ninefin(config.sample_data, config.client_id, config.client_secret, self.now)
        self.use(source, config.securities, bool(config.client_id and config.client_secret))
        self.daily = None
        self.wake.set()

    async def run(self) -> None:
        await asyncio.gather(self._check(), self._licences())

    async def _check(self) -> None:
        while True:
            self.wake.clear()
            try:
                await self.check()
            except meridian.MeridianError as failed:
                self.status.last_error = f"the deployment refused a recording: {failed}"
                log.warning("this check stopped: %s", failed)
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self.wake.wait(), timeout=CHECK_SECONDS)

    async def _licences(self) -> None:
        while True:
            try:
                await self.wants.read_licences()
            except meridian.MeridianError as failed:
                log.warning("the datasets' licences were not read this time: %s", failed)
            await asyncio.sleep(LICENCES_SECONDS)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    reference = Reference()
    lake = Running(reference=reference)
    hold(lake)
    meridian.run(
        declaration=DECLARATION,
        roles=[lake, reference],
        pages=pages,
        port=PORT,
        on_settings=lake.on_settings,
        figures=lambda: figures(lake),
    )


if __name__ == "__main__":
    main()

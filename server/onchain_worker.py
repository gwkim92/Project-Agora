from __future__ import annotations

import argparse
import logging
import sys
import time

from server.config import settings
from server.onchain_sync import sync_once
from server.storage import get_store


logger = logging.getLogger("agora.onchain_worker")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Project Agora onchain sync worker")
    parser.add_argument("--once", action="store_true", help="Run a single sync iteration and exit")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    if not settings.ONCHAIN_SYNC_ENABLED:
        logger.info("onchain_sync_disabled")
        return 0
    if not settings.RPC_URL:
        logger.error("missing_rpc_url")
        return 2

    store = get_store()

    if args.once:
        res = sync_once(store)
        logger.info("sync_once_done %s", res)
        return 0

    poll = int(getattr(settings, "ONCHAIN_SYNC_POLL_SECONDS", 5))
    logger.info("onchain_worker_started poll=%s", poll)
    while True:
        try:
            res = sync_once(store)
            logger.info("sync_once %s", res)
        except Exception:
            logger.exception("sync_once_failed")
        time.sleep(max(1, poll))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


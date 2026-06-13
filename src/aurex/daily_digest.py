"""Public Aurex entrypoint for the daily digest automation."""

from nick_engine.daily_digest import *  # noqa: F401,F403 - compatibility re-export.
from nick_engine.daily_digest import main


if __name__ == "__main__":
    raise SystemExit(main())


"""Lambda-friendly logging configuration.

Must be imported BEFORE any module that uses `logging.getLogger()`.
The composition root (src/main.py) imports this first so every handler
benefits transparently.

Lambda Python runtime pre-configures the root logger at WARNING level,
which silently drops all .info() and .debug() calls from our code.
Calling logging.basicConfig() with force=True overrides that.
"""

import logging
import os
import sys


def configure_logging() -> None:
    """Configure root logger for Lambda visibility.

    Idempotent — safe to call multiple times. The `force=True` flag
    replaces Lambda's default handler so our format and level apply.
    """
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format='[%(levelname)s] %(name)s %(message)s',
        stream=sys.stdout,
        force=True,  # critical — Lambda already configured logging once
    )

    # Silence noisy AWS SDK loggers — keep our own at INFO
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("aiobotocore").setLevel(logging.WARNING)

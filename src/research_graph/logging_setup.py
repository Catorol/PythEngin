import logging
import sys

_NOISY = ("httpx", "httpcore", "urllib3", "asyncio")


def setup_logging(level: str) -> None:
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root.addHandler(handler)
    root.setLevel(level.upper())
    for name in _NOISY:
        logging.getLogger(name).setLevel(logging.WARNING)

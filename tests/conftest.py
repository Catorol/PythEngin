import logging
import os
from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for key in list(os.environ):
        if key.startswith("RG_"):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(tmp_path)


@pytest.fixture(autouse=True)
def restore_logging() -> Iterator[None]:
    root = logging.getLogger()
    old_handlers = root.handlers[:]
    old_level = root.level
    yield
    for handler in root.handlers[:]:
        root.removeHandler(handler)
    for handler in old_handlers:
        root.addHandler(handler)
    root.setLevel(old_level)
    for name in ("httpx", "httpcore", "urllib3", "asyncio"):
        logging.getLogger(name).setLevel(logging.NOTSET)

from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session, sessionmaker

from research_graph.config import get_settings
from research_graph.db import create_db_engine, create_session_factory


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return create_session_factory(create_db_engine(get_settings().database_url))


def get_db() -> Iterator[Session]:
    with get_session_factory()() as session:
        yield session


DbSession = Annotated[Session, Depends(get_db)]

from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import func, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from research_graph.db import Base, create_db_engine, create_session_factory
from research_graph.models import Creator, Hook, ModelVersion, Prediction, Product, Video
from research_graph.models.video import video_hooks


@pytest.fixture
def session(tmp_path: Path) -> Iterator[Session]:
    engine = create_db_engine(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    Base.metadata.create_all(engine)
    with create_session_factory(engine)() as db:
        yield db
    engine.dispose()


def new_creator(external_id: str = "c1") -> Creator:
    return Creator(
        external_id=external_id,
        tier="Micro",
        category="Beauty",
        country="US",
        followers=1000,
        engagement_rate=0.05,
    )


def make_video(db: Session, external_id: str = "v1") -> Video:
    video = Video(
        external_id=external_id,
        creator=new_creator(f"c-{external_id}"),
        product=Product(external_id=f"p-{external_id}", category="Beauty", price=19.9),
        video_format="Tutorial",
        length_seconds=30,
        features={"hook_type": "Curiosity"},
    )
    db.add(video)
    db.commit()
    return video


def test_all_tables_created(session: Session) -> None:
    tables = set(inspect(session.get_bind()).get_table_names())
    assert tables == {
        "creators",
        "products",
        "videos",
        "hooks",
        "video_hooks",
        "model_versions",
        "predictions",
    }


def test_creator_external_id_is_unique(session: Session) -> None:
    session.add_all([new_creator("dup"), new_creator("dup")])
    with pytest.raises(IntegrityError):
        session.commit()


def test_video_status_default_and_check(session: Session) -> None:
    video = make_video(session)
    assert video.status == "published"
    video.status = "deleted"
    with pytest.raises(IntegrityError):
        session.commit()


def test_video_requires_existing_creator_and_product(session: Session) -> None:
    session.add(
        Video(external_id="x", creator_id=999, product_id=999, length_seconds=10, features={})
    )
    with pytest.raises(IntegrityError):
        session.commit()


def test_video_hooks_many_to_many(session: Session) -> None:
    video = make_video(session)
    first, second = Hook(code="demo", title="Demo"), Hook(code="story", title="Story")
    video.hooks = [first, second]
    session.commit()
    session.refresh(first)
    assert len(video.hooks) == 2
    assert [v.external_id for v in first.videos] == ["v1"]


def test_deleting_video_removes_links_but_keeps_hooks(session: Session) -> None:
    video = make_video(session)
    video.hooks = [Hook(code="demo", title="Demo")]
    session.commit()
    session.delete(video)
    session.commit()
    assert session.scalar(select(func.count()).select_from(video_hooks)) == 0
    assert session.scalar(select(func.count()).select_from(Hook)) == 1


def test_only_one_active_model_version(session: Session) -> None:
    session.add(ModelVersion(name="m1", filename="m1.pkl", is_active=True))
    session.commit()
    session.add(ModelVersion(name="m2", filename="m2.pkl", is_active=True))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
    session.add(ModelVersion(name="m3", filename="m3.pkl", is_active=False))
    session.commit()


def test_prediction_probability_must_be_between_0_and_1(session: Session) -> None:
    version = ModelVersion(name="m1", filename="m1.pkl")
    session.add(version)
    session.commit()
    session.add(Prediction(model_version_id=version.id, probability=1.5, predicted_flag=1))
    with pytest.raises(IntegrityError):
        session.commit()


def test_prediction_links_video_and_model(session: Session) -> None:
    video = make_video(session)
    version = ModelVersion(name="m1", filename="m1.pkl")
    session.add(version)
    session.commit()
    session.add(
        Prediction(
            video_id=video.id, model_version_id=version.id, probability=0.7, predicted_flag=1
        )
    )
    session.commit()
    session.refresh(video)
    assert len(video.predictions) == 1
    assert video.predictions[0].model_version.name == "m1"

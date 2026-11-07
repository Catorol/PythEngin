from importlib.metadata import version as pkg_version
from pathlib import Path

import typer

from research_graph.config import get_settings
from research_graph.logging_setup import setup_logging

app = typer.Typer(help="research-graph CLI", no_args_is_help=True)


def mask_token(token: str | None) -> str:
    if not token:
        return "не задан"
    if len(token) <= 8:
        return "****"
    return f"{token[:4]}****{token[-4:]}"


@app.command()
def version() -> None:
    typer.echo(pkg_version("research-graph"))


@app.command("check-config")
def check_config() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)
    typer.echo(f"data_dir:         {settings.data_dir}")
    typer.echo(f"model_dir:        {settings.model_dir}")
    typer.echo(f"log_level:        {settings.log_level}")
    typer.echo(f"request_timeout:  {settings.request_timeout}")
    typer.echo(f"max_concurrency:  {settings.max_concurrency}")
    typer.echo(f"github_token:     {mask_token(settings.github_token)}")


@app.command("make-sample")
def make_sample_cmd(
    csv: Path = typer.Option(..., "--csv", exists=True, dir_okay=False, help="Полный CSV"),
    out: Path = typer.Option(Path("data/sample/tiktok_sample.csv"), "--out", help="Куда сохранить"),
    n: int = typer.Option(5000, "-n", min=100, help="Размер выборки"),
) -> None:
    """Сделать небольшую выборку для репозитория и Docker."""
    from research_graph.ml.train import make_sample

    size = make_sample(csv, out, n=n)
    typer.echo(f"Сохранено {size} строк -> {out}")


@app.command()
def train(
    csv: Path = typer.Option(..., "--csv", exists=True, dir_okay=False, help="CSV с данными"),
    out_dir: Path | None = typer.Option(None, "--out-dir", help="Каталог для модели"),
    nrows: int | None = typer.Option(None, "--nrows", min=100, help="Читать только N строк"),
    k_features: int = typer.Option(25, "--k-features", min=1, help="Сколько признаков оставить"),
) -> None:
    """Обучить и сравнить 3 модели, сохранить лучшую."""
    from research_graph.ml.train import load_dataset, train_and_compare

    settings = get_settings()
    setup_logging(settings.log_level)
    target_dir = out_dir or settings.model_dir
    metrics = train_and_compare(load_dataset(csv, nrows), target_dir, k_features=k_features)
    for name, res in metrics["models"].items():
        typer.echo(f"{name:<24} ROC-AUC={res['roc_auc']}")
    typer.echo(
        f"Лучшая: {metrics['best_model']} (ROC-AUC={metrics['best_roc_auc']}) -> {target_dir}"
    )


@app.command("register-model")
def register_model_cmd(
    path: Path = typer.Option(
        Path("models/model.pkl"), "--path", exists=True, dir_okay=False, help="Файл модели"
    ),
) -> None:
    """Зарегистрировать обученную модель в БД и сделать её активной (повтор безопасен)."""
    from research_graph.db import create_db_engine, create_session_factory
    from research_graph.services.ml import register_baseline

    settings = get_settings()
    setup_logging(settings.log_level)
    factory = create_session_factory(create_db_engine(settings.database_url))
    with factory() as db:
        version, created = register_baseline(db, path)
    if created:
        typer.echo(f"Модель зарегистрирована и активна: id={version.id}, {version.algorithm}")
    else:
        typer.echo(f"Модель уже зарегистрирована: id={version.id}")

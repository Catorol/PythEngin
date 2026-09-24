from importlib.metadata import version as pkg_version

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
    typer.echo(f"log_level:        {settings.log_level}")
    typer.echo(f"request_timeout:  {settings.request_timeout}")
    typer.echo(f"max_concurrency:  {settings.max_concurrency}")
    typer.echo(f"github_token:     {mask_token(settings.github_token)}")

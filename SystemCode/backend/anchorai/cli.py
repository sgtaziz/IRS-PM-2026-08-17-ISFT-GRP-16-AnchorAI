from pathlib import Path

import typer
from sqlmodel import Session

from anchorai import pipeline
from anchorai.config import get_settings
from anchorai.db import migrate
from anchorai.db.seeds import run_seeds
from anchorai.db.session import get_engine, reset_engine

app = typer.Typer(help="AnchorAI command line.", no_args_is_help=True)
db_app = typer.Typer(help="App database: migrations and seeds.", no_args_is_help=True)
data_app = typer.Typer(help="Data tables (Stream A).", no_args_is_help=True)
kg_app = typer.Typer(help="Knowledge graph (Stream C).", no_args_is_help=True)
app.add_typer(db_app, name="db")
app.add_typer(data_app, name="data")
app.add_typer(kg_app, name="kg")


def _seed(demo: bool) -> None:
    layers = ("base", "demo") if demo else ("base",)
    with Session(get_engine()) as session:
        run_seeds(session, layers)
    typer.echo(f"Seeded: {', '.join(layers)}")


@db_app.command("upgrade")
def db_upgrade() -> None:
    """Apply migrations to head."""
    migrate.upgrade()


@db_app.command("seed")
def db_seed(demo: bool = typer.Option(False, "--demo", help="Also load the demo layer.")) -> None:
    """Load the base seeds, plus demo with --demo."""
    _seed(demo)


@db_app.command("reset")
def db_reset() -> None:
    """Delete the SQLite database, upgrade to head and seed with --demo."""
    url = get_settings().anchorai_db_url
    if not url.startswith("sqlite:///"):
        typer.echo(f"Refusing to reset a non-SQLite database: {url}", err=True)
        raise typer.Exit(1)
    reset_engine()
    db_path = Path(url.removeprefix("sqlite:///"))
    db_path.unlink(missing_ok=True)
    migrate.upgrade()
    _seed(demo=True)
    typer.echo(f"Reset {db_path}")


@data_app.command("build")
def data_build() -> None:
    """Regenerate the parquet tables and model artefacts from data/raw/."""
    try:
        out = pipeline.run()
    except FileNotFoundError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1) from None
    typer.echo(f"Wrote data tables to {out}")


@kg_app.command("load")
def kg_load() -> None:
    """Load the knowledge graph into Neo4j from the parquet tables."""
    typer.echo("kg load: not implemented yet (Stream C)")


@app.command()
def setup() -> None:
    """Fresh clone to working demo: data build, db reset, kg load."""
    data_build()
    db_reset()
    kg_load()

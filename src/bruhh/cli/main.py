import typer
from bruhh.cli.subcommands import system
from rich.logging import RichHandler
import logging

logging.basicConfig(level="INFO", format="%(message)s", handlers=[RichHandler()])

_main_help = """Bruhh CLI - A command line interface for agent-based LLM things, do `bruhh system init`"""

app = typer.Typer(
    help=_main_help,
    no_args_is_help=True,
    epilog="Bruhh CLI is a command line interface for agent-based LLM things.",
)
app.add_typer(system, name="system", help="System commands, including daemon management.")


if __name__ == "__main__":
    app()

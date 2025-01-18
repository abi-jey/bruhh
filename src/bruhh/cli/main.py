import typer
from bruhh.cli.subcommands import Daemon

app = typer.Typer(help="Bruhh CLI - a command line interface for background tasks.", no_args_is_help=True)

@app.command()
def run():
    """
    Start the Bruhh background service (daemon) or perform actions directly.
    """
    typer.echo("Running Bruhh service... (placeholder for future logic)")

@app.command()
def status():
    """
    Check the status of the background service.
    """
    # Placeholder logic: you'd probably check if the daemon is running, etc.
    typer.echo("Bruhh status: (placeholder) Service is idle or running.")


def main():
    """Entry point for CLI."""
    app()

if __name__ == "__main__":
    main()
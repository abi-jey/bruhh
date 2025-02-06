import sys
import logging
import getopt
import asyncio

from rich.console import Console
from rich.panel import Panel
from rich.box import DOUBLE
from rich.logging import RichHandler

from bruhh.cli.subcommands.system import cmd_init, cmd_status
from bruhh.client.main import BruhhClient

# -----------------------------------------------------------------------------
# Logging config with Rich
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler()],
)
logger = logging.getLogger("bruhh.cli")
console = Console()


# -----------------------------------------------------------------------------
# Help Print Functions
# -----------------------------------------------------------------------------
def print_top_level_help():
    text = (
        "usage: bruhh [system] [options] | <any other text>\n\n"
        "Bruhh CLI - A command line interface for agent-based LLM things.\n\n"
        "Subcommands:\n"
        "  system        System commands, including daemon management.\n\n"
        "Options:\n"
        "  -h, --help    Show this help message and exit.\n"
    )
    console.print(
        Panel(
            text,
            title="[bold magenta]Bruhh CLI Help[/bold magenta]",
            border_style="bright_cyan",
            box=DOUBLE,
            expand=True,
        )
    )


def print_system_help():
    text = (
        "usage: bruhh system <command> [options]\n\n"
        "Available system commands:\n"
        "  init          Initialize the bruhh service (create venv, systemd, etc.)\n"
        "  status        Check the status of the bruhh background service.\n\n"
        "Options:\n"
        "  -h, --help    Show this help message and exit.\n"
    )
    console.print(
        Panel(text, title="[bold red]Bruhh System Help[/bold red]", border_style="bright_cyan", box=DOUBLE, expand=True)
    )


def print_init_help():
    text = (
        "usage: bruhh system init [options]\n\n"
        "Initialize the bruhh service (create venv, systemd, etc.).\n\n"
        "Options:\n"
        "  -h, --help              Show help for this command and exit.\n"
        "  --daemon-from=PATH      Install daemon from a specified path (e.g., .whl file).\n"
    )
    console.print(
        Panel(
            text,
            title="[bold green]Bruhh System Init Help[/bold green]",
            border_style="bright_cyan",
            box=DOUBLE,
            expand=True,
        )
    )


def print_status_help():
    text = (
        "usage: bruhh system status\n\n"
        "Check the status of the bruhh background service.\n\n"
        "Options:\n"
        "  -h, --help    Show help for this command and exit.\n"
    )
    console.print(
        Panel(
            text,
            title="[bold green]Bruhh System Status Help[/bold green]",
            border_style="bright_cyan",
            box=DOUBLE,
            expand=True,
        )
    )


# -----------------------------------------------------------------------------
# Command Processing Functions Using getopt
# -----------------------------------------------------------------------------
def process_system_init(args_list):
    """
    Process the 'init' subcommand for the system.
    Allowed options:
      -h, --help
      --daemon-from=PATH
    """
    try:
        opts, _ = getopt.getopt(args_list, "h", ["help", "daemon-from="])
    except getopt.GetoptError as err:
        console.print(f"[red]Error: {err}[/red]")
        print_init_help()
        sys.exit(2)

    daemon_from = None
    for opt, val in opts:
        if opt in ("-h", "--help"):
            print_init_help()
            sys.exit(0)
        elif opt == "--daemon-from":
            daemon_from = val

    # Create a simple object to mimic an argparse.Namespace.
    class Args:
        pass

    args_obj = Args()
    args_obj.daemon_from = daemon_from
    cmd_init(args_obj)


def process_system_status(args_list):
    """
    Process the 'status' subcommand.
    Allowed option:
      -h, --help
    """
    try:
        opts, _ = getopt.getopt(args_list, "h", ["help"])
    except getopt.GetoptError as err:
        console.print(f"[red]Error: {err}[/red]")
        print_status_help()
        sys.exit(2)

    for opt, _ in opts:
        if opt in ("-h", "--help"):
            print_status_help()
            sys.exit(0)

    class Args:
        pass

    args_obj = Args()
    cmd_status(args_obj)


def process_system_command(args_list):
    """
    Process system subcommands.
    """
    if not args_list:
        print_system_help()
        sys.exit(0)

    command = args_list[0]
    if command in ("-h", "--help"):
        print_system_help()
        sys.exit(0)
    elif command == "init":
        process_system_init(args_list[1:])
    elif command == "status":
        process_system_status(args_list[1:])
    else:
        print_system_help()
        sys.exit(0)


# -----------------------------------------------------------------------------
# Chat Input Handler
# -----------------------------------------------------------------------------
async def _handle_client_input(user_input):
    logger.info("Starting BruhhClient for custom input...")
    logger.info(f"User input: {user_input}")
    client = BruhhClient()
    await client.connect_cli_user(prompt=" ".join(user_input))
    # Additional chat logic can be added here.


# -----------------------------------------------------------------------------
# Main Command Dispatching Logic
# -----------------------------------------------------------------------------
def main():
    # Use sys.argv (excluding the script name) to get command-line arguments.
    args = sys.argv[1:]

    if not args:
        print_top_level_help()
        sys.exit(0)

    # Top-level help flag.
    if args[0] in ("-h", "--help"):
        print_top_level_help()
        sys.exit(0)

    # If the first argument is "system", handle system subcommands.
    if args[0] == "system":
        process_system_command(args[1:])
        sys.exit(0)

    # Otherwise, treat the arguments as chat input.
    asyncio.run(_handle_client_input(args))


if __name__ == "__main__":
    main()

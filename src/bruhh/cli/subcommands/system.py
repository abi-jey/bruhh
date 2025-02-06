import os
import sys
import subprocess
import time
import logging
from pathlib import Path
from asyncio import run
from argparse import Namespace
from bruhh.client.main import BruhhClient

try:
    from bruhh import __version__
except ImportError:
    __version__ = "unknown"

logger = logging.getLogger(__name__)


def ensure_root_privileges():
    """
    If not running as root, re-run this exact command with sudo.
    """
    if os.geteuid() != 0:
        logger.info("Elevating privileges: re-running with sudo...")
        command = ["sudo", sys.executable] + sys.argv
        subprocess.run(command)
        sys.exit(0)


def cmd_init(args: Namespace):
    """
    Implements: bruhh system init [--daemon-from ...]
    Creates a venv in /opt/bruhh/venv, installs the package,
    sets up systemd service, and starts it.
    """
    daemon_from = args.daemon_from

    ensure_root_privileges()

    venv_path = Path("/opt/bruhh/venv")
    venv_python = venv_path / "bin" / "python"
    service_name = "bruhh.service"
    systemd_path = Path("/etc/systemd/system") / service_name

    # 1. Recreate venv
    if venv_path.exists():
        logger.info(f"Virtual environment already exists at {venv_path}, removing it...")
        try:
            subprocess.run(["rm", "-rf", str(venv_path)], check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to remove old virtual environment: {e}")
            sys.exit(1)

    logger.info(f"Creating venv at {venv_path}...")
    try:
        subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to create virtual environment: {e}")
        sys.exit(1)

    # 2. Install bruhh inside venv
    try:
        subprocess.run([str(venv_python), "-m", "ensurepip", "--upgrade"], check=True)
        subprocess.run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"], check=True)

        logger.info(f"Daemon package is installed from {daemon_from if daemon_from else 'pypi'}")
        if daemon_from:
            pkg_spec = daemon_from
        else:
            pkg_spec = f"bruhh[daemon]=={__version__}"

        logger.info(f"Installing {pkg_spec} into {venv_path}")
        subprocess.run([str(venv_python), "-m", "pip", "install", pkg_spec], check=True)

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install dependencies: {e}")
        sys.exit(1)

    # 3. Create or recreate systemd service for bruhh
    if systemd_path.exists():
        logger.info(f"Removing existing service file at {systemd_path}...")
        try:
            systemd_path.unlink()
        except Exception as e:
            logger.error(f"Failed to remove old service file: {e}")
            sys.exit(1)

    exec_start = f"{venv_python} -m bruhh.daemon.main"
    service_content = f"""\
[Unit]
Description=Bruhh background service
After=network.target

[Service]
Type=simple
ExecStart={exec_start}
Restart=on-failure

[Install]
WantedBy=multi-user.target
"""

    logger.info(f"Writing systemd service file to {systemd_path}...")
    try:
        with systemd_path.open("w") as f:
            f.write(service_content)
    except Exception as e:
        logger.error(f"Failed to write service file: {e}")
        sys.exit(1)

    # 4. Enable & start the service
    try:
        logger.info("Reloading systemd to pick up the new service...")
        subprocess.run(["systemctl", "daemon-reload"], check=True)

        logger.info("Stopping any running instance of the service...")
        subprocess.run(["systemctl", "stop", service_name], check=False)

        logger.info(f"Enabling {service_name}...")
        subprocess.run(["systemctl", "enable", service_name], check=True)

        logger.info(f"Starting {service_name}...")
        subprocess.run(["systemctl", "start", service_name], check=True)
        logger.info(f"Service {service_name} started successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to enable/start {service_name}: {e}")
        sys.exit(1)

    # 5. Wait for the service to start (poll /health endpoint)
    while True:
        logger.info("Waiting for the service to become healthy...")
        if _service_is_healthy():
            logger.info("Service is running.")
            break
        time.sleep(1)

    # 6. TODO: write config files to /etc/bruhh or wherever needed
    # config_path = Path("/etc/bruhh")
    # ...


def cmd_status(_args):
    """
    Implements: bruhh system status
    Checks the status of the background service via systemctl.
    """
    service_name = "bruhh.service"
    logger.info(f"Checking status of {service_name}...")
    try:
        subprocess.run(["systemctl", "status", service_name], check=False)
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to check status of {service_name}: {e}")
        sys.exit(1)


def _service_is_healthy() -> bool:
    """
    A simple check to see if the daemon's /health endpoint is reachable.
    """
    try:
        # Use the asynchronous client in a blocking manner
        run(_check_health())
        return True
    except Exception:
        return False


async def _check_health():
    client = BruhhClient()
    await client.get_health()  # raises if not healthy

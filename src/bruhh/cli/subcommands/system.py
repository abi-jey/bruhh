import os
import sys
import subprocess
from logging import getLogger
from pathlib import Path
from typer import Typer
from typing import Annotated
from typer import Option
import time


try:
    from bruhh import __version__
except ImportError:
    __version__ = None

logger = getLogger(__name__)
system = Typer(help="", no_args_is_help=True)


def ensure_root_privileges():
    """
    If not running as root, re-run this exact command with sudo.
    """
    if os.geteuid() != 0:
        logger.info("Elevating privileges: re-running with sudo...")
        command = ["sudo", sys.executable] + sys.argv
        subprocess.run(command)
        sys.exit(0)


@system.command("init")
def init(
    deamon_from: Annotated[
        None | str,
        Option(
            help="if you want to install daemon from a whl file for example, specify the path to whl file, this is useful for debugging deamon"
        ),
    ] = None,
):
    """
    Initialize the service. It will:
      1. Create or recreate a virtual environment in /opt/bruhh_venv
      2. Install bruhh in the virtual environment
      3. Create or recreate a systemd service for bruhh
      4. Enable & start the service
      5. Wait for the service to start
      6. write the config files
    """

    ensure_root_privileges()

    # 1. Create or recreate a virtual environment in /opt/bruhh_venv
    venv_path = Path("/opt/bruhh/venv")
    venv_python = venv_path / "bin" / "python"
    service_name = "bruhh.service"
    systemd_path = Path("/etc/systemd/system") / service_name

    if venv_path.exists():
        logger.info(f"Virtual environment already exists at {venv_path}, removing it...")
        try:
            subprocess.run(["rm", "-rf", str(venv_path)], check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to remove old virtual environment: {e}")
            sys.exit(1)

    logger.info(f"Creating venv at {venv_path} ...")
    try:
        subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to create virtual environment: {e}")
        sys.exit(1)

    # 2. Install bruhh in the virtual environment
    try:
        subprocess.run([str(venv_python), "-m", "ensurepip", "--upgrade"], check=True)
        subprocess.run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"], check=True)

        if deamon_from:
            deamon = deamon_from
        else:
            deamon = f"bruhh[daemon]=={__version__}"
        subprocess.run([str(venv_python), "-m", "pip", "install", deamon], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install dependencies: {e}")
        sys.exit(1)

    # 3. Create or recreate if exists a systemd service for bruhh
    if systemd_path.exists():
        logger.info(f"Removing existing service file at {systemd_path} for recreation...")
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

    logger.info(f"Writing systemd service file to {systemd_path} ...")
    try:
        with systemd_path.open("w") as f:
            f.write(service_content)
    except Exception as e:
        logger.error(f"Failed to write service file: {e}")
        sys.exit(1)
    # 4. Enable & start the service
    try:
        logger.info("Reloading systemd to pick up the new service ...")
        subprocess.run(["systemctl", "daemon-reload"], check=True)

        logger.info("Disabling the service to stop it if it's running ...")
        subprocess.run(["systemctl", "stop", service_name], check=True)

        logger.info(f"Enabling {service_name} to start on boot ...")
        subprocess.run(["systemctl", "enable", service_name], check=True)

        logger.info(f"Starting {service_name} ...")
        subprocess.run(["systemctl", "start", service_name], check=True)
        logger.info(f"Service {service_name} has been started successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to enable/start {service_name}: {e}")
        sys.exit(1)

    # 5. Wait for the service to start
    logger.info(f"Waiting for the service to start...")
    while True:
        time.sleep(1)    
        logger.info("Checking status...")
        
    # 6. write the config files
    config_path = Path("/etc/bruhh")
    # TODO: write the config files


@system.command("status")
def status():
    """
    Check the status of the background service.
    """
    service_name = "bruhh.service"
    logger.info(f"Checking status of {service_name}...")
    try:
        subprocess.run(["systemctl", "status", service_name], check=False)
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to check status of {service_name}: {e}")
        sys.exit(1)

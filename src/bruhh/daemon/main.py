# This is the server file that only implementes api calls that will communcate with deamon
# the deamon is seprated in it's own class/file

import asyncio
import logging
from uvicorn import run
from fastapi import FastAPI
from getpass import getuser
from bruhh.daemon.daemon import Daemon

logger = logging.getLogger("service")
logging.basicConfig(encoding="utf-8", level=logging.INFO)
try:
    from bruhh import __version__
except ImportError:
    __version__ = "unknown"
    logger.warning("Could not find __version__ from bruhh package")


async def daemon_task():
    """
    Background task that runs indefinitely.
    """
    daemon = Daemon()
    daemon_task_loop = asyncio.create_task(daemon.run_forever())
    while True:
        try:
            logger.info(f"[service]: daemon running task with user: {getuser()}")
        except Exception as _:
            logger.exception("[service]: daemon task failed")
        await asyncio.sleep(5)


async def lifespan(app: FastAPI):
    """
    Example of a lifespan event handler.
    """
    logger.info("[service] Starting up...")
    try:
        app.state.daemon_task = asyncio.create_task(daemon_task())
        app.websocket("/ws")(Daemon().ws_handler)
        yield
    finally:
        logger.info("[service] Shutting down...")


app = FastAPI(lifespan=lifespan)
port = 7878


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/version")
async def version():
    return {"version": str(__version__)}


def main():
    """
    Entry point for running the daemon in an async loop.
    """
    try:
        logger.info("Starting bruhh daemon...")
        run(app, host="127.0.0.1", port=port, workers=1)
    except KeyboardInterrupt:
        logger.info("Stopping bruhh daemon...")


if __name__ == "__main__":
    main()

import asyncio
import logging
from uvicorn import run
from fastapi import FastAPI
from getpass import getuser

logger = logging.getLogger("service")
logging.basicConfig(encoding="utf-8", level=logging.INFO)


async def daemon_task():
    """
    Background task that runs indefinitely.
    """
    while True:
        try:
            logger.info(f"Daemon running task with user: {getuser()}")
        except Exception as e:
            logger.error(f"Daemon task failed: {e}")
        await asyncio.sleep(5)


async def lifespan(app: FastAPI):
    """
    Example of a lifespan event handler.
    """
    logger.info("[daemon] Starting up...")
    try:
        app.state.daemon_task = asyncio.create_task(daemon_task())
        yield
    finally:
        logger.info("[daemon] Shutting down...")


app = FastAPI(lifespan=lifespan)
port = 7878


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/version")
async def version():
    return {"version": "0.1.0"}


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

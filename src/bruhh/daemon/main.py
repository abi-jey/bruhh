import asyncio
import os
import logging

logger = logging.getLogger("main")
logging.basicConfig(encoding='utf-8', level=logging.INFO)

async def daemon_task():
    """
    Example of a background task that runs indefinitely.
    """
    while True:
        # You might do some scheduled or event-driven logic here
        logger.info(f"Daemon running task with user:{os.getlogin()}")
        await asyncio.sleep(5)  # Sleep to avoid busy-looping

def main():
    """
    Entry point for running the daemon in an async loop.
    """
    try:
        logger.info("Starting bruhh daemon...")
        asyncio.run(daemon_task())
    except KeyboardInterrupt:
        logger.info("Stopping bruhh daemon...")

if __name__ == "__main__":
    main()
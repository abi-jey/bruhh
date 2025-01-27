import asyncio
import logging

import aiohttp

logger = logging.getLogger("bruhh.client")


class BruhhClient:
    def __init__(self, base_url="http://127.0.0.1:7878"):
        """
        :param base_url: The base URL of the Bruhh daemon's API.
        """
        self.base_url = base_url
        self.session = aiohttp.ClientSession()

    async def close(self):
        """
        Close the underlying aiohttp session.
        """
        await self.session.close()

    async def get_health(self):
        """
        Hit the /health endpoint to check if the daemon is alive.
        Returns a dict with { "status": "ok" } if the daemon is up.
        """
        url = f"{self.base_url}/health"
        logger.info(f"GET {url}")
        async with self.session.get(url) as resp:
            resp.raise_for_status()  # raise an exception for 4xx or 5xx status
            return await resp.json()

    async def get_version(self):
        """
        Hit the /version endpoint to retrieve daemon version info.
        Returns a dict with { "version": "0.1.0" } for example.
        """
        url = f"{self.base_url}/version"
        logger.info(f"GET {url}")
        async with self.session.get(url) as resp:
            resp.raise_for_status()
            return await resp.json()

    # Example of a generic fetch if you need it
    async def fetch_raw(self, path: str):
        """
        A generic GET request to the specified path, returning raw text.
        """
        url = f"{self.base_url}/{path.lstrip('/')}"
        logger.info(f"GET {url}")
        async with self.session.get(url) as resp:
            resp.raise_for_status()
            return await resp.text()


async def main():
    """
    Example usage of the BruhhClient. This will:
      - Instantiate the client
      - Check the daemon's health
      - Check the daemon's version
      - Print the results
      - Close the client session
    """
    client = BruhhClient(base_url="http://127.0.0.1:7878")

    try:
        health = await client.get_health()
        logger.info(f"Health Response: {health}")

        version_data = await client.get_version()
        logger.info(f"Version Response: {version_data}")
        
    except aiohttp.ClientError as e:
        logger.error(f"Error connecting to the daemon: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())

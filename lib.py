import aiohttp
from config import Settings


async def get_wikipedia_entry(title: str) -> str:
    """
    Fetch a Wikipedia article asynchronously by its title.
    """
    settings = Settings()
    params = {
        "action": "query",
        "format": "json",
        "titles": title,
        "prop": "extracts",
        "explaintext": "1",
        "formatversion": "2",
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(settings.wikipedia_base_url, params=params) as response:
            if response.status != 200:
                raise Exception(f"Wikipedia API request failed with status {response.status}")

            data = await response.json()

            try:
                page = data["query"]["pages"][0]
                if "missing" in page:
                    raise Exception(f"Wikipedia article '{title}' not found")
                return page["extract"]
            except (KeyError, IndexError):
                raise Exception("Failed to parse Wikipedia API response")

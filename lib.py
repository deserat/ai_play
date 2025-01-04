import aiohttp
from config import Settings
from models import WikiEntry
from database import get_db
from datetime import datetime


async def get_wikipedia_entry(title: str) -> str:
    """
    Fetch a Wikipedia article asynchronously by its title and cache it in the database.
    """
    # First try to get from database
    db = next(get_db())
    cached_entry = db.query(WikiEntry).filter(WikiEntry.title == title).first()

    if cached_entry:
        return cached_entry.content

    # If not in database, fetch from Wikipedia
    settings = Settings()
    params = {
        "action": "query",
        "format": "json",
        "titles": title,
        "prop": "extracts",
        "explaintext": "1",  # Use "1" instead of True for the API
        "formatversion": "2",  # Also convert this to string
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(settings.wikipedia_base_url, params=params) as response:
            if response.status != 200:
                raise Exception(
                    f"Wikipedia API request failed with status {response.status}"
                )

            data = await response.json()

            # Extract the page content
            try:
                page = data["query"]["pages"][0]
                if "missing" in page:
                    raise Exception(f"Wikipedia article '{title}' not found")
                content = page["extract"]

                # Store in database
                wiki_entry = WikiEntry(title=title, content=content)
                db.add(wiki_entry)
                db.commit()

                return content
            except (KeyError, IndexError):
                raise Exception("Failed to parse Wikipedia API response")
            finally:
                db.close()

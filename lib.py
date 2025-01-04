import aiohttp
import json
from config import Settings

async def get_wikipedia_entry(title: str) -> str:
    """
    Fetch a Wikipedia article asynchronously by its title.
    
    Args:
        title (str): The title of the Wikipedia article
        
    Returns:
        str: The article content text
        
    Raises:
        Exception: If the API request fails or article is not found
    """
    settings = Settings()
    params = {
        "action": "query",
        "format": "json",
        "titles": title,
        "prop": "extracts",
        "explaintext": "1",  # Use "1" instead of True for the API
        "formatversion": "2"  # Also convert this to string
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(settings.wikipedia_base_url, params=params) as response:
            if response.status != 200:
                raise Exception(f"Wikipedia API request failed with status {response.status}")
            
            data = await response.json()
            
            # Extract the page content
            try:
                page = data["query"]["pages"][0]
                if "missing" in page:
                    raise Exception(f"Wikipedia article '{title}' not found")
                return page["extract"]
            except (KeyError, IndexError):
                raise Exception("Failed to parse Wikipedia API response")

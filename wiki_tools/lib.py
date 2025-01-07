import aiohttp
import asyncio
import re
from datetime import datetime, timedelta

from config import Settings
from wiki_tools.models import WikiEntry, WikiEntryLog


async def get_wiki(db, title: str) -> tuple[str, str]:
    """
    Fetch a Wikipedia article and store it in the database.
    If the article exists in the database and is less than a week old, it will be retrieved from there.
    
    Args:
        db: Database session
        title: Title of the Wikipedia article
        
    Returns:
        tuple: (content: str, status_message: str)
    """
    try:
        should_update, entry = should_update_entry(db, title)

        if not should_update and entry:
            content = entry.content
            status = "Retrieved from database cache."
            log_wiki_action(
                db=db,
                title=title,
                wiki_entry_id=entry.id,
                action_type="check",
                cache_hit=True,
                needed_update=False,
                was_updated=False,
            )
        else:
            # Fetch from Wikipedia API (now directly async)
            content = await get_wikipedia_entry(title)

            if entry:
                # Update existing entry
                entry.content = content
                entry.created_at = datetime.utcnow()
                status = "Article successfully updated in database."
                log_wiki_action(
                    db=db,
                    title=title,
                    wiki_entry_id=entry.id,
                    action_type="update",
                    cache_hit=False,
                    needed_update=True,
                    was_updated=True,
                )
            else:
                # Create new entry
                entry = WikiEntry(title=title, content=content)
                db.add(entry)
                db.commit()  # Commit to get the entry.id
                status = "Article successfully stored in database."
                log_wiki_action(
                    db=db,
                    title=title,
                    wiki_entry_id=entry.id,
                    action_type="create",
                    cache_hit=False,
                    needed_update=True,
                    was_updated=True,
                )

            db.commit()

        return content, status

    except Exception as e:
        raise Exception(f"Error getting wiki entry: {str(e)}")


def log_wiki_action(
    db,
    title: str,
    wiki_entry_id: int | None,
    action_type: str,
    cache_hit: bool,
    needed_update: bool,
    was_updated: bool,
) -> None:
    """
    Log an action performed on a wiki entry.

    Args:
        db: Database session
        title: Title of the article
        wiki_entry_id: ID of the WikiEntry (can be None for new entries)
        action_type: Type of action performed ('check', 'update', 'create')
        cache_hit: Whether the content was served from cache
        needed_update: Whether the entry needed updating
        was_updated: Whether the entry was actually updated
    """
    log_entry = WikiEntryLog(
        wiki_entry_id=wiki_entry_id,
        title=title,
        action_type=action_type,
        cache_hit=cache_hit,
        needed_update=needed_update,
        was_updated=was_updated,
    )
    db.add(log_entry)
    db.commit()


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
                raise Exception(
                    f"Wikipedia API request failed with status {response.status}"
                )

            data = await response.json()

            try:
                page = data["query"]["pages"][0]
                if "missing" in page:
                    raise Exception(f"Wikipedia article '{title}' not found")
                return page["extract"]
            except (KeyError, IndexError):
                raise Exception("Failed to parse Wikipedia API response")


async def get_related_wikipedia_entries(title: str) -> dict:
    """
    Fetch a Wikipedia article and its "See Also" articles asynchronously.

    Args:
        title: The title of the Wikipedia article to fetch

    Returns:
        dict: A dictionary containing the main article and a list of related articles
        {
            'main_article': str,
            'related_articles': list[dict]
        }
    """
    settings = Settings()

    # First get the main article
    main_content = await get_wikipedia_entry(title)

    # Find the "See also" section using regex
    see_also_pattern = r"(?:==\s*See also\s*==\n)(.*?)(?:\n==|\Z)"
    see_also_match = re.search(see_also_pattern, main_content, re.DOTALL)

    related_articles = []
    if see_also_match:
        # Extract the "See also" content
        see_also_content = see_also_match.group(1).strip()

        # Split into lines and clean up
        related_titles = [
            line.strip("* \n") for line in see_also_content.split("\n") if line.strip()
        ]

        # Fetch all related articles concurrently
        async with aiohttp.ClientSession() as session:
            tasks = []
            for related_title in related_titles:
                params = {
                    "action": "query",
                    "format": "json",
                    "titles": related_title,
                    "prop": "extracts",
                    "explaintext": "1",
                    "formatversion": "2",
                }
                tasks.append(session.get(settings.wikipedia_base_url, params=params))

            # Wait for all requests to complete
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            # Process responses
            for title, response in zip(related_titles, responses):
                try:
                    if isinstance(response, Exception):
                        continue

                    data = await response.json()
                    page = data["query"]["pages"][0]

                    if "missing" not in page:
                        related_articles.append(
                            {"title": title, "content": page["extract"]}
                        )
                except (KeyError, IndexError, Exception):
                    continue

    return {"main_article": main_content, "related_articles": related_articles}


def should_update_entry(db, title: str) -> tuple[bool, WikiEntry | None]:
    """
    Check if a wiki entry exists and needs updating (older than 1 week).

    Args:
        db: Database session
        title: Title of the Wikipedia article

    Returns:
        tuple: (should_update: bool, entry: WikiEntry | None)
    """
    entry = db.query(WikiEntry).filter(WikiEntry.title == title).first()
    if not entry:
        return True, None

    week_ago = datetime.utcnow() - timedelta(days=7)
    return entry.created_at < week_ago, entry




def wiki_to_markdown(wiki_text: str) -> str:
    """
    Convert Wikipedia text format to Markdown.

    Args:
        wiki_text: String containing Wikipedia formatted text

    Returns:
        String formatted as Markdown
    """
    # Initialize converted text
    md_text = wiki_text

    # Handle section headers (from most specific to least specific)
    # ==== Level 4 headers ====
    md_text = re.sub(r"====\s*([^=]+?)\s*====", r"#### \1", md_text)
    # === Level 3 headers ===
    md_text = re.sub(r"===\s*([^=]+?)\s*===", r"### \1", md_text)
    # == Level 2 headers ==
    md_text = re.sub(r"==\s*([^=]+?)\s*==", r"## \1", md_text)

    # Handle lists
    # Bullet points
    md_text = re.sub(r"^\*\s*(.+)$", r"* \1", md_text, flags=re.MULTILINE)
    # Numbered lists
    md_text = re.sub(r"^\#\s*(.+)$", r"1. \1", md_text, flags=re.MULTILINE)

    # Handle basic formatting
    # Bold
    md_text = re.sub(r"'''(.+?)'''", r"**\1**", md_text)
    # Italic
    md_text = re.sub(r"''(.+?)''", r"*\1*", md_text)

    # Handle links
    # Internal links with display text: [[target|display]]
    md_text = re.sub(r"\[\[([^|\]]+?)\|([^\]]+?)\]\]", r"[\2](\1)", md_text)
    # Internal links without display text: [[target]]
    md_text = re.sub(r"\[\[([^\]]+?)\]\]", r"[\1](\1)", md_text)
    # External links with display text: [url display]
    md_text = re.sub(r"\[(\S+?)\s+([^\]]+?)\]", r"[\2](\1)", md_text)
    # External links without display text: [url]
    md_text = re.sub(r"\[(\S+?)\]", r"[\1](\1)", md_text)

    # Clean up extra newlines
    md_text = re.sub(r"\n{3,}", "\n\n", md_text)

    return md_text.strip()

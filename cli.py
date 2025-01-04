import typer
import asyncio
from lib import get_wikipedia_entry
from rich import print as rprint
from rich.panel import Panel
from rich.text import Text
from database import init_db, get_db
from models import WikiEntry

app = typer.Typer()


@app.command()
def hello(name: str):
    print(f"Hello {name}")


@app.command()
def get_wiki(title: str):
    """
    Fetch a Wikipedia article and store it in the database.
    If the article exists in the database, it will be retrieved from there.

    Args:
        title: The title of the Wikipedia article to fetch
    """
    try:
        db = next(get_db())
        
        # First check if article exists in database
        cached_entry = db.query(WikiEntry).filter(WikiEntry.title == title).first()
        if cached_entry:
            content = cached_entry.content
            rprint("[yellow]Retrieved from database cache.[/yellow]")
        else:
            # Fetch from Wikipedia API if not in database
            content = asyncio.run(get_wikipedia_entry(title))
            
            # Store in database
            wiki_entry = WikiEntry(title=title, content=content)
            db.add(wiki_entry)
            db.commit()
            rprint("[green]Article successfully stored in database.[/green]")

        # Format and display the content
        text = Text(content, justify="left")
        panel = Panel(text, title=f"Wikipedia: {title}", width=100, padding=(1, 2))
        rprint(panel)

    except Exception as e:
        rprint(f"[red]Error:[/red] {str(e)}")
    finally:
        db.close()


def init():
    init_db()


@app.command()
def list_entries():
    """
    List all Wikipedia articles stored in the local database.
    """
    try:
        db = next(get_db())
        entries = db.query(WikiEntry).order_by(WikiEntry.created_at.desc()).all()

        if not entries:
            rprint("[yellow]No Wikipedia articles found in the database.[/yellow]")
            return

        rprint("[blue]Stored Wikipedia Articles:[/blue]")
        for entry in entries:
            created_at = entry.created_at.strftime("%Y-%m-%d %H:%M:%S")
            rprint(f"[green]• {entry.title}[/green] (stored on {created_at})")

        rprint(f"\nTotal entries: {len(entries)}")

    except Exception as e:
        rprint(f"[red]Error listing entries:[/red] {str(e)}")
    finally:
        db.close()


@app.command()
def get_wiki_related(title: str):
    """
    Fetch a Wikipedia article and all articles listed in its "See Also" section.
    
    Args:
        title: The title of the Wikipedia article to fetch
    """
    try:
        result = asyncio.run(get_related_wikipedia_entries(title))
        
        # Display main article
        main_text = Text(result["main_article"], justify="left")
        main_panel = Panel(main_text, title=f"Wikipedia: {title}", width=100, padding=(1, 2))
        rprint(main_panel)
        
        # Display related articles
        if result["related_articles"]:
            rprint("\n[blue]Related Articles:[/blue]")
            for article in result["related_articles"]:
                rprint(f"\n[green]• {article['title']}[/green]")
                text = Text(article["content"][:500] + "...", justify="left")
                panel = Panel(text, title=f"Wikipedia: {article['title']}", width=100, padding=(1, 2))
                rprint(panel)
        else:
            rprint("\n[yellow]No related articles found.[/yellow]")
            
    except Exception as e:
        rprint(f"[red]Error:[/red] {str(e)}")


if __name__ == "__main__":
    init()  # Initialize database tables
    app()

import typer
import asyncio
from datetime import datetime
from lib import get_wikipedia_entry, get_related_wikipedia_entries, should_update_entry, log_wiki_action
from rich import print as rprint
from rich.panel import Panel
from rich.text import Text
from database import init_db, get_db
from models import WikiEntry, WikiEntryLog

app = typer.Typer()



@app.command()
def hello(name: str):
    print(f"Hello {name}")


@app.command()
def get_wiki(title: str):
    """
    Fetch a Wikipedia article and store it in the database.
    If the article exists in the database and is less than a week old, it will be retrieved from there.
    """
    try:
        db = next(get_db())
        should_update, entry = should_update_entry(db, title)

        if not should_update and entry:
            content = entry.content
            rprint("[yellow]Retrieved from database cache.[/yellow]")
            log_wiki_action(
                db=db,
                title=title,
                wiki_entry_id=entry.id,
                action_type='check',
                cache_hit=True,
                needed_update=False,
                was_updated=False
            )
        else:
            # Fetch from Wikipedia API
            content = asyncio.run(get_wikipedia_entry(title))
            
            if entry:
                # Update existing entry
                entry.content = content
                entry.created_at = datetime.utcnow()
                rprint("[green]Article successfully updated in database.[/green]")
                log_wiki_action(
                    db=db,
                    title=title,
                    wiki_entry_id=entry.id,
                    action_type='update',
                    cache_hit=False,
                    needed_update=True,
                    was_updated=True
                )
            else:
                # Create new entry
                entry = WikiEntry(title=title, content=content)
                db.add(entry)
                db.commit()  # Commit to get the entry.id
                rprint("[green]Article successfully stored in database.[/green]")
                log_wiki_action(
                    db=db,
                    title=title,
                    wiki_entry_id=entry.id,
                    action_type='create',
                    cache_hit=False,
                    needed_update=True,
                    was_updated=True
                )
            
            db.commit()

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
    Store all articles in the database. Updates articles older than a week.
    """
    try:
        db = next(get_db())
        result = asyncio.run(get_related_wikipedia_entries(title))
        
        # Store and display main article
        should_update, main_entry = should_update_entry(db, title)
        
        if not should_update and main_entry:
            rprint(f"[yellow]Main article '{title}' retrieved from cache.[/yellow]")
            log_wiki_action(
                db=db,
                title=title,
                wiki_entry_id=main_entry.id,
                action_type='check',
                cache_hit=True,
                needed_update=False,
                was_updated=False
            )
        else:
            if main_entry:
                main_entry.content = result["main_article"]
                main_entry.created_at = datetime.utcnow()
                rprint(f"[green]Main article '{title}' updated in database.[/green]")
                log_wiki_action(
                    db=db,
                    title=title,
                    wiki_entry_id=main_entry.id,
                    action_type='update',
                    cache_hit=False,
                    needed_update=True,
                    was_updated=True
                )
            else:
                main_entry = WikiEntry(title=title, content=result["main_article"])
                db.add(main_entry)
                db.commit()  # Commit to get the entry.id
                rprint(f"[green]Main article '{title}' stored in database.[/green]")
                log_wiki_action(
                    db=db,
                    title=title,
                    wiki_entry_id=main_entry.id,
                    action_type='create',
                    cache_hit=False,
                    needed_update=True,
                    was_updated=True
                )
            db.commit()

        main_text = Text(result["main_article"], justify="left")
        main_panel = Panel(main_text, title=f"Wikipedia: {title}", width=100, padding=(1, 2))
        rprint(main_panel)
        
        # Store and display related articles
        if result["related_articles"]:
            rprint("\n[blue]Related Articles:[/blue]")
            for article in result["related_articles"]:
                should_update, related_entry = should_update_entry(db, article['title'])
                
                if not should_update and related_entry:
                    rprint(f"[yellow]Related article '{article['title']}' retrieved from cache.[/yellow]")
                else:
                    if related_entry:
                        related_entry.content = article['content']
                        related_entry.created_at = datetime.utcnow()
                        rprint(f"[green]Related article '{article['title']}' updated in database.[/green]")
                    else:
                        related_entry = WikiEntry(title=article['title'], content=article['content'])
                        db.add(related_entry)
                        rprint(f"[green]Related article '{article['title']}' stored in database.[/green]")
                    db.commit()

                # Display article preview
                rprint(f"\n[green]• {article['title']}[/green]")
                text = Text(article["content"][:500] + "...", justify="left")
                panel = Panel(text, title=f"Wikipedia: {article['title']}", width=100, padding=(1, 2))
                rprint(panel)
        else:
            rprint("\n[yellow]No related articles found.[/yellow]")
            
    except Exception as e:
        rprint(f"[red]Error:[/red] {str(e)}")
    finally:
        db.close()


@app.command()
def view_logs(title: str | None = None, limit: int = 20):
    """
    View logs of article actions. Optionally filter by title.
    """
    try:
        db = next(get_db())
        query = db.query(WikiEntryLog).order_by(WikiEntryLog.action_time.desc())
        
        if title:
            query = query.filter(WikiEntryLog.title == title)
        
        logs = query.limit(limit).all()
        
        if not logs:
            rprint("[yellow]No logs found.[/yellow]")
            return

        rprint("[blue]Article Action Logs:[/blue]")
        for log in logs:
            action_time = log.action_time.strftime("%Y-%m-%d %H:%M:%S")
            cache_status = "Cache Hit" if log.cache_hit else "Cache Miss"
            update_status = "Updated" if log.was_updated else "No Update"
            rprint(f"[green]• {log.title}[/green] ({action_time})")
            rprint(f"  Action: {log.action_type}, {cache_status}, {update_status}")

    except Exception as e:
        rprint(f"[red]Error viewing logs:[/red] {str(e)}")
    finally:
        db.close()


if __name__ == "__main__":
    init()  # Initialize database tables
    app()

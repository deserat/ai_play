import sys
import pathlib
import json
from pathlib import Path
from datetime import datetime

sys.path.append(pathlib.Path().resolve())

import typer
import asyncio
from rich import print as rprint
from rich.panel import Panel
from rich.text import Text

from wiki_tools.database import init_db, get_db
from wiki_tools.models import WikiEntry, WikiEntryLog
import wiki_tools.lib
from wiki_tools.lib import (
    get_wikipedia_entry,
    get_related_wikipedia_entries,
    should_update_entry,
    log_wiki_action,
    get_wiki,
)

app = typer.Typer()


@app.command()
def hello(name: str):
    print(f"Hello {name}")


@app.command()
def get_wiki_entry(title: str):
    """
    Fetch a Wikipedia article and store it in the database.
    If the article exists in the database and is less than a week old, it will be retrieved from there.
    """
    try:
        db = next(get_db())
        content, status = asyncio.run(wiki_tools.lib.get_wiki(db, title))

        rprint(f"[yellow]{status}[/yellow]")

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
def db_upgrade():
    """Run database migrations"""
    from alembic.config import Config
    from alembic import command

    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    rprint("[green]Database migrations completed successfully[/green]")


@app.command()
def db_downgrade():
    """Downgrade database by one revision"""
    from alembic.config import Config
    from alembic import command

    alembic_cfg = Config("alembic.ini")
    command.downgrade(alembic_cfg, "-1")
    rprint("[yellow]Database downgraded by one revision[/yellow]")


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
                action_type="check",
                cache_hit=True,
                needed_update=False,
                was_updated=False,
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
                    action_type="update",
                    cache_hit=False,
                    needed_update=True,
                    was_updated=True,
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
                    action_type="create",
                    cache_hit=False,
                    needed_update=True,
                    was_updated=True,
                )
            db.commit()

        main_text = Text(result["main_article"], justify="left")
        main_panel = Panel(
            main_text, title=f"Wikipedia: {title}", width=100, padding=(1, 2)
        )
        rprint(main_panel)

        # Store and display related articles
        if result["related_articles"]:
            rprint("\n[blue]Related Articles:[/blue]")
            for article in result["related_articles"]:
                should_update, related_entry = should_update_entry(db, article["title"])

                if not should_update and related_entry:
                    rprint(
                        f"[yellow]Related article '{article['title']}' retrieved from cache.[/yellow]"
                    )
                    log_wiki_action(
                        db=db,
                        title=article["title"],
                        wiki_entry_id=related_entry.id,
                        action_type="check",
                        cache_hit=True,
                        needed_update=False,
                        was_updated=False,
                    )
                else:
                    if related_entry:
                        related_entry.content = article["content"]
                        related_entry.created_at = datetime.utcnow()
                        rprint(
                            f"[green]Related article '{article['title']}' updated in database.[/green]"
                        )
                        log_wiki_action(
                            db=db,
                            title=article["title"],
                            wiki_entry_id=related_entry.id,
                            action_type="update",
                            cache_hit=False,
                            needed_update=True,
                            was_updated=True,
                        )
                    else:
                        related_entry = WikiEntry(
                            title=article["title"], content=article["content"]
                        )
                        db.add(related_entry)
                        db.commit()  # Commit to get the entry.id
                        rprint(
                            f"[green]Related article '{article['title']}' stored in database.[/green]"
                        )
                        log_wiki_action(
                            db=db,
                            title=article["title"],
                            wiki_entry_id=related_entry.id,
                            action_type="create",
                            cache_hit=False,
                            needed_update=True,
                            was_updated=True,
                        )
                    db.commit()

                # Display article preview
                rprint(f"\n[green]• {article['title']}[/green]")
                text = Text(article["content"][:500] + "...", justify="left")
                panel = Panel(
                    text,
                    title=f"Wikipedia: {article['title']}",
                    width=100,
                    padding=(1, 2),
                )
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


@app.command()
def show_logs(
    title: str | None = None,
    limit: int = 20,
    format: str = "detailed",
    action_type: str | None = None,
):
    """
    Show detailed logs with the most recent entries first.

    Args:
        title: Optional filter by article title
        limit: Number of logs to show (default: 20)
        format: Output format ('detailed' or 'compact')
        action_type: Filter by action type ('check', 'update', 'create')
    """
    try:
        db = next(get_db())
        query = db.query(WikiEntryLog).order_by(WikiEntryLog.action_time.desc())

        # Apply filters
        if title:
            query = query.filter(WikiEntryLog.title == title)
        if action_type:
            query = query.filter(WikiEntryLog.action_type == action_type)

        logs = query.limit(limit).all()

        if not logs:
            rprint("[yellow]No logs found.[/yellow]")
            return

        rprint(f"[blue]Article Action Logs[/blue] (showing {len(logs)} entries)")

        if format == "detailed":
            for log in logs:
                action_time = log.action_time.strftime("%Y-%m-%d %H:%M:%S")
                cache_status = (
                    "[green]Cache Hit[/green]"
                    if log.cache_hit
                    else "[red]Cache Miss[/red]"
                )
                update_status = (
                    "[green]Updated[/green]"
                    if log.was_updated
                    else "[yellow]No Update[/yellow]"
                )

                rprint("─" * 80)
                rprint(f"[bold blue]{log.title}[/bold blue]")
                rprint(f"Time: {action_time}")
                rprint(f"Action: [cyan]{log.action_type.upper()}[/cyan]")
                rprint(f"Cache Status: {cache_status}")
                rprint(f"Update Status: {update_status}")
                rprint(f"Needed Update: {'Yes' if log.needed_update else 'No'}")
        else:  # compact format
            for log in logs:
                action_time = log.action_time.strftime("%Y-%m-%d %H:%M")
                status = "🟢" if log.cache_hit else "🔄" if log.was_updated else "⚪"
                rprint(
                    f"{status} {action_time} | [cyan]{log.action_type:^7}[/cyan] | {log.title}"
                )

        # Show summary
        rprint("\n[blue]Summary:[/blue]")
        total = len(logs)
        cache_hits = sum(1 for log in logs if log.cache_hit)
        updates = sum(1 for log in logs if log.was_updated)
        rprint(f"Total Entries: {total}")
        rprint(f"Cache Hits: {cache_hits} ({cache_hits/total*100:.1f}%)")
        rprint(f"Updates: {updates} ({updates/total*100:.1f}%)")

    except Exception as e:
        rprint(f"[red]Error viewing logs:[/red] {str(e)}")
    finally:
        db.close()


@app.command()
def refresh_all(force: bool = False):
    """
    Refresh all Wikipedia entries in the database.

    Args:
        force: If True, updates all entries regardless of age. If False, only updates entries older than a week.
    """
    """
    Refresh all Wikipedia entries in the database.
    
    Args:
        force: If True, updates all entries regardless of age. If False, only updates entries older than a week.
    """
    try:
        db = next(get_db())
        # Get titles and created_at timestamps
        entries = db.query(WikiEntry.title, WikiEntry.created_at).all()

        if not entries:
            rprint("[yellow]No entries found in database to refresh.[/yellow]")
            return

        rprint(f"[blue]Starting refresh of {len(entries)} articles...[/blue]")

        updated_count = 0
        skipped_count = 0
        error_count = 0

        for entry_title in entries:
            try:
                should_update, _ = should_update_entry(db, entry_title.title, entry_title.created_at)

                if not force and not should_update:
                    rprint(
                        f"[yellow]Skipping '{entry_title.title}' - not old enough to update[/yellow]"
                    )
                    skipped_count += 1
                    continue

                rprint(f"[cyan]Updating '{entry_title.title}'...[/cyan]")

                # Fetch new content
                content = asyncio.run(get_wikipedia_entry(entry_title.title))

                # Get the entry to update
                entry = db.query(WikiEntry).filter(WikiEntry.title == entry_title.title).first()
                if entry:
                    # Update entry
                    entry.content = content
                    entry.created_at = datetime.utcnow()

                    # Log the update
                    log_wiki_action(
                        db=db,
                        title=entry_title.title,
                        wiki_entry_id=entry.id,
                        action_type="update",
                        cache_hit=False,
                        needed_update=True,
                        was_updated=True,
                    )

                db.commit()
                updated_count += 1
                rprint(f"[green]Successfully updated '{entry.title}'[/green]")

            except Exception as e:
                error_count += 1
                rprint(f"[red]Error updating '{entry.title}': {str(e)}[/red]")
                continue

        # Print summary
        rprint("\n[blue]Refresh Summary:[/blue]")
        rprint(f"Total entries: {len(entries)}")
        rprint(f"Updated: [green]{updated_count}[/green]")
        rprint(f"Skipped: [yellow]{skipped_count}[/yellow]")
        if error_count:
            rprint(f"Errors: [red]{error_count}[/red]")

    except Exception as e:
        rprint(f"[red]Error during refresh:[/red] {str(e)}")
    finally:
        db.close()


@app.command()
def db_dump(output_dir: str = "db_dumps"):
    """
    Dump all database tables to JSON files.

    Args:
        output_dir: Directory to store the dump files (default: db_dumps)
    """
    try:
        db = next(get_db())

        # Create output directory if it doesn't exist
        dump_dir = Path(output_dir)
        dump_dir.mkdir(parents=True, exist_ok=True)

        # Generate timestamp for the dump
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Dump WikiEntry table
        entries = db.query(WikiEntry).all()
        entries_data = [
            {
                "id": entry.id,
                "title": entry.title,
                "content": entry.content,
                "created_at": entry.created_at.isoformat(),
                "modified_at": entry.modified_at.isoformat(),
            }
            for entry in entries
        ]

        with open(
            dump_dir / f"wiki_entries_{timestamp}.json", "w", encoding="utf-8"
        ) as f:
            json.dump(entries_data, f, indent=2, ensure_ascii=False)

        # Dump WikiEntryLog table
        logs = db.query(WikiEntryLog).all()
        logs_data = [
            {
                "id": log.id,
                "wiki_entry_id": log.wiki_entry_id,
                "title": log.title,
                "action_type": log.action_type,
                "action_time": log.action_time.isoformat(),
                "cache_hit": log.cache_hit,
                "needed_update": log.needed_update,
                "was_updated": log.was_updated,
            }
            for log in logs
        ]

        with open(
            dump_dir / f"wiki_entry_logs_{timestamp}.json", "w", encoding="utf-8"
        ) as f:
            json.dump(logs_data, f, indent=2, ensure_ascii=False)

        rprint(f"[green]Database successfully dumped to {dump_dir}[/green]")
        rprint(f"Entries file: wiki_entries_{timestamp}.json")
        rprint(f"Logs file: wiki_entry_logs_{timestamp}.json")

    except Exception as e:
        rprint(f"[red]Error dumping database:[/red] {str(e)}")
    finally:
        db.close()


@app.command()
def db_restore(entries_file: str, logs_file: str, clear_existing: bool = True):
    """
    Restore database from JSON dump files.

    Args:
        entries_file: Path to the wiki entries JSON file
        logs_file: Path to the wiki entry logs JSON file
        clear_existing: Whether to clear existing data before restore (default: True)
    """
    try:
        db = next(get_db())

        if clear_existing:
            rprint("[yellow]Clearing existing data...[/yellow]")
            db.query(WikiEntryLog).delete()
            db.query(WikiEntry).delete()
            db.commit()

        # Restore WikiEntry records
        with open(entries_file, "r", encoding="utf-8") as f:
            entries_data = json.load(f)

        for entry_data in entries_data:
            entry = WikiEntry(
                id=entry_data["id"],
                title=entry_data["title"],
                content=entry_data["content"],
                created_at=datetime.fromisoformat(entry_data["created_at"]),
                modified_at=datetime.fromisoformat(entry_data["modified_at"]),
            )
            db.add(entry)

        db.commit()
        rprint(f"[green]Restored {len(entries_data)} wiki entries[/green]")

        # Restore WikiEntryLog records
        with open(logs_file, "r", encoding="utf-8") as f:
            logs_data = json.load(f)

        for log_data in logs_data:
            log = WikiEntryLog(
                id=log_data["id"],
                wiki_entry_id=log_data["wiki_entry_id"],
                title=log_data["title"],
                action_type=log_data["action_type"],
                action_time=datetime.fromisoformat(log_data["action_time"]),
                cache_hit=log_data["cache_hit"],
                needed_update=log_data["needed_update"],
                was_updated=log_data["was_updated"],
            )
            db.add(log)

        db.commit()
        rprint(f"[green]Restored {len(logs_data)} wiki entry logs[/green]")

    except Exception as e:
        db.rollback()
        rprint(f"[red]Error restoring database:[/red] {str(e)}")
    finally:
        db.close()


if __name__ == "__main__":
    init()  # Initialize database tables
    app()

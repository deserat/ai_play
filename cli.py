import typer
import asyncio
from lib import get_wikipedia_entry
from rich import print as rprint
from rich.panel import Panel
from rich.text import Text
from database import init_db

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
        # Run the async function in the event loop
        content = asyncio.run(get_wikipedia_entry(title))

        # Format and display the content
        text = Text(content, justify="left")
        panel = Panel(
            text,
            title=f"Wikipedia: {title}",
            width=100,
            padding=(1, 2)
        )
        rprint(panel)
        rprint("[green]Article successfully stored in database.[/green]")

    except Exception as e:
        rprint(f"[red]Error:[/red] {str(e)}")


def init():
    init_db()


if __name__ == "__main__":
    init()  # Initialize database tables
    app()

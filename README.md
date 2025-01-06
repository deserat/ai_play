# Wiki Tools

A Python-based tool for fetching, storing, and managing Wikipedia articles locally. This project provides both CLI and web interfaces for interacting with Wikipedia content, with features for caching, tracking changes, and managing the local article database.

## Features

- Fetch and cache Wikipedia articles locally
- Track article update history and access patterns
- Convert Wikipedia markup to Markdown
- Web interface for browsing cached articles
- CLI tools for database management
- Backup and restore functionality
- Automatic article refresh for outdated content

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd wiki-tools
```

2. Install dependencies using `uv` (recommended) or `pip`:
```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```

3. Initialize the database:
```bash
python cli.py db-upgrade
```

## Usage

### Command Line Interface

#### Fetch Wikipedia Articles
```bash
# Fetch a single article
python cli.py get-wiki-entry "Article Title"

# Fetch an article and its related articles
python cli.py get-wiki-related "Article Title"
```

#### Manage Local Database
```bash
# List all stored articles
python cli.py list-entries

# View action logs
python cli.py show-logs
python cli.py show-logs --title "Article Title" --format detailed

# Refresh outdated articles
python cli.py refresh-all
python cli.py refresh-all --force  # Refresh all regardless of age

# Backup database
python cli.py db-dump --output-dir my_backups

# Restore from backup
python cli.py db-restore \
    --entries-file my_backups/wiki_entries_20240220_123456.json \
    --logs-file my_backups/wiki_entry_logs_20240220_123456.json
```

### Web Interface

1. Start the web server:
```bash
uvicorn main:app --reload
```

2. Open `http://localhost:8000` in your browser

The web interface provides:
- List of cached articles
- Article viewing with Markdown rendering
- Article fetching interface
- Last modified timestamps

## Database Management

The project uses SQLite with SQLAlchemy and Alembic for database management.

### Database Migrations
```bash
# Apply migrations
python cli.py db-upgrade

# Revert last migration
python cli.py db-downgrade
```

### Backup and Restore
```bash
# Create a backup
python cli.py db-dump

# Restore from backup
python cli.py db-restore --entries-file <path> --logs-file <path>
```

## Project Structure

```
wiki-tools/
├── alembic/              # Database migration scripts
├── web/                  # Web interface files
│   ├── static/          # Static assets
│   └── templates/       # HTML templates
├── wiki_tools/          # Core package
│   ├── models.py        # Database models
│   ├── database.py      # Database configuration
│   └── lib.py          # Core functionality
├── cli.py               # Command line interface
├── main.py              # FastAPI web application
└── config.py            # Configuration settings
```

## Configuration

Configuration is managed through environment variables or a `.env` file:

- `DATABASE_URL`: SQLite database path (default: `sqlite:///./newmexico.db`)
- `WIKIPEDIA_BASE_URL`: Wikipedia API endpoint
- `ITEMS_PER_USER`: Pagination limit

## Development

1. Create a virtual environment:
```bash
uv venv
source .venv/bin/activate
```

2. Install development dependencies:
```bash
uv pip install -e ".[dev]"
```

3. Run tests:
```bash
pytest
```

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]

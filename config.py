from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Awesome API"
    admin_email: str = "vance@themojave.com"
    items_per_user: int = 50
    wikipedia_base_url: str = "https://en.wikipedia.org/w/api.php"
    database_url: str = "sqlite:///./wiki.db"  # Default to SQLite

import sys

sys.path.append("..")

from datetime import datetime
from typing import Union, List

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, Union
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session


from config import Settings
from wiki_tools import models
from wiki_tools.database import get_db
from wiki_tools.lib import wiki_to_markdown, get_wiki

settings = Settings()


class EntryListResponse(BaseModel):
    id: int
    title: str
    modified_at: datetime

    class Config:
        from_attributes = True


class EntryDetailResponse(BaseModel):
    id: int
    title: str
    content: str
    created_at: datetime
    modified_at: datetime

    class Config:
        from_attributes = True


app = FastAPI()
templates = Jinja2Templates(directory="web/templates")
app.mount("/static/", StaticFiles(directory="web/static"))


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Specify your allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/wiki-entries/", response_model=List[EntryListResponse])
def list_wiki_entries(db: Session = Depends(get_db)):
    """
    Get all Wikipedia entries stored in the database.
    Returns only id, title and last modified date.
    """
    entries = (
        db.query(
            models.WikiEntry.id, models.WikiEntry.title, models.WikiEntry.modified_at
        )
        .order_by(models.WikiEntry.modified_at.desc())
        .all()
    )
    return entries


@app.get("/wiki-entries/{entry_id}", response_model=EntryDetailResponse)
def get_wiki_entry(entry_id: int, db: Session = Depends(get_db)):
    """
    Get a specific Wikipedia entry by its ID.
    Returns the complete entry including content converted to Markdown.
    """
    entry = db.query(models.WikiEntry).filter(models.WikiEntry.id == entry_id).first()
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")

    # Create a copy of the entry to avoid modifying the database object
    response = EntryDetailResponse(
        id=entry.id,
        title=entry.title,
        content=wiki_to_markdown(entry.content),  # Convert to markdown
        created_at=entry.created_at,
        modified_at=entry.modified_at,
    )
    return response


@app.post("/wiki-entries/fetch/", response_model=Dict[str, Union[str, str]])
def fetch_wiki_entry(title: str, db: Session = Depends(get_db)):
    """
    Fetch a Wikipedia article by title, store it in the database, and return it.
    If the article exists in the database and is less than a week old, it will be retrieved from there.
    
    Args:
        title: Title of the Wikipedia article to fetch
        db: Database session (injected by FastAPI)
    
    Returns:
        Dict containing the article content and status message
    """
    try:
        content, status = get_wiki(db, title)
        return {
            "content": content,
            "status": status
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

from typing import Union, List
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from .config import Settings
from . import models
from .database import get_db

settings = Settings()


class EntryListResponse(BaseModel):
    id: int
    title: str
    modified_at: datetime

    class Config:
        from_attributes = True


class WikiEntryDetail(BaseModel):
    id: int
    title: str
    content: str
    created_at: datetime
    modified_at: datetime

    class Config:
        from_attributes = True


app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}


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


@app.get("/wiki-entries/{entry_id}", response_model=WikiEntryDetail)
def get_wiki_entry(entry_id: int, db: Session = Depends(get_db)):
    """
    Get a specific Wikipedia entry by its ID.
    Returns the complete entry including content.
    """
    entry = db.query(models.WikiEntry).filter(models.WikiEntry.id == entry_id).first()
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry

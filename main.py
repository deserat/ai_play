from typing import Union, List
from datetime import datetime
from fastapi import FastAPI, Depends
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

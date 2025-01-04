from typing import Union, List
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from . import models
from .database import get_db
from .config import Settings
from pydantic import BaseModel

settings = Settings()

class WikiEntryResponse(BaseModel):
    id: int
    title: str
    content: str
    created_at: str
    modified_at: str

    class Config:
        from_attributes = True

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}

@app.get("/wiki-entries/", response_model=List[WikiEntryResponse])
def list_wiki_entries(db: Session = Depends(get_db)):
    """
    Get all Wikipedia entries stored in the database.
    """
    entries = db.query(models.WikiEntry).order_by(models.WikiEntry.created_at.desc()).all()
    return entries

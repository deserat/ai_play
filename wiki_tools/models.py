from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    func,
    Boolean,
    ForeignKey,
)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class WikiEntry(Base):
    __tablename__ = "wiki_entries"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), unique=True, nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    modified_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self):
        return f"<WikiEntry(title='{self.title}')>"


class WikiEntryLog(Base):
    __tablename__ = "wiki_entry_logs"

    id = Column(Integer, primary_key=True)
    wiki_entry_id = Column(Integer, ForeignKey("wiki_entries.id"), nullable=True)
    title = Column(String(255), nullable=False)
    action_type = Column(String(50), nullable=False)  # 'check', 'update', 'create'
    action_time = Column(DateTime, server_default=func.now(), nullable=False)
    cache_hit = Column(Boolean, nullable=False)
    needed_update = Column(Boolean, nullable=False)
    was_updated = Column(Boolean, nullable=False)

    def __repr__(self):
        return f"<WikiEntryLog(title='{self.title}', action='{self.action_type}')>"

from datetime import datetime
from typing import Literal, Optional, List
from uuid import uuid4

from pydantic import BaseModel, Field


class SourceKey(BaseModel):
    key: str
    country: str
    authority: str
    listing_urls: List[str] = []
    enabled: bool = True
    last_crawled: Optional[datetime] = None


class RegulatoryAlert(BaseModel):
    alert_id: str = Field(default_factory=lambda: uuid4().hex)
    source_key: str
    authority: str
    country: str
    title: str
    url: str
    doc_type: Literal["regulation", "guideline", "circular", "press_release", "other"]
    published: Optional[str] = None
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    impact_summary: Optional[str] = None
    related_products: list[str] = []


class ChangeRecord(BaseModel):
    url: str
    source_key: str
    old_hash: str
    new_hash: str
    similarity: float
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    summary: Optional[str] = None


class ComplianceDeadline(BaseModel):
    deadline_id: str = Field(default_factory=lambda: uuid4().hex)
    title: str
    due_date: str
    product: Optional[str] = None
    source: Literal["manual", "crawled"]
    authority: Optional[str] = None

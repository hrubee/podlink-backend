from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional
from datetime import datetime

class SocialLinkSchema(BaseModel):
    url: HttpUrl
    platform_type: str

class PodcastMetadata(BaseModel):
    external_id: str
    title: str
    description: Optional[str]
    rating: Optional[float] = 0.0
    categories: List[str] = []
    social_links: List[SocialLinkSchema] = []
    last_synced: datetime = Field(default_factory=datetime.utcnow)

class GuestMetadata(BaseModel):
    external_id: str
    name: str
    bio: Optional[str]
    expertise: List[str] = []
    past_appearances_count: int = 0
    last_synced: datetime = Field(default_factory=datetime.utcnow)

class IngestionJobStatus(BaseModel):
    job_id: str
    status: str  # pending, running, completed, failed
    records_processed: int = 0
    errors: List[str] = []

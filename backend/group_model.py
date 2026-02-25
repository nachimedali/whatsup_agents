"""
WhatsAppGroup — stores the groups the bot is allowed to listen in.
Only messages from these group IDs will be processed.
"""

from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime
from database import Base
import uuid


class WhatsAppGroup(Base):
    __tablename__ = "whatsapp_groups"

    id          = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    # The raw WhatsApp group ID, e.g. "1234567890-9876543210@g.us"
    group_id    = Column(String, unique=True, nullable=False)
    # Human-readable name fetched from WhatsApp
    group_name  = Column(String, nullable=True)
    # Whether this group is active (the bot will respond)
    enabled     = Column(Boolean, default=True, nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

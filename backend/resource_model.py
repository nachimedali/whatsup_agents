"""
AgentResource — attached to an agent, defines external context it can access.

Two kinds:
  - repository : inject file contents into the prompt at call time
  - database   : expose as a Claude tool (function calling) so Claude can run queries
"""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey
from database import Base
import uuid


class AgentResource(Base):
    __tablename__ = "agent_resources"

    id          = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id    = Column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    name        = Column(String, nullable=False)   # human label, e.g. "Auth Service Repo"
    kind        = Column(String, nullable=False)   # "repository" | "database"

    # ── Repository fields ───────────────────────────────────────────────────
    repo_path   = Column(String, nullable=True)
    # JSON list of glob patterns relative to repo_path, e.g. ["src/auth/**", "README.md"]
    repo_globs  = Column(JSON, nullable=True, default=list)

    # ── Database fields ─────────────────────────────────────────────────────
    # Full SQLAlchemy connection string
    db_url      = Column(String, nullable=True)
    # Restrict Claude to only these tables (empty = all tables)
    db_tables   = Column(JSON, nullable=True, default=list)

    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

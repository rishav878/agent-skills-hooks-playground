import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status = Column(String(32), nullable=False, default="pending", index=True)
    input = Column(Text, nullable=False)
    output = Column(Text, nullable=True)
    selected_skill = Column(String(128), nullable=True)
    error = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    trace_id = Column(String(64), nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    events = relationship("ExecutionEvent", back_populates="run", lazy="selectin")


class ExecutionEvent(Base):
    __tablename__ = "execution_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(
        String(36), ForeignKey("agent_runs.id"), nullable=False, index=True
    )
    trace_id = Column(String(64), nullable=False)
    event_type = Column(String(32), nullable=False, index=True)
    component = Column(String(32), nullable=False)
    status = Column(String(24), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC), index=True)
    duration_ms = Column(Integer, nullable=True)
    input = Column(Text, nullable=True)
    output = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    metadata_ = Column("metadata", Text, nullable=True)

    run = relationship("AgentRun", back_populates="events")


class Skill(Base):
    __tablename__ = "skills"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(128), nullable=False, unique=True)
    description = Column(Text, nullable=False)
    version = Column(String(32), nullable=False)
    instructions = Column(Text, nullable=False)
    input_schema = Column(Text, nullable=True)
    output_schema = Column(Text, nullable=True)
    allowed_tools = Column(Text, nullable=True)
    metadata_ = Column("metadata", Text, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


class Hook(Base):
    __tablename__ = "hooks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(128), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    lifecycle_event = Column(String(32), nullable=False)
    priority = Column(Integer, nullable=False, default=0)
    enabled = Column(Boolean, nullable=False, default=True)
    metadata_ = Column("metadata", Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))


class Tool(Base):
    __tablename__ = "tools"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(128), nullable=False, unique=True)
    description = Column(Text, nullable=False)
    input_schema = Column(Text, nullable=True)
    output_schema = Column(Text, nullable=True)
    risk_level = Column(String(16), nullable=False, default="medium")
    permissions = Column(Text, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(
        String(36), ForeignKey("agent_runs.id"), nullable=False, index=True
    )
    skill_name = Column(String(128), nullable=False)
    input_summary = Column(Text, nullable=False)
    asker = Column(String(64), nullable=False)
    reason = Column(Text, nullable=True)
    status = Column(String(16), nullable=False, default="pending", index=True)
    state_snapshot = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    decided_at = Column(DateTime, nullable=True)


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    key_hash = Column(String(128), nullable=False, unique=True)
    label = Column(String(128), nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))


class ConversationMemory(Base):
    __tablename__ = "conversation_memory"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(
        String(36), ForeignKey("agent_runs.id"), nullable=False, index=True
    )
    trace_id = Column(String(64), nullable=False)
    skill_name = Column(String(128), nullable=False)
    task = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(256), nullable=False)
    content = Column(Text, nullable=False)
    source = Column(String(256), nullable=True)
    skill_name = Column(String(128), nullable=True, index=True)
    metadata_ = Column("metadata", Text, nullable=True)
    embedding_updated = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))

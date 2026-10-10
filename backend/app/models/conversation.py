import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint, Enum, Text, Float, Integer, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base
import enum

class SenderType(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    system = "system"

class ExecutionTarget(str, enum.Enum):
    hosted = "hosted"
    local_runtime = "local_runtime"
    team_runtime = "team_runtime"

class LifecycleState(str, enum.Enum):
    active = "active"
    archived = "archived"
    deleted = "deleted"

class RequestStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    cancelled = "cancelled"

class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    owner_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    team_id: Mapped[str] = mapped_column(String, ForeignKey("teams.id", ondelete="CASCADE"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Branch Metadata
    parent_conversation_id: Mapped[str] = mapped_column(String, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=True, index=True)
    snapshot_sequence_id: Mapped[int] = mapped_column(Integer, nullable=True)
    lifecycle_state: Mapped[LifecycleState] = mapped_column(Enum(LifecycleState), nullable=False, default=LifecycleState.active)

    # AI Configuration
    ai_provider: Mapped[str] = mapped_column(String, nullable=False, default="mock")
    ai_model: Mapped[str] = mapped_column(String, nullable=False, default="default")
    ai_execution_target: Mapped[ExecutionTarget] = mapped_column(Enum(ExecutionTarget), nullable=False, default=ExecutionTarget.hosted)
    ai_system_instructions: Mapped[str] = mapped_column(Text, nullable=True)
    ai_temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)

    team = relationship("Team")
    participants = relationship("ConversationParticipant", back_populates="conversation", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.sequence_id.asc()")
    shares = relationship("ConversationShare", back_populates="conversation", cascade="all, delete-orphan")
    access_requests = relationship("ConversationAccessRequest", foreign_keys="ConversationAccessRequest.branch_conversation_id", back_populates="branch_conversation", cascade="all, delete-orphan")

class ConversationParticipant(Base):
    __tablename__ = "conversation_participants"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    conversation_id: Mapped[str] = mapped_column(String, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    conversation = relationship("Conversation", back_populates="participants")
    user = relationship("User")

    __table_args__ = (
        UniqueConstraint("conversation_id", "user_id", name="uq_conv_user_participant"),
    )

class Message(Base):
    __tablename__ = "messages"

    from sqlalchemy import FetchedValue
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    sequence_id: Mapped[int] = mapped_column(Integer, FetchedValue(), unique=True, index=True)
    conversation_id: Mapped[str] = mapped_column(String, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    sender_type: Mapped[SenderType] = mapped_column(Enum(SenderType), nullable=False, default=SenderType.user)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship("User")

class ConversationShare(Base):
    __tablename__ = "conversation_shares"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    conversation_id: Mapped[str] = mapped_column(String, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    created_by: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    conversation = relationship("Conversation", back_populates="shares")
    creator = relationship("User")
    access_requests = relationship("ConversationAccessRequest", back_populates="share", cascade="all, delete-orphan")

class ConversationAccessRequest(Base):
    __tablename__ = "conversation_access_requests"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    share_id: Mapped[str] = mapped_column(String, ForeignKey("conversation_shares.id", ondelete="CASCADE"), nullable=False, index=True)
    requester_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_conversation_id: Mapped[str] = mapped_column(String, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[RequestStatus] = mapped_column(Enum(RequestStatus), nullable=False, default=RequestStatus.pending)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    share = relationship("ConversationShare", back_populates="access_requests")
    requester = relationship("User")
    branch_conversation = relationship("Conversation", foreign_keys=[branch_conversation_id], back_populates="access_requests")

    __table_args__ = (
        Index("ix_uq_pending_request", "share_id", "requester_id", unique=True, postgresql_where=status == 'pending'),
    )

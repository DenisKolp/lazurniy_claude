"""
SQLAlchemy database models
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    BigInteger, String, Boolean, DateTime, Text, Integer,
    ForeignKey, Enum as SQLEnum, JSON
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum


class Base(DeclarativeBase):
    """Base class for all models"""
    pass


class UserStatus(enum.Enum):
    """User verification status"""
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class VotingStatus(enum.Enum):
    """Voting status"""
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TicketStatus(enum.Enum):
    """Ticket status"""
    NEW = "new"
    IN_PROGRESS = "in_progress"
    ANSWERED = "answered"
    CLOSED = "closed"


class User(Base):
    """User model"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255))
    first_name: Mapped[Optional[str]] = mapped_column(String(255))
    last_name: Mapped[Optional[str]] = mapped_column(String(255))
    full_name: Mapped[Optional[str]] = mapped_column(String(500))
    phone_number: Mapped[Optional[str]] = mapped_column(String(20))

    # Verification
    status: Mapped[UserStatus] = mapped_column(
        SQLEnum(UserStatus),
        default=UserStatus.PENDING
    )
    verification_documents: Mapped[Optional[str]] = mapped_column(Text)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    rejected_reason: Mapped[Optional[str]] = mapped_column(Text)

    # Profile
    address: Mapped[Optional[str]] = mapped_column(String(500))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_manager: Mapped[bool] = mapped_column(Boolean, default=False)

    # Notifications settings
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationships
    votes: Mapped[list["Vote"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    tickets: Mapped[list["Ticket"]] = relationship(
        back_populates="user",
        foreign_keys="Ticket.user_id",
        cascade="all, delete-orphan"
    )
    created_votings: Mapped[list["Voting"]] = relationship(
        back_populates="creator",
        foreign_keys="Voting.creator_id"
    )
    created_events: Mapped[list["Event"]] = relationship(
        back_populates="creator",
        foreign_keys="Event.creator_id"
    )
    responded_tickets: Mapped[list["Ticket"]] = relationship(
        back_populates="responder",
        foreign_keys="Ticket.responded_by"
    )


class Voting(Base):
    """Voting model"""
    __tablename__ = "votings"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text)

    # Options stored as JSON array
    options: Mapped[dict] = mapped_column(JSON)

    # Status and settings
    status: Mapped[VotingStatus] = mapped_column(
        SQLEnum(VotingStatus),
        default=VotingStatus.DRAFT
    )
    quorum_percent: Mapped[int] = mapped_column(Integer, default=50)

    # Creator
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    creator: Mapped["User"] = relationship(
        back_populates="created_votings",
        foreign_keys=[creator_id]
    )

    # Timing
    starts_at: Mapped[datetime] = mapped_column(DateTime)
    ends_at: Mapped[datetime] = mapped_column(DateTime)

    # Results
    total_votes: Mapped[int] = mapped_column(Integer, default=0)
    results: Mapped[Optional[dict]] = mapped_column(JSON)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationships
    votes: Mapped[list["Vote"]] = relationship(back_populates="voting", cascade="all, delete-orphan")


class Vote(Base):
    """Vote model"""
    __tablename__ = "votes"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Foreign keys
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    voting_id: Mapped[int] = mapped_column(ForeignKey("votings.id"))

    # Vote data
    option_index: Mapped[int] = mapped_column(Integer)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="votes")
    voting: Mapped["Voting"] = relationship(back_populates="votes")


class Event(Base):
    """Event model"""
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text)
    location: Mapped[Optional[str]] = mapped_column(String(500))

    # Timing
    event_date: Mapped[datetime] = mapped_column(DateTime)
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    # Creator (admin)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    creator: Mapped["User"] = relationship(
        back_populates="created_events",
        foreign_keys=[creator_id]
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )


class Ticket(Base):
    """Ticket (Initiative group) model"""
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)

    # User
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped["User"] = relationship(
        back_populates="tickets",
        foreign_keys=[user_id]
    )

    # Content
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text)
    attachments: Mapped[Optional[str]] = mapped_column(Text)  # JSON array of file paths

    # Status
    status: Mapped[TicketStatus] = mapped_column(
        SQLEnum(TicketStatus),
        default=TicketStatus.NEW
    )

    # Response
    response: Mapped[Optional[str]] = mapped_column(Text)
    responded_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    responded_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    responder: Mapped[Optional["User"]] = relationship(
        back_populates="responded_tickets",
        foreign_keys=[responded_by]
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )


class Notification(Base):
    """Notification model"""
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Target (None = all users)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))

    # Content
    title: Mapped[str] = mapped_column(String(500))
    message: Mapped[str] = mapped_column(Text)
    notification_type: Mapped[str] = mapped_column(String(50))  # voting, event, ticket, emergency

    # Status
    sent: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Scheduling
    scheduled_for: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

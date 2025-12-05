"""
CRUD operations for database models
"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from .models import (
    User, UserStatus, Voting, VotingStatus, Vote,
    Event, Ticket, TicketStatus, Notification
)


class UserCRUD:
    """CRUD operations for User model"""

    @staticmethod
    async def get_by_id(session: AsyncSession, user_id: int) -> Optional[User]:
        """Get user by ID"""
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_telegram_id(session: AsyncSession, telegram_id: int) -> Optional[User]:
        """Get user by telegram ID"""
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create(session: AsyncSession, telegram_id: int, **kwargs) -> User:
        """Create new user"""
        user = User(telegram_id=telegram_id, **kwargs)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    @staticmethod
    async def update(session: AsyncSession, user: User, **kwargs) -> User:
        """Update user"""
        for key, value in kwargs.items():
            setattr(user, key, value)
        await session.commit()
        await session.refresh(user)
        return user

    @staticmethod
    async def get_all_verified(session: AsyncSession) -> List[User]:
        """Get all association members"""
        result = await session.execute(
            select(User).where(User.status == UserStatus.VERIFIED)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_pending_verification(session: AsyncSession) -> List[User]:
        """Get users pending verification"""
        result = await session.execute(
            select(User).where(User.status == UserStatus.PENDING)
        )
        return list(result.scalars().all())

    @staticmethod
    async def count_verified(session: AsyncSession) -> int:
        """Count association members"""
        result = await session.execute(
            select(func.count(User.id)).where(User.status == UserStatus.VERIFIED)
        )
        return result.scalar_one()


class VotingCRUD:
    """CRUD operations for Voting model"""

    @staticmethod
    async def create(session: AsyncSession, **kwargs) -> Voting:
        """Create new voting"""
        voting = Voting(**kwargs)
        session.add(voting)
        await session.commit()
        await session.refresh(voting)
        return voting

    @staticmethod
    async def get_by_id(session: AsyncSession, voting_id: int) -> Optional[Voting]:
        """Get voting by ID with creator loaded"""
        result = await session.execute(
            select(Voting)
            .options(selectinload(Voting.creator))
            .where(Voting.id == voting_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_active(session: AsyncSession) -> List[Voting]:
        """Get all active votings"""
        result = await session.execute(
            select(Voting).where(
                and_(
                    Voting.status == VotingStatus.ACTIVE,
                    Voting.ends_at > datetime.utcnow()
                )
            ).order_by(desc(Voting.created_at))
        )
        return list(result.scalars().all())

    @staticmethod
    async def update(session: AsyncSession, voting: Voting, **kwargs) -> Voting:
        """Update voting"""
        for key, value in kwargs.items():
            setattr(voting, key, value)
        await session.commit()
        await session.refresh(voting)
        return voting

    @staticmethod
    async def get_user_votings(session: AsyncSession, user_id: int) -> List[Voting]:
        """Get votings created by user"""
        result = await session.execute(
            select(Voting).where(Voting.creator_id == user_id)
            .order_by(desc(Voting.created_at))
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_draft_votings(session: AsyncSession) -> List[Voting]:
        """Get all draft votings (proposed questions)"""
        result = await session.execute(
            select(Voting).where(Voting.status == VotingStatus.DRAFT)
            .order_by(desc(Voting.created_at))
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_completed(session: AsyncSession) -> List[Voting]:
        """Get all completed votings"""
        result = await session.execute(
            select(Voting).where(Voting.status == VotingStatus.COMPLETED)
            .order_by(desc(Voting.ends_at))
        )
        return list(result.scalars().all())

    @staticmethod
    async def delete(session: AsyncSession, voting: Voting):
        """Delete voting (cancel)"""
        voting.status = VotingStatus.CANCELLED
        await session.commit()
        await session.refresh(voting)


class VoteCRUD:
    """CRUD operations for Vote model"""

    @staticmethod
    async def create(session: AsyncSession, **kwargs) -> Vote:
        """Create new vote"""
        vote = Vote(**kwargs)
        session.add(vote)
        await session.commit()
        await session.refresh(vote)
        return vote

    @staticmethod
    async def get_user_vote(
        session: AsyncSession,
        user_id: int,
        voting_id: int
    ) -> Optional[Vote]:
        """Check if user already voted"""
        result = await session.execute(
            select(Vote).where(
                and_(
                    Vote.user_id == user_id,
                    Vote.voting_id == voting_id
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def count_votes(session: AsyncSession, voting_id: int) -> int:
        """Count votes for voting"""
        result = await session.execute(
            select(func.count(Vote.id)).where(Vote.voting_id == voting_id)
        )
        return result.scalar_one()

    @staticmethod
    async def get_voting_results(session: AsyncSession, voting_id: int) -> dict:
        """Get voting results"""
        result = await session.execute(
            select(Vote.option_index, func.count(Vote.id))
            .where(Vote.voting_id == voting_id)
            .group_by(Vote.option_index)
        )
        return dict(result.all())


class EventCRUD:
    """CRUD operations for Event model"""

    @staticmethod
    async def create(session: AsyncSession, **kwargs) -> Event:
        """Create new event"""
        event = Event(**kwargs)
        session.add(event)
        await session.commit()
        await session.refresh(event)
        return event

    @staticmethod
    async def get_by_id(session: AsyncSession, event_id: int) -> Optional[Event]:
        """Get event by ID"""
        result = await session.execute(
            select(Event).where(Event.id == event_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_upcoming(session: AsyncSession, limit: int = 10) -> List[Event]:
        """Get upcoming events"""
        result = await session.execute(
            select(Event)
            .where(Event.event_date > datetime.utcnow())
            .order_by(Event.event_date)
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_for_reminders(session: AsyncSession, before_hours: int) -> List[Event]:
        """Get events that need reminders (events happening in before_hours +/- 1 hour window)"""
        from datetime import timedelta
        now = datetime.utcnow()
        # Window: from (before_hours - 1) to (before_hours + 1) hours from now
        time_start = now + timedelta(hours=before_hours - 1)
        time_end = now + timedelta(hours=before_hours + 1)

        result = await session.execute(
            select(Event).where(
                and_(
                    Event.reminder_sent == False,
                    Event.event_date >= time_start,
                    Event.event_date <= time_end
                )
            )
        )
        return list(result.scalars().all())

    @staticmethod
    async def update(session: AsyncSession, event: Event, **kwargs) -> Event:
        """Update event"""
        for key, value in kwargs.items():
            setattr(event, key, value)
        await session.commit()
        await session.refresh(event)
        return event

    @staticmethod
    async def delete(session: AsyncSession, event: Event):
        """Delete event"""
        await session.delete(event)
        await session.commit()


class TicketCRUD:
    """CRUD operations for Ticket model"""

    @staticmethod
    async def create(session: AsyncSession, **kwargs) -> Ticket:
        """Create new ticket"""
        ticket = Ticket(**kwargs)
        session.add(ticket)
        await session.commit()
        await session.refresh(ticket)
        return ticket

    @staticmethod
    async def get_by_id(session: AsyncSession, ticket_id: int) -> Optional[Ticket]:
        """Get ticket by ID"""
        result = await session.execute(
            select(Ticket).where(Ticket.id == ticket_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_tickets(session: AsyncSession, user_id: int) -> List[Ticket]:
        """Get user's tickets"""
        result = await session.execute(
            select(Ticket)
            .where(Ticket.user_id == user_id)
            .order_by(desc(Ticket.created_at))
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_open_tickets(session: AsyncSession) -> List[Ticket]:
        """Get open tickets"""
        result = await session.execute(
            select(Ticket)
            .where(Ticket.status.in_([TicketStatus.NEW, TicketStatus.IN_PROGRESS]))
            .order_by(desc(Ticket.created_at))
        )
        return list(result.scalars().all())

    @staticmethod
    async def update(session: AsyncSession, ticket: Ticket, **kwargs) -> Ticket:
        """Update ticket"""
        for key, value in kwargs.items():
            setattr(ticket, key, value)
        await session.commit()
        await session.refresh(ticket)
        return ticket


class NotificationCRUD:
    """CRUD operations for Notification model"""

    @staticmethod
    async def create(session: AsyncSession, **kwargs) -> Notification:
        """Create new notification"""
        notification = Notification(**kwargs)
        session.add(notification)
        await session.commit()
        await session.refresh(notification)
        return notification

    @staticmethod
    async def get_pending(session: AsyncSession) -> List[Notification]:
        """Get pending notifications"""
        result = await session.execute(
            select(Notification).where(
                and_(
                    Notification.sent == False,
                    or_(
                        Notification.scheduled_for == None,
                        Notification.scheduled_for <= datetime.utcnow()
                    )
                )
            )
        )
        return list(result.scalars().all())

    @staticmethod
    async def mark_sent(session: AsyncSession, notification: Notification):
        """Mark notification as sent"""
        notification.sent = True
        notification.sent_at = datetime.utcnow()
        await session.commit()

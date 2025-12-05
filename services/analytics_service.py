"""
Analytics service
"""
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_
from database.session import async_session_maker
from database.models import User, Voting, Vote, Event, Ticket, UserStatus


class AnalyticsService:
    """Service for analytics and statistics"""

    @staticmethod
    async def get_user_statistics():
        """Get user statistics"""
        async with async_session_maker() as session:
            total = await session.scalar(select(func.count(User.id)))
            verified = await session.scalar(
                select(func.count(User.id)).where(User.status == UserStatus.VERIFIED)
            )
            pending = await session.scalar(
                select(func.count(User.id)).where(User.status == UserStatus.PENDING)
            )

            return {
                'total': total,
                'verified': verified,
                'pending': pending
            }

    @staticmethod
    async def get_voting_statistics():
        """Get voting statistics"""
        async with async_session_maker() as session:
            total_votings = await session.scalar(select(func.count(Voting.id)))
            total_votes = await session.scalar(select(func.count(Vote.id)))

            # Get average participation rate
            result = await session.execute(
                select(
                    Voting.id,
                    func.count(Vote.id).label('vote_count')
                )
                .outerjoin(Vote)
                .group_by(Voting.id)
            )

            votings_data = result.all()
            avg_participation = sum(v[1] for v in votings_data) / len(votings_data) if votings_data else 0

            return {
                'total_votings': total_votings,
                'total_votes': total_votes,
                'avg_participation': round(avg_participation, 2)
            }

    @staticmethod
    async def get_activity_statistics(days: int = 30):
        """Get activity statistics for last N days"""
        since = datetime.utcnow() - timedelta(days=days)

        async with async_session_maker() as session:
            new_users = await session.scalar(
                select(func.count(User.id)).where(User.created_at >= since)
            )
            new_votings = await session.scalar(
                select(func.count(Voting.id)).where(Voting.created_at >= since)
            )
            new_tickets = await session.scalar(
                select(func.count(Ticket.id)).where(Ticket.created_at >= since)
            )
            new_events = await session.scalar(
                select(func.count(Event.id)).where(Event.created_at >= since)
            )

            return {
                'period_days': days,
                'new_users': new_users,
                'new_votings': new_votings,
                'new_tickets': new_tickets,
                'new_events': new_events
            }

    @staticmethod
    async def get_top_active_users(limit: int = 10):
        """Get most active users by votes and tickets"""
        async with async_session_maker() as session:
            # Users with most votes
            result = await session.execute(
                select(
                    User.id,
                    User.first_name,
                    User.last_name,
                    func.count(Vote.id).label('vote_count')
                )
                .join(Vote)
                .group_by(User.id, User.first_name, User.last_name)
                .order_by(func.count(Vote.id).desc())
                .limit(limit)
            )

            return result.all()

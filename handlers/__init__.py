"""
Handlers package initialization
"""
from .start import register_start_handlers
from .voting import register_voting_handlers
from .events import register_events_handlers
from .tickets import register_tickets_handlers
from .admin import register_admin_handlers

__all__ = [
    'register_start_handlers',
    'register_voting_handlers',
    'register_events_handlers',
    'register_tickets_handlers',
    'register_admin_handlers'
]

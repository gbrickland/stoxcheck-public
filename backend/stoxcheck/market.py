"""US regular-session checks used to avoid collecting outside the intended schedule."""

from datetime import datetime, time
from zoneinfo import ZoneInfo

NEW_YORK = ZoneInfo("America/New_York")


def is_regular_session(now: datetime | None = None) -> bool:
    """Return true only during weekday 09:30–16:00 New York time."""
    """Basic session guard; Cloud Scheduler will later add an exchange holiday calendar."""
    local = (now or datetime.now(NEW_YORK)).astimezone(NEW_YORK)
    return local.weekday() < 5 and time(9, 30) <= local.time() < time(16, 0)

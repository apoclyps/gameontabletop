from datetime import date, time, timedelta

from dateutil.rrule import MONTHLY, WEEKLY, rrule


def generate_occurrence_dates(
    recurrence: str,
    start_date: date,
    from_date: date,
    to_date: date,
    end_date: date | None = None,
) -> list[date]:
    """Return occurrence dates within [from_date, to_date] for the given recurrence."""
    if recurrence == "once":
        if from_date <= start_date <= to_date:
            return [start_date]
        return []

    effective_until = min(to_date, end_date) if end_date else to_date

    if recurrence == "weekly":
        rule = rrule(WEEKLY, dtstart=start_date, until=effective_until)
    elif recurrence == "biweekly":
        rule = rrule(WEEKLY, interval=2, dtstart=start_date, until=effective_until)
    elif recurrence == "monthly":
        rule = rrule(MONTHLY, dtstart=start_date, until=effective_until)
    else:
        return []

    return [d.date() for d in rule if d.date() >= from_date]


async def ensure_occurrences_generated(series, session, weeks_ahead: int = 8) -> None:
    """Create missing auto-generated occurrences for the next `weeks_ahead` weeks."""
    from sqlalchemy import select

    from app.models.scheduler import NightOccurrence

    today = date.today()
    target_end = today + timedelta(weeks=weeks_ahead)
    start = series.series_start_date or today

    if series.status != "active":
        return

    if series.recurrence == "once":
        existing = await session.execute(
            select(NightOccurrence)
            .where(NightOccurrence.series_id == series.id)
            .where(NightOccurrence.is_auto_generated.is_(True))
        )
        if existing.scalar_one_or_none():
            return

    existing_result = await session.execute(
        select(NightOccurrence.occurrence_date)
        .where(NightOccurrence.series_id == series.id)
        .where(NightOccurrence.is_auto_generated.is_(True))
        .where(NightOccurrence.occurrence_date >= today)
    )
    existing_dates = set(existing_result.scalars().all())

    new_dates = generate_occurrence_dates(
        series.recurrence, start, today, target_end, series.series_end_date
    )

    default_time = series.default_start_time or time(19, 0)

    new_occurrences = [
        NightOccurrence(
            series_id=series.id,
            occurrence_date=d,
            start_time=default_time,
            location_id=series.default_location_id,
            is_auto_generated=True,
            status="scheduled",
        )
        for d in new_dates
        if d not in existing_dates
    ]

    if new_occurrences:
        session.add_all(new_occurrences)
        await session.commit()

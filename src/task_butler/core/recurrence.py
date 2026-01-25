"""Recurrence logic for generating task instances."""

from datetime import datetime, timedelta
from calendar import monthrange

from ..models.task import Task, RecurrenceRule
from ..models.enums import Frequency, Status


class RecurrenceGenerator:
    """Generate instances of recurring tasks."""

    def get_next_occurrence(
        self, rule: RecurrenceRule, after: datetime
    ) -> datetime | None:
        """Calculate the next occurrence after the given date."""
        if rule.end_date and after >= rule.end_date:
            return None

        if rule.frequency == Frequency.DAILY:
            return self._next_daily(rule, after)
        elif rule.frequency == Frequency.WEEKLY:
            return self._next_weekly(rule, after)
        elif rule.frequency == Frequency.MONTHLY:
            return self._next_monthly(rule, after)
        elif rule.frequency == Frequency.YEARLY:
            return self._next_yearly(rule, after)

        return None

    def _next_daily(self, rule: RecurrenceRule, after: datetime) -> datetime:
        """Get next daily occurrence."""
        next_date = after + timedelta(days=rule.interval)
        return next_date.replace(hour=0, minute=0, second=0, microsecond=0)

    def _next_weekly(self, rule: RecurrenceRule, after: datetime) -> datetime:
        """Get next weekly occurrence."""
        if rule.days_of_week:
            # Find next matching day of week
            current = after + timedelta(days=1)
            days_checked = 0

            while days_checked < 7 * rule.interval + 7:
                if current.weekday() in rule.days_of_week:
                    return current.replace(hour=0, minute=0, second=0, microsecond=0)
                current += timedelta(days=1)
                days_checked += 1

        # Default: same day next week(s)
        next_date = after + timedelta(weeks=rule.interval)
        return next_date.replace(hour=0, minute=0, second=0, microsecond=0)

    def _next_monthly(self, rule: RecurrenceRule, after: datetime) -> datetime:
        """Get next monthly occurrence."""
        # Calculate target month
        target_month = after.month + rule.interval
        target_year = after.year

        while target_month > 12:
            target_month -= 12
            target_year += 1

        # Determine day of month
        if rule.day_of_month:
            day = rule.day_of_month
        else:
            day = after.day

        # Ensure day is valid for the month
        max_day = monthrange(target_year, target_month)[1]
        day = min(day, max_day)

        return datetime(target_year, target_month, day)

    def _next_yearly(self, rule: RecurrenceRule, after: datetime) -> datetime:
        """Get next yearly occurrence."""
        target_year = after.year + rule.interval

        # Handle Feb 29 edge case
        if after.month == 2 and after.day == 29:
            # Check if target year has Feb 29
            if monthrange(target_year, 2)[1] < 29:
                return datetime(target_year, 2, 28)

        return datetime(target_year, after.month, after.day)

    def generate_instances(
        self,
        template: Task,
        start_date: datetime,
        end_date: datetime,
    ) -> list[Task]:
        """Generate task instances for a recurring task within a date range."""
        if not template.recurrence:
            return []

        instances = []
        current_date = start_date

        while True:
            next_date = self.get_next_occurrence(template.recurrence, current_date)

            if next_date is None or next_date > end_date:
                break

            # Create instance
            instance = Task(
                title=template.title,
                description=template.description,
                priority=template.priority,
                tags=template.tags.copy(),
                project=template.project,
                parent_id=template.parent_id,
                estimated_hours=template.estimated_hours,
                due_date=next_date,
                recurrence_parent_id=template.id,
            )

            instances.append(instance)
            current_date = next_date

        return instances

    def should_generate_next(self, template: Task, existing_instances: list[Task]) -> bool:
        """Check if we should generate the next instance of a recurring task."""
        if not template.recurrence:
            return False

        # Find the latest instance
        if not existing_instances:
            return True

        open_instances = [t for t in existing_instances if t.is_open]

        # If there are no open instances, we might need to generate one
        return len(open_instances) == 0

    def create_next_instance(self, template: Task) -> Task | None:
        """Create the next instance of a recurring task."""
        if not template.recurrence:
            return None

        next_date = self.get_next_occurrence(template.recurrence, datetime.now())
        if next_date is None:
            return None

        return Task(
            title=template.title,
            description=template.description,
            priority=template.priority,
            tags=template.tags.copy(),
            project=template.project,
            parent_id=template.parent_id,
            estimated_hours=template.estimated_hours,
            due_date=next_date,
            recurrence_parent_id=template.id,
        )

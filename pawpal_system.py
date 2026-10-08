"""PawPal+ logic layer: backend classes for owners, pets, tasks, and scheduling."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time
from typing import Optional


@dataclass
class TimeWindow:
    """A block of time when the owner is available. start must be before end."""

    start: time
    end: time

    def __post_init__(self) -> None:
        # TODO: raise ValueError if start is not before end
        pass

    def duration_minutes(self) -> int:
        pass

    def fits(self, start: time, duration_minutes: int) -> bool:
        """Return True if a task starting at `start` ends within this window."""
        pass

    def overlaps(self, other: TimeWindow) -> bool:
        """Return True if the windows overlap. Windows that only touch do not overlap."""
        pass


@dataclass
class Task:
    """A single pet care activity."""

    description: str
    duration_minutes: int
    priority: str  # "low", "medium", or "high"
    time: Optional[time] = None  # required start time, e.g. meds at 08:00; None lets the scheduler choose
    frequency: str = "daily"  # "daily", "weekly", or "once"
    completed: bool = False

    def mark_complete(self) -> None:
        pass


@dataclass
class Pet:
    name: str
    species: str
    breed: str = ""
    age: int = 0
    special_needs: list[str] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        pass

    def remove_task(self, description: str) -> None:
        pass

    def get_pending_tasks(self) -> list[Task]:
        pass


@dataclass
class Owner:
    name: str
    availability: list[TimeWindow] = field(default_factory=list)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        pass

    def remove_pet(self, name: str) -> None:
        pass

    def get_all_tasks(self) -> list[Task]:
        pass

    def add_availability(self, window: TimeWindow) -> None:
        """Add a window. Raises ValueError if it overlaps an existing window."""
        pass

    def total_available_minutes(self) -> int:
        pass


@dataclass
class ScheduledItem:
    task: Task
    pet: Pet
    start_time: time
    end_time: time
    reason: str


@dataclass
class DailyPlan:
    plan_date: date
    items: list[ScheduledItem] = field(default_factory=list)

    def total_minutes(self) -> int:
        pass


class Scheduler:
    """Builds a daily plan from the owner's pets, tasks, and availability.

    Tasks are never split across windows. If a task doesn't fit, try the next
    window; if it fits in none, leave it out of the plan.

    A set-time task that conflicts with one already scheduled is left out of
    the plan.
    """

    def __init__(self, owner: Owner) -> None:
        self.owner = owner

    def generate_plan(self) -> DailyPlan:
        pass

    def sort_by_priority(self, tasks: list[Task]) -> list[Task]:
        pass

    def filter_tasks(
        self, pet_name: Optional[str] = None, completed: Optional[bool] = None
    ) -> list[Task]:
        pass

    def detect_conflicts(
        self, candidate: ScheduledItem, items: list[ScheduledItem]
    ) -> list[ScheduledItem]:
        """Return the already-scheduled items that overlap `candidate`.

        If any are returned, the candidate is not added to the plan. Set-time
        tasks are placed in priority order, so the higher-priority task keeps
        its slot.
        """
        pass

    def explain_plan(self, plan: DailyPlan) -> str:
        pass

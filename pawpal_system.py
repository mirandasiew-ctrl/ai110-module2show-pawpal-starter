"""PawPal+ logic layer: backend classes for owners, pets, tasks, and scheduling."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time
from typing import ClassVar, Optional

# Lower number = higher priority. Used for sorting and for validating Task.priority.
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def to_minutes(t: time) -> int:
    """Convert a time to minutes since midnight (datetime.time has no arithmetic)."""
    pass


def from_minutes(minutes: int) -> time:
    """Convert minutes since midnight back to a time."""
    pass


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
    pet_id: Optional[int] = None  # set by Pet

    def __post_init__(self) -> None:
        # TODO: raise ValueError if priority is not in PRIORITY_ORDER
        # TODO: raise ValueError if duration_minutes is not greater than 0
        pass

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
    pet_id: int = field(init=False)

    _max_pet_id: ClassVar[int] = 0  # greatest pet_id assigned so far

    def __post_init__(self) -> None:
        # TODO: set pet_id to _max_pet_id + 1, then update _max_pet_id
        # TODO: set pet_id on any tasks passed in through `tasks`
        pass

    def add_task(self, task: Task) -> None:
        """Add a task and set its pet_id to this pet's id.

        Raises ValueError if the task already belongs to a different pet.
        """
        pass

    def remove_task(self, description: str) -> None:
        """Remove the task and set its pet_id back to None."""
        pass

    def get_pending_tasks(self) -> list[Task]:
        pass


@dataclass
class Owner:
    name: str
    availability: list[TimeWindow] = field(default_factory=list)
    pets: list[Pet] = field(default_factory=list)

    def __post_init__(self) -> None:
        # TODO: raise ValueError if any windows passed in through `availability` overlap
        # TODO: raise ValueError if any pets passed in through `pets` share a pet_id
        pass

    def add_pet(self, pet: Pet) -> None:
        """Add a pet. Raises ValueError if a pet with the same pet_id is already added."""
        pass

    def remove_pet(self, pet_id: int) -> None:
        pass

    def get_pet(self, pet_id: int) -> Optional[Pet]:
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
    task: Task  # task.pet_id identifies the pet
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

    Only pending (not completed) tasks are planned. Completed tasks do not
    reset, so frequency is stored but does not change the plan.

    1. Set-time tasks are placed first, in priority order. One that doesn't fit
       entirely inside a window (window.fits(task.time, task.duration_minutes)),
       or conflicts with a task already placed, is left out of the plan.
    2. The free gaps are the windows (sorted by start time) minus the set-time
       tasks.
    3. Remaining tasks, in priority order, go into the first gap they fit; that
       gap then shrinks. Earlier gaps stay usable by later, shorter tasks.
       A gap shrunk to zero length is removed, not kept as a TimeWindow.

    Tasks are never split across gaps. A task that fits in no gap is left out
    of the plan.
    """

    def __init__(self, owner: Owner) -> None:
        self.owner = owner

    def generate_plan(self) -> DailyPlan:
        """Build today's plan. Items are sorted by start_time before returning,
        since set-time tasks are placed before the others."""
        pass

    def sort_by_priority(self, tasks: list[Task]) -> list[Task]:
        """Sort by PRIORITY_ORDER; ties go to the shorter task first."""
        pass

    def filter_tasks(
        self, pet_id: Optional[int] = None, completed: Optional[bool] = None
    ) -> list[Task]:
        pass

    def detect_conflicts(
        self, candidate: ScheduledItem, items: list[ScheduledItem]
    ) -> list[ScheduledItem]:
        """Return the already-scheduled items that overlap `candidate`.

        Only needed for set-time tasks; other tasks are placed in free gaps,
        which can't overlap anything. If any are returned, the candidate is
        left out of the plan.
        """
        pass

    def find_free_gaps(self, placed: list[ScheduledItem]) -> list[TimeWindow]:
        """Return the owner's windows, sorted by start, minus the placed items.

        Zero-length gaps (e.g. a set-time task at the very start of a window)
        are skipped, since TimeWindow requires start < end.
        """
        pass

    def explain_plan(self, plan: DailyPlan) -> str:
        """Describe each item. If the task's pet was removed (get_pet returns
        None), label it as a removed pet instead of failing."""
        pass

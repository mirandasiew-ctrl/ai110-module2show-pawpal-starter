"""PawPal+ logic layer: backend classes for owners, pets, tasks, and scheduling."""

from __future__ import annotations

from dataclasses import dataclass, field, fields, replace
from datetime import date, time, timedelta
from typing import ClassVar, Optional

# Lower number = higher priority. Used for sorting and for validating Task.priority.
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}

# Days until the next occurrence of a recurring task. "once" tasks don't recur.
RECURRENCE_DAYS = {"daily": 1, "weekly": 7}
FREQUENCIES = (*RECURRENCE_DAYS, "once")

MINUTES_PER_DAY = 24 * 60


def to_minutes(t: time) -> int:
    """Convert a time to minutes since midnight (datetime.time has no arithmetic)."""
    return t.hour * 60 + t.minute


def from_minutes(minutes: int) -> time:
    """Convert minutes since midnight back to a time."""
    if not 0 <= minutes < MINUTES_PER_DAY:
        raise ValueError(f"{minutes} minutes is outside a single day")
    return time(minutes // 60, minutes % 60)


@dataclass
class TimeWindow:
    """A block of time when the owner is available. start must be before end."""

    start: time
    end: time

    def __post_init__(self) -> None:
        """Raise ValueError if start is not before end."""
        if self.start >= self.end:
            raise ValueError(
                f"Window start {self.start:%H:%M} must be before end {self.end:%H:%M}"
            )

    def duration_minutes(self) -> int:
        """Return the length of the window in minutes."""
        return to_minutes(self.end) - to_minutes(self.start)

    def fits(self, start: time, duration_minutes: int) -> bool:
        """Return True if a task starting at `start` ends within this window."""
        task_start = to_minutes(start)
        return (
            to_minutes(self.start) <= task_start
            and task_start + duration_minutes <= to_minutes(self.end)
        )

    def overlaps(self, other: TimeWindow) -> bool:
        """Return True if the windows overlap. Windows that only touch do not overlap."""
        return self.start < other.end and other.start < self.end


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
    due_date: date = field(default_factory=date.today)

    def __post_init__(self) -> None:
        """Raise ValueError for an unknown priority or frequency, or a non-positive duration."""
        if self.priority not in PRIORITY_ORDER:
            raise ValueError(
                f"Priority must be one of {', '.join(PRIORITY_ORDER)}, got {self.priority!r}"
            )
        if self.frequency not in FREQUENCIES:
            raise ValueError(
                f"Frequency must be one of {', '.join(FREQUENCIES)}, got {self.frequency!r}"
            )
        if self.duration_minutes <= 0:
            raise ValueError("duration_minutes must be greater than 0")

    def update(self, **changes) -> None:
        """Change fields with the same validation as a new task; nothing changes if invalid.

        Use Owner.move_task() to move a task to a different pet.
        """
        if "pet_id" in changes:
            raise ValueError("Use Owner.move_task() to change a task's pet")
        updated = replace(self, **changes)  # runs __post_init__ validation
        for f in fields(self):
            setattr(self, f.name, getattr(updated, f.name))

    def is_due(self, on: date) -> bool:
        """Return True if the task is not completed and is due on or before `on`."""
        return not self.completed and self.due_date <= on

    def mark_complete(self) -> Optional[Task]:
        """Mark this task as done and return its next occurrence, if it recurs.

        Daily tasks come back the next day and weekly tasks 7 days later,
        counted from the due date (or from today, if the task was overdue).
        "once" tasks return None. The new task is not attached to a pet yet;
        use Pet.complete_task() to complete and re-add in one step.
        """
        self.completed = True
        if self.frequency not in RECURRENCE_DAYS:
            return None
        next_due = max(self.due_date, date.today()) + timedelta(days=RECURRENCE_DAYS[self.frequency])
        return replace(self, completed=False, pet_id=None, due_date=next_due)


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
        """Assign the next pet_id and attach any tasks passed to the constructor."""
        Pet._max_pet_id += 1
        self.pet_id = Pet._max_pet_id

        # Route tasks passed to the constructor through add_task() so they get
        # this pet's id and the same checks.
        initial_tasks, self.tasks = self.tasks, []
        for task in initial_tasks:
            self.add_task(task)

    def add_task(self, task: Task) -> None:
        """Add a task and set its pet_id to this pet's id.

        Raises ValueError if the task already belongs to a different pet, or
        has already been added to this pet.
        """
        if task.pet_id is not None and task.pet_id != self.pet_id:
            raise ValueError(f"Task {task.description!r} already belongs to another pet")
        if any(t is task for t in self.tasks):
            raise ValueError(f"Task {task.description!r} is already added to {self.name}")
        task.pet_id = self.pet_id
        self.tasks.append(task)

    def remove_task(self, task: Task | str) -> None:
        """Remove the task and set its pet_id back to None.

        Pass the Task itself, or a description to remove the first task with
        that description. Raises ValueError if there is no match.
        """
        for i, t in enumerate(self.tasks):
            matches = (t is task) if isinstance(task, Task) else (t.description == task)
            if matches:
                del self.tasks[i]
                t.pet_id = None
                return
        label = task.description if isinstance(task, Task) else task
        raise ValueError(f"{self.name} has no task {label!r}")

    def complete_task(self, task: Task) -> Optional[Task]:
        """Mark one of this pet's tasks complete and add its next occurrence, if any."""
        if not any(t is task for t in self.tasks):
            raise ValueError(f"Task {task.description!r} does not belong to {self.name}")
        next_task = task.mark_complete()
        if next_task is not None:
            self.add_task(next_task)
        return next_task

    def get_pending_tasks(self) -> list[Task]:
        """Return this pet's tasks that are not completed."""
        return [task for task in self.tasks if not task.completed]


@dataclass
class Owner:
    name: str
    availability: list[TimeWindow] = field(default_factory=list)
    pets: list[Pet] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate windows and pets passed to the constructor."""
        # Route lists passed to the constructor through the add_* methods so
        # they get the same overlap and duplicate checks.
        initial_windows, self.availability = self.availability, []
        for window in initial_windows:
            self.add_availability(window)

        initial_pets, self.pets = self.pets, []
        for pet in initial_pets:
            self.add_pet(pet)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet. Raises ValueError if a pet with the same pet_id is already added."""
        if self.get_pet(pet.pet_id) is not None:
            raise ValueError(f"{pet.name} is already added")
        self.pets.append(pet)

    def remove_pet(self, pet_id: int) -> None:
        """Remove the pet with this pet_id. Raises ValueError if there is none."""
        pet = self.get_pet(pet_id)
        if pet is None:
            raise ValueError(f"No pet with id {pet_id}")
        self.pets.remove(pet)

    def get_pet(self, pet_id: int) -> Optional[Pet]:
        """Return the pet with this pet_id, or None if it isn't found."""
        return next((pet for pet in self.pets if pet.pet_id == pet_id), None)

    def get_all_tasks(self) -> list[Task]:
        """Return every task across all of this owner's pets."""
        return [task for pet in self.pets for task in pet.tasks]

    def move_task(self, task: Task, to_pet_id: int) -> None:
        """Move a task from its current pet to another of this owner's pets."""
        new_pet = self.get_pet(to_pet_id)
        old_pet = self.get_pet(task.pet_id)
        if new_pet is None or old_pet is None:
            raise ValueError("Both pets must belong to this owner")
        if new_pet is old_pet:
            return
        old_pet.remove_task(task)
        new_pet.add_task(task)

    def add_availability(self, window: TimeWindow) -> None:
        """Add a window. Raises ValueError if it overlaps an existing window."""
        for existing in self.availability:
            if window.overlaps(existing):
                raise ValueError(
                    f"{window.start:%H:%M}-{window.end:%H:%M} overlaps your "
                    f"{existing.start:%H:%M}-{existing.end:%H:%M} window"
                )
        self.availability.append(window)

    def remove_availability(self, window: TimeWindow) -> None:
        """Remove this window. Raises ValueError if it isn't one of the owner's windows."""
        for i, w in enumerate(self.availability):
            if w is window:
                del self.availability[i]
                return
        raise ValueError("That window isn't in your availability")

    def update_availability(self, old: TimeWindow, new: TimeWindow) -> None:
        """Replace a window, keeping the old one if the new one overlaps another window."""
        index = next((i for i, w in enumerate(self.availability) if w is old), None)
        if index is None:
            raise ValueError("That window isn't in your availability")
        del self.availability[index]
        try:
            self.add_availability(new)
        except ValueError:
            self.availability.insert(index, old)
            raise

    def total_available_minutes(self) -> int:
        """Return the combined length of all availability windows in minutes."""
        return sum(window.duration_minutes() for window in self.availability)


@dataclass
class ScheduledItem:
    task: Task  # task.pet_id identifies the pet
    start_time: time
    end_time: time
    reason: str


@dataclass
class SkippedTask:
    """A due task that generate_plan() left out: its set time is outside the
    owner's windows, it conflicts with a higher-priority set-time task, or no
    free gap is long enough."""

    task: Task  # task.pet_id identifies the pet
    reason: str  # why it was left out of the plan


@dataclass
class DailyPlan:
    plan_date: date
    items: list[ScheduledItem] = field(default_factory=list)
    skipped: list[SkippedTask] = field(default_factory=list)

    def total_minutes(self) -> int:
        """Return the total scheduled time in minutes."""
        return sum(
            to_minutes(item.end_time) - to_minutes(item.start_time) for item in self.items
        )


class Scheduler:
    """Builds a daily plan from the owner's pets, tasks, and availability.

    The Scheduler works across all of the owner's pets: it always reads tasks
    through Owner.get_all_tasks(), never from a single Pet.

    Only tasks due on the plan's date (not completed, due_date on or before
    it) are planned. Recurring tasks come back through Pet.complete_task().

    1. Set-time tasks are placed first, in priority order. One that doesn't fit
       entirely inside a window (window.fits(task.time, task.duration_minutes)),
       or conflicts with a task already placed, is left out of the plan.
    2. The free gaps are the windows (sorted by start time) minus the set-time
       tasks.
    3. Remaining tasks, in priority order, go into the first gap they fit; that
       gap then shrinks. Earlier gaps stay usable by later, shorter tasks.
       A gap shrunk to zero length is removed, not kept as a TimeWindow.

    Tasks are never split across gaps. A task that fits in no gap is left out
    of the plan. Every task left out goes in DailyPlan.skipped with the reason.
    """

    def __init__(self, owner: Owner) -> None:
        """Create a scheduler for this owner's pets and availability."""
        self.owner = owner

    def generate_plan(self, plan_date: Optional[date] = None) -> DailyPlan:
        """Build the plan for `plan_date` (default today) for all pets, from
        filter_tasks(due_on=plan_date).

        Items are sorted by start_time before returning, since set-time tasks
        are placed before the others. Tasks left out go in plan.skipped, in the
        order they were tried, each with the reason (see the class docstring).
        """
        plan_date = plan_date or date.today()
        pending = self.filter_tasks(due_on=plan_date)
        set_time_tasks = self.sort_by_priority([t for t in pending if t.time is not None])
        flexible_tasks = self.sort_by_priority([t for t in pending if t.time is None])

        placed: list[ScheduledItem] = []
        skipped: list[SkippedTask] = []

        # 1. Set-time tasks
        for task in set_time_tasks:
            if not any(w.fits(task.time, task.duration_minutes) for w in self.owner.availability):
                skipped.append(
                    SkippedTask(task, f"set for {task.time:%H:%M}, outside your available time")
                )
                continue
            item = ScheduledItem(
                task=task,
                start_time=task.time,
                end_time=from_minutes(to_minutes(task.time) + task.duration_minutes),
                reason=f"{task.priority} priority; set for {task.time:%H:%M}",
            )
            conflicts = self.detect_conflicts(item, placed)
            if conflicts:
                other = conflicts[0]
                skipped.append(
                    SkippedTask(
                        task,
                        f"set for {task.time:%H:%M}, conflicts with {other.task.description} "
                        f"({self._pet_name(other.task)}) at "
                        f"{other.start_time:%H:%M}-{other.end_time:%H:%M}",
                    )
                )
                continue
            placed.append(item)

        # 2. Free gaps around the set-time tasks
        gaps = self.find_free_gaps(placed)

        # 3. Flexible tasks go into the first gap they fit
        for task in flexible_tasks:
            for i, gap in enumerate(gaps):
                if gap.duration_minutes() < task.duration_minutes:
                    continue
                end = from_minutes(to_minutes(gap.start) + task.duration_minutes)
                placed.append(
                    ScheduledItem(
                        task=task,
                        start_time=gap.start,
                        end_time=end,
                        reason=f"{task.priority} priority; earliest free slot that fits",
                    )
                )
                if end == gap.end:
                    del gaps[i]
                else:
                    gaps[i] = TimeWindow(end, gap.end)
                break
            else:
                skipped.append(
                    SkippedTask(task, f"no free slot of {task.duration_minutes} minutes left")
                )

        placed.sort(key=lambda item: item.start_time)
        return DailyPlan(plan_date=plan_date, items=placed, skipped=skipped)

    def sort_by_priority(self, tasks: list[Task]) -> list[Task]:
        """Sort by PRIORITY_ORDER; ties go to the shorter task first."""
        return sorted(tasks, key=lambda t: (PRIORITY_ORDER[t.priority], t.duration_minutes))

    def sort_by_time(self, tasks: list[Task]) -> list[Task]:
        """Sort set-time tasks by start time, earliest first; flexible tasks go last.

        Tasks set for the same time, and flexible tasks, are ordered by
        sort_by_priority's rule (priority, then shorter task first).
        """
        return sorted(
            tasks,
            key=lambda t: (
                t.time is None,
                t.time or time.min,  # placeholder so None is never compared to a time
                PRIORITY_ORDER[t.priority],
                t.duration_minutes,
            ),
        )

    def filter_tasks(
        self,
        pet_id: Optional[int] = None,
        completed: Optional[bool] = None,
        due_on: Optional[date] = None,
        pet_name: Optional[str] = None,
    ) -> list[Task]:
        """Start from self.owner.get_all_tasks(), then filter by pet_id, pet_name,
        completed, and/or due_on.

        pet_name ignores case and surrounding spaces. Pet names aren't unique,
        so it keeps tasks from every pet with that name; use pet_id for one pet.
        """
        tasks = self.owner.get_all_tasks()
        if pet_id is not None:
            tasks = [t for t in tasks if t.pet_id == pet_id]
        if pet_name is not None:
            name = pet_name.strip().casefold()
            pet_ids = {p.pet_id for p in self.owner.pets if p.name.strip().casefold() == name}
            tasks = [t for t in tasks if t.pet_id in pet_ids]
        if completed is not None:
            tasks = [t for t in tasks if t.completed == completed]
        if due_on is not None:
            tasks = [t for t in tasks if t.is_due(due_on)]
        return tasks

    def detect_conflicts(
        self, candidate: ScheduledItem, items: list[ScheduledItem]
    ) -> list[ScheduledItem]:
        """Return the already-scheduled items that overlap `candidate`.

        Only needed for set-time tasks; other tasks are placed in free gaps,
        which can't overlap anything. If any are returned, the candidate is
        left out of the plan.
        """
        return [
            item
            for item in items
            if candidate.start_time < item.end_time and item.start_time < candidate.end_time
        ]

    def find_conflicts(self, plan_date: Optional[date] = None) -> list[tuple[Task, Task]]:
        """Return each pair of set-time tasks due on `plan_date` (default today)
        whose times overlap, whether they're for the same pet or different pets.

        Each pair is (earlier task, later task); for the same start time, the
        higher-priority task comes first. Tasks that only touch (one ends as the
        next starts) don't conflict. Flexible tasks never conflict, since the
        scheduler places them in free gaps.

        The tasks are sorted by start time, then each one is compared with the
        tasks after it until one starts at or after it ends; since the rest
        start even later, none of them can overlap it either.

        Use this to warn the owner before planning. generate_plan() keeps the
        higher-priority task of each pair (ties go to the shorter task) and
        puts the other in DailyPlan.skipped.
        """
        plan_date = plan_date or date.today()
        timed = self.sort_by_time([t for t in self.filter_tasks(due_on=plan_date) if t.time is not None])

        conflicts: list[tuple[Task, Task]] = []
        for i, first in enumerate(timed):
            first_end = to_minutes(first.time) + first.duration_minutes
            for second in timed[i + 1 :]:
                # Sorted by start time, so once one starts after `first` ends, the rest do too.
                if to_minutes(second.time) >= first_end:
                    break
                conflicts.append((first, second))
        return conflicts

    def find_free_gaps(self, placed: list[ScheduledItem]) -> list[TimeWindow]:
        """Return the owner's windows, sorted by start, minus the placed items.

        Zero-length gaps (e.g. a set-time task at the very start of a window)
        are skipped, since TimeWindow requires start < end.
        """
        gaps: list[TimeWindow] = []
        busy = sorted(placed, key=lambda item: item.start_time)

        for window in sorted(self.owner.availability, key=lambda w: w.start):
            cursor = window.start
            for item in busy:
                if item.end_time <= window.start or item.start_time >= window.end:
                    continue
                if cursor < item.start_time:
                    gaps.append(TimeWindow(cursor, item.start_time))
                cursor = max(cursor, item.end_time)
            if cursor < window.end:
                gaps.append(TimeWindow(cursor, window.end))

        return gaps

    def explain_plan(self, plan: DailyPlan) -> str:
        """Describe each item, then each skipped task and why it was left out.
        If the task's pet was removed (get_pet returns None), label it as a
        removed pet instead of failing."""
        if plan.items:
            lines = [f"Plan for {plan.plan_date:%A, %B %d}:"]
            for item in plan.items:
                lines.append(
                    f"  {item.start_time:%H:%M}-{item.end_time:%H:%M}  "
                    f"{item.task.description} ({self._pet_name(item.task)}): {item.reason}"
                )
            lines.append(f"Total scheduled: {plan.total_minutes()} minutes")
        else:
            lines = [f"No tasks scheduled for {plan.plan_date:%A, %B %d}."]

        if plan.skipped:
            lines.append("Skipped:")
            for skipped in plan.skipped:
                lines.append(
                    f"  {skipped.task.description} ({self._pet_name(skipped.task)}): {skipped.reason}"
                )
        return "\n".join(lines)

    def _pet_name(self, task: Task) -> str:
        """Return the name of the task's pet, or "removed pet" if it's gone."""
        pet = self.owner.get_pet(task.pet_id)
        return pet.name if pet is not None else "removed pet"

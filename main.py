"""Command-line demo for PawPal+: builds an owner with two pets, shows sorting and
filtering, and prints today's schedule."""

from datetime import time

from pawpal_system import Owner, Pet, Scheduler, Task, TimeWindow


def print_tasks(title: str, tasks: list[Task], owner: Owner) -> None:
    """Print one line per task: time (or "flexible"), description, pet, priority, status."""
    print(title)
    if not tasks:
        print("  (none)")
    for task in tasks:
        when = f"{task.time:%H:%M}" if task.time else "flexible"
        pet = owner.get_pet(task.pet_id)
        status = "done" if task.completed else "pending"
        print(
            f"  {when:<8}  {task.emoji} {task.description:<14} {pet.name:<6} "
            f"{task.priority:<6}  {task.duration_minutes:>3} min  {status}"
        )
    print()


def main() -> None:
    owner = Owner(
        "Jordan",
        availability=[
            TimeWindow(time(7, 0), time(9, 0)),
            TimeWindow(time(12, 0), time(13, 0)),
            TimeWindow(time(18, 0), time(20, 0)),
        ],
    )

    # Tasks are added out of time order on purpose, to show sort_by_time().
    mochi = Pet("Mochi", "dog", breed="Shiba Inu", age=3)
    mochi.add_task(Task("Evening walk", 45, "medium", time=time(18, 30)))
    mochi.add_task(Task("Morning walk", 30, "high"))
    mochi.add_task(Task("Lunch treat", 5, "low", time=time(12, 15)))
    mochi.add_task(Task("Morning meds", 5, "high", time=time(7, 30)))
    mochi.add_task(Task("Vet call", 10, "medium", frequency="once"))

    luna = Pet("Luna", "cat", age=7)
    luna.add_task(Task("Brushing", 15, "low"))
    luna.add_task(Task("Feeding", 10, "high", time=time(18, 0)))
    luna.add_task(Task("Play session", 20, "medium"))
    luna.add_task(Task("Breakfast", 10, "medium", time=time(7, 30)))

    owner.add_pet(mochi)
    owner.add_pet(luna)

    # Complete a one-time task so the completion filter has something to show.
    vet_call = next(t for t in mochi.tasks if t.description == "Vet call")
    mochi.complete_task(vet_call)

    scheduler = Scheduler(owner)

    print_tasks("All tasks, in the order they were added:", owner.get_all_tasks(), owner)
    print_tasks("Sorted by time (flexible tasks last):", scheduler.sort_by_time(owner.get_all_tasks()), owner)
    print_tasks(
        "Sorted by priority, then time:", scheduler.sort_by_priority_then_time(owner.get_all_tasks()), owner
    )
    print_tasks(
        "Pending tasks, by priority then time:",
        scheduler.sort_by_priority_then_time(scheduler.filter_tasks(completed=False)),
        owner,
    )
    print_tasks("Completed tasks:", scheduler.filter_tasks(completed=True), owner)
    print_tasks(
        'Luna\'s tasks (filter pet_name=" luna "), by priority then time:',
        scheduler.sort_by_priority_then_time(scheduler.filter_tasks(pet_name=" luna ")),
        owner,
    )
    print_tasks(
        "Mochi's pending tasks, by priority then time:",
        scheduler.sort_by_priority_then_time(scheduler.filter_tasks(pet_name="Mochi", completed=False)),
        owner,
    )

    print("Conflicts among today's set-time tasks (checked before planning):")
    conflicts = scheduler.find_conflicts()
    if not conflicts:
        print("  (none)")
    for first, second in conflicts:
        print(
            f"  WARNING: {first.emoji} {first.description} ({owner.get_pet(first.pet_id).name}) "
            f"at {first.time:%H:%M} overlaps {second.emoji} {second.description} "
            f"({owner.get_pet(second.pet_id).name}) at {second.time:%H:%M}"
        )
    print()

    plan = scheduler.generate_plan()
    print(f"Today's Schedule for {owner.name}")
    print(f"Available: {owner.total_available_minutes()} minutes across {len(owner.availability)} windows")
    print()
    print(scheduler.explain_plan(plan))


if __name__ == "__main__":
    main()

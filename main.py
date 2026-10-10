"""Command-line demo for PawPal+: builds an owner with two pets and prints today's schedule."""

from datetime import time

from pawpal_system import Owner, Pet, Scheduler, Task, TimeWindow


def main() -> None:
    owner = Owner(
        "Jordan",
        availability=[
            TimeWindow(time(7, 0), time(9, 0)),
            TimeWindow(time(12, 0), time(13, 0)),
            TimeWindow(time(18, 0), time(20, 0)),
        ],
    )

    mochi = Pet("Mochi", "dog", breed="Shiba Inu", age=3)
    mochi.add_task(Task("Morning meds", 5, "high", time=time(7, 30)))
    mochi.add_task(Task("Morning walk", 30, "high"))
    mochi.add_task(Task("Evening walk", 45, "medium", time=time(18, 30)))

    luna = Pet("Luna", "cat", age=7)
    luna.add_task(Task("Feeding", 10, "high", time=time(18, 0)))
    luna.add_task(Task("Brushing", 15, "low"))
    luna.add_task(Task("Play session", 20, "medium"))

    owner.add_pet(mochi)
    owner.add_pet(luna)

    scheduler = Scheduler(owner)
    plan = scheduler.generate_plan()

    print(f"Today's Schedule for {owner.name}")
    print(f"Available: {owner.total_available_minutes()} minutes across {len(owner.availability)} windows")
    print()
    print(scheduler.explain_plan(plan))


if __name__ == "__main__":
    main()

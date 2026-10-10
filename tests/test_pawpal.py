"""Tests for the PawPal+ logic layer, focused on scheduling behavior."""

from datetime import date, time, timedelta

import pytest

from pawpal_system import Owner, Pet, Scheduler, Task, TimeWindow


def make_owner(*windows: tuple[time, time]) -> Owner:
    return Owner("Jordan", availability=[TimeWindow(start, end) for start, end in windows])


def plan_summary(owner: Owner) -> list[tuple[str, time, time]]:
    plan = Scheduler(owner).generate_plan()
    return [(item.task.description, item.start_time, item.end_time) for item in plan.items]


# --- TimeWindow -------------------------------------------------------------


def test_window_start_must_be_before_end():
    with pytest.raises(ValueError):
        TimeWindow(time(9, 0), time(7, 0))
    with pytest.raises(ValueError):
        TimeWindow(time(9, 0), time(9, 0))


def test_window_fits_task_ending_exactly_at_window_end():
    window = TimeWindow(time(7, 0), time(8, 0))
    assert window.fits(time(7, 30), 30)
    assert not window.fits(time(7, 31), 30)
    assert not window.fits(time(6, 59), 10)


def test_touching_windows_do_not_overlap():
    morning = TimeWindow(time(7, 0), time(9, 0))
    assert not morning.overlaps(TimeWindow(time(9, 0), time(10, 0)))
    assert morning.overlaps(TimeWindow(time(8, 59), time(10, 0)))


# --- Task -------------------------------------------------------------------


def test_task_rejects_unknown_priority_and_non_positive_duration():
    with pytest.raises(ValueError):
        Task("Walk", 30, "urgent")
    with pytest.raises(ValueError):
        Task("Walk", 0, "high")


def test_mark_complete_changes_task_status():
    task = Task("Walk", 30, "high")
    assert task.completed is False

    task.mark_complete()

    assert task.completed is True


# --- Recurring tasks --------------------------------------------------------

TODAY = date.today()


def test_task_rejects_unknown_frequency():
    with pytest.raises(ValueError):
        Task("Walk", 30, "high", frequency="monthly")


@pytest.mark.parametrize("frequency, days", [("daily", 1), ("weekly", 7)])
def test_recurring_task_returns_next_occurrence(frequency, days):
    task = Task("Walk", 30, "high", frequency=frequency)
    next_task = task.mark_complete()

    assert task.completed is True
    assert next_task is not None
    assert next_task.completed is False
    assert next_task.due_date == TODAY + timedelta(days=days)
    assert next_task.description == "Walk"


def test_once_task_does_not_recur():
    assert Task("Vet visit", 60, "high", frequency="once").mark_complete() is None


def test_complete_task_adds_next_occurrence_to_pet():
    mochi = Pet("Mochi", "dog")
    walk = Task("Walk", 30, "high")
    mochi.add_task(walk)

    next_walk = mochi.complete_task(walk)

    assert len(mochi.tasks) == 2
    assert next_walk in mochi.tasks
    assert next_walk.pet_id == mochi.pet_id


def test_completed_daily_task_is_planned_tomorrow_not_today():
    owner = make_owner((time(7, 0), time(9, 0)))
    mochi = Pet("Mochi", "dog", tasks=[Task("Walk", 30, "high")])
    owner.add_pet(mochi)
    mochi.complete_task(mochi.tasks[0])

    scheduler = Scheduler(owner)
    assert scheduler.generate_plan(TODAY).items == []
    tomorrow = scheduler.generate_plan(TODAY + timedelta(days=1))
    assert [item.task.description for item in tomorrow.items] == ["Walk"]


def test_task_due_later_is_not_planned_today():
    owner = make_owner((time(7, 0), time(9, 0)))
    owner.add_pet(
        Pet("Mochi", "dog", tasks=[Task("Bath", 30, "low", due_date=TODAY + timedelta(days=3))])
    )
    assert plan_summary(owner) == []


# --- Pet --------------------------------------------------------------------


def test_add_task_increases_pet_task_count():
    mochi = Pet("Mochi", "dog")
    assert len(mochi.tasks) == 0

    mochi.add_task(Task("Walk", 30, "high"))
    assert len(mochi.tasks) == 1

    mochi.add_task(Task("Meds", 5, "high"))
    assert len(mochi.tasks) == 2


def test_pets_get_unique_ids_and_tasks_get_their_pet_id():
    walk = Task("Walk", 30, "high")
    mochi = Pet("Mochi", "dog", tasks=[walk])
    luna = Pet("Luna", "cat")
    meds = Task("Meds", 5, "high")
    luna.add_task(meds)

    assert mochi.pet_id != luna.pet_id
    assert walk.pet_id == mochi.pet_id
    assert meds.pet_id == luna.pet_id


def test_task_cannot_belong_to_two_pets():
    walk = Task("Walk", 30, "high")
    Pet("Mochi", "dog").add_task(walk)
    with pytest.raises(ValueError):
        Pet("Luna", "cat").add_task(walk)


def test_remove_task_resets_pet_id():
    mochi = Pet("Mochi", "dog")
    walk = Task("Walk", 30, "high")
    mochi.add_task(walk)
    mochi.remove_task("Walk")

    assert walk not in mochi.tasks
    assert walk.pet_id is None
    with pytest.raises(ValueError):
        mochi.remove_task("Walk")


# --- Owner ------------------------------------------------------------------


def test_overlapping_windows_are_rejected_in_add_and_constructor():
    owner = make_owner((time(7, 0), time(9, 0)))
    with pytest.raises(ValueError):
        owner.add_availability(TimeWindow(time(8, 0), time(10, 0)))
    with pytest.raises(ValueError):
        make_owner((time(7, 0), time(9, 0)), (time(8, 0), time(10, 0)))


def test_total_available_minutes():
    owner = make_owner((time(7, 0), time(9, 0)), (time(18, 0), time(18, 30)))
    assert owner.total_available_minutes() == 150


def test_duplicate_pet_is_rejected():
    mochi = Pet("Mochi", "dog")
    owner = Owner("Jordan", pets=[mochi])
    with pytest.raises(ValueError):
        owner.add_pet(mochi)


def test_get_all_tasks_spans_every_pet():
    owner = Owner("Jordan")
    owner.add_pet(Pet("Mochi", "dog", tasks=[Task("Walk", 30, "high")]))
    owner.add_pet(Pet("Luna", "cat", tasks=[Task("Feeding", 10, "high")]))
    assert {t.description for t in owner.get_all_tasks()} == {"Walk", "Feeding"}


# --- Scheduler --------------------------------------------------------------


def test_sort_by_priority_breaks_ties_with_shorter_task():
    tasks = [
        Task("Low", 5, "low"),
        Task("Long high", 60, "high"),
        Task("Medium", 10, "medium"),
        Task("Short high", 10, "high"),
    ]
    ordered = Scheduler(Owner("Jordan")).sort_by_priority(tasks)
    assert [t.description for t in ordered] == ["Short high", "Long high", "Medium", "Low"]


def test_plan_includes_tasks_from_all_pets():
    owner = make_owner((time(7, 0), time(9, 0)))
    owner.add_pet(Pet("Mochi", "dog", tasks=[Task("Walk", 30, "high")]))
    owner.add_pet(Pet("Luna", "cat", tasks=[Task("Feeding", 10, "high")]))
    assert {name for name, _, _ in plan_summary(owner)} == {"Walk", "Feeding"}


def test_set_time_task_keeps_its_time():
    owner = make_owner((time(7, 0), time(9, 0)))
    owner.add_pet(Pet("Mochi", "dog", tasks=[Task("Meds", 10, "high", time=time(8, 0))]))
    assert plan_summary(owner) == [("Meds", time(8, 0), time(8, 10))]


def test_shorter_task_fills_earlier_gap_before_set_time_task():
    owner = make_owner((time(7, 0), time(9, 0)))
    owner.add_pet(
        Pet(
            "Mochi",
            "dog",
            tasks=[
                Task("Meds", 10, "high", time=time(7, 30)),
                Task("Walk", 60, "high"),
                Task("Feeding", 15, "low"),
            ],
        )
    )
    assert plan_summary(owner) == [
        ("Feeding", time(7, 0), time(7, 15)),
        ("Meds", time(7, 30), time(7, 40)),
        ("Walk", time(7, 40), time(8, 40)),
    ]


def test_set_time_task_at_window_start_and_task_filling_gap_exactly():
    owner = make_owner((time(7, 0), time(8, 0)))
    owner.add_pet(
        Pet(
            "Rex",
            "dog",
            tasks=[Task("Meds", 10, "high", time=time(7, 0)), Task("Walk", 50, "medium")],
        )
    )
    assert plan_summary(owner) == [
        ("Meds", time(7, 0), time(7, 10)),
        ("Walk", time(7, 10), time(8, 0)),
    ]


def test_task_never_split_moves_to_later_window():
    owner = make_owner((time(7, 0), time(7, 30)), (time(18, 0), time(19, 0)))
    owner.add_pet(Pet("Mochi", "dog", tasks=[Task("Walk", 45, "high")]))
    assert plan_summary(owner) == [("Walk", time(18, 0), time(18, 45))]


def test_set_time_task_running_past_window_end_is_left_out():
    owner = make_owner((time(7, 0), time(9, 0)))
    owner.add_pet(Pet("Mochi", "dog", tasks=[Task("Meds", 10, "high", time=time(8, 55))]))
    assert plan_summary(owner) == []


def test_conflicting_set_time_task_with_lower_priority_is_left_out():
    owner = make_owner((time(7, 0), time(9, 0)))
    owner.add_pet(Pet("Mochi", "dog", tasks=[Task("Mochi meds", 10, "high", time=time(8, 0))]))
    owner.add_pet(Pet("Luna", "cat", tasks=[Task("Luna meds", 5, "medium", time=time(8, 5))]))
    assert plan_summary(owner) == [("Mochi meds", time(8, 0), time(8, 10))]


def test_completed_and_too_long_tasks_are_left_out():
    done = Task("Brush", 5, "low")
    done.mark_complete()
    owner = make_owner((time(7, 0), time(8, 0)))
    owner.add_pet(Pet("Mochi", "dog", tasks=[done, Task("Hike", 120, "high"), Task("Play", 20, "medium")]))
    assert plan_summary(owner) == [("Play", time(7, 0), time(7, 20))]


def test_plan_items_are_in_time_order():
    owner = make_owner((time(7, 0), time(9, 0)))
    owner.add_pet(
        Pet("Mochi", "dog", tasks=[Task("Meds", 10, "high", time=time(8, 30)), Task("Walk", 20, "low")])
    )
    starts = [start for _, start, _ in plan_summary(owner)]
    assert starts == sorted(starts)


def test_filter_tasks_by_pet_and_status():
    owner = Owner("Jordan")
    mochi = Pet("Mochi", "dog", tasks=[Task("Walk", 30, "high"), Task("Meds", 5, "high")])
    luna = Pet("Luna", "cat", tasks=[Task("Feeding", 10, "high")])
    owner.add_pet(mochi)
    owner.add_pet(luna)
    mochi.tasks[1].mark_complete()

    scheduler = Scheduler(owner)
    assert [t.description for t in scheduler.filter_tasks(pet_id=mochi.pet_id)] == ["Walk", "Meds"]
    assert {t.description for t in scheduler.filter_tasks(completed=False)} == {"Walk", "Feeding"}


def test_explain_plan_handles_removed_pet():
    owner = make_owner((time(7, 0), time(9, 0)))
    mochi = Pet("Mochi", "dog", tasks=[Task("Walk", 30, "high")])
    owner.add_pet(mochi)
    scheduler = Scheduler(owner)
    plan = scheduler.generate_plan()

    owner.remove_pet(mochi.pet_id)
    assert "removed pet" in scheduler.explain_plan(plan)

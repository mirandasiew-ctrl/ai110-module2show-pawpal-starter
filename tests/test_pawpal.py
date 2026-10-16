"""Tests for the PawPal+ logic layer, focused on scheduling behavior."""

from datetime import date, time, timedelta

import pytest

import pawpal_system
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


def freeze_today(monkeypatch, frozen: date) -> None:
    """Make pawpal_system's date.today() return `frozen`."""

    class FrozenDate(date):
        @classmethod
        def today(cls) -> date:
            return frozen

    monkeypatch.setattr(pawpal_system, "date", FrozenDate)


def test_completing_task_twice_does_not_add_a_second_occurrence():
    mochi = Pet("Mochi", "dog")
    walk = Task("Walk", 30, "high")
    mochi.add_task(walk)

    mochi.complete_task(walk)
    assert mochi.complete_task(walk) is None
    assert len(mochi.tasks) == 2


def test_overdue_daily_task_comes_back_tomorrow_not_in_the_past(monkeypatch):
    freeze_today(monkeypatch, date(2026, 3, 10))
    task = Task("Walk", 30, "high", due_date=date(2026, 3, 7))
    assert task.mark_complete().due_date == date(2026, 3, 11)


def test_weekly_task_completed_early_counts_from_due_date(monkeypatch):
    freeze_today(monkeypatch, date(2026, 3, 10))
    task = Task("Bath", 30, "low", frequency="weekly", due_date=date(2026, 3, 13))
    assert task.mark_complete().due_date == date(2026, 3, 20)


@pytest.mark.parametrize(
    "today, frequency, expected",
    [
        (date(2026, 12, 31), "daily", date(2027, 1, 1)),
        (date(2028, 2, 28), "daily", date(2028, 2, 29)),  # leap year
        (date(2026, 2, 25), "weekly", date(2026, 3, 4)),
    ],
)
def test_recurrence_rolls_over_month_and_year(monkeypatch, today, frequency, expected):
    freeze_today(monkeypatch, today)
    task = Task("Walk", 30, "high", frequency=frequency, due_date=today)
    assert task.mark_complete().due_date == expected


def test_overdue_task_is_still_planned_today():
    owner = make_owner((time(7, 0), time(9, 0)))
    owner.add_pet(
        Pet("Mochi", "dog", tasks=[Task("Walk", 30, "high", due_date=TODAY - timedelta(days=1))])
    )
    assert plan_summary(owner) == [("Walk", time(7, 0), time(7, 30))]


def test_next_occurrence_keeps_settings_and_is_a_separate_object():
    task = Task("Meds", 5, "high", time=time(8, 0), frequency="weekly")
    next_task = task.mark_complete()

    assert next_task is not task
    assert (next_task.description, next_task.duration_minutes, next_task.priority) == (
        "Meds", 5, "high"
    )
    assert (next_task.time, next_task.frequency) == (time(8, 0), "weekly")

    next_task.update(duration_minutes=10)
    assert task.duration_minutes == 5 and task.completed is True


def test_completing_one_pets_task_leaves_other_pets_alone():
    owner = make_owner((time(7, 0), time(9, 0)))
    mochi = Pet("Mochi", "dog", tasks=[Task("Walk", 30, "high")])
    luna = Pet("Luna", "cat", tasks=[Task("Feeding", 10, "high")])
    owner.add_pet(mochi)
    owner.add_pet(luna)

    mochi.complete_task(mochi.tasks[0])

    assert [t.description for t in luna.tasks] == ["Feeding"]
    assert luna.tasks[0].completed is False
    assert [name for name, _, _ in plan_summary(owner)] == ["Feeding"]


def test_tomorrows_plan_has_next_occurrence_once():
    owner = make_owner((time(7, 0), time(9, 0)))
    mochi = Pet("Mochi", "dog", tasks=[Task("Walk", 30, "high")])
    owner.add_pet(mochi)
    mochi.complete_task(mochi.tasks[0])

    tomorrow = Scheduler(owner).generate_plan(TODAY + timedelta(days=1))

    assert [item.task.description for item in tomorrow.items] == ["Walk"]
    assert tomorrow.items[0].task.completed is False


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


# --- Editing ----------------------------------------------------------------


def test_task_update_changes_fields():
    task = Task("Walk", 30, "high")
    task.update(description="Long walk", duration_minutes=45, priority="medium", time=time(7, 0))
    assert (task.description, task.duration_minutes, task.priority, task.time) == (
        "Long walk", 45, "medium", time(7, 0)
    )


def test_invalid_task_update_changes_nothing():
    task = Task("Walk", 30, "high")
    with pytest.raises(ValueError):
        task.update(description="Long walk", priority="urgent")
    assert (task.description, task.priority) == ("Walk", "high")


def test_remove_task_by_object_removes_that_exact_task():
    mochi = Pet("Mochi", "dog")
    first, second = Task("Walk", 30, "high"), Task("Walk", 30, "high")
    mochi.add_task(first)
    mochi.add_task(second)
    mochi.remove_task(second)
    assert len(mochi.tasks) == 1 and mochi.tasks[0] is first


def test_move_task_to_another_pet():
    owner = Owner("Jordan")
    mochi = Pet("Mochi", "dog", tasks=[Task("Walk", 30, "high")])
    luna = Pet("Luna", "cat")
    owner.add_pet(mochi)
    owner.add_pet(luna)
    walk = mochi.tasks[0]

    owner.move_task(walk, luna.pet_id)

    assert mochi.tasks == [] and luna.tasks[0] is walk
    assert walk.pet_id == luna.pet_id


def test_update_availability_keeps_old_window_if_new_one_overlaps():
    owner = make_owner((time(7, 0), time(9, 0)), (time(18, 0), time(19, 0)))
    evening = owner.availability[1]

    with pytest.raises(ValueError):
        owner.update_availability(evening, TimeWindow(time(8, 0), time(10, 0)))
    assert evening in owner.availability

    owner.update_availability(evening, TimeWindow(time(17, 0), time(19, 0)))
    assert owner.total_available_minutes() == 120 + 120


def test_remove_availability():
    owner = make_owner((time(7, 0), time(9, 0)))
    owner.remove_availability(owner.availability[0])
    assert owner.availability == []


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


def test_sort_by_time_puts_earliest_first_and_flexible_tasks_last():
    tasks = [
        Task("Flexible low", 10, "low"),
        Task("Evening meds", 5, "high", time=time(18, 0)),
        Task("Flexible high", 20, "high"),
        Task("Breakfast", 10, "medium", time=time(7, 30)),
        Task("Morning meds", 5, "high", time=time(7, 30)),
    ]
    ordered = Scheduler(Owner("Jordan")).sort_by_time(tasks)
    assert [t.description for t in ordered] == [
        "Morning meds",
        "Breakfast",
        "Evening meds",
        "Flexible high",
        "Flexible low",
    ]


def test_sort_by_time_handles_empty_list():
    assert Scheduler(Owner("Jordan")).sort_by_time([]) == []


def test_sort_by_priority_keeps_insertion_order_for_full_ties():
    tasks = [Task("First", 10, "high"), Task("Second", 10, "high"), Task("Third", 10, "high")]
    ordered = Scheduler(Owner("Jordan")).sort_by_priority(tasks)
    assert [t.description for t in ordered] == ["First", "Second", "Third"]


def test_sorting_does_not_change_the_input_list():
    tasks = [Task("Low", 5, "low"), Task("High", 10, "high", time=time(9, 0))]
    original = list(tasks)
    scheduler = Scheduler(Owner("Jordan"))

    scheduler.sort_by_priority(tasks)
    scheduler.sort_by_time(tasks)

    assert tasks == original


def test_plan_with_no_availability_skips_everything():
    owner = Owner("Jordan")
    owner.add_pet(Pet("Mochi", "dog", tasks=[Task("Walk", 30, "high")]))
    scheduler = Scheduler(owner)

    plan = scheduler.generate_plan()

    assert plan.items == []
    assert [s.task.description for s in plan.skipped] == ["Walk"]
    assert scheduler.explain_plan(plan).startswith("No tasks scheduled")


def test_pet_with_no_tasks_does_not_affect_scheduling():
    owner = make_owner((time(7, 0), time(9, 0)))
    luna = Pet("Luna", "cat")
    owner.add_pet(Pet("Mochi", "dog", tasks=[Task("Walk", 30, "high", time=time(7, 0))]))
    owner.add_pet(luna)
    scheduler = Scheduler(owner)

    assert scheduler.filter_tasks(pet_id=luna.pet_id) == []
    assert scheduler.find_conflicts() == []
    assert plan_summary(owner) == [("Walk", time(7, 0), time(7, 30))]


def test_owner_whose_only_pet_has_no_tasks_gets_empty_plan():
    owner = make_owner((time(7, 0), time(9, 0)))
    owner.add_pet(Pet("Luna", "cat"))

    plan = Scheduler(owner).generate_plan()

    assert plan.items == [] and plan.skipped == []


def test_same_start_time_same_priority_keeps_shorter_task():
    owner = make_owner((time(7, 0), time(9, 0)))
    owner.add_pet(Pet("Mochi", "dog", tasks=[Task("Walk", 30, "high", time=time(8, 0))]))
    owner.add_pet(Pet("Luna", "cat", tasks=[Task("Feeding", 10, "high", time=time(8, 0))]))

    plan = Scheduler(owner).generate_plan()

    assert [(i.task.description, i.start_time, i.end_time) for i in plan.items] == [
        ("Feeding", time(8, 0), time(8, 10))
    ]
    assert [(s.task.description, s.reason) for s in plan.skipped] == [
        ("Walk", "set for 08:00, conflicts with Feeding (Luna) at 08:00-08:10")
    ]


def test_find_conflicts_different_pets_exact_same_time():
    owner = Owner("Jordan")
    owner.add_pet(Pet("Mochi", "dog", tasks=[Task("Walk", 30, "medium", time=time(8, 0))]))
    owner.add_pet(Pet("Luna", "cat", tasks=[Task("Meds", 5, "high", time=time(8, 0))]))
    # Same start time: the higher-priority task comes first, whatever order pets were added.
    assert conflict_names(owner) == [("Meds", "Walk")]


def test_plan_with_only_completed_tasks_is_empty():
    owner = make_owner((time(7, 0), time(9, 0)))
    done = Task("Vet visit", 60, "high", frequency="once")
    owner.add_pet(Pet("Mochi", "dog", tasks=[done]))
    done.mark_complete()

    plan = Scheduler(owner).generate_plan()

    assert plan.items == [] and plan.skipped == []


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


def conflict_names(owner: Owner) -> list[tuple[str, str]]:
    return [(a.description, b.description) for a, b in Scheduler(owner).find_conflicts()]


def test_find_conflicts_same_pet_same_time():
    owner = Owner("Jordan")
    owner.add_pet(
        Pet(
            "Mochi",
            "dog",
            tasks=[
                Task("Breakfast", 10, "medium", time=time(7, 30)),
                Task("Meds", 5, "high", time=time(7, 30)),
            ],
        )
    )
    assert conflict_names(owner) == [("Meds", "Breakfast")]


def test_find_conflicts_different_pets_partial_overlap():
    owner = Owner("Jordan")
    owner.add_pet(Pet("Mochi", "dog", tasks=[Task("Walk", 30, "high", time=time(7, 30))]))
    owner.add_pet(Pet("Luna", "cat", tasks=[Task("Feeding", 10, "high", time=time(7, 45))]))
    assert conflict_names(owner) == [("Walk", "Feeding")]


def test_find_conflicts_lists_every_overlapping_pair():
    owner = Owner("Jordan")
    owner.add_pet(
        Pet(
            "Mochi",
            "dog",
            tasks=[
                Task("Walk", 60, "high", time=time(7, 0)),
                Task("Meds", 5, "high", time=time(7, 10)),
                Task("Treat", 5, "low", time=time(7, 50)),
            ],
        )
    )
    assert conflict_names(owner) == [("Walk", "Meds"), ("Walk", "Treat")]


def test_find_conflicts_ignores_touching_flexible_completed_and_not_due_tasks():
    done = Task("Brush", 10, "low", time=time(7, 30))
    done.mark_complete()
    owner = Owner("Jordan")
    owner.add_pet(
        Pet(
            "Mochi",
            "dog",
            tasks=[
                Task("Meds", 30, "high", time=time(7, 0)),
                Task("Walk", 30, "high", time=time(7, 30)),  # starts as Meds ends
                Task("Play", 20, "low"),  # flexible
                done,
                Task("Bath", 30, "low", time=time(7, 0), due_date=TODAY + timedelta(days=1)),
            ],
        )
    )
    assert conflict_names(owner) == []


def test_plan_records_why_each_task_was_skipped():
    owner = make_owner((time(7, 0), time(8, 0)))
    owner.add_pet(
        Pet(
            "Mochi",
            "dog",
            tasks=[
                Task("Meds", 10, "high", time=time(7, 30)),
                Task("Late meds", 10, "high", time=time(9, 0)),
                Task("Hike", 90, "medium"),
            ],
        )
    )
    owner.add_pet(Pet("Luna", "cat", tasks=[Task("Breakfast", 10, "medium", time=time(7, 35))]))

    plan = Scheduler(owner).generate_plan()

    assert [item.task.description for item in plan.items] == ["Meds"]
    reasons = {s.task.description: s.reason for s in plan.skipped}
    assert reasons == {
        "Late meds": "set for 09:00, outside your available time",
        "Breakfast": "set for 07:35, conflicts with Meds (Mochi) at 07:30-07:40",
        "Hike": "no free slot of 90 minutes left",
    }


def test_explain_plan_lists_skipped_tasks():
    owner = make_owner((time(7, 0), time(8, 0)))
    owner.add_pet(Pet("Mochi", "dog", tasks=[Task("Hike", 90, "high")]))
    scheduler = Scheduler(owner)

    text = scheduler.explain_plan(scheduler.generate_plan())

    assert text.startswith("No tasks scheduled")
    assert "Skipped:" in text
    assert "Hike (Mochi): no free slot of 90 minutes left" in text


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


def test_filter_tasks_by_pet_name_and_status():
    owner = Owner("Jordan")
    mochi = Pet("Mochi", "dog", tasks=[Task("Walk", 30, "high"), Task("Meds", 5, "high")])
    luna = Pet("Luna", "cat", tasks=[Task("Feeding", 10, "high")])
    owner.add_pet(mochi)
    owner.add_pet(luna)
    mochi.tasks[1].mark_complete()

    scheduler = Scheduler(owner)
    assert [t.description for t in scheduler.filter_tasks(pet_name="  mochi ")] == ["Walk", "Meds"]
    assert [t.description for t in scheduler.filter_tasks(pet_name="Mochi", completed=True)] == ["Meds"]
    assert scheduler.filter_tasks(pet_name="Rex") == []


def test_explain_plan_handles_removed_pet():
    owner = make_owner((time(7, 0), time(9, 0)))
    mochi = Pet("Mochi", "dog", tasks=[Task("Walk", 30, "high")])
    owner.add_pet(mochi)
    scheduler = Scheduler(owner)
    plan = scheduler.generate_plan()

    owner.remove_pet(mochi.pet_id)
    assert "removed pet" in scheduler.explain_plan(plan)

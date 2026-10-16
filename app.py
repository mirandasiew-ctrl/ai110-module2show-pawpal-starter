from datetime import date, time

import streamlit as st

from pawpal_system import Owner, Pet, Scheduler, Task, TimeWindow

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")
st.caption(
    "Plan your pets' care around your day. Add the time you have free, your pets, and "
    "their tasks, then build a schedule that fits the most important care first."
)

st.divider()

SPECIES = ["dog", "cat", "other"]
PRIORITIES = ["high", "medium", "low"]
FREQUENCIES = ["daily", "weekly", "once"]

# Shared column formats for the tables below; priority shows as a colored badge.
PRIORITY_COLUMN = st.column_config.MultiselectColumn(
    "Priority", options=PRIORITIES, color=["red", "orange", "blue"]
)
TASK_COLUMNS = {
    "Pet": st.column_config.TextColumn("Pet", pinned=True),
    "Task": st.column_config.TextColumn("Task", pinned=True),
    "Minutes": st.column_config.NumberColumn("Length", format="%d min"),
    "Priority": PRIORITY_COLUMN,
    "Set time": st.column_config.TimeColumn("Set time", format="HH:mm"),
    "Repeats": st.column_config.TextColumn("Repeats"),
    "Due": st.column_config.DateColumn("Due", format="MMM D"),
    "Done": st.column_config.CheckboxColumn("Done"),
    "Conflict": st.column_config.TextColumn("Conflict", help="Set-time tasks that overlap this one"),
}

# One Owner per browser session; its pets, tasks, and windows live inside it.
st.session_state.setdefault("owner", Owner("Jordan"))
owner: Owner = st.session_state.owner
scheduler = Scheduler(owner)  # reads the owner live, so one per run is enough


def window_label(w: TimeWindow) -> str:
    return f"{w.start:%H:%M}–{w.end:%H:%M}"


def pet_name(pet_id: int) -> str:
    pet = owner.get_pet(pet_id)
    return pet.name if pet is not None else "removed pet"


def conflicting_tasks(task: Task) -> list[Task]:
    """Return the set-time tasks that overlap `task` on its due date."""
    if task.time is None or task.completed:
        return []
    return [
        b if a is task else a
        for a, b in scheduler.find_conflicts(task.due_date)
        if a is task or b is task
    ]


def conflict_line(a: Task, b: Task) -> str:
    return (
        f"- {a.emoji} **{a.description}** ({pet_name(a.pet_id)}, {a.time:%H:%M}, {a.duration_minutes} min) "
        f"overlaps {b.emoji} **{b.description}** ({pet_name(b.pet_id)}, {b.time:%H:%M}, {b.duration_minutes} min)"
    )


def conflict_warning(task: Task) -> str | None:
    """Describe the set-time tasks that overlap `task` on its due date, or None if none do."""
    others = conflicting_tasks(task)
    if not others:
        return None
    clashes = ", ".join(
        f"**{o.description}** ({pet_name(o.pet_id)}, {o.time:%H:%M}, {o.duration_minutes} min)"
        for o in others
    )
    return (
        f"**{task.description}** ({pet_name(task.pet_id)}) at {task.time:%H:%M} on "
        f"{task.due_date:%b %d} overlaps {clashes}. When you build that day's schedule, "
        "only the higher-priority task is kept and the other is left out."
    )


def parse_needs(text: str) -> list[str]:
    return [need.strip() for need in text.split(",") if need.strip()]


# --- Owner and availability -------------------------------------------------

st.subheader("Owner")
st.session_state.setdefault("owner_name", owner.name)
st.text_input("Owner name", key="owner_name")
owner.name = st.session_state.owner_name.strip() or owner.name

st.markdown("#### Available time")
with st.form("add_window"):
    col1, col2 = st.columns(2)
    window_start = col1.time_input("From", value=time(7, 0), step=900, key="add_window_start")
    window_end = col2.time_input("To", value=time(9, 0), step=900, key="add_window_end")
    if st.form_submit_button("Add time window"):
        try:
            owner.add_availability(TimeWindow(window_start, window_end))
        except ValueError as e:
            st.error(str(e))

if owner.availability:
    windows = sorted(owner.availability, key=lambda w: w.start)
    st.write(
        ", ".join(window_label(w) for w in windows)
        + f" ({owner.total_available_minutes()} minutes)"
    )

    with st.expander("Edit or remove a time window"):
        w = windows[
            st.selectbox("Window to edit", range(len(windows)), format_func=lambda i: window_label(windows[i]))
        ]
        k = id(w)
        with st.form(f"edit_window_{k}"):
            col1, col2 = st.columns(2)
            new_start = col1.time_input("From", value=w.start, step=900, key=f"ew_start_{k}")
            new_end = col2.time_input("To", value=w.end, step=900, key=f"ew_end_{k}")
            col1, col2 = st.columns(2)
            save = col1.form_submit_button("Save changes")
            delete = col2.form_submit_button("Remove window")
        if save:
            try:
                owner.update_availability(w, TimeWindow(new_start, new_end))
                st.rerun()
            except ValueError as e:
                st.error(str(e))
        if delete:
            owner.remove_availability(w)
            st.rerun()
else:
    st.info("No available time yet. Add at least one window so tasks can be scheduled.")

st.divider()

# --- Pets ---------------------------------------------------------------------

st.subheader("Pets")
with st.form("add_pet", clear_on_submit=True):
    col1, col2 = st.columns(2)
    new_pet_name = col1.text_input("Pet name", key="add_pet_name")
    new_species = col2.selectbox("Species", SPECIES, key="add_pet_species")
    new_breed = col1.text_input("Breed (optional)", key="add_pet_breed")
    new_age = col2.number_input("Age", min_value=0, max_value=40, value=0, key="add_pet_age")
    new_needs = st.text_input("Special needs (optional, comma-separated)", key="add_pet_needs")
    if st.form_submit_button("Add pet"):
        if new_pet_name.strip():
            owner.add_pet(
                Pet(
                    new_pet_name.strip(),
                    new_species,
                    breed=new_breed.strip(),
                    age=int(new_age),
                    special_needs=parse_needs(new_needs),
                )
            )
        else:
            st.error("Enter a pet name.")

if owner.pets:
    st.dataframe(
        [
            {
                "Name": p.name,
                "Species": p.species,
                "Breed": p.breed,
                "Age": p.age,
                "Special needs": p.special_needs,
                "Tasks to do": len(p.get_pending_tasks()),
            }
            for p in owner.pets
        ],
        column_config={
            "Age": st.column_config.NumberColumn("Age", format="%d yr"),
            "Special needs": st.column_config.MultiselectColumn("Special needs", color="gray"),
        },
        hide_index=True,
    )

    with st.expander("Edit or remove a pet"):
        pet = owner.get_pet(
            st.selectbox("Pet to edit", [p.pet_id for p in owner.pets], format_func=pet_name)
        )
        k = pet.pet_id
        with st.form(f"edit_pet_{k}"):
            col1, col2 = st.columns(2)
            name = col1.text_input("Pet name", value=pet.name, key=f"ep_name_{k}")
            species = col2.selectbox(
                "Species",
                SPECIES,
                index=SPECIES.index(pet.species) if pet.species in SPECIES else len(SPECIES) - 1,
                key=f"ep_species_{k}",
            )
            breed = col1.text_input("Breed", value=pet.breed, key=f"ep_breed_{k}")
            age = col2.number_input("Age", min_value=0, max_value=40, value=pet.age, key=f"ep_age_{k}")
            needs = st.text_input(
                "Special needs (comma-separated)", value=", ".join(pet.special_needs), key=f"ep_needs_{k}"
            )
            col1, col2 = st.columns(2)
            save = col1.form_submit_button("Save changes")
            delete = col2.form_submit_button("Remove pet and its tasks")
        if save:
            if name.strip():
                pet.name = name.strip()
                pet.species = species
                pet.breed = breed.strip()
                pet.age = int(age)
                pet.special_needs = parse_needs(needs)
                st.rerun()
            else:
                st.error("Enter a pet name.")
        if delete:
            owner.remove_pet(pet.pet_id)
            st.rerun()
else:
    st.info("No pets yet. Add one above.")

st.divider()

# --- Tasks --------------------------------------------------------------------

st.subheader("Tasks")
if not owner.pets:
    st.caption("Add a pet first, then give it tasks.")
else:
    with st.form("add_task", clear_on_submit=True):
        task_pet_id = st.selectbox(
            "Pet", [p.pet_id for p in owner.pets], format_func=pet_name, key="add_task_pet"
        )
        task_title = st.text_input("Task", key="add_task_title")
        col1, col2, col3 = st.columns(3)
        duration = col1.number_input(
            "Duration (minutes)", min_value=1, max_value=240, value=20, key="add_task_duration"
        )
        priority = col2.selectbox("Priority", PRIORITIES, key="add_task_priority")
        frequency = col3.selectbox("Repeats", FREQUENCIES, key="add_task_frequency")
        col1, col2, col3 = st.columns(3)
        due = col1.date_input("Due date", value=date.today(), key="add_task_due")
        has_set_time = col2.checkbox("Set time", key="add_task_has_time")
        set_time = col3.time_input(
            "Time", value=time(8, 0), step=300, key="add_task_time", label_visibility="hidden"
        )
        if st.form_submit_button("Add task"):
            if not task_title.strip():
                st.error("Enter a task name.")
            else:
                try:
                    new_task = Task(
                        task_title.strip(),
                        int(duration),
                        priority,
                        time=set_time if has_set_time else None,
                        frequency=frequency,
                        due_date=due,
                    )
                    owner.get_pet(task_pet_id).add_task(new_task)
                    st.session_state.task_conflict = conflict_warning(new_task)
                except ValueError as e:
                    st.error(str(e))

    # Set by adding or editing a task; editing reruns the page, so show it here.
    if warning := st.session_state.pop("task_conflict", None):
        st.warning(warning)

    all_tasks: list[Task] = []  # the tasks shown, after filtering and sorting
    if not owner.get_all_tasks():
        st.info("No tasks yet. Add one above.")
    else:
        with st.container(horizontal=True):
            show_pet = st.selectbox(
                "Pet",
                [None] + [p.pet_id for p in owner.pets],
                format_func=lambda pid: "All pets" if pid is None else pet_name(pid),
                key="task_filter_pet",
            )
            show_status = st.segmented_control(
                "Status", ["To do", "Done", "All"], default="To do", key="task_filter_status"
            )
            sort_by = st.segmented_control(
                "Sort by", ["Time", "Priority"], default="Time", key="task_sort"
            )

        # "All", or a deselected control, passes None so both statuses are kept.
        completed = {"To do": False, "Done": True}.get(show_status)
        all_tasks = scheduler.filter_tasks(pet_id=show_pet, completed=completed)
        if sort_by == "Priority":
            all_tasks = scheduler.sort_by_priority_then_time(all_tasks)
        else:
            # sort_by_time orders within a day; the stable sort by date keeps that order.
            all_tasks = sorted(scheduler.sort_by_time(all_tasks), key=lambda t: t.due_date)

    if owner.get_all_tasks() and not all_tasks:
        st.info("No tasks match these filters.")
    elif all_tasks:
        st.dataframe(
            [
                {
                    "Pet": pet_name(t.pet_id),
                    "Task": f"{t.emoji} {t.description}",
                    "Minutes": t.duration_minutes,
                    "Priority": [t.priority],
                    "Set time": t.time,
                    "Repeats": t.frequency,
                    "Due": t.due_date,
                    "Done": t.completed,
                    "Conflict": ", ".join(
                        f"⚠️ {o.emoji} {o.description} ({pet_name(o.pet_id)})" for o in conflicting_tasks(t)
                    ),
                }
                for t in all_tasks
            ],
            column_config=TASK_COLUMNS,
            hide_index=True,
        )

        with st.expander("Edit, complete, or remove a task"):
            task = all_tasks[
                st.selectbox(
                    "Task to edit",
                    range(len(all_tasks)),
                    format_func=lambda i: (
                        f"{pet_name(all_tasks[i].pet_id)}: {all_tasks[i].emoji} {all_tasks[i].description} "
                        f"(due {all_tasks[i].due_date:%b %d})"
                    ),
                )
            ]
            k = id(task)
            pet_ids = [p.pet_id for p in owner.pets]
            with st.form(f"edit_task_{k}"):
                new_pet_id = st.selectbox(
                    "Pet", pet_ids, index=pet_ids.index(task.pet_id), format_func=pet_name, key=f"et_pet_{k}"
                )
                title = st.text_input("Task", value=task.description, key=f"et_title_{k}")
                col1, col2, col3 = st.columns(3)
                duration = col1.number_input(
                    "Duration (minutes)",
                    min_value=1,
                    max_value=240,
                    value=task.duration_minutes,
                    key=f"et_duration_{k}",
                )
                priority = col2.selectbox(
                    "Priority", PRIORITIES, index=PRIORITIES.index(task.priority), key=f"et_priority_{k}"
                )
                frequency = col3.selectbox(
                    "Repeats", FREQUENCIES, index=FREQUENCIES.index(task.frequency), key=f"et_frequency_{k}"
                )
                col1, col2, col3 = st.columns(3)
                due = col1.date_input("Due date", value=task.due_date, key=f"et_due_{k}")
                has_set_time = col2.checkbox("Set time", value=task.time is not None, key=f"et_has_time_{k}")
                set_time = col3.time_input(
                    "Time",
                    value=task.time or time(8, 0),
                    step=300,
                    key=f"et_time_{k}",
                    label_visibility="hidden",
                )
                completed = st.checkbox("Done", value=task.completed, key=f"et_done_{k}")
                col1, col2 = st.columns(2)
                save = col1.form_submit_button("Save changes")
                delete = col2.form_submit_button("Remove task")
            if save:
                if not title.strip():
                    st.error("Enter a task name.")
                else:
                    try:
                        task.update(
                            description=title.strip(),
                            duration_minutes=int(duration),
                            priority=priority,
                            frequency=frequency,
                            due_date=due,
                            time=set_time if has_set_time else None,
                            completed=completed,
                        )
                        owner.move_task(task, new_pet_id)
                        st.session_state.task_conflict = conflict_warning(task)
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))
            if delete:
                owner.get_pet(task.pet_id).remove_task(task)
                st.rerun()

            if not task.completed:
                st.caption("Marking a repeating task complete also adds its next occurrence.")
                if st.button("Mark complete", key=f"complete_{k}"):
                    owner.get_pet(task.pet_id).complete_task(task)
                    st.rerun()

st.divider()

# --- Build schedule -----------------------------------------------------------

st.subheader("Build schedule")
st.caption("Plans the selected day's tasks for all pets within your available time.")

plan_date = st.date_input("Plan for", value=date.today())

# Warn before planning, so the owner can fix times instead of losing a task.
if conflicts := scheduler.find_conflicts(plan_date):
    st.warning(
        f"{len(conflicts)} time conflict(s) on {plan_date:%b %d}. Only the higher-priority task "
        "of each pair will be scheduled; edit a task's time to keep both.\n"
        + "\n".join(conflict_line(a, b) for a, b in conflicts),
        icon=":material/warning:",
    )

if st.button("Generate schedule", type="primary"):
    plan = scheduler.generate_plan(plan_date)

    minutes_used = sum(item.task.duration_minutes for item in plan.items)
    minutes_free = owner.total_available_minutes()
    with st.container(horizontal=True):
        st.metric("Tasks scheduled", len(plan.items), border=True)
        st.metric(
            "Time used",
            f"{minutes_used} of {minutes_free} min",
            help="Minutes of scheduled tasks out of your total available time",
            border=True,
        )
        st.metric("Tasks left out", len(plan.skipped), border=True)

    if plan.items:
        st.dataframe(
            [
                {
                    "Time": f"{item.start_time:%H:%M}–{item.end_time:%H:%M}",
                    "Task": f"{item.task.emoji} {item.task.description}",
                    "Pet": pet_name(item.task.pet_id),
                    "Priority": [item.task.priority],
                    "Why": item.reason,
                }
                for item in plan.items
            ],
            column_config={
                "Time": st.column_config.TextColumn("Time", pinned=True),
                "Priority": PRIORITY_COLUMN,
                "Why": st.column_config.TextColumn("Why", width="large"),
            },
            hide_index=True,
        )

    with st.expander("Plan explanation", expanded=not plan.items):
        st.text(scheduler.explain_plan(plan))

    if plan.items and not plan.skipped:
        st.success(f"All {len(plan.items)} task(s) due fit in your available time.")
    if plan.skipped:
        st.warning(
            f"{len(plan.skipped)} task(s) left out of the plan:\n"
            + "\n".join(
                f"- {s.task.emoji} **{s.task.description}** ({pet_name(s.task.pet_id)}): {s.reason}"
                for s in plan.skipped
            )
        )

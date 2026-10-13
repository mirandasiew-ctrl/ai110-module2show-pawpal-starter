from datetime import date, time

import streamlit as st

from pawpal_system import Owner, Pet, Scheduler, Task, TimeWindow

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

SPECIES = ["dog", "cat", "other"]
PRIORITIES = ["high", "medium", "low"]
FREQUENCIES = ["daily", "weekly", "once"]

# One Owner per browser session; its pets, tasks, and windows live inside it.
st.session_state.setdefault("owner", Owner("Jordan"))
owner: Owner = st.session_state.owner


def window_label(w: TimeWindow) -> str:
    return f"{w.start:%H:%M}–{w.end:%H:%M}"


def pet_name(pet_id: int) -> str:
    pet = owner.get_pet(pet_id)
    return pet.name if pet is not None else "removed pet"


def conflict_warning(task: Task) -> str | None:
    """Describe the set-time tasks that overlap `task` on its due date, or None if none do."""
    if task.time is None or task.completed:
        return None
    others = [
        b if a is task else a
        for a, b in Scheduler(owner).find_conflicts(task.due_date)
        if a is task or b is task
    ]
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
    st.table(
        [
            {
                "Name": p.name,
                "Species": p.species,
                "Breed": p.breed,
                "Age": p.age,
                "Special needs": ", ".join(p.special_needs),
                "Tasks": len(p.tasks),
            }
            for p in owner.pets
        ]
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

    all_tasks = owner.get_all_tasks()
    if all_tasks:
        st.table(
            [
                {
                    "Pet": pet_name(t.pet_id),
                    "Task": t.description,
                    "Minutes": t.duration_minutes,
                    "Priority": t.priority,
                    "Set time": f"{t.time:%H:%M}" if t.time else "—",
                    "Repeats": t.frequency,
                    "Due": f"{t.due_date:%b %d}",
                    "Done": "✓" if t.completed else "",
                }
                for t in all_tasks
            ]
        )

        with st.expander("Edit, complete, or remove a task"):
            task = all_tasks[
                st.selectbox(
                    "Task to edit",
                    range(len(all_tasks)),
                    format_func=lambda i: (
                        f"{pet_name(all_tasks[i].pet_id)}: {all_tasks[i].description} "
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
    else:
        st.info("No tasks yet. Add one above.")

st.divider()

# --- Build schedule -----------------------------------------------------------

st.subheader("Build schedule")
st.caption("Plans the selected day's tasks for all pets within your available time.")

plan_date = st.date_input("Plan for", value=date.today())
if st.button("Generate schedule", type="primary"):
    scheduler = Scheduler(owner)
    plan = scheduler.generate_plan(plan_date)

    if plan.items:
        st.table(
            [
                {
                    "Time": f"{item.start_time:%H:%M}–{item.end_time:%H:%M}",
                    "Task": item.task.description,
                    "Pet": pet_name(item.task.pet_id),
                    "Why": item.reason,
                }
                for item in plan.items
            ]
        )

    with st.expander("Plan explanation", expanded=not plan.items):
        st.text(scheduler.explain_plan(plan))

    if plan.skipped:
        st.warning(
            f"{len(plan.skipped)} task(s) left out of the plan:\n"
            + "\n".join(
                f"- **{s.task.description}** ({pet_name(s.task.pet_id)}): {s.reason}"
                for s in plan.skipped
            )
        )

# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Paste a sample of your app's CLI or Streamlit output here so a reader can see what a generated plan looks like:

```
# e.g.:
# Daily plan for Biscuit (Golden Retriever):
#   08:00 — Morning walk (30 min) [priority: high]
#   09:00 — Feeding (10 min) [priority: high]
#   ...
```
Plan for Saturday, October 10:
  07:00-07:30  Morning walk (Mochi): high priority; earliest free slot that fits
  07:30-07:35  Morning meds (Mochi): high priority; set for 07:30
  07:35-07:55  Play session (Luna): medium priority; earliest freeslot that fits
  07:55-08:10  Brushing (Luna): low priority; earliest free slot that fits
  18:00-18:10  Feeding (Luna): high priority; set for 18:00
  18:30-19:15  Evening walk (Mochi): medium priority; set for 18:30
Total scheduled: 125 minutes

## 🧪 Testing PawPal+
The test suite (`tests/test_pawpal.py`, 65 tests) covers the scheduling logic in `pawpal_system.py`:
- **Validation:** rejects invalid time windows, priorities, frequencies, task durations, overlapping availability windows and duplicate pets.
- **Pets and tasks:** adding, removing, editing and moving tasks between pets, and making sure each task belongs to exactly one pet.
- **Sorting:** priority order with shorter tasks first on ties, chronological order with tasks that have no set time last, stable order for full ties, and no change to the input list.
- **Recurring tasks:** daily and weekly tasks come back on the right date. This includes overdue tasks, tasks completed early, month, year and leap-year rollovers, and not creating a duplicate when a task is completed twice.
- **Scheduling:** tasks from every pet go in one plan, set-time tasks keep their time, other tasks fill the earliest gap that fits, tasks are never split, and the plan is in time order.
- **Conflicts:** overlapping or identical times are flagged for the same pet and across pets, the higher-priority task wins, and each skipped task gets a reason. Tasks that only touch, completed tasks and tasks not yet due are not flagged.
- **Edge cases:** a pet with no tasks, an owner with no free time, a plan where every task is completed, and explaining a plan after a pet is removed.

```bash
# Run the full test suite:
pytest

# Run with coverage:
pytest --cov
```

Sample test output:

```
# Paste your pytest output here
```
python -m pytest
================= test session starts =================
platform win32 -- Python 3.13.0, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Development\AI110\Projects\ai110-module2show-pawpal-starter
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.15.1, platformdirs-4.13.0
collected 65 items                                     

tests\test_pawpal.py ........................... [ 41%]
......................................           [100%]

================= 65 passed in 0.27s ==================

python -m pytest --cov
================================= test session starts ==================================
platform win32 -- Python 3.13.0, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Development\AI110\Projects\ai110-module2show-pawpal-starter
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.15.1, platformdirs-4.13.0, cov-7.1.0
collected 65 items                                                                      

tests\test_pawpal.py ............................................................ [ 92%]
.....                                                                             [100%]

==================================== tests coverage ====================================
___________________ coverage: platform win32, python 3.13.0-final-0 ____________________

Name                   Stmts   Miss  Cover
------------------------------------------
pawpal_system.py         270     11    96%
tests\test_pawpal.py     381      0   100%
------------------------------------------
TOTAL                    651     11    98%
================================== 65 passed in 0.52s ==================================

 My Confidence Level (1–5 stars) in the system's reliability based on test results: 5

## 📐 Smarter Scheduling
This system plans one day of pet care for an owner with several pets, fitting tasks into the times the owner is free. It has the following classes: Owner, TimeWindow, Pet, Task, Scheduler, DailyPlan, ScheduledItem and SkippedTask. Owner holds the owner's pets and free time. TimeWindow holds the free periods of the Owner. Pet holds a pet's details and its tasks. Task holds care activities. Scheduler builds the plan. It reads tasks from the owner so one plan covers every pet. DailyPlan, ScheduledItem and SkippedTask are the result: a list of scheduled tasks, each with a start time, an end time and the reason it was placed there, plus a list of tasks that were left out and why.

> Fill in once you've implemented scheduling logic.

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting |Scheduler.sort_by_priority(), Scheduler.sort_by_time() | sort_by_priority: by PRIORITY_ORDER; ties go to the shorter task first. sort_by_time: set-time tasks earliest first, flexible tasks last; ties use the priority rule. |
| Filtering |Scheduler.filter_tasks() | Start from self.owner.get_all_tasks(), then filter by any mix of pet_id, pet_name, completed and due_on; a task must match all of them. pet_name ignores case and surrounding spaces, and keeps tasks from every pet with that name (use pet_id for one pet). due_on keeps tasks not completed and due on or before that date. |
| Conflict handling |Scheduler.find_conflicts(), Scheduler.detect_conflicts(), DailyPlan.skipped, TimeWindow.overlaps() | find_conflicts lists every pair of set-time tasks due that day whose times overlap, for the same or different pets (tasks that only touch don't conflict); the app warns when a new or edited task clashes. While planning, a set-time task that overlaps one already placed is left out (higher priority wins) and added to plan.skipped with the reason, along with tasks outside the owner's free time or with no free slot long enough. Overlapping availability windows are rejected. |
| Recurring tasks |Task.mark_complete(), Pet.complete_task(), Task.is_due() | Pet.complete_task marks the task done and adds the next occurrence to the same pet: daily → +1 day, weekly → +7 days (with timedelta), once → no repeat. The next date counts from the due date or today, whichever is later, so an overdue task comes back tomorrow, not in the past. Plans include only tasks due that day. |

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. Add your free time. Under Owner, add two windows: 07:00–09:00 and 18:00–20:00. The app shows "07:00–09:00, 18:00–20:00 (240 minutes)".
2. Add pets. For example, add Mochi (dog, age 3) and Luna (cat, age 7). Both appear in the pets table.
3. Add tasks.
  - For Mochi: Morning meds, 5 min, high priority, set time 07:30. Then Morning walk, 30 min, high priority, no set time.
  - For Luna: Breakfast, 10 min, medium priority, set time 07:30. A warning appears right away saying it overlaps Morning meds.
  - For Luna: Play session, 20 min, medium priority, no set time.
4. Sort and filter. Switch Sort by between Time and Priority to see the order change. Pick Luna in the pet filter to see only her tasks.
5. View today's schedule. Under Build schedule, keep today's date. The conflict warning is already showing.
   Click Generate schedule:
Morning meds keeps 07:30, because it's higher priority than Breakfast.
Morning walk fills the gap from 07:00 to 07:30.
Play session goes right after the meds.
Breakfast is listed under "left out" with the reason that it conflicts with Morning meds.
6. Fix the conflict. Edit Breakfast's time to 08:00 and generate the schedule again. Now every task fits, and the app shows a green success message.
7. Complete a recurring task. Mark Morning walk complete. It moves to the Done filter, and a new Morning walk due tomorrow appears in To do. Set the plan date to tomorrow and generate the schedule to see it there.

Key Scheduler behaviors shown
- Sorting by time: set-time tasks are listed earliest first and tasks with no set time come last. Tasks at the same time are ordered by priority.
- Sorting by priority: high, then medium, then low. On a tie, the shorter task comes first.
- Filtering: by pet and by done or not done, across all pets.
- Conflict warnings: overlapping set-time tasks are flagged when you add or edit them, in the task table, and before planning.
- Conflict resolution: the higher-priority task keeps its time, and the other is left out with a reason.
- Gap filling: tasks with no set time go into the earliest free gap they fit. A short task can still use an early gap.
- Recurrence: completing a daily task creates tomorrow's copy, and a weekly task comes back 7 days later.
Explanations: every scheduled task and every skipped task shows why.

Sample CLI output (python main.py)
main.py builds an owner with two pets and three free windows. It prints the tasks sorted and filtered, warns about conflicts, and then prints today's plan:
Sorted by time (flexible tasks last):
  07:30     Morning meds   Mochi  high      5 min  pending
  07:30     Breakfast      Luna   medium   10 min  pending
  12:15     Lunch treat    Mochi  low       5 min  pending
  18:00     Feeding        Luna   high     10 min  pending
  18:30     Evening walk   Mochi  medium   45 min  pending
  flexible  Morning walk   Mochi  high     30 min  pending
  flexible  Vet call       Mochi  medium   10 min  done
  flexible  Play session   Luna   medium   20 min  pending
  flexible  Brushing       Luna   low      15 min  pending

...

Luna's tasks (filter pet_name=" luna "), sorted by time:
  07:30     Breakfast      Luna   medium   10 min  pending
  18:00     Feeding        Luna   high     10 min  pending
  flexible  Play session   Luna   medium   20 min  pending
  flexible  Brushing       Luna   low      15 min  pending

...

Conflicts among today's set-time tasks (checked before planning):
  WARNING: Morning meds (Mochi) at 07:30 overlaps Breakfast (Luna) at 07:30

Today's Schedule for Jordan
Available: 300 minutes across 3 windows

Plan for Friday, October 16:
  07:00-07:30  Morning walk (Mochi): high priority; earliest free slot that fits
  07:30-07:35  Morning meds (Mochi): high priority; set for 07:30
  07:35-07:55  Play session (Luna): medium priority; earliest free slot that fits
  07:55-08:10  Brushing (Luna): low priority; earliest free slot that fits
  12:15-12:20  Lunch treat (Mochi): low priority; set for 12:15
  18:00-18:10  Feeding (Luna): high priority; set for 18:00
  18:30-19:15  Evening walk (Mochi): medium priority; set for 18:30
Total scheduled: 130 minutes
Skipped:
  Breakfast (Luna): set for 07:30, conflicts with Morning meds (Mochi) at 07:30-07:35

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->

# Challenge 3: Advanced Priority Scheduling

python main.py 
All tasks, in the order they were added:
  18:30     Evening walk   Mochi  medium   45 min  pending
  flexible  Morning walk   Mochi  high     30 min  pending
  12:15     Lunch treat    Mochi  low       5 min  pending
  07:30     Morning meds   Mochi  high      5 min  pending
  flexible  Vet call       Mochi  medium   10 min  done
  flexible  Brushing       Luna   low      15 min  pending
  18:00     Feeding        Luna   high     10 min  pending
  flexible  Play session   Luna   medium   20 min  pending
  07:30     Breakfast      Luna   medium   10 min  pending

Sorted by time (flexible tasks last):
  07:30     Morning meds   Mochi  high      5 min  pending
  07:30     Breakfast      Luna   medium   10 min  pending
  12:15     Lunch treat    Mochi  low       5 min  pending
  18:00     Feeding        Luna   high     10 min  pending
  18:30     Evening walk   Mochi  medium   45 min  pending
  flexible  Morning walk   Mochi  high     30 min  pending
  flexible  Vet call       Mochi  medium   10 min  done
  flexible  Play session   Luna   medium   20 min  pending
  flexible  Brushing       Luna   low      15 min  pending

Sorted by priority, then time:
  07:30     Morning meds   Mochi  high      5 min  pending
  18:00     Feeding        Luna   high     10 min  pending
  flexible  Morning walk   Mochi  high     30 min  pending
  07:30     Breakfast      Luna   medium   10 min  pending
  18:30     Evening walk   Mochi  medium   45 min  pending
  flexible  Vet call       Mochi  medium   10 min  done
  flexible  Play session   Luna   medium   20 min  pending
  12:15     Lunch treat    Mochi  low       5 min  pending
  flexible  Brushing       Luna   low      15 min  pending

Pending tasks, by priority then time:
  07:30     Morning meds   Mochi  high      5 min  pending
  18:00     Feeding        Luna   high     10 min  pending
  flexible  Morning walk   Mochi  high     30 min  pending
  07:30     Breakfast      Luna   medium   10 min  pending
  18:30     Evening walk   Mochi  medium   45 min  pending
  flexible  Play session   Luna   medium   20 min  pending
  12:15     Lunch treat    Mochi  low       5 min  pending
  flexible  Brushing       Luna   low      15 min  pending

Completed tasks:
  flexible  Vet call       Mochi  medium   10 min  done

Luna's tasks (filter pet_name=" luna "), by priority then time:
  18:00     Feeding        Luna   high     10 min  pending
  07:30     Breakfast      Luna   medium   10 min  pending
  flexible  Play session   Luna   medium   20 min  pending
  flexible  Brushing       Luna   low      15 min  pending

Mochi's pending tasks, by priority then time:
  07:30     Morning meds   Mochi  high      5 min  pending
  flexible  Morning walk   Mochi  high     30 min  pending
  18:30     Evening walk   Mochi  medium   45 min  pending
  12:15     Lunch treat    Mochi  low       5 min  pending

Conflicts among today's set-time tasks (checked before planning):
  WARNING: Morning meds (Mochi) at 07:30 overlaps Breakfast (Luna) at 07:30

Today's Schedule for Jordan
Available: 300 minutes across 3 windows

Plan for Friday, October 16:
  07:00-07:30  Morning walk (Mochi): high priority; earliest free slot that fits
  07:30-07:35  Morning meds (Mochi): high priority; set for 07:30
  07:35-07:55  Play session (Luna): medium priority; earliest free slot that fits
  07:55-08:10  Brushing (Luna): low priority; earliest free slot that fits
  12:15-12:20  Lunch treat (Mochi): low priority; set for 12:15
  18:00-18:10  Feeding (Luna): high priority; set for 18:00
  18:30-19:15  Evening walk (Mochi): medium priority; set for 18:30
Total scheduled: 130 minutes
Skipped:
  Breakfast (Luna): set for 07:30, conflicts with Morning meds (Mochi) at 07:30-07:35

# Challenge 4: Professional UI and Output Formatting

No extra libraries were added. The web app uses only **Streamlit** (already in `requirements.txt`), and the CLI and emojis use only the **Python standard library**.

### Streamlit app (`app.py`)

| Feature | What the user sees | Function / library |
|---|---|---|
| Status messages | Yellow warnings for conflicts and skipped tasks, red errors for invalid input, blue info boxes for empty states, a green message when every task fits | `st.warning` (with `icon=":material/warning:"`), `st.error`, `st.info`, `st.success` |
| Conflict warning before planning | Every overlapping pair of set-time tasks for the chosen day, listed before you click Generate | `Scheduler.find_conflicts()` + `st.warning` |
| Summary cards | Bordered cards above the plan: tasks scheduled, time used (e.g. "25 of 120 min"), tasks left out | `st.metric(..., border=True)` inside `st.container(horizontal=True)` |
| Interactive tables | Task, plan, and pet tables with hidden index columns; columns can be sorted by clicking a header | `st.dataframe(..., column_config=..., hide_index=True)` |
| Colored priority badges | Red = high, orange = medium, blue = low | `st.column_config.MultiselectColumn(options=["high", "medium", "low"], color=["red", "orange", "blue"])` |
| Special needs badges | Each special need as a gray badge | `st.column_config.MultiselectColumn(color="gray")` |
| Done checkbox | A checkbox instead of text for completed tasks | `st.column_config.CheckboxColumn` |
| Formatted values | Times as `07:30`, dates as `Oct 16`, lengths as `20 min`, ages as `3 yr` | `st.column_config.TimeColumn(format="HH:mm")`, `DateColumn(format="MMM D")`, `NumberColumn(format="%d min")` |
| Pinned columns | Pet, Task, and Time columns stay visible when scrolling sideways | `st.column_config.TextColumn(pinned=True)` |
| Conflict column | ⚠️ plus the name of the clashing task, e.g. "⚠️ 💊 Meds (Luna)" | `Scheduler.find_conflicts()` + f-string |
| Filter and sort controls | Pick a pet; show To do / Done / All; sort by Time or Priority | `st.selectbox`, `st.segmented_control`, `Scheduler.filter_tasks()`, `sort_by_time()`, `sort_by_priority_then_time()` |
| Plan explanation | The full plan and skipped tasks as text, in a collapsible section | `st.expander` + `st.text(Scheduler.explain_plan(plan))` |

### Task type emojis (app and CLI)

Each task gets an emoji from keywords in its description: 🦮 walk, 💊 meds, 🥣 meals, 🦴 treats, 🩺 vet, 🛁 grooming, 🎾 play, 💧 water, 🎓 training, 🧹 cleaning, and 🐾 for anything else.

- **Where:** the `Task.emoji` property and the `TASK_TYPE_EMOJIS` table in `pawpal_system.py`.
- **How:** no emoji library. The emojis are plain Unicode characters. Python's built-in `re` module (`re.findall`) splits the description into words, and `str.lower()` and `str.startswith()` match them against keywords, so "Feeding" matches "feed". The first match wins, so "Lunch treat" is 🦴, not 🥣.
- Only single-character emojis are used, so the CLI columns stay aligned.

### CLI output (`main.py`)

| Feature | Function / library |
|---|---|
| Aligned columns (time, emoji, task, pet, priority, length, status) | f-string padding, e.g. `{task.description:<14}`, `{task.duration_minutes:>3} min` (no table library) |
| Sections sorted and filtered different ways | `Scheduler.sort_by_time()`, `sort_by_priority_then_time()`, `filter_tasks()` |
| `WARNING:` lines for conflicts | `Scheduler.find_conflicts()` |
| Plan with a reason for every task, plus skipped tasks | `Scheduler.explain_plan()` |


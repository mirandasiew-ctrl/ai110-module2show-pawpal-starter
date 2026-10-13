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

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->

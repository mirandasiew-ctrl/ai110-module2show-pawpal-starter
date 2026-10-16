# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.
My initial UML design models one owner who has one or more pets. Each pet has its own care tasks, and a scheduler fits those tasks into the owner's available time to build a plan for the day. I started with four classes (Owner, Pet, Task, Scheduler) and added three supporting classes (TimeWindow, DailyPlan, ScheduledItem) once it was clear the scheduler needed to know when the owner is free and needed somewhere to put its output.

- What classes did you include, and what responsibilities did you assign to each?
Owner: stores the owner's name, their pets, and their availability as a list of time windows. It adds and removes pets, collects every pet's tasks, adds availability windows (rejecting any that overlap an existing window), and totals the available minutes.

TimeWindow: one block of free time with a start and an end. It validates that the start is before the end, reports its length, checks whether a task of a given length fits starting at a given time, and checks whether it overlaps another window.

Pet: stores the pet's details (name, species, breed, age, special needs) and its list of tasks. It adds and removes tasks and returns the ones not yet completed.

Task: a single care activity with a description, duration, priority, optional set time (e.g., meds at 08:00), frequency, and completion status. It can be marked complete.

Scheduler: holds the scheduling logic. It sorts tasks by priority, filters them by pet or status, and generates the daily plan. It places set-time tasks first and leaves out any that conflict with a task already scheduled, then fills each window with the remaining tasks in priority order. Tasks are never split across windows, and a task that fits in no window is left out. It also explains the resulting plan.

DailyPlan: the output for one day, holding the date and the list of scheduled items, and totaling the scheduled minutes.

ScheduledItem: one entry in the plan, linking a task and its pet to a start time, an end time, and a short reason it was placed there.

**b. Design changes**

- Did your design change during implementation?
Yes.

- If yes, describe at least one change and why you made it.
Missing Task - Pet relationship. 
Owner.get_all_tasks() returns a list[Task], and a Task doesn't record which pet it belongs to. Once tasks come out of get_all_tasks(), the scheduler can't tell whose task it is. filter_tasks() has the same problem

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
The scheduler considers these constraints:
- Available time: tasks are only scheduled inside the owner's availability windows, and a task must fit entirely inside one window. Tasks are never split across windows or gaps.
- Set times: a task with a set time (e.g. meds at 08:00) is placed at exactly that time or left out. It is never moved to another slot.
- Priority: high, medium and low decide the order tasks are placed in. When two set-time tasks overlap, the higher-priority one keeps its time.
- Duration: a task only goes into a free gap that is at least as long as the task. When two tasks have the same priority, the shorter one goes first, so more tasks fit.
- No overlaps: two tasks can't be scheduled at the same time, even for different pets, because one owner does all the care. Tasks that only touch (one ends at 8:00 and the next starts at 8:00) are allowed.
- Due date and status: only tasks that aren't completed and are due on or before the plan date are scheduled. Overdue tasks carry over, and future tasks wait.
- Frequency: daily and weekly tasks come back after they are completed, so each day's plan only includes that day's copy.

It does not consider pet preferences. Breed, age and special needs are stored on each pet and shown in the app, but the scheduler doesn't use them. A preference like "walk Mochi in the morning" has to be entered as a set time on the task.

- How did you decide which constraints mattered most?
I sorted the constraints into hard ones that a plan can never break and soft ones that decide what happens when not everything fits. The hard constraints come from what's physically or medically possible: available time, no overlaps, set times, and no splitting.

For the soft constraints, I ranked priority first. Among tasks with the same priority, shorter ones go first so more of them fit. Due dates and completion status decide which tasks are in the plan at all, rather than how they're placed. Overdue tasks carry over because a missed daily task still needs doing.

I left pet preferences out of the scheduler on purpose. They're harder to define as rules, and a set time already covers the most common one.

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
The scheduler is greedy and priority-first: it places one task at a time, highest priority first, and never goes back to rearrange what it has already placed. When two set-time tasks overlap (for the same pet or different pets), the higher-priority one keeps its time and the other is left out of the plan rather than moved to a nearby free slot. Flexible tasks go into the first free gap that fits, so the plan isn't always the one that fits the most tasks. For example, a long task can take up an early gap that two shorter tasks could have shared. Instead of searching for a better arrangement, the plan lists every skipped task with the reason, e.g. "Breakfast (Luna): set for 07:30, conflicts with Morning meds (Mochi) at 07:30-07:35", and the app warns when a new task clashes with another.

- Why is that tradeoff reasonable for this scenario?
A pet owner's day has a handful of tasks, not hundreds, so the extra tasks an optimal search might fit in are few, while a greedy plan is fast, predictable, and easy to explain. Priority-first also matches what matters: meds and feeding should never lose their slot to a lower-priority task like brushing. A set time usually means something (meds at 08:00), so quietly moving a clashing task could do more harm than leaving it out and telling the owner, who can then decide whether to change the time.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
I use AI tools for design brainstorming, generate class diagram, implentation, and testing.

- What kinds of prompts or questions were most helpful?
The most helpful prompts asked the AI to review and explain during design phase. This confirmed the design meeting requirements and no missing relationships and potential logic bottlenecks. Broad requests like "implement the classes" worked well only after the design had been reviewed several times.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
One moment was on the ScheduledItem.pet field. I questioned it, and the AI agreed it wasn't needed.

- How did you evaluate or verify what the AI suggested?
I reviewed the classes and fields AI suggested, questioned them when they didn't make sense for me or I didn't understand. Then the AI explained it or the AI agreed with me and made the changes accordingly. After implementation, the AI generated comprehensive test cases and ran for me to verify. 
---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
The test suite has 65 pytest tests in tests/test_pawpal.py. They test sorting, recurring tasks, conflict detection, scheduling, edge cases like a pet with no tasks, an owner with no free time, a plan where every task is completed, overdue tasks carrying over, and explaining a plan after a pet was removed. They also test validation and data rules such as invalid time windows.

- Why were these tests important?
These tests were important because the scheduler's mistakes would be easy to miss but costly for a real pet owner. A plan that silently drops a medication task, or schedules two tasks at once, looks fine on screen until something goes wrong.

The logic has many interacting rules. Set-time tasks, free gaps, priority order and conflict handling all affect each other. Clicking through the app might never produce the exact case where an early gap gets used up wrongly, but a test with fixed times checks the exact output.

Most bugs happen at the edges. That includes a task ending exactly at a window's end, two tasks that only touch, two tasks at the same time, and dates at the end of a month or year. These are the cases where it's easy to mix up < and <=, so I tested each one directly.

Recurrence depends on dates. It's easy to get wrong without noticing, for example an overdue task coming back with a date in the past. Fixing "today" to a set date in the tests made those checks repeatable.

The tests found a real bug. Completing the same task twice, which a double-click in the app could do, created two copies of tomorrow's task. Writing the test first exposed the bug, and the same test now stops it from coming back.
They let me change code safely. When I added sorting, filtering and conflict warnings, and later reworked the app, running all the tests showed that the existing scheduling still worked.

They lock in the design rules. For example, the scheduler must plan across all pets, never just one. A test enforces that, so a later change can't quietly break it.

**b. Confidence**

- How confident are you that your scheduler works correctly?
I am over 90% confident that the scheduler works correctly.

- What edge cases would you test next if you had more time?
I would test marking a completed task as not done, tasks near midnight that will end past midnight to confirm it is skipped cleanly, three or more tasks at the same time that only the highest-priority one is kept.

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?
I'm most satisfied with the design part. I started from a UML diagram, questioned the AI's suggestions until each class made sense to me, and the final code ended up with the same eight classes. Key rules like "the scheduler always reads tasks from the owner, across all pets" stayed consistent from the diagram to the code to the tests.

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?
I would improve on using preferences in scheduling. Pet has special_needs, age and breed information, but the scheduler ignores them. I would add the design to make use of this information when scheduling.

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
What I have learned is if something I don't understand or have questions about, ask the AI, then the AI will review and may found that there is a bug.  And, it is very important to work with the AI to come up with a correct design first, then the AI will implement the logic correctly at the first place instead of making changes later on that may produce more bugs and more work to clean up.


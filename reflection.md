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
- How did you decide which constraints mattered most?

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
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?

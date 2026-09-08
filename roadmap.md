# TRACE — Advanced Feature Roadmap

> Companion document to `project.md`. This is the strategic proposal and build order for advanced differentiating features in TRACE.

Legend: **Complexity** = rough build effort. **Depends on** = existing TRACE modules and services.

---

## Tier 1 — High Impact, Builds Directly on Core TRACE Stack

### 1. Task Health Score (tree-aware risk indicator)
A single computed signal (Green / Yellow / Red) per task node, rolled up to parents so a PM can see risk without opening every leaf.

- **Inputs:** time-in-current-status vs. estimated hours, commit frequency vs. task age, LLM sentiment/blocker detection on the task's group chat messages, GitHub issue activity (stale issue = red flag).
- **Rollup rule:** a parent's health = worst health among children with a weighting toward nodes closer to deadline. Store computed value (`health_score`, `health_reason`), don't compute live on every read.
- **Depends on:** existing task tree, `evaluate-tree` endpoint, ProjectGroup chat, Celery Beat.
- **Complexity:** Medium. Celery periodic task (`compute_task_health`) + UI health badge.
- **Why unique:** Turns your infinite task tree into a live risk map instead of a static Kanban board.

### 2. Explainable AI Evaluation + Dispute Workflow
Extend commit verification and productivity scores with transparency and a human-in-the-loop override.

- **What to build:** extend LLM response schema to require a structured `{verdict, confidence, reasoning, evidence}` JSON. Add a "Contest Verdict" button on low-confidence or failed verifications that creates a review request routed to the task's Team Lead/PM, who can override with their own note (stored alongside the AI verdict).
- **Depends on:** LLM Commit Verification (Module 3c), Productivity Scoring (Module 4).
- **Complexity:** Low–Medium. Prompt engineering + `evaluation_disputes` table + review queue UI.
- **Why unique:** Transparent AI verdicts with an explicit appeal trail build organizational trust.

### 3. AI Task Decomposition
Given a parent task's title + description, the LLM proposes a child-task tree (titles, priorities, rough estimates, suggested role level) that the PM/Team Lead can accept, edit, or discard before creation.

- **Flow:** `POST /tasks/{id}/suggest-subtasks` → Celery job calls OpenAI SDK with task context + sibling task history → returns draft JSON → frontend renders as an editable tree preview → user confirms → bulk-create via existing task CRUD.
- **Depends on:** Infinite Task Tree (Module 3a), OpenAI SDK via Celery.
- **Complexity:** Medium.
- **Why unique:** Turns manual breakdown into AI-assisted tree planning.

### 4. Scope-Drift Detection (longitudinal commit analysis)
Extend single-commit verification to track drift across a task's *entire* commit history over time — flagging when accumulated changes wander from the original task scope.

- **Implementation:** store each commit's LLM-extracted intent summary in a `task_commit_log` table. A Celery Beat job periodically re-evaluates the task description against aggregated intent history and flags scope drift.
- **Depends on:** Module 3c (LLM Commit Verification), Celery Beat.
- **Complexity:** Medium.
- **Why unique:** Temporal scope-creep detection across multi-commit development cycles.

### 5. Cross-Tree Overallocation Detection
Because roles rotate per task node, the same employee can be assigned as a Member/Team Lead across several unrelated task subtrees simultaneously.

- **Implementation:** a nightly Celery job aggregates all active task-role assignments per user across all trees, cross-references estimated hours + due dates, and flags overlapping high-load windows. Surface on Manager dashboard as "Workload Conflicts".
- **Depends on:** Task Tree, HRMS shift/attendance data (for real available-hours baseline).
- **Complexity:** Low–Medium.
- **Why unique:** Solves a structural edge case created by TRACE's rotating-role tree design.

---

## Tier 2 — Strong Differentiators, Moderate Build Effort

### 6. Chat-Ops: Natural-Language Task Commands
Inside tree-scoped group chat, allow users to type commands like `@trace create subtask under 1.2, assign @sam, due friday, priority high` and have the LLM parse it into structured task creation calls respecting role permissions.
- **Depends on:** Project Group Chat (3e), OpenAI SDK, @mention tag rules.
- **Complexity:** Medium.

### 7. Auto-Escalation Engine
When a task's Health Score stays Red for N days or a task is blocked without commit activity, auto-post an escalation message up the rotation chain (Member → Team Lead → PM) and trigger notifications via Mailpit.
- **Depends on:** #1 Task Health Score, Progress Propagation (3d), Celery Beat, Mailpit service.
- **Complexity:** Low (once #1 exists).

### 8. Reusable Subtree Templates
Save any subtree (e.g. standard "Sprint" or "Feature Rollout" hierarchy) as a reusable template and instantiate it under any new parent task in one action.
- **Depends on:** Task Tree CRUD.
- **Complexity:** Low–Medium.

### 9. Skill-Aware Assignment Recommendation
When assigning ground-level tasks, recommend the best-fit Member based on historical commit-verification pass rates and productivity scores for similar task tags/descriptions.
- **Depends on:** Productivity Scoring (Module 4), Commit Verification history (3c), task tags.
- **Complexity:** Medium.

### 10. Contribution Heatmap (GitHub-Style Cross-System Visual)
A combined employee heatmap visual merging attendance clock-ins, task completions, and verified commits into a unified visual matrix.
- **Depends on:** Attendance (2b), Task Tree (3a), Commit Verification (3c).
- **Complexity:** Low.

---

## Tier 3 — Next-Gen Innovations & Enterprise Capabilities

### 11. Voice/Whiteboard-to-Task-Tree
Upload a whiteboard planning photo or voice memo; LLM (vision + transcription) parses it into a draft subtask tree for review and instantiation.
- **Complexity:** High.

### 12. Critical-Path & Dependency Graph Overlay
Detect implicit dependencies from GitHub issue cross-references, commit messages, and chat mentions, rendering a DAG overlay on the tree with computed critical paths and completion projections.
- **Complexity:** High.

### 13. Fairness & Bias Audit for AI Scoring
A transparency dashboard tracking whether productivity and commit-verification scores show systematic variance across departments or teams.
- **Complexity:** Medium.

---

## Suggested Execution Order

1. **Task Health Score** (#1) — Foundational risk indicator; enables #7 auto-escalation.
2. **Explainable AI Evaluation + Dispute Workflow** (#2) — Structured JSON verdicts and appeal queue for user trust.
3. **Auto-Escalation Engine** (#7) — Auto-escalate stuck tasks up the rotation chain.
4. **AI Task Decomposition** (#3) — High-impact AI tree planning demo.
5. **Cross-Tree Overallocation Detection** (#5) — Prevents resource burnout across infinite tree nodes.

---

## Technical & Architectural Guidelines for AI Agent

- **Asynchronous Execution:** All LLM tasks must run asynchronously via **Celery workers wrapping the OpenAI SDK**. Never invoke LLM calls synchronously within FastAPI HTTP request handlers.
- **Structured JSON Schema Output:** Always enforce structured JSON schemas (`{verdict, confidence, reasoning, evidence}`) for LLM evaluations to ensure machine readability and auditing.
- **Celery Beat Scheduling:** Group periodic jobs (Health Score computation, Scope-Drift detection, Overallocation queries) under central Celery Beat schedules.
- **Additive Architecture:** Build features as non-breaking extensions on top of the recursive `parent_task_id` schema.

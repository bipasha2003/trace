"""
TRACE - The AI pipeline's job bodies (CORE.md §3–6)

Plain async functions: `app/tasks.py` calls them from Celery with a fresh session,
the AI client and the GitHub client; tests call them with fakes. Each one that
writes records its failure where people will see it (CORE.md §2 rule 6):
`projects.ai_errors[<job>]` or `tasks.progress_doc_error`.

Suggestion jobs write nothing — their result is the Celery job result.
"""

import json
import logging
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import TraceException
from app.models.project import Project, ProjectAssignment, ProjectSourceFile, TaskGroup
from app.models.task import Task
from app.schemas.ai import (
    GanttRevisionOut, PeopleSuggestionsOut, ProgressReportOut, ProjectDocumentOut,
    TaskGroupPlanOut, TaskProgressPlanOut, TaskSuggestionsOut,
)
from app.services import gantt_service
from app.services import notification_service as notifications
from app.services.ai_service import AINotConfigured, complete
from app.services.github_service import GitHubClient, GitHubNotConfigured
from app.services.project_service import active_employees, person
from app.services.scoring_service import candidate_stats

logger = logging.getLogger("trace.ai_jobs")

# Where each document lives in the project repository (CORE.md §10)
DOC_PATHS = {
    "initial": "docs/project_initial_doc.md",
    "doc": "docs/project_doc.md",
    "progress": "docs/project_progress_doc.md",
    "report": "docs/project_report_doc.md",
}
DOC_COLUMNS = {
    "initial": "project_initial_doc", "doc": "project_doc",
    "progress": "project_progress_doc", "report": "project_report_doc",
}
SOURCE_CHAR_LIMIT = 60_000
TASK_DOC_CHAR_LIMIT = 4_000
MAX_CANDIDATES = 25


def task_doc_path(task_id: int) -> str:
    return f"docs/tasks/task-{task_id}.md"


def describe(exc: Exception) -> str:
    if isinstance(exc, TraceException):
        return str(exc.detail)
    return str(exc) or exc.__class__.__name__


def set_ai_error(project: Project, job: str, message: str | None) -> None:
    errors = dict(project.ai_errors or {})
    if message:
        errors[job] = {"message": message[:1000], "at": datetime.now(timezone.utc).isoformat()}
    else:
        errors.pop(job, None)
    project.ai_errors = errors or None


def _require(ai, github) -> None:
    if ai is None:
        raise AINotConfigured()
    if github is None:
        raise GitHubNotConfigured()


async def _commit_doc(github: GitHubClient, project: Project, path: str, content: str,
                      job: str, job_id: str | None) -> str:
    return await github.commit_file(
        project.github_repo, path, content, f"TRACE: {path} ({job} {job_id or 'manual'})",
        project.github_default_branch,
    )


async def read_document(github: GitHubClient, project: Project, path: str) -> str | None:
    return await github.read_file(project.github_repo, path, project.github_default_branch)


# ══════════════════════════════════════════════════════════════════
#  Stage 1 — evaluate_project (§3 steps 1–6, 9)
# ══════════════════════════════════════════════════════════════════

DOC_SYSTEM = (
    "You are the requirements analyst of TRACE, a project management system. From the source "
    "documents, write the project document the team will plan from: purpose, scope, features "
    "(one heading each, with acceptance points), non-functional requirements, open questions. "
    "Markdown, factual, no invented requirements."
)
GROUPS_SYSTEM = (
    "You are the delivery planner of TRACE. Split the project into 3–10 task groups (modules of "
    "work that each end in something demonstrable). Give each a realistic duration in working-"
    "calendar days for a small team, a sequence starting at 1, and depends_on: names of earlier "
    "groups that must finish first. Only add a dependency when the work truly waits for it."
)


def _sources_text(files: list[ProjectSourceFile]) -> str:
    parts, used = [], 0
    for f in files:
        room = SOURCE_CHAR_LIMIT - used
        if room <= 0:
            break
        text = (f.extracted_text or "")[:room]
        used += len(text)
        parts.append(f"## Source file: {f.file_name}\n\n{text}")
    return "\n\n".join(parts)


async def run_evaluate_project(db: AsyncSession, project_id: int, *, job_id: str | None,
                               ai, github: GitHubClient | None) -> dict:
    project = await db.get(Project, project_id)
    if project is None or project.deleted_at is not None:
        return {"status": "skipped", "reason": "project not found"}
    step = "starting"
    try:
        _require(ai, github)
        step = "reading the source files"
        files = (await db.execute(select(ProjectSourceFile).where(
            ProjectSourceFile.project_id == project_id, ProjectSourceFile.deleted_at.is_(None),
            func.length(func.coalesce(ProjectSourceFile.extracted_text, "")) > 0,
        ).order_by(ProjectSourceFile.id))).scalars().all()
        if not files:
            raise TraceException(409, "no source file has any extracted text")

        step = "writing the project document"
        doc = await complete(ai, ProjectDocumentOut, DOC_SYSTEM,
                             f"Project: {project.name}\n{project.description or ''}\n\n{_sources_text(files)}")
        markdown = doc.markdown if doc.markdown.lstrip().startswith("#") else f"# {doc.title}\n\n{doc.markdown}"

        step = "committing the project documents"
        initial_url = await _commit_doc(github, project, DOC_PATHS["initial"], markdown, "evaluate_project", job_id)
        doc_url = await _commit_doc(github, project, DOC_PATHS["doc"], markdown, "evaluate_project", job_id)

        step = "planning the task groups"
        plan = await complete(ai, TaskGroupPlanOut, GROUPS_SYSTEM, markdown)

        step = "building the Gantt chart"
        if (await db.execute(select(func.count(Task.id)).where(
                Task.project_id == project_id, Task.deleted_at.is_(None)))).scalar():
            raise TraceException(409, "the project has tasks now, so its task groups can no longer be replaced")
        now = datetime.now(timezone.utc)
        for old in (await db.execute(select(TaskGroup).where(
                TaskGroup.project_id == project_id, TaskGroup.deleted_at.is_(None)))).scalars():
            old.deleted_at = now

        today = date.today()
        project.start_date = project.start_date or today
        ids: dict[str, int] = {}
        groups = []
        for sequence, g in enumerate(plan.task_groups, start=1):
            row = TaskGroup(project_id=project_id, name=g.name.strip(), description=g.description or None,
                            sequence=sequence, estimated_duration_days=g.estimated_duration_days,
                            status="Pending", created_by="AI", completion_percentage=0)
            db.add(row)
            await db.flush()
            row.depends_on = [ids[d.strip().lower()] for d in g.depends_on] or None
            ids[row.name.lower()] = row.id
            groups.append(row)
        gantt_service.schedule(groups, project.start_date, today)
        project.end_date = project.end_date or max(g.planned_end_date for g in groups)
        project.project_initial_doc, project.project_doc = initial_url, doc_url
        await db.flush()
        await gantt_service.snapshot(db, project, "initial", job_id)

        project.status = "Active"
        project.last_evaluated_at = now
        set_ai_error(project, "evaluate_project", None)
        outbox = await notifications.notify(  # CORE.md §9 — the Manager who pressed Evaluate
            db, [project.created_by_user_id], "project_evaluated", f"Evaluated: {project.name}",
            f"{project.name} has its project document, {len(groups)} task groups and a Gantt chart.",
            project_id=project.id)
        await db.commit()
        notifications.deliver(outbox)
        return {"status": "success", "task_groups": len(groups)}
    except Exception as exc:
        await db.rollback()
        logger.exception("[evaluate_project] project %s failed while %s", project_id, step)
        project = await db.get(Project, project_id)
        project.status = "Active" if project.last_evaluated_at else "Draft"
        message = f"Failed while {step}: {describe(exc)}"
        set_ai_error(project, "evaluate_project", message)
        outbox = await notifications.notify(
            db, [project.created_by_user_id], "project_evaluated", f"Evaluation failed: {project.name}",
            message, project_id=project.id)
        await db.commit()
        notifications.deliver(outbox)
        return {"status": "failed", "error": message}


# ══════════════════════════════════════════════════════════════════
#  Suggestions (§3 steps 7–8, §4) — nothing is written
# ══════════════════════════════════════════════════════════════════

PM_SYSTEM = (
    "You rank candidates to be the Project Manager of a project. Rank on projects delivered, "
    "on-time delivery rate, and average task completion across the projects they manage; "
    "a strong task record counts when they have not managed a project yet. Score 0–1. "
    "Reason briefly from the numbers given; never invent facts. Return at most 10."
)
ASSIGNEE_SYSTEM = (
    "You rank candidates to be assigned one task. Rank on tasks completed, on-time rate, current "
    "open workload, and how similar their recently completed task titles are to this task. "
    "Score 0–1. Reason briefly from the data given; never invent facts. Return at most 10."
)
TASKS_SYSTEM = (
    "You break one task group of a project into concrete tasks a single person can finish in "
    "1–5 days. Do not repeat tasks that already exist. Give each an estimate in hours."
)


async def _rank_people(db: AsyncSession, ai, system: str, brief: str, users: list) -> dict:
    if ai is None:
        raise AINotConfigured()
    if not users:
        return {"suggestions": []}
    stats = await candidate_stats(db, [u.id for u in users])
    users = sorted(users, key=lambda u: stats[u.id]["tasks_completed"], reverse=True)[:MAX_CANDIDATES]
    by_id = {u.id: u for u in users}
    candidates = [{"user_id": u.id, "name": u.name, **stats[u.id]} for u in users]
    out = await complete(ai, PeopleSuggestionsOut, system,
                         f"{brief}\n\nCandidates:\n{json.dumps(candidates, default=str)}",
                         context={"candidates": set(by_id)})
    return {"suggestions": [{
        "user": person(by_id[s.user_id]), "score": s.score, "reasoning": s.reasoning,
        "evidence": s.evidence, "stats": stats[s.user_id],
    } for s in out.suggestions]}


async def _project_brief(db: AsyncSession, project: Project) -> str:
    groups = (await db.execute(select(TaskGroup.name).where(
        TaskGroup.project_id == project.id, TaskGroup.deleted_at.is_(None)).order_by(TaskGroup.sequence)
    )).scalars().all()
    return (f"Project: {project.name}\n{project.description or ''}\n"
            f"Task groups: {', '.join(groups) or 'none yet'}")


async def run_suggest_managers(db: AsyncSession, project_id: int, *, ai, **_) -> dict:
    project = await db.get(Project, project_id)
    current = set((await db.execute(select(ProjectAssignment.user_id).where(
        ProjectAssignment.project_id == project_id, ProjectAssignment.project_role == "Project Manager",
        ProjectAssignment.deleted_at.is_(None)))).scalars())
    users = [u for u in await active_employees(db) if u.id not in current]
    return await _rank_people(db, ai, PM_SYSTEM, await _project_brief(db, project), users)


async def run_suggest_assignees(db: AsyncSession, project_id: int, title: str, description: str | None,
                                *, ai, **_) -> dict:
    project = await db.get(Project, project_id)
    brief = f"{await _project_brief(db, project)}\n\nTask: {title}\n{description or ''}"
    return await _rank_people(db, ai, ASSIGNEE_SYSTEM, brief, await active_employees(db))


async def run_suggest_tasks(db: AsyncSession, group_id: int, *, ai, **_) -> dict:
    if ai is None:
        raise AINotConfigured()
    group = await db.get(TaskGroup, group_id)
    project = await db.get(Project, group.project_id)
    existing = (await db.execute(select(Task.title).where(
        Task.task_group_id == group_id, Task.deleted_at.is_(None)))).scalars().all()
    out = await complete(ai, TaskSuggestionsOut, TASKS_SYSTEM, (
        f"Project: {project.name}\n{project.description or ''}\n\n"
        f"Task group: {group.name}\n{group.description or ''}\n\n"
        f"Existing tasks: {json.dumps(existing)}"))
    return {"task_group_id": group_id, **out.model_dump()}


# ══════════════════════════════════════════════════════════════════
#  Stage 2 — generate_task_progress_doc (§4)
# ══════════════════════════════════════════════════════════════════

TASK_DOC_SYSTEM = (
    "You write the working plan for one task in a software project: ordered, concrete steps "
    "and testable acceptance criteria. Keep it proportionate to the task."
)


def render_task_doc(task: Task, plan: TaskProgressPlanOut) -> str:
    lines = [f"# {task.title}", "", task.description or "", "", "## Steps", ""]
    for step in sorted(plan.steps, key=lambda s: s.order):
        lines.append(f"- [{'x' if step.done else ' '}] **{step.title}**" + (f" — {step.detail}" if step.detail else ""))
    lines += ["", "## Acceptance criteria", ""] + [f"- [ ] {c}" for c in plan.acceptance_criteria]
    if task.github_issue_url:
        lines += ["", f"GitHub issue: {task.github_issue_url}"]
    return "\n".join(lines).replace("\n\n\n", "\n\n") + "\n"


async def run_task_progress_doc(db: AsyncSession, task_id: int, *, job_id: str | None,
                                ai, github: GitHubClient | None) -> dict:
    task = (await db.execute(select(Task).where(Task.id == task_id).options(
        selectinload(Task.task_group), selectinload(Task.project)))).scalar_one_or_none()
    if task is None or task.deleted_at is not None:
        return {"status": "skipped", "reason": "task not found"}
    try:
        _require(ai, github)
        plan = await complete(ai, TaskProgressPlanOut, TASK_DOC_SYSTEM, (
            f"Project: {task.project.name}\nTask group: {task.task_group.name if task.task_group else '—'}\n"
            f"Task: {task.title}\nPriority: {task.priority}\nDue: {task.due_date or 'not set'}\n\n"
            f"{task.description or ''}"))
        url = await _commit_doc(github, task.project, task_doc_path(task.id), render_task_doc(task, plan),
                                "generate_task_progress_doc", job_id)
        task.task_progress_doc, task.progress_doc_error = url, None
        await db.commit()
        return {"status": "success", "url": url}
    except Exception as exc:
        await db.rollback()
        logger.exception("[generate_task_progress_doc] task %s failed", task_id)
        task = await db.get(Task, task_id)
        task.progress_doc_error = describe(exc)[:1000]
        await db.commit()
        return {"status": "failed", "error": task.progress_doc_error}


# ══════════════════════════════════════════════════════════════════
#  Stage 3 — reevaluate_gantt (§5)
# ══════════════════════════════════════════════════════════════════

REVISE_SYSTEM = (
    "The project document changed. Given it and every task group's progress, re-estimate the "
    "remaining duration (in days, from its start) of unfinished groups whose scope changed, and "
    "add new groups only for features that no existing group covers. Leave everything else out."
)


async def _revise_from_document(db: AsyncSession, project: Project, groups: list[TaskGroup],
                                ai, github: GitHubClient | None, job_id: str | None) -> list[TaskGroup]:
    _require(ai, github)
    document = await read_document(github, project, DOC_PATHS["doc"])
    if not document:
        raise TraceException(409, "the project document could not be read from the repository")
    open_ids = {g.id for g in groups if g.status != "Completed"}
    summary = [{"task_group_id": g.id, "name": g.name, "status": g.status,
                "completion_percentage": float(g.completion_percentage or 0),
                "estimated_duration_days": g.estimated_duration_days} for g in groups]
    out = await complete(ai, GanttRevisionOut, REVISE_SYSTEM,
                         f"Task groups:\n{json.dumps(summary)}\n\nProject document:\n{document[:SOURCE_CHAR_LIMIT]}",
                         context={"open_groups": open_ids, "all_groups": {g.id for g in groups}})
    by_id = {g.id: g for g in groups}
    for r in out.revisions:
        by_id[r.task_group_id].estimated_duration_days = r.estimated_duration_days
    added = []
    sequence = max((g.sequence for g in groups), default=0)
    for n in out.new_groups:
        sequence += 1
        row = TaskGroup(project_id=project.id, name=n.name.strip(), description=n.description or None,
                        sequence=sequence, estimated_duration_days=n.estimated_duration_days,
                        depends_on=n.depends_on or None, status="Pending", created_by="AI",
                        completion_percentage=0)
        db.add(row)
        added.append(row)
    await db.flush()
    return added


async def run_reevaluate_gantt(db: AsyncSession, project_id: int, reason: str, requested_at: str, *,
                               job_id: str | None, ai, github: GitHubClient | None) -> dict:
    project = await db.get(Project, project_id)
    if project is None or project.deleted_at is not None:
        return {"status": "skipped", "reason": "project not found"}
    latest = next(iter(await gantt_service.versions(db, project_id)), None)
    if latest and latest.generated_at and latest.generated_at > datetime.fromisoformat(requested_at):
        return {"status": "skipped", "reason": f"already covered by version {latest.version}"}
    groups = [g for g, _ in await gantt_service.groups_with_tasks(db, project_id)]
    if not groups:
        return {"status": "skipped", "reason": "the project has no task groups"}

    if reason == "project_doc_updated":
        try:
            groups += await _revise_from_document(db, project, groups, ai, github, job_id)
            set_ai_error(project, "reevaluate_gantt", None)
        except Exception as exc:
            logger.exception("[reevaluate_gantt] AI revision failed for project %s", project_id)
            set_ai_error(project, "reevaluate_gantt",
                         f"The AI could not re-read the project document ({describe(exc)}); "
                         "the chart was re-planned from the current task groups without it")

    today = date.today()
    gantt_service.schedule(groups, project.start_date or today, today)
    await db.flush()
    version = await gantt_service.snapshot(db, project, reason, job_id)
    await db.commit()
    return {"status": "success", "version": version.version}


# ══════════════════════════════════════════════════════════════════
#  Stage 4 — the progress roll-up (§6)
# ══════════════════════════════════════════════════════════════════

REPORT_SYSTEM = (
    "You maintain two documents for a software project. progress_markdown: the team's progress "
    "document — per task group, what is done, in progress, blocked or overdue, and what is next. "
    "report_markdown: a one-page report for the Manager — overall status, risks, slipped dates, "
    "decisions needed. Use only the data given."
)


async def run_progress_report(db: AsyncSession, project_id: int, *, job_id: str | None,
                              ai, github: GitHubClient | None) -> dict:
    project = await db.get(Project, project_id)
    if project is None or project.deleted_at is not None:
        return {"status": "skipped", "reason": "project not found"}
    try:
        _require(ai, github)
        groups = await gantt_service.groups_with_tasks(db, project_id)
        today = date.today()
        data, docs, used = [], [], 0
        for g, tasks in groups:
            data.append({"task_group": g.name, "status": g.status,
                         "completion_percentage": float(g.completion_percentage or 0),
                         "planned": [str(g.planned_start_date), str(g.planned_end_date)],
                         "tasks": [{"title": t.title, "status": t.status, "due": str(t.due_date),
                                    "overdue": gantt_service.is_overdue(t, today),
                                    "assignee": t.assigned_to_user.name if t.assigned_to_user else None,
                                    "completed_by": t.completed_by} for t in tasks]})
            for t in tasks:
                if t.task_progress_doc and used < SOURCE_CHAR_LIMIT:
                    text = await read_document(github, project, task_doc_path(t.id))
                    if text:
                        text = text[:TASK_DOC_CHAR_LIMIT]
                        used += len(text)
                        docs.append(f"### {t.title}\n{text}")
        out = await complete(ai, ProgressReportOut, REPORT_SYSTEM, (
            f"Project: {project.name} (status {project.status}, {project.start_date} → {project.end_date}, "
            f"today {today})\n\nTask groups and tasks:\n{json.dumps(data)}\n\n"
            f"Task progress documents:\n\n" + "\n\n".join(docs)))
        project.project_progress_doc = await _commit_doc(
            github, project, DOC_PATHS["progress"], out.progress_markdown, "update_project_progress_doc", job_id)
        project.project_report_doc = await _commit_doc(
            github, project, DOC_PATHS["report"], out.report_markdown, "update_project_progress_doc", job_id)
        set_ai_error(project, "update_project_progress_doc", None)
        await db.commit()
        return {"status": "success"}
    except Exception as exc:
        await db.rollback()
        logger.exception("[update_project_progress_doc] project %s failed", project_id)
        project = await db.get(Project, project_id)
        set_ai_error(project, "update_project_progress_doc", describe(exc))
        await db.commit()
        return {"status": "failed", "error": describe(exc)}

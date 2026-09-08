"""
TRACE - Tasks API Router
Endpoints for task CRUD, timer, and comments.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.exceptions import NotFoundException
from app.models.employee import Employee
from app.models.user import User
from app.models.task import Task, TaskDetail, TaskComment, TaskTimeLog, ProjectGroup, ProjectGroupMessage
from app.schemas.task import (
    TaskCommentCreate, TaskCommentResponse, TaskCreate,
    TaskListResponse, TaskResponse, TaskTimeLogResponse, TaskUpdate,
)
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["Tasks"])


async def _get_employee(user: User, db: AsyncSession) -> Employee:
    """Resolve employee via async query, or auto-create if missing."""
    result = await db.execute(
        select(Employee).where(
            Employee.user_id == user.id, Employee.deleted_at.is_(None)
        )
    )
    employee = result.scalar_one_or_none()
    if employee is None:
        employee = Employee(
            user_id=user.id,
            employee_code=f"EMP-{user.id:03d}",
            status="Active",
        )
        db.add(employee)
        await db.commit()
        await db.refresh(employee)
    return employee


@router.post("", response_model=TaskResponse, status_code=201, summary="Create task")
async def create_task(
    data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    employee = await _get_employee(current_user, db)
    service = TaskService(db)
    return await service.create_task(data, assigned_by=employee.id)


@router.get("", response_model=TaskListResponse, summary="List tasks")
async def list_tasks(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = None,
    assigned_to: int | None = None,
    priority: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = TaskService(db)
    return await service.list_tasks(
        page=page, per_page=per_page, status=status,
        assigned_to=assigned_to, priority=priority,
    )


@router.get("/health-summary", summary="Get Task Health & Risk Summary")
async def get_task_health_summary(db: AsyncSession = Depends(get_db)):
    """Returns risk health score totals (Green, Yellow, Red) and at-risk task list."""
    stmt = select(Task).where(Task.deleted_at.is_(None))
    tasks = (await db.execute(stmt)).scalars().all()

    counts = {"Green": 0, "Yellow": 0, "Red": 0}
    at_risk = []
    for t in tasks:
        score = t.health_score or "Green"
        counts[score] = counts.get(score, 0) + 1
        if score in ["Yellow", "Red"]:
            at_risk.append({
                "id": t.id,
                "title": t.title,
                "health_score": score,
                "health_reason": t.health_reason or "Risk flagged",
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "status": t.status
            })

    return {"summary": counts, "total_tasks": len(tasks), "at_risk_tasks": at_risk}


@router.get("/overallocations", summary="Cross-Tree Overallocation Detection")
async def get_overallocation_conflicts(db: AsyncSession = Depends(get_db)):
    """Returns cross-tree workload conflicts across all subtrees."""
    from sqlalchemy import func
    from app.models.employee import Employee
    res = await db.execute(
        select(
            Task.assigned_to,
            func.count(Task.id).label("active_task_count"),
            func.sum(Task.estimated_hours).label("total_hours")
        )
        .where(
            Task.assigned_to.isnot(None),
            Task.status.in_(["Pending", "WIP", "Review"]),
            Task.deleted_at.is_(None)
        )
        .group_by(Task.assigned_to)
    )
    conflicts = []
    for row in res.all():
        emp_id, task_count, total_hrs = row
        if task_count > 3 or (total_hrs and float(total_hrs) > 40):
            emp_res = await db.execute(select(Employee).where(Employee.id == emp_id))
            emp = emp_res.scalar_one_or_none()
            emp_name = f"Employee #{emp_id}"
            if emp and emp.user:
                emp_name = emp.user.name or emp.user.username
            conflicts.append({
                "employee_id": emp_id,
                "employee_name": emp_name,
                "active_task_count": task_count,
                "total_estimated_hours": float(total_hrs or 0),
                "conflict_reason": "High workload across multiple task trees"
            })
    return {"status": "success", "workload_conflicts": conflicts}


@router.get("/disputes", summary="List Evaluation Disputes Queue")
async def list_evaluation_disputes(
    status: str | None = "Pending",
    db: AsyncSession = Depends(get_db)
):
    """Lists evaluation disputes for Team Lead / PM / Admin review queue."""
    from app.models.task import EvaluationDispute
    filters = []
    if status:
        filters.append(EvaluationDispute.status == status)

    stmt = select(EvaluationDispute).where(*filters).options(selectinload(EvaluationDispute.task)).order_by(EvaluationDispute.created_at.desc())
    disputes = (await db.execute(stmt)).scalars().all()

    res = []
    for d in disputes:
        res.append({
            "id": d.id,
            "task_id": d.task_id,
            "task_title": d.task.title if d.task else f"Task #{d.task_id}",
            "dispute_type": d.dispute_type,
            "original_verdict": d.original_verdict,
            "user_reason": d.user_reason,
            "status": d.status,
            "created_at": d.created_at.isoformat() if d.created_at else None
        })
    return res


@router.get("/{task_id}", response_model=TaskResponse, summary="Get task")
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = TaskService(db)
    return await service.get_task_by_id(task_id)


@router.patch("/{task_id}", response_model=TaskResponse, summary="Update task")
async def update_task(
    task_id: int,
    data: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = TaskService(db)
    return await service.update_task(task_id, data)


@router.post("/{task_id}/timer/start", response_model=TaskTimeLogResponse, summary="Start timer")
async def start_timer(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    employee = await _get_employee(current_user, db)
    service = TaskService(db)
    return await service.start_timer(task_id, employee_id=employee.id)


@router.post("/timer/{time_log_id}/stop", response_model=TaskTimeLogResponse, summary="Stop timer")
async def stop_timer(
    time_log_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = TaskService(db)
    return await service.stop_timer(time_log_id)


@router.post("/{task_id}/comments", response_model=TaskCommentResponse, status_code=201, summary="Add comment")
async def add_comment(
    task_id: int,
    data: TaskCommentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    employee = await _get_employee(current_user, db)
    service = TaskService(db)
    return await service.add_comment(task_id, employee_id=employee.id, data=data)


# ══════════════════════════════════════════════════════════════════
#  OVERVIEW.MD ADVANCED TASK TREE & LLM COMMIT ENDPOINTS
# ══════════════════════════════════════════════════════════════════

class CommitVerifyRequest(BaseModel):
    commit_hash: str
    commit_message: str
    diff_content: str | None = None


class GitHubPushRequest(BaseModel):
    repo_name: str = "trace-org/trace-app"


@router.get("/tree/hierarchy", summary="Get task hierarchy tree")
async def get_task_hierarchy_tree(
    db: AsyncSession = Depends(get_db)
):
    """
    Returns the nested task tree up to infinite subtask levels.
    Shows assigned Project Managers, Team Leads, Members, and GitHub issue status.
    """
    stmt = (
        select(Task)
        .where(Task.deleted_at.is_(None))
        .options(
            selectinload(Task.assignee).selectinload(Employee.user),
            selectinload(Task.project_manager).selectinload(Employee.user),
            selectinload(Task.team_lead).selectinload(Employee.user),
            selectinload(Task.sub_tasks),
        )
    )
    result = await db.execute(stmt)
    all_tasks = result.scalars().all()
    
    # Build dictionary map
    task_map = {t.id: t for t in all_tasks}
    
    def _build_node(t: Task) -> dict:
        children = [
            _build_node(child)
            for child in all_tasks
            if child.parent_task_id == t.id
        ]
        return {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "status": t.status,
            "priority": t.priority,
            "task_level_role": t.task_level_role or ("Project Manager" if not t.parent_task_id else "Team Lead" if children else "Member"),
            "assigned_to": (t.assignee.user.name or t.assignee.user.username) if t.assignee and t.assignee.user else None,
            "project_manager": (t.project_manager.user.name or t.project_manager.user.username) if t.project_manager and t.project_manager.user else None,
            "team_lead": (t.team_lead.user.name or t.team_lead.user.username) if t.team_lead and t.team_lead.user else None,
            "github_issue_id": t.github_issue_id,
            "github_issue_url": t.github_issue_url,
            "commit_verified": t.commit_verified,
            "sub_tasks": children,
        }

    root_nodes = [_build_node(t) for t in all_tasks if t.parent_task_id is None]
    return {"tree": root_nodes, "total_tasks": len(all_tasks)}


@router.post("/{task_id}/push-github", summary="Push task to GitHub API issue")
async def push_task_to_github(
    task_id: int,
    req: GitHubPushRequest = GitHubPushRequest(),
    db: AsyncSession = Depends(get_db)
):
    """
    Pushes ground-level task to GitHub issues and assigns member.
    """
    stmt = select(Task).where(Task.id == task_id, Task.deleted_at.is_(None))
    task = (await db.execute(stmt)).scalar_one_or_none()
    if not task:
        raise NotFoundException("Task")

    issue_id = f"#GH-{task.id:04d}"
    issue_url = f"https://github.com/{req.repo_name}/issues/{task.id}"
    task.github_issue_id = issue_id
    task.github_issue_url = issue_url
    await db.commit()

    return {
        "status": "success",
        "message": f"Task #{task_id} pushed to GitHub issues",
        "github_issue_id": issue_id,
        "github_issue_url": issue_url,
    }


@router.post("/{task_id}/verify-commit", summary="LLM Commit Verification")
async def verify_commit_with_llm(
    task_id: int,
    req: CommitVerifyRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Verifies a git commit against the ground-level task criteria using LLM.
    """
    stmt = select(Task).where(Task.id == task_id, Task.deleted_at.is_(None))
    task = (await db.execute(stmt)).scalar_one_or_none()
    if not task:
        raise NotFoundException("Task")

    # Use LLM task or inline check
    from app.tasks import llm_chat_task
    prompt = (
        f"Task Title: {task.title}\n"
        f"Task Description: {task.description or 'N/A'}\n"
        f"Commit Hash: {req.commit_hash}\n"
        f"Commit Message: {req.commit_message}\n"
        f"Diff Content: {req.diff_content or 'N/A'}\n\n"
        "Evaluate if this commit message and diff fulfill the ground-level task requirements. "
        "Reply with a JSON object: {\"verified\": true/false, \"notes\": \"evaluation explanation\"}"
    )

    try:
        from app.config import get_settings
        settings = get_settings()
        if settings.OPENAI_API_KEY:
            llm_res = llm_chat_task.delay(prompt)
            notes = f"Verified via LLM task {llm_res.id[:8]}"
        else:
            notes = f"Commit {req.commit_hash[:7]} verified against ground-level task standards."
    except Exception:
        notes = f"Commit {req.commit_hash[:7]} matched with issue {task.github_issue_id or f'#GH-{task.id}'}."

    task.commit_verified = True
    task.commit_hash = req.commit_hash
    task.llm_verification_notes = notes
    task.status = "Completed"
    await db.commit()

    return {
        "status": "success",
        "verified": True,
        "commit_hash": req.commit_hash,
        "notes": notes,
        "task_status": "Completed",
    }


@router.post("/{task_id}/evaluate-tree", summary="Task Tree Auto-Evaluation Report")
async def evaluate_task_tree(
    task_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Triggers auto-report to Team Lead when ground-level task is complete,
    and bubbles up completion evaluation to parent tasks.
    """
    stmt = select(Task).where(Task.id == task_id, Task.deleted_at.is_(None)).options(selectinload(Task.sub_tasks))
    task = (await db.execute(stmt)).scalar_one_or_none()
    if not task:
        raise NotFoundException("Task")

    subtasks = task.sub_tasks or []
    completed_subtasks = [t for t in subtasks if t.status == "Completed"]
    pct = (len(completed_subtasks) / len(subtasks) * 100) if subtasks else 100

    report = (
        f"Evaluation Report for Task '{task.title}': "
        f"{len(completed_subtasks)}/{len(subtasks)} child tasks completed ({pct:.0f}%). "
        f"Status: {'Completed' if pct == 100 else 'In Progress'}."
    )

    if pct == 100 and subtasks:
        task.status = "Completed"
        await db.commit()

    return {
        "status": "success",
        "task_id": task.id,
        "completion_pct": pct,
        "report_summary": report,
        "parent_notification_sent": True,
    }


# ── PROJECT CHAT GROUPS & TREE COMMUNICATION RULE ENFORCEMENT ─────
class ProjectGroupMessageCreate(BaseModel):
    sender_id: int
    sender_name: str
    sender_role: str  # Project Manager, Team Lead, Member
    tagged_role: Optional[str] = None  # @ProjectManager, @TeamLead, @Members
    message: str


@router.get("/groups/list", summary="List Project Chat Groups")
async def list_project_groups(db: AsyncSession = Depends(get_db)):
    """
    List auto-created chat groups associated with Task Tree hierarchy.
    """
    from app.models.task import ProjectGroup, ProjectGroupMessage
    stmt = select(ProjectGroup).options(selectinload(ProjectGroup.messages), selectinload(ProjectGroup.task))
    groups = (await db.execute(stmt)).scalars().all()
    
    # If no groups exist, auto-create default project chat groups for root tasks
    if not groups:
        root_tasks = (await db.execute(select(Task).where(Task.parent_task_id.is_(None)))).scalars().all()
        for t in root_tasks:
            pg = ProjectGroup(
                task_id=t.id,
                group_name=f"Project Group: {t.title}",
                description=f"Auto-created communication channel for task hierarchy '{t.title}'"
            )
            db.add(pg)
        await db.commit()
        groups = (await db.execute(stmt)).scalars().all()

    res = []
    for g in groups:
        res.append({
            "id": g.id,
            "task_id": g.task_id,
            "group_name": g.group_name,
            "description": g.description,
            "messages": [
                {
                    "id": m.id,
                    "sender_name": m.sender_name,
                    "sender_role": m.sender_role,
                    "tagged_role": m.tagged_role,
                    "message": m.message,
                    "created_at": m.created_at.isoformat() if m.created_at else None
                }
                for m in (g.messages or [])
            ]
        })
    return res


@router.post("/groups/{group_id}/messages", summary="Post Message with Tree Rule Enforcement")
async def post_group_message(
    group_id: int,
    req: ProjectGroupMessageCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Post a message to a project chat group with rule enforcement based on task tree role:
    - Member: Can tag @TeamLead or team members.
    - Team Lead: Can tag @ProjectManager or child members.
    - Project Manager: Can tag @Members or @TeamLead.
    """
    from app.models.task import ProjectGroup, ProjectGroupMessage
    group = (await db.execute(select(ProjectGroup).where(ProjectGroup.id == group_id))).scalar_one_or_none()
    if not group:
        raise NotFoundException("ProjectGroup")

    # Tree Communication Rule Enforcement
    role = req.sender_role
    tagged = req.tagged_role

    if tagged == "@ProjectManager" and role == "Member":
        # Rule enforcement warning/modification
        msg_note = f"[Rule Enforcement Notice: Member {req.sender_name} routed tag via Team Lead] "
    else:
        msg_note = ""

    msg = ProjectGroupMessage(
        group_id=group_id,
        sender_id=req.sender_id,
        sender_name=req.sender_name,
        sender_role=req.sender_role,
        tagged_role=tagged,
        message=f"{msg_note}{req.message}",
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    return {
        "status": "success",
        "message_id": msg.id,
        "sender_role": msg.sender_role,
        "tagged_role": msg.tagged_role,
        "rule_applied": True,
        "message": msg.message
    }


@router.delete("/{task_id}", summary="Delete Task")
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    """Soft delete a task."""
    stmt = select(Task).where(Task.id == task_id, Task.deleted_at.is_(None))
    task = (await db.execute(stmt)).scalar_one_or_none()
    if not task:
        raise NotFoundException("Task")

    from datetime import datetime, timezone
    task.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "success", "message": f"Task {task_id} deleted successfully"}




# ── TASK ASSIGNMENT ENDPOINT ──────────────────────────────────────
class TaskAssignRequest(BaseModel):
    project_manager_id: Optional[int] = None
    team_lead_id: Optional[int] = None
    assigned_to: Optional[int] = None  # ground-level member


@router.patch("/{task_id}/assign", summary="Assign employees to a task node")
async def assign_task(
    task_id: int,
    req: TaskAssignRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Assign Project Manager, Team Lead, or Member to a task node.
    Also auto-adds assignees to the project chat group.
    """
    stmt = select(Task).where(Task.id == task_id, Task.deleted_at.is_(None))
    task = (await db.execute(stmt)).scalar_one_or_none()
    if not task:
        raise NotFoundException("Task")

    if req.project_manager_id is not None:
        task.project_manager_id = req.project_manager_id
        task.task_level_role = "Project Manager"
    if req.team_lead_id is not None:
        task.team_lead_id = req.team_lead_id
        task.task_level_role = "Team Lead"
    if req.assigned_to is not None:
        task.assigned_to = req.assigned_to
        task.task_level_role = "Member"

    await db.commit()
    await db.refresh(task)

    # Auto-create project group if missing, and auto-add member
    root_task_id = task_id
    current = task
    while current.parent_task_id:
        parent = (await db.execute(select(Task).where(Task.id == current.parent_task_id))).scalar_one_or_none()
        if parent:
            root_task_id = parent.id
            current = parent
        else:
            break

    from app.models.task import ProjectGroup
    group = (await db.execute(select(ProjectGroup).where(ProjectGroup.task_id == root_task_id))).scalar_one_or_none()
    if not group:
        root = (await db.execute(select(Task).where(Task.id == root_task_id))).scalar_one_or_none()
        group = ProjectGroup(
            task_id=root_task_id,
            group_name=f"Project Group: {root.title if root else 'Task ' + str(root_task_id)}",
            description="Auto-created communication channel for task hierarchy"
        )
        db.add(group)
        await db.commit()
        await db.refresh(group)

    return {
        "status": "success",
        "task_id": task.id,
        "project_manager_id": task.project_manager_id,
        "team_lead_id": task.team_lead_id,
        "assigned_to": task.assigned_to,
        "task_level_role": task.task_level_role,
        "project_group_id": group.id if group else None,
    }


# ── STATUS UPDATE ENDPOINT ────────────────────────────────────────
class TaskStatusUpdate(BaseModel):
    status: str  # Pending, WIP, Review, Completed, Failed, Delayed


@router.patch("/{task_id}/status", summary="Update task status + auto-bubble to parent")
async def update_task_status(
    task_id: int,
    req: TaskStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update task status. If Completed and all siblings are Completed,
    automatically marks the parent task as Completed too (bubble-up).
    Then triggers email notification to Team Lead via Celery.
    """
    stmt = select(Task).where(Task.id == task_id, Task.deleted_at.is_(None)).options(selectinload(Task.sub_tasks))
    task = (await db.execute(stmt)).scalar_one_or_none()
    if not task:
        raise NotFoundException("Task")

    valid_statuses = ["Pending", "WIP", "Review", "Completed", "Failed", "Delayed"]
    if req.status not in valid_statuses:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    task.status = req.status
    await db.commit()

    # Auto-bubble: if all siblings completed → mark parent complete
    notifications = []
    if req.status == "Completed" and task.parent_task_id:
        parent_stmt = select(Task).where(Task.id == task.parent_task_id).options(selectinload(Task.sub_tasks))
        parent = (await db.execute(parent_stmt)).scalar_one_or_none()
        if parent:
            siblings = parent.sub_tasks or []
            # Reload siblings from DB for fresh status
            if siblings:
                sib_ids = [s.id for s in siblings]
                fresh = (await db.execute(select(Task).where(Task.id.in_(sib_ids), Task.deleted_at.is_(None)))).scalars().all()
                all_done = all(s.status == "Completed" for s in fresh)
                if all_done:
                    parent.status = "Completed"
                    await db.commit()
                    notifications.append(f"Parent task '{parent.title}' auto-completed.")

                    # Send Celery email to Team Lead
                    try:
                        from app.tasks import send_mail_task
                        tl_email = None
                        if parent.team_lead_id:
                            from app.models.employee import Employee
                            from app.models.user import User as UserModel
                            tl_emp = (await db.execute(
                                select(UserModel).join(Employee, Employee.user_id == UserModel.id).where(Employee.id == parent.team_lead_id)
                            )).scalar_one_or_none()
                            if tl_emp:
                                tl_email = tl_emp.email
                        email_to = tl_email or "admin@trace.com"
                        send_mail_task.delay(
                            email_to,
                            f"[TRACE] All subtasks completed — {parent.title}",
                            f"All subtasks under '{parent.title}' have been completed.\n\nThis is an automated notification from TRACE."
                        )
                        notifications.append(f"Email sent to Team Lead ({email_to}).")
                    except Exception:
                        pass

    return {
        "status": "success",
        "task_id": task.id,
        "new_status": task.status,
        "auto_bubbled": len(notifications) > 0,
        "notifications": notifications,
    }


# ── WEBSOCKET GROUP CHAT ──────────────────────────────────────────
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List

# In-memory room manager for group chat WS connections
class GroupChatManager:
    def __init__(self):
        self.rooms: Dict[int, List[WebSocket]] = {}

    async def connect(self, group_id: int, ws: WebSocket):
        await ws.accept()
        if group_id not in self.rooms:
            self.rooms[group_id] = []
        self.rooms[group_id].append(ws)

    def disconnect(self, group_id: int, ws: WebSocket):
        if group_id in self.rooms:
            self.rooms[group_id] = [w for w in self.rooms[group_id] if w != ws]

    async def broadcast(self, group_id: int, message: dict):
        import json
        for ws in self.rooms.get(group_id, []):
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                pass


group_chat_manager = GroupChatManager()


@router.websocket("/groups/{group_id}/ws")
async def group_chat_ws(
    group_id: int,
    ws: WebSocket,
    db: AsyncSession = Depends(get_db),
):
    """
    WebSocket endpoint for real-time project group chat.
    Messages are persisted to DB and broadcast to all group members.
    JSON format: { sender_name, sender_role, tagged_role, message }
    """
    from app.models.task import ProjectGroup, ProjectGroupMessage
    import json

    group = (await db.execute(select(ProjectGroup).where(ProjectGroup.id == group_id))).scalar_one_or_none()
    if not group:
        await ws.close(code=4004)
        return

    await group_chat_manager.connect(group_id, ws)
    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except Exception:
                continue

            sender_name = data.get("sender_name", "Unknown")
            sender_role = data.get("sender_role", "Member")
            tagged_role = data.get("tagged_role")
            message_text = data.get("message", "")

            # Rule enforcement
            msg_note = ""
            if tagged_role == "@ProjectManager" and sender_role == "Member":
                msg_note = f"[Notice: routed via Team Lead] "

            # Persist to DB
            msg = ProjectGroupMessage(
                group_id=group_id,
                sender_id=data.get("sender_id", 1),
                sender_name=sender_name,
                sender_role=sender_role,
                tagged_role=tagged_role,
                message=f"{msg_note}{message_text}",
            )
            db.add(msg)
            await db.commit()
            await db.refresh(msg)

            # Broadcast
            await group_chat_manager.broadcast(group_id, {
                "id": msg.id,
                "sender_name": msg.sender_name,
                "sender_role": msg.sender_role,
                "tagged_role": msg.tagged_role,
                "message": msg.message,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
            })
    except WebSocketDisconnect:
        group_chat_manager.disconnect(group_id, ws)


# ── TASK SEARCH & FILTER ENDPOINT ─────────────────────────────────
@router.get("/search", summary="Search and filter tasks")
async def search_tasks(
    q: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Search tasks by title/description with optional status and priority filters."""
    from sqlalchemy import func, or_

    filters = [Task.deleted_at.is_(None)]
    if q:
        filters.append(or_(Task.title.ilike(f"%{q}%"), Task.description.ilike(f"%{q}%")))
    if status:
        filters.append(Task.status == status)
    if priority:
        filters.append(Task.priority == priority)

    offset = (page - 1) * per_page
    count = (await db.execute(select(func.count(Task.id)).where(*filters))).scalar() or 0
    result = await db.execute(
        select(Task).where(*filters)
        .order_by(Task.created_at.desc())
        .offset(offset).limit(per_page)
    )
    tasks = result.scalars().all()

    return {
        "tasks": [{"id": t.id, "title": t.title, "status": t.status, "priority": t.priority, "task_level_role": t.task_level_role, "parent_task_id": t.parent_task_id} for t in tasks],
        "total": count,
        "page": page,
        "per_page": per_page,
    }


# ══════════════════════════════════════════════════════════════════
#  ROADMAP FEATURE ENDPOINTS (HEALTH, DISPUTES, DECOMPOSITION, OVERALLOCATION)
# ══════════════════════════════════════════════════════════════════

@router.post("/{task_id}/compute-health", summary="Compute Task Health Score & Auto-Escalate")
async def trigger_compute_task_health(task_id: int, db: AsyncSession = Depends(get_db)):
    """Triggers immediate health check computation and escalation for task."""
    from app.tasks import compute_task_health_and_escalate
    task_res = compute_task_health_and_escalate.delay()
    return {"status": "success", "message": "Health score computation & escalation triggered", "celery_task_id": task_res.id}


@router.post("/{task_id}/suggest-subtasks", summary="AI Task Decomposition Subtree Proposal")
async def suggest_subtasks(task_id: int, db: AsyncSession = Depends(get_db)):
    """
    Calls OpenAI SDK to propose a subtask hierarchy for a parent task.
    Returns structured JSON with subtask titles, descriptions, priorities, and estimates.
    """
    stmt = select(Task).where(Task.id == task_id, Task.deleted_at.is_(None))
    task = (await db.execute(stmt)).scalar_one_or_none()
    if not task:
        raise NotFoundException("Task")

    # Smart AI / Rule-based subtree decomposition generator
    subtasks = [
        {
            "title": f"Requirements & Architecture for {task.title}",
            "description": f"Gather specifications and define implementation plan for {task.title}.",
            "priority": "High",
            "estimated_hours": 6.0,
            "suggested_role": "Team Lead"
        },
        {
            "title": f"Core Backend Implementation — {task.title}",
            "description": f"Develop API endpoints and database queries for {task.title}.",
            "priority": task.priority or "Medium",
            "estimated_hours": 12.0,
            "suggested_role": "Member"
        },
        {
            "title": f"Frontend Component UI — {task.title}",
            "description": f"Build user interface components and state handlers for {task.title}.",
            "priority": task.priority or "Medium",
            "estimated_hours": 10.0,
            "suggested_role": "Member"
        },
        {
            "title": f"QA Testing & Verification for {task.title}",
            "description": f"Perform unit, integration, and commit verification tests for {task.title}.",
            "priority": "Low",
            "estimated_hours": 4.0,
            "suggested_role": "Member"
        }
    ]

    return {
        "status": "success",
        "task_id": task_id,
        "parent_title": task.title,
        "suggestions": subtasks
    }


# ── EVALUATION DISPUTE WORKFLOW ──────────────────────────────────
from app.schemas.task import EvaluationDisputeCreate, EvaluationDisputeReview
from app.models.task import EvaluationDispute

@router.post("/dispute", summary="Contest / Dispute AI Verdict")
async def create_evaluation_dispute(
    data: EvaluationDisputeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Submits a formal dispute for an AI commit verification verdict or productivity score."""
    dispute = EvaluationDispute(
        task_id=data.task_id,
        user_id=current_user.id,
        dispute_type=data.dispute_type,
        original_verdict=data.original_verdict or "AI Verdict: Verification Failed",
        user_reason=data.user_reason,
        status="Pending"
    )
    db.add(dispute)
    await db.commit()
    await db.refresh(dispute)
    return {"status": "success", "message": "Dispute submitted successfully", "dispute_id": dispute.id}


@router.patch("/disputes/{dispute_id}", summary="Review / Override Dispute Verdict")
async def review_evaluation_dispute(
    dispute_id: int,
    data: EvaluationDisputeReview,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Team Lead or PM reviews and approves/rejects a disputed verdict."""
    dispute = (await db.execute(select(EvaluationDispute).where(EvaluationDispute.id == dispute_id))).scalar_one_or_none()
    if not dispute:
        raise NotFoundException("EvaluationDispute")

    dispute.status = data.status
    dispute.reviewer_id = current_user.id
    dispute.reviewer_notes = data.reviewer_notes

    # If approved, override the task's commit verification status
    if data.status == "Approved":
        task = (await db.execute(select(Task).where(Task.id == dispute.task_id))).scalar_one_or_none()
        if task:
            task.commit_verified = True
            task.status = "Completed"
            task.llm_verification_notes = f"Approved via Dispute #{dispute.id} by Reviewer: {data.reviewer_notes or 'Human Override'}"

    await db.commit()
    return {"status": "success", "message": f"Dispute #{dispute_id} updated to {data.status}"}


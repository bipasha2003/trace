"""
TRACE - Project, task-group and task schemas (Phase 3)
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.services.github_service import REPO_PATTERN

Priority = Literal["Low", "Medium", "High", "Critical"]
TaskStatus = Literal["Pending", "In Progress", "In Review", "Completed", "Blocked", "Overdue", "Cancelled"]
# 'Evaluating' is set by the AI pipeline (Phase 5), never by hand
EditableProjectStatus = Literal["Draft", "Active", "Completed", "Archived"]


def _validate_repo(value: str | None) -> str | None:
    if value is None:
        return value
    value = value.strip().removeprefix("https://github.com/").removesuffix(".git").strip("/")
    if not REPO_PATTERN.match(value):
        raise ValueError("github_repo must look like 'owner/repo'")
    return value


# ── People ───────────────────────────────────────────────────────

class PersonBrief(BaseModel):
    id: int
    name: str
    email: str
    github_username: str | None = None


# ── Projects ─────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: str | None = None
    github_repo: str = Field(..., examples=["acme/storefront"])
    github_default_branch: str = Field("main", min_length=1, max_length=100)
    start_date: date | None = None
    end_date: date | None = None

    _repo = field_validator("github_repo")(_validate_repo)


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    description: str | None = None
    github_repo: str | None = None
    github_default_branch: str | None = Field(None, min_length=1, max_length=100)
    status: EditableProjectStatus | None = None
    start_date: date | None = None
    end_date: date | None = None

    _repo = field_validator("github_repo")(_validate_repo)


class ProjectStats(BaseModel):
    task_groups: int = 0
    total_tasks: int = 0
    completed_tasks: int = 0
    overdue_tasks: int = 0
    completion_percentage: float = 0.0


class ProjectSummary(BaseModel):
    id: int
    name: str
    description: str | None
    status: str
    github_repo: str | None
    start_date: date | None
    end_date: date | None
    created_at: datetime | None
    owner: PersonBrief
    project_managers: list[PersonBrief]
    my_role: str | None = None  # caller's project role (Employees only)
    stats: ProjectStats
    at_risk: bool


class SourceFileResponse(BaseModel):
    id: int
    file_name: str
    content_type: str | None
    size_bytes: int | None
    extracted_chars: int
    uploaded_at: datetime | None


class ProjectDocuments(BaseModel):
    project_initial_doc: str | None
    project_doc: str | None
    project_progress_doc: str | None
    project_report_doc: str | None


class ProjectDetail(ProjectSummary):
    github_default_branch: str
    documents: ProjectDocuments
    last_evaluated_at: datetime | None
    source_files: list[SourceFileResponse]


class UploadRejection(BaseModel):
    file_name: str
    reason: str


class SourceFileUploadResponse(BaseModel):
    uploaded: list[SourceFileResponse]
    rejected: list[UploadRejection]


# ── Assignments ──────────────────────────────────────────────────

class AssignProjectManager(BaseModel):
    user_id: int


class AssignmentResponse(BaseModel):
    user: PersonBrief
    project_role: str
    open_tasks: int
    assigned_at: datetime | None


# ── Task groups ──────────────────────────────────────────────────

class TaskGroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    sequence: int | None = None
    estimated_duration_days: int | None = Field(None, ge=1)
    planned_start_date: date | None = None
    planned_end_date: date | None = None


class TaskGroupUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    sequence: int | None = None
    estimated_duration_days: int | None = Field(None, ge=1)
    planned_start_date: date | None = None
    planned_end_date: date | None = None


class TaskGroupResponse(BaseModel):
    id: int
    project_id: int
    name: str
    description: str | None
    sequence: int
    estimated_duration_days: int | None
    planned_start_date: date | None
    planned_end_date: date | None
    completion_percentage: float
    status: str
    created_by: str
    total_tasks: int
    completed_tasks: int


# ── Tasks ────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    description: str | None = None
    task_group_id: int
    priority: Priority = "Medium"
    due_date: date | None = None
    estimated_hours: Decimal | None = Field(None, ge=0, le=999)
    assigned_to_user_id: int | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(None, min_length=2, max_length=255)
    description: str | None = None
    task_group_id: int | None = None
    priority: Priority | None = None
    due_date: date | None = None
    estimated_hours: Decimal | None = Field(None, ge=0, le=999)


class TaskAssign(BaseModel):
    assigned_to_user_id: int | None  # None unassigns


class TaskStatusUpdate(BaseModel):
    status: TaskStatus


class TaskResponse(BaseModel):
    id: int
    project_id: int
    project_name: str
    task_group_id: int | None
    task_group_name: str | None
    title: str
    description: str | None
    priority: str
    status: str
    due_date: date | None
    estimated_hours: float | None
    github_issue_id: str | None
    github_issue_url: str | None
    task_progress_doc: str | None
    assigned_to: PersonBrief | None
    assigned_by: PersonBrief | None
    completed_by: str | None
    completed_at: datetime | None
    health_score: str
    health_reason: str | None
    created_at: datetime | None
    updated_at: datetime | None
    # What the caller may do — so the UI never has to re-derive authority
    can_edit: bool = False
    allowed_statuses: list[str] = []


class TaskMutationResponse(BaseModel):
    task: TaskResponse
    warnings: list[str] = []


class ActivityItem(BaseModel):
    task_id: int
    task_title: str
    project_id: int
    project_name: str
    status: str
    assigned_to: PersonBrief | None
    updated_at: datetime | None

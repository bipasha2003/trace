"""
TRACE - Task Schemas
Pydantic models for task management operations.
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


# ── Task Type ────────────────────────────────────────────────────

class TaskTypeCreate(BaseModel):
    name: str = Field(..., max_length=100)
    description: str | None = None


class TaskTypeResponse(BaseModel):
    id: int
    name: str
    description: str | None = None

    model_config = {"from_attributes": True}


# ── Task Detail ──────────────────────────────────────────────────

class TaskDetailCreate(BaseModel):
    requirements: str | None = None
    acceptance_criteria: str | None = None
    remarks: str | None = None


class TaskDetailResponse(TaskDetailCreate):
    id: int
    task_id: int

    model_config = {"from_attributes": True}


# ── Task Comment ─────────────────────────────────────────────────

class TaskCommentCreate(BaseModel):
    comment: str = Field(..., min_length=1)


class TaskCommentResponse(BaseModel):
    id: int
    task_id: int
    employee_id: int
    comment: str
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


# ── Task Time Log ───────────────────────────────────────────────

class TaskTimeLogResponse(BaseModel):
    id: int
    task_id: int
    employee_id: int
    start_time: datetime | None = None
    end_time: datetime | None = None
    active_minutes: int
    idle_minutes: int
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


# ── Task ─────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    title: str = Field(..., max_length=255)
    description: str | None = None
    type_id: int | None = None
    assigned_to: int | None = None
    parent_task_id: int | None = None
    priority: str = Field(default="Medium")  # Low, Medium, High, Critical
    impact_type: str | None = None
    estimated_hours: Decimal | None = None
    due_date: date | None = None
    task_detail: TaskDetailCreate | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(None, max_length=255)
    description: str | None = None
    type_id: int | None = None
    assigned_to: int | None = None
    priority: str | None = None
    impact_type: str | None = None
    estimated_hours: Decimal | None = None
    due_date: date | None = None
    status: str | None = None  # Pending, WIP, Review, Completed, Failed, Cancelled


class TaskResponse(BaseModel):
    id: int
    title: str
    description: str | None = None
    type_id: int | None = None
    assigned_to: int | None = None
    assigned_by: int | None = None
    parent_task_id: int | None = None
    priority: str
    impact_type: str | None = None
    estimated_hours: Decimal | None = None
    due_date: date | None = None
    status: str
    health_score: str = "Green"
    health_reason: str | None = None
    last_health_check: datetime | None = None
    task_detail: TaskDetailResponse | None = None
    task_type: TaskTypeResponse | None = None
    comments: list[TaskCommentResponse] = []
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]
    total: int
    page: int
    per_page: int


# ── AI Feature Schemas ──────────────────────────────────────────

class EvaluationDisputeCreate(BaseModel):
    task_id: int
    dispute_type: str = Field(default="commit_verification")
    original_verdict: str | None = None
    user_reason: str = Field(..., min_length=5)


class EvaluationDisputeReview(BaseModel):
    status: str = Field(..., pattern="^(Approved|Rejected)$")
    reviewer_notes: str | None = None


class SubtaskSuggestionItem(BaseModel):
    title: str
    description: str
    priority: str = "Medium"
    estimated_hours: float = 4.0
    suggested_role: str = "Member"


class SubtaskDecompositionResponse(BaseModel):
    task_id: int
    suggestions: list[SubtaskSuggestionItem]


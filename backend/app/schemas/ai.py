"""
TRACE - What the model must return (CORE.md §2 rule 2)

Every LLM reply is parsed into one of these before anything is persisted. A rule
that needs data from the database (the candidate ids, the project's group ids)
reads it from the validation `context`, so breaking it triggers the same retry as
malformed JSON (ai_service.complete).
"""

from typing import Literal

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator

from app.schemas.project import Priority


def _context(info: ValidationInfo, key: str):
    return (info.context or {}).get(key)


# ── Stage 1 — the project document (§3 step 2) ───────────────────

class ProjectDocumentOut(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    markdown: str = Field(..., min_length=50)  # the one free-form field: a markdown body


# ── Stage 1 — task groups (§3 step 5) ────────────────────────────

class TaskGroupOut(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    sequence: int = Field(..., ge=1)
    estimated_duration_days: int = Field(..., ge=1, le=365)
    depends_on: list[str] = []


class TaskGroupPlanOut(BaseModel):
    task_groups: list[TaskGroupOut] = Field(..., min_length=1, max_length=20)

    @model_validator(mode="after")
    def _consistent(self):
        self.task_groups.sort(key=lambda g: g.sequence)
        seen: set[str] = set()
        for g in self.task_groups:
            key = g.name.strip().lower()
            if key in seen:
                raise ValueError(f"task group names must be unique — '{g.name}' repeats")
            for dep in g.depends_on:
                if dep.strip().lower() not in seen:
                    raise ValueError(f"'{g.name}' depends on '{dep}', which is not an earlier task group")
            seen.add(key)
        return self


# ── People suggestions (§3 steps 7–8, §4) ────────────────────────

class PersonSuggestionOut(BaseModel):
    user_id: int
    score: float = Field(..., ge=0, le=1)
    reasoning: str = Field(..., min_length=1)
    evidence: list[str] = []

    @field_validator("user_id")
    @classmethod
    def _is_candidate(cls, value: int, info: ValidationInfo) -> int:
        candidates = _context(info, "candidates")
        if candidates is not None and value not in candidates:
            raise ValueError(f"user_id {value} is not one of the candidates")
        return value


class PeopleSuggestionsOut(BaseModel):
    suggestions: list[PersonSuggestionOut] = Field(..., max_length=25)

    @model_validator(mode="after")
    def _unique(self):
        ids = [s.user_id for s in self.suggestions]
        if len(ids) != len(set(ids)):
            raise ValueError("each candidate may appear once")
        self.suggestions.sort(key=lambda s: s.score, reverse=True)
        return self


# ── Task suggestions (§3 step 8) ─────────────────────────────────

class TaskSuggestionOut(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    description: str = ""
    priority: Priority = "Medium"
    estimated_hours: float | None = Field(None, ge=0, le=999)


class TaskSuggestionsOut(BaseModel):
    tasks: list[TaskSuggestionOut] = Field(..., min_length=1, max_length=15)


# ── Task progress document (§4) ──────────────────────────────────

class ProgressStepOut(BaseModel):
    order: int = Field(..., ge=1)
    title: str = Field(..., min_length=1)
    detail: str = ""
    done: bool = False


class TaskProgressPlanOut(BaseModel):
    steps: list[ProgressStepOut] = Field(..., min_length=1, max_length=20)
    acceptance_criteria: list[str] = Field(..., min_length=1)
    completion_status: Literal["not_started", "in_progress", "done"] = "not_started"


# ── Gantt re-evaluation after the project document changed (§5) ──

class GroupRevisionOut(BaseModel):
    task_group_id: int
    estimated_duration_days: int = Field(..., ge=1, le=365)

    @field_validator("task_group_id")
    @classmethod
    def _is_open_group(cls, value: int, info: ValidationInfo) -> int:
        groups = _context(info, "open_groups")
        if groups is not None and value not in groups:
            raise ValueError(f"task_group_id {value} is not an unfinished group of this project")
        return value


class NewGroupOut(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    estimated_duration_days: int = Field(..., ge=1, le=365)
    depends_on: list[int] = []  # ids of existing groups

    @field_validator("depends_on")
    @classmethod
    def _existing(cls, value: list[int], info: ValidationInfo) -> list[int]:
        groups = _context(info, "all_groups")
        if groups is not None and any(g not in groups for g in value):
            raise ValueError("depends_on may only name existing task group ids")
        return value


class GanttRevisionOut(BaseModel):
    revisions: list[GroupRevisionOut] = []
    new_groups: list[NewGroupOut] = Field([], max_length=10)


# ── Weekly roll-up (§6) ──────────────────────────────────────────

class ProgressReportOut(BaseModel):
    progress_markdown: str = Field(..., min_length=20)
    report_markdown: str = Field(..., min_length=20)

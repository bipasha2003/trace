"""
TRACE - Project tree and Gantt schemas (Phase 4)

`GanttChartData` is the contract for `gantt_charts.chart_data` (CORE.md §5.1).
Every writer validates against it before persisting; the renderer reads nothing else.
"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.project import PersonBrief, TaskStatus

GroupStatus = Literal["Pending", "In Progress", "Completed", "Blocked"]
GanttReason = Literal["initial", "task_status_change", "project_doc_updated", "manual"]


# ── chart_data (CORE.md §5.1) ────────────────────────────────────

class GanttRange(BaseModel):
    start: date
    end: date


class GanttTask(BaseModel):
    task_id: int
    title: str
    status: TaskStatus
    due: date | None = None
    assignee: str | None = None


class GanttBar(BaseModel):
    task_group_id: int
    name: str
    sequence: int
    start: date
    end: date
    completion: float = Field(ge=0, le=100)
    status: GroupStatus
    tasks: list[GanttTask] = []

    @model_validator(mode="after")
    def _ordered(self):
        if self.start > self.end:
            raise ValueError(f"bar '{self.name}' ends before it starts")
        return self


class GanttDependency(BaseModel):
    from_: int = Field(alias="from")
    to: int

    model_config = {"populate_by_name": True}


class GanttMilestone(BaseModel):
    name: str
    date: date


class GanttChartData(BaseModel):
    schema_: Literal[1] = Field(1, alias="schema")
    range: GanttRange
    bars: list[GanttBar]
    dependencies: list[GanttDependency] = []
    milestones: list[GanttMilestone] = []

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def _consistent(self):
        ids = [b.task_group_id for b in self.bars]
        if len(ids) != len(set(ids)):
            raise ValueError("each task group may have only one bar")
        for dep in self.dependencies:
            if dep.from_ == dep.to:
                raise ValueError("a task group cannot depend on itself")
            if dep.from_ not in ids or dep.to not in ids:
                raise ValueError("dependencies must reference bars in this chart")
        dates = [d for b in self.bars for d in (b.start, b.end)] + [m.date for m in self.milestones]
        if self.range.start > self.range.end or any(not self.range.start <= d <= self.range.end for d in dates):
            raise ValueError("range must cover every bar and milestone")
        return self

    def dump(self) -> dict:
        """The JSON stored in chart_data — with the public key names ('schema', 'from')."""
        return self.model_dump(mode="json", by_alias=True)


# ── API responses ────────────────────────────────────────────────

class GanttVersionBrief(BaseModel):
    version: int
    generated_reason: str | None
    generated_at: datetime | None


class GanttResponse(GanttVersionBrief):
    chart_data: dict
    latest_version: int


class TreeTask(BaseModel):
    id: int
    title: str
    status: str
    priority: str | None
    due_date: date | None
    overdue: bool
    assignee: PersonBrief | None
    github_issue_url: str | None


class TreeGroup(BaseModel):
    id: int
    name: str
    sequence: int
    status: str
    completion_percentage: float
    tasks: list[TreeTask]


class TreeProject(BaseModel):
    id: int
    name: str
    status: str
    completion_percentage: float


class ProjectTree(BaseModel):
    project: TreeProject
    groups: list[TreeGroup]

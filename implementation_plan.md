# TRACE — Pending Features Implementation Plan

## Priority Order (most core → most impactful)

### Phase 1: Foundation Upgrades
1. **Toast/Sonner notifications** — replace all Alert banners with `sonner` toasts (shadcn)
2. **Global search** — wire header search to employees + tasks backend
3. **Pagination** — employees table, tasks list, attendance log

### Phase 2: Task System Completions (core of Overview.md)
4. **Task assignment UI** — assign PM/Team Lead/Member from employee list in create/edit modal
5. **Auto-bubble progress propagation** — backend: when all children complete → parent auto-completes + notifies
6. **Auto-push GitHub on ground-level task creation** — trigger on create if no parent_task
7. **Auto-add member to project group** — trigger when task is assigned to an employee
8. **Real-time WebSocket group chat** — upgrade existing REST chat to WS
9. **Task status update** — inline status dropdown on Kanban cards

### Phase 3: HRMS Completions
10. **Manager attendance view** — endpoint + UI tab to see ALL employees' attendance
11. **Shift assignment to employee** — `/hrms/employee/{id}/assign-shift` + UI
12. **Leave balance tracking** — simple annual quota system (10 Casual, 7 Sick etc.)

### Phase 4: Automation (Celery)
13. **Celery Beat schedules** — wire existing tasks to Beat (weekly score, nightly delayed, weekly report)
14. **Email report to Team Lead** — send via Mailpit when all subtasks under a team complete

### Phase 5: UI Polish
15. **Kanban drag-and-drop** — `@dnd-kit` for status column drag
16. **Task filter** — filter by priority and status in list/tree view
17. **Mobile sidebar** — responsive Sheet-based sidebar

## Files to create/modify
- `backend/app/api/v1/tasks.py` — add auto-bubble, auto-group-add, assignment endpoints
- `backend/app/api/v1/hrms.py` — add shift assignment, leave balance, all-employee attendance
- `backend/app/api/v1/attendance.py` — add manager all-employees view
- `backend/app/celery_app.py` — wire Beat schedules
- `frontend/src/pages/TasksPage.jsx` — assignment UI, status update, filters, WS chat
- `frontend/src/pages/AttendancePage.jsx` — manager view tab, shift assignment
- `frontend/src/main.jsx` — add Sonner Toaster
- New: `frontend/src/hooks/useToast.js` — toast wrapper





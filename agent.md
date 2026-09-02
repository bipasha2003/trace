# agent.md — TRACE Development Context

> This file is your development context. Read it at the start of every session.
> **Do not use this for project feature tracking** — that lives in `project.md`.

---

## The Golden Rule

**After implementing or changing any feature, update `project.md` accordingly.**
- Mark newly implemented features as ✅
- Change partial features from 🔲 to 🔶
- Add new decisions to the "Key Architectural Decisions" table
- Add new future ideas to the "Future Plans" section

Also update `ui.md` if new UI patterns are introduced or component usage changes.

---

## Tech Stack (Quick Reference)

| Layer | Technology |
|-------|-----------|
| Frontend | Vite + React (JSX) |
| UI Library | shadcn/ui — preset `b1tNnRXF5` (`base-mira` style) |
| CSS | Tailwind CSS v4, OKLCH design tokens |
| Icons | `lucide-react` **only** |
| Font | Raleway Variable |
| Backend | FastAPI + async SQLAlchemy 2.0 + Pydantic V2 |
| Database | PostgreSQL (Alembic migrations) |
| Cache / Queue | Redis + Celery 5 (Worker + Beat) |
| Object Storage | MinIO (S3-compatible) |
| Mail | Mailpit (SMTP catch-all) |
| AI / LLM | OpenAI SDK (via Celery task) |
| Auth | JWT access token in `localStorage` |

---

## Mandatory UI Rules

1. **Only use shadcn/ui components.** Never write custom CSS or inline styles.
2. **Icons from `lucide-react` only.** No `react-icons`, `heroicons`, etc.
3. **Dark mode = `.dark` class on `<html>`.** `ThemeContext.toggleMode()` handles it.
4. **Tailwind classes: semantic tokens only.** Use `bg-background`, `text-muted-foreground`, `border-border`, etc. Never `bg-violet-500/20` or `text-white/60`.
5. **See `ui.md`** for component patterns (Card, Button, Dialog, Table, Tabs, etc.) before writing new UI.

---

## Key Import Paths

```js
// shadcn components
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Switch } from '@/components/ui/switch'
import { Skeleton } from '@/components/ui/skeleton'
import { Progress } from '@/components/ui/progress'

// API layer
import { employeesApi, tasksApi, attendanceApi, hrmsApi, productivityApi, authApi } from '@/api'
import api from '@/api/client'
import servicesApi from '@/api/services'

// Contexts
import { useAuth } from '@/contexts/AuthContext'
import { useTheme } from '@/contexts/ThemeContext'

// Utilities
import { cn, getInitials, timeAgo } from '@/lib/utils'
```

---

## Backend API Reference

**Base URL:** `http://localhost:8000/api/v1` (proxied via Vite)

| Module | Route Prefix | File |
|--------|-------------|------|
| Auth | `/auth` | `api/v1/auth.py` |
| Users | `/users` | `api/v1/users.py` |
| Employees + Departments | `/employees` | `api/v1/employees.py` |
| Attendance | `/attendance` | `api/v1/attendance.py` |
| HRMS (Leaves / Holidays / Shifts) | `/hrms` | `api/v1/hrms.py` |
| Tasks (Tree, GitHub, LLM, Groups) | `/tasks` | `api/v1/tasks.py` |
| Productivity + Reports | `/productivity`, `/reports` | `api/v1/productivity.py` |
| Services / Health / WS / MinIO / Mail / LLM | `/services` | `api/v1/services.py` |

### Key Task Endpoints
```
GET  /tasks/tree/hierarchy         → full infinite tree
POST /tasks/                       → create task
PUT  /tasks/{id}                   → update task
DELETE /tasks/{id}                 → delete task
POST /tasks/{id}/push-github       → push to GitHub Issues
POST /tasks/{id}/verify-commit     → LLM commit verification
GET  /tasks/{id}/evaluate-tree     → tree evaluation report
GET  /tasks/groups/list            → project chat groups
POST /tasks/groups/{id}/messages   → post to group chat
```

---

## File Structure (Frontend)

```
frontend/src/
  components/
    ui/                  ← shadcn-generated (NEVER manually edit)
    ServiceMonitor.jsx   ← infrastructure health overlay
  layouts/
    DashboardLayout.jsx  ← SidebarProvider + SidebarInset
    Sidebar.jsx          ← shadcn Sidebar primitives + NavLink
    Header.jsx           ← SidebarTrigger + search + theme toggle
  pages/
    LoginPage.jsx
    DashboardPage.jsx
    EmployeesPage.jsx
    AttendancePage.jsx
    TasksPage.jsx
    ProductivityPage.jsx
    FilesPage.jsx
    SettingsPage.jsx
    NotFoundPage.jsx
  contexts/
    AuthContext.jsx      ← JWT auth, user state
    ThemeContext.jsx     ← dark/light via .dark class
  api/
    index.js             ← re-exports all API modules
    client.js            ← axios base instance
    services.js          ← service monitor API
  lib/
    utils.js             ← cn(), getInitials(), timeAgo()
  index.css              ← shadcn token definitions ONLY
```

---

## Development Commands

```bash
# Full stack (recommended)
./start.sh start

# Stop everything
./start.sh stop

# DB migrations
./start.sh migrate

# Service status
./start.sh status

# Frontend only
cd frontend && npm run dev

# Backend only (from backend/)
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

---

## Default Credentials & URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| Frontend | http://localhost:5173 | — |
| API Docs | http://localhost:8000/docs | — |
| pgAdmin | http://localhost:5050 | admin@trace.com / Admin@123 |
| Mailpit | http://localhost:8025 | — |
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin |
| App Login | http://localhost:5173 | admin@trace.com / Admin@123 |

---

## Layout Patterns

### Sidebar Navigation (NavLink integration)
```jsx
<SidebarMenuButton
  render={<NavLink to="/dashboard" />}
  isActive={location.pathname === '/dashboard'}
  tooltip="Dashboard"
>
  <LayoutDashboard />
  <span>Dashboard</span>
</SidebarMenuButton>
```

### Standard Page Shell
```jsx
<div id="page-id" className="space-y-6 max-w-[1400px]">
  {/* Page header */}
  <div className="flex items-center justify-between">
    <div>
      <h1 className="text-2xl font-bold tracking-tight">Page Title</h1>
      <p className="text-sm text-muted-foreground">Subtitle</p>
    </div>
    <Button onClick={refresh} variant="outline" size="icon"><RefreshCw /></Button>
  </div>

  {/* Content */}
</div>
```

### Alert (success/error feedback)
```jsx
<Alert variant={msg.type === 'success' ? 'default' : 'destructive'}>
  {msg.type === 'success' ? <CheckCircle className="size-4" /> : <AlertTriangle className="size-4" />}
  <AlertDescription>{msg.text}</AlertDescription>
</Alert>
```

---

## Anti-Patterns

```jsx
// ❌ Never do this
import { MdDashboard } from 'react-icons/md'
<div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-xl">
<span className="text-violet-400 bg-violet-500/20">

// ✅ Always do this
import { LayoutDashboard } from 'lucide-react'
<Card><CardContent>…</CardContent></Card>
<Badge variant="secondary">label</Badge>
```

---

## Document Map

| File | Purpose | Edit? |
|------|---------|-------|
| `project.md` | Feature registry, decisions, plans — **the project mirror** | ✅ Keep updated |
| `agent.md` | This file — your dev context | ✅ Keep updated |
| `ui.md` | shadcn component usage guide | ✅ Update when patterns change |
| `Overview.md` | Original handwritten scope (historical) | ❌ Archive only |
| `Devplopment.md` | Original service notes (historical) | ❌ Archive only |
| `AGENT.md` | Original agent report (historical) | ❌ Archive only |
| `README.md` | Quick-start guide | Update as needed |

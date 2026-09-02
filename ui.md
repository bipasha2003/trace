# TRACE — UI Practices

## Design System

TRACE uses **shadcn/ui** as the single source of truth for all UI components. The preset `b1tNnRXF5` (`base-mira` style, Vite template) was used to initialize the design system. This preset defines OKLCH-based color tokens, Raleway Variable as the font, and a `0.625rem` border radius.

---

## Core Rules

1. **Never create custom-styled components.** All UI elements must use shadcn primitives from `@/components/ui/`.
2. **Never write inline color or glass styles.** Do not use `bg-violet-500/20`, `text-white/60`, `backdrop-blur`, or any hardcoded colors.
3. **Use semantic token classes only.** Use `bg-background`, `text-foreground`, `text-muted-foreground`, `bg-primary`, `bg-muted`, `border-border`, etc.
4. **Icons:** Use `lucide-react` exclusively. Do not import `react-icons/md` or any other icon library.
5. **Dark mode:** Toggle the `.dark` class on `<html>`. The `ThemeContext` handles this via `document.documentElement.classList.toggle('dark')`.

---

## Component Usage Guide

### Layout
```jsx
// Sidebar-based layout
<SidebarProvider>
  <AppSidebar />          // shadcn Sidebar primitives
  <SidebarInset>
    <Header />            // sticky top bar
    <main className="flex-1 p-6 overflow-auto">
      <Outlet />
    </main>
  </SidebarInset>
</SidebarProvider>
```

### Cards
```jsx
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

// Stat card pattern
<Card>
  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
    <CardTitle className="text-sm font-medium text-muted-foreground">Label</CardTitle>
    <Icon className="size-4 text-muted-foreground" />
  </CardHeader>
  <CardContent>
    <div className="text-2xl font-bold">Value</div>
  </CardContent>
</Card>
```

### Buttons
```jsx
import { Button } from '@/components/ui/button'

<Button>Default</Button>
<Button variant="outline">Outline</Button>
<Button variant="ghost" size="icon"><Icon /></Button>
<Button variant="destructive">Delete</Button>
```

### Badges
```jsx
import { Badge } from '@/components/ui/badge'

<Badge>default</Badge>
<Badge variant="secondary">secondary</Badge>
<Badge variant="outline">outline</Badge>
<Badge variant="destructive">error</Badge>
```

### Forms
```jsx
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

<div className="space-y-2">
  <Label htmlFor="field">Field Name</Label>
  <Input id="field" placeholder="…" />
</div>
```

### Dialogs / Modals
```jsx
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'

<Dialog open={open} onOpenChange={setOpen}>
  <DialogContent>
    <DialogHeader><DialogTitle>Title</DialogTitle></DialogHeader>
    {/* content */}
    <DialogFooter>
      <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
      <Button>Confirm</Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

### Tables
```jsx
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

<Table>
  <TableHeader>
    <TableRow>
      <TableHead>Column</TableHead>
    </TableRow>
  </TableHeader>
  <TableBody>
    <TableRow>
      <TableCell>Data</TableCell>
    </TableRow>
  </TableBody>
</Table>
```

### Tabs
```jsx
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

<Tabs defaultValue="first">
  <TabsList>
    <TabsTrigger value="first">First</TabsTrigger>
  </TabsList>
  <TabsContent value="first">…</TabsContent>
</Tabs>
```

### Alerts
```jsx
import { Alert, AlertDescription } from '@/components/ui/alert'

<Alert variant="destructive">
  <AlertCircle className="size-4" />
  <AlertDescription>Error message</AlertDescription>
</Alert>
```

---

## Sidebar Navigation

The sidebar uses `SidebarMenuButton` with the `render` prop for router integration:

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

The sidebar supports `collapsible="icon"` mode — when collapsed, labels are hidden and `SidebarRail` provides a drag handle.

---

## Dark Mode

The theme is driven by the `.dark` CSS class on `<html>`. The `ThemeContext` manages this:

```jsx
// Toggle theme
const { toggleMode, mode } = useTheme()
```

All shadcn component colors adapt automatically via the OKLCH CSS variables defined in `index.css`.

---

## File Structure

```
src/
  components/
    ui/           ← shadcn-generated components (do not edit manually)
    ServiceMonitor.jsx
  layouts/
    DashboardLayout.jsx
    Sidebar.jsx
    Header.jsx
  pages/          ← all page components
  contexts/
    AuthContext.jsx
    ThemeContext.jsx
  lib/
    utils.js      ← cn(), getInitials(), timeAgo()
  index.css       ← shadcn token definitions only
```

---

## Anti-Patterns (Do Not Do)

```jsx
// ❌ Custom glassmorphism
<div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-xl p-5">

// ❌ Hardcoded colors
<span className="text-violet-400 bg-violet-500/20">

// ❌ react-icons
import { MdDashboard } from 'react-icons/md'

// ❌ Custom GlassCard component
import { GlassCard } from '@/components/ui/GlassCard'

// ✅ Correct patterns
<Card><CardContent>…</CardContent></Card>
<Badge variant="secondary">label</Badge>
import { LayoutDashboard } from 'lucide-react'
```

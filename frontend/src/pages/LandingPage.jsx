/**
 * TRACE — Landing Page (/)
 * Public, marketing-quality. Guests only — authenticated users redirect to their panel.
 * Sections: Hero · Problem · How it works (3 steps) · Feature grid · Footer.
 * PROJECT.md §17. Stack: shadcn/ui + Tailwind v4 tokens + lucide-react.
 */

import { useNavigate } from 'react-router-dom'
import {
  ArrowRight,
  Zap,
  GitBranch,
  BarChart3,
  ShieldCheck,
  Bot,
  FolderKanban,
  CheckCircle2,
  Users,
  FileText,
  Sparkles,
  Cpu,
  Bell,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useTheme } from '@/contexts/ThemeContext'
import { Sun, Moon } from 'lucide-react'

/* ─── data ─────────────────────────────────────────────────────── */

const HOW_IT_WORKS = [
  {
    step: '01',
    icon: FileText,
    title: 'Manager uploads requirements',
    body: 'Drop in any combination of PDFs, Word docs, or markdown files. TRACE extracts the intent.',
  },
  {
    step: '02',
    icon: Bot,
    title: 'AI plans the project',
    body: 'The AI authors a living project document, generates task groups, assigns a Gantt chart, and ranks candidate Project Managers — all in one pipeline run.',
  },
  {
    step: '03',
    icon: GitBranch,
    title: 'The team delivers',
    body: 'Every task is a GitHub issue. Whoever does the work updates its status; completing it closes the issue and moves the Gantt.',
  },
]

const FEATURES = [
  {
    icon: Sparkles,
    title: 'AI Project Evaluation',
    body: 'Upload requirement documents and receive a structured project plan, task breakdown, and Gantt chart — generated end-to-end.',
  },
  {
    icon: FolderKanban,
    title: 'Living Project Documents',
    body: 'The project doc starts as what the AI understood. The PM refines it. Every edit triggers Gantt re-evaluation.',
  },
  {
    icon: CheckCircle2,
    title: 'Tasks Are GitHub Issues',
    body: 'Each project gets its own public repository. Creating a task opens an issue; completing it closes the issue.',
  },
  {
    icon: Users,
    title: 'AI-Ranked Assignee Suggestions',
    body: 'The AI scores employees on task throughput, on-time rate, and past subject matter — and shows its reasoning.',
  },
  {
    icon: BarChart3,
    title: 'Auto-Maintained Gantt',
    body: 'The chart regenerates on every status change. Each version is stamped with the reason it moved.',
  },
  {
    icon: Bell,
    title: 'Smart Notifications',
    body: 'Assignment, due-date, and completion events reach the right people in-app and via email — no polling required.',
  },
  {
    icon: ShieldCheck,
    title: 'Server-Enforced Authority',
    body: 'Only a task’s assignee or its Project Manager can change its status — checked by the API, not just hidden in the UI.',
  },
  {
    icon: Cpu,
    title: 'Three-Role Panel Separation',
    body: 'Admin, Manager, and Employee each live in a fully isolated panel. Cross-panel access returns a 403 — never a silent redirect.',
  },
]

/* ─── component ─────────────────────────────────────────────────── */

export default function LandingPage() {
  const navigate = useNavigate()
  const { mode, toggleMode } = useTheme()

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">

      {/* ── Nav ───────────────────────────────────────────────── */}
      <nav className="sticky top-0 z-50 border-b bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="mx-auto max-w-6xl px-6 flex h-14 items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex size-7 items-center justify-center rounded-md bg-primary text-primary-foreground text-xs font-bold">
              T
            </div>
            <span className="font-semibold tracking-tight">TRACE</span>
          </div>

          <div className="flex items-center gap-2">
            <Button
              id="landing-btn-theme"
              variant="ghost"
              size="icon-sm"
              onClick={toggleMode}
              title={mode === 'dark' ? 'Light mode' : 'Dark mode'}
            >
              {mode === 'dark' ? <Sun className="size-4" /> : <Moon className="size-4" />}
            </Button>
            <Button
              id="landing-btn-sign-in"
              variant="outline"
              size="sm"
              onClick={() => navigate('/login')}
            >
              Sign in
            </Button>
            <Button
              id="landing-btn-get-started"
              size="sm"
              onClick={() => navigate('/login')}
            >
              Get started <ArrowRight className="size-4" />
            </Button>
          </div>
        </div>
      </nav>

      {/* ── Hero ──────────────────────────────────────────────── */}
      <section className="relative flex flex-col items-center justify-center text-center px-6 py-28 overflow-hidden">
        {/* Background gradient orbs */}
        <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden>
          <div className="absolute -top-32 left-1/2 -translate-x-1/2 size-[600px] rounded-full bg-primary/10 blur-3xl" />
          <div className="absolute top-20 right-0 size-72 rounded-full bg-primary/5 blur-2xl" />
        </div>

        <div className="relative max-w-3xl space-y-6">
          <Badge variant="secondary" className="gap-1.5 px-3 py-1 text-xs">
            <Zap className="size-3" />
            AI-Driven Project Management
          </Badge>

          <h1 className="text-5xl md:text-6xl font-bold tracking-tight leading-[1.1]">
            From requirements<br />
            to{' '}
            <span className="text-primary">delivered tasks</span>
            ,<br />
            automatically.
          </h1>

          <p className="text-lg text-muted-foreground max-w-2xl mx-auto leading-relaxed">
            TRACE turns a folder of requirement documents into a structured project plan, a
            living Gantt chart, and GitHub issues — then keeps them current as code ships.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
            <Button
              id="hero-btn-get-started"
              size="lg"
              className="gap-2 px-8"
              onClick={() => navigate('/login')}
            >
              Get started free
              <ArrowRight className="size-4" />
            </Button>
            <Button
              id="hero-btn-learn-more"
              size="lg"
              variant="outline"
              className="gap-2 px-8"
              onClick={() => document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth' })}
            >
              See how it works
            </Button>
          </div>
        </div>
      </section>

      {/* ── Problem ───────────────────────────────────────────── */}
      <section className="bg-muted/40 border-y px-6 py-20">
        <div className="mx-auto max-w-4xl text-center space-y-4">
          <h2 className="text-3xl font-bold tracking-tight">The problem with project handoffs</h2>
          <p className="text-muted-foreground text-lg max-w-2xl mx-auto leading-relaxed">
            Requirements live in PDFs. Plans live in spreadsheets. Tasks live in Jira.
            Nobody knows if the code matches any of them — until it ships and it doesn't.
          </p>
          <p className="text-muted-foreground text-base max-w-xl mx-auto">
            TRACE puts all three in one pipeline, connected by AI and anchored to the same
            GitHub repository the team is pushing to.
          </p>
        </div>
      </section>

      {/* ── How it works ──────────────────────────────────────── */}
      <section id="how-it-works" className="px-6 py-24">
        <div className="mx-auto max-w-5xl">
          <div className="text-center space-y-3 mb-16">
            <h2 className="text-3xl font-bold tracking-tight">How TRACE works</h2>
            <p className="text-muted-foreground">Three steps from brief to verified delivery.</p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {HOW_IT_WORKS.map(({ step, icon: Icon, title, body }) => (
              <div
                key={step}
                className="relative flex flex-col items-start gap-4 rounded-xl border bg-card p-6 shadow-sm hover:shadow-md transition-shadow"
              >
                <div className="flex items-center gap-3">
                  <span className="text-4xl font-black text-primary/20 leading-none">{step}</span>
                  <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10">
                    <Icon className="size-4 text-primary" />
                  </div>
                </div>
                <div className="space-y-1">
                  <h3 className="font-semibold text-base">{title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">{body}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Feature grid ──────────────────────────────────────── */}
      <section className="bg-muted/40 border-y px-6 py-24">
        <div className="mx-auto max-w-5xl">
          <div className="text-center space-y-3 mb-16">
            <h2 className="text-3xl font-bold tracking-tight">Everything in one platform</h2>
            <p className="text-muted-foreground">
              From raw requirements to delivered, tracked work.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {FEATURES.map(({ icon: Icon, title, body }) => (
              <div
                key={title}
                className="flex flex-col gap-3 rounded-xl border bg-card p-5 hover:shadow-md transition-shadow"
              >
                <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10">
                  <Icon className="size-4 text-primary" />
                </div>
                <h3 className="font-semibold text-sm">{title}</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">{body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ───────────────────────────────────────────────── */}
      <section className="px-6 py-24 text-center">
        <div className="mx-auto max-w-2xl space-y-6">
          <h2 className="text-3xl font-bold tracking-tight">
            Ready to automate your project lifecycle?
          </h2>
          <p className="text-muted-foreground text-lg">
            Sign in to your TRACE workspace and start turning requirements into results.
          </p>
          <Button
            id="cta-btn-get-started"
            size="lg"
            className="gap-2 px-10"
            onClick={() => navigate('/login')}
          >
            Get started
            <ArrowRight className="size-4" />
          </Button>
        </div>
      </section>

      {/* ── Footer ────────────────────────────────────────────── */}
      <footer className="border-t bg-muted/30 px-6 py-8">
        <div className="mx-auto max-w-6xl flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-2">
            <div className="flex size-5 items-center justify-center rounded bg-primary text-primary-foreground text-[10px] font-bold">
              T
            </div>
            <span className="font-medium text-foreground">TRACE</span>
            <span>— Task and Resource Attendance and Comprehensive Evaluation</span>
          </div>
          <p>© {new Date().getFullYear()} TRACE. All rights reserved.</p>
        </div>
      </footer>
    </div>
  )
}

/**
 * TRACE — Project selector (Manager + Employee topbars)
 * "All" → the panel's combined dashboard; a project → its detail route.
 * The URL is the source of truth for which project is selected. PROJECT.md §19–20.
 */

import { useEffect, useState } from 'react'
import { useLocation, useMatch, useNavigate } from 'react-router-dom'
import { Check, ChevronDown, FolderKanban, LayoutGrid } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { projectsApi } from '@/api/projects'

export default function ProjectSelector({ base }) {
  const navigate = useNavigate()
  const location = useLocation()
  const match = useMatch(`${base}/projects/:id`)
  const selectedId = match && /^\d+$/.test(match.params.id) ? Number(match.params.id) : null
  const [projects, setProjects] = useState([])

  // Refetch on navigation so a project created a moment ago shows up
  useEffect(() => {
    projectsApi.list().then((res) => setProjects(res.data)).catch(() => setProjects([]))
  }, [location.pathname])

  const selected = projects.find((p) => p.id === selectedId)

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button
            id={`${base.slice(1)}-project-selector`}
            variant="outline"
            size="sm"
            className="gap-2 min-w-[180px] max-w-[280px] justify-between"
          />
        }
      >
        <span className="flex items-center gap-1.5 truncate">
          {selected ? <FolderKanban className="size-3.5 shrink-0" /> : <LayoutGrid className="size-3.5 shrink-0" />}
          <span className="truncate">{selected ? selected.name : 'All projects'}</span>
        </span>
        <ChevronDown className="size-3.5 shrink-0 text-muted-foreground" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-72">
        <DropdownMenuItem onClick={() => navigate(base)}>
          <LayoutGrid className="size-3.5" />
          <span className="flex-1">All projects</span>
          {!selectedId && <Check className="size-3.5" />}
        </DropdownMenuItem>
        {projects.length > 0 && <DropdownMenuSeparator />}
        {projects.length > 0 && (
          <DropdownMenuGroup>
            <DropdownMenuLabel>Projects</DropdownMenuLabel>
            {projects.map((p) => (
              <DropdownMenuItem key={p.id} onClick={() => navigate(`${base}/projects/${p.id}`)}>
                <FolderKanban className="size-3.5" />
                <span className="flex-1 truncate">{p.name}</span>
                {p.my_role && (
                  <span className="text-[10px] text-muted-foreground">
                    {p.my_role === 'Project Manager' ? 'PM' : 'Member'}
                  </span>
                )}
                {p.id === selectedId && <Check className="size-3.5" />}
              </DropdownMenuItem>
            ))}
          </DropdownMenuGroup>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

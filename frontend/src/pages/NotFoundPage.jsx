/**
 * TRACE — 404 Not Found
 */

import { Link } from 'react-router-dom'
import { Home, SearchX } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function NotFoundPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="text-center">
        <SearchX className="size-16 text-muted-foreground/30 mx-auto mb-6" />
        <h1 className="text-6xl font-bold text-muted-foreground/20 mb-2">404</h1>
        <p className="text-base text-muted-foreground mb-1">Page Not Found</p>
        <p className="text-sm text-muted-foreground/60 mb-8">
          The page you&apos;re looking for doesn&apos;t exist or has been moved.
        </p>
        <Link to="/dashboard">
          <Button>
            <Home className="size-4" /> Back to Dashboard
          </Button>
        </Link>
      </div>
    </div>
  )
}

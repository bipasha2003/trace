/**
 * TRACE — Renders a generated markdown document (project, progress, task docs).
 * GitHub-flavoured (task lists, tables). Styled with tokens only; links open in a new tab.
 */

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

const COMPONENTS = {
  h1: (p) => <h1 className="mb-3 mt-2 text-xl font-semibold tracking-tight" {...p} />,
  h2: (p) => <h2 className="mb-2 mt-6 border-b pb-1 text-lg font-semibold" {...p} />,
  h3: (p) => <h3 className="mb-2 mt-4 font-semibold" {...p} />,
  p: (p) => <p className="my-2 leading-relaxed" {...p} />,
  ul: ({ className, ...p }) => (
    <ul className={`my-2 space-y-1 ${className?.includes('contains-task-list') ? 'list-none pl-1' : 'list-disc pl-5'}`} {...p} />
  ),
  ol: (p) => <ol className="my-2 list-decimal space-y-1 pl-5" {...p} />,
  input: (p) => <input {...p} disabled className="mr-2 translate-y-0.5 accent-primary" />,
  a: (p) => <a className="text-primary underline-offset-2 hover:underline" target="_blank" rel="noopener noreferrer" {...p} />,
  code: (p) => <code className="rounded bg-muted px-1 py-0.5 font-mono text-xs" {...p} />,
  pre: (p) => <pre className="my-3 overflow-x-auto rounded-lg bg-muted p-3 text-xs" {...p} />,
  blockquote: (p) => <blockquote className="my-3 border-l-2 pl-3 text-muted-foreground" {...p} />,
  table: (p) => <div className="my-3 overflow-x-auto"><table className="w-full text-left text-xs" {...p} /></div>,
  th: (p) => <th className="border-b px-2 py-1 font-medium" {...p} />,
  td: (p) => <td className="border-b px-2 py-1" {...p} />,
  hr: () => <hr className="my-4" />,
}

export default function Markdown({ children }) {
  return (
    <div className="min-w-0 text-sm text-foreground">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={COMPONENTS}>{children || ''}</ReactMarkdown>
    </div>
  )
}

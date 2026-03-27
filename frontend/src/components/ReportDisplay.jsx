import ReactMarkdown from 'react-markdown'

export default function ReportDisplay({ report, llm }) {
  const isUnavailable = llm?.status === 'unavailable' || !llm

  return (
    <article className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-lg font-semibold">AI Scouting Report</h3>
        <span
          className={`rounded-full border px-2.5 py-1 text-xs font-medium ${
            isUnavailable
              ? 'border-amber-400/40 bg-amber-500/10 text-amber-200'
              : 'border-emerald-400/40 bg-emerald-500/10 text-emerald-200'
          }`}
        >
          {isUnavailable ? 'LLM unavailable' : `LLM: ${llm?.model || 'connected'}`}
        </span>
      </div>

      {isUnavailable && (
        <p className="mt-2 text-xs text-amber-200/90">Live model output is currently unavailable.</p>
      )}

      <div className="mt-3 text-sm leading-relaxed text-slate-200 prose prose-invert max-w-none">
        <ReactMarkdown
          components={{
            h3: ({ node, ...props }) => <h3 className="mt-4 mb-2 text-base font-semibold text-slate-100" {...props} />,
            h4: ({ node, ...props }) => <h4 className="mt-3 mb-2 text-sm font-semibold text-slate-200" {...props} />,
            p: ({ node, ...props }) => <p className="mb-2" {...props} />,
            ul: ({ node, ...props }) => <ul className="mb-2 ml-4 list-disc" {...props} />,
            li: ({ node, ...props }) => <li className="mb-1" {...props} />,
            strong: ({ node, ...props }) => <strong className="font-semibold text-slate-100" {...props} />,
          }}
        >
          {report}
        </ReactMarkdown>
      </div>
    </article>
  )
}

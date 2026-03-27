export default function ReportDisplay({ report, llm }) {
  const isUnavailable = report === 'LLM unavailable' || llm?.status === 'unavailable'

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

      <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-200">{report}</p>
    </article>
  )
}

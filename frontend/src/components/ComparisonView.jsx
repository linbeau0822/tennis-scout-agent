import ReactMarkdown from 'react-markdown'

export default function ComparisonView({ data, onBack }) {
  if (!data) return null

  const { players, snapshots, report, llm } = data
  const isLLMUnavailable = llm?.status === 'unavailable' || !llm

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={onBack}
          className="rounded-lg border border-slate-700 px-3 py-1.5 text-sm text-slate-300 transition hover:bg-slate-800 hover:text-white"
        >
          ← Back to Search
        </button>
        <h2 className="text-xl font-bold">Player Comparison</h2>
      </div>

      {/* Player Overview – side by side */}
      <div className="grid gap-4 md:grid-cols-2">
        {players.map((player, idx) => (
          <div
            key={player.id}
            className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 text-center"
          >
            <h3 className="text-lg font-bold">{player.name}</h3>
            <p className="mt-1 text-sm text-slate-400">
              {player.ranking ? `Rank #${player.ranking} • ` : ''}{player.country || 'N/A'}
            </p>
          </div>
        ))}
      </div>

      {/* Stats Comparison */}
      <StatsComparison snapshots={snapshots} />

      {/* AI Analysis */}
      <AnalysisSection report={report} llm={llm} isUnavailable={isLLMUnavailable} />
    </div>
  )
}

/* ───────────── Stats Comparison ───────────── */

function StatsComparison({ snapshots }) {
  if (!snapshots || snapshots.length < 2) return null

  const [a, b] = snapshots
  const statsA = a.stats
  const statsB = b.stats

  const rows = [
    { label: 'Matches', valA: statsA.matches_played, valB: statsB.matches_played },
    { label: 'Wins', valA: statsA.wins, valB: statsB.wins },
    { label: 'Losses', valA: statsA.losses, valB: statsB.losses },
    { label: 'Win %', valA: `${statsA.win_pct}%`, valB: `${statsB.win_pct}%`, numA: statsA.win_pct, numB: statsB.win_pct },
    { label: 'Ace %', valA: `${statsA.averages.ace_pct}%`, valB: `${statsB.averages.ace_pct}%`, numA: statsA.averages.ace_pct, numB: statsB.averages.ace_pct },
    { label: '1st Serve %', valA: `${statsA.averages.first_serve_pct ?? 'N/A'}%`, valB: `${statsB.averages.first_serve_pct ?? 'N/A'}%`, numA: statsA.averages.first_serve_pct, numB: statsB.averages.first_serve_pct },
    { label: '1st Serve Win %', valA: `${statsA.averages.first_serve_win_pct}%`, valB: `${statsB.averages.first_serve_win_pct}%`, numA: statsA.averages.first_serve_win_pct, numB: statsB.averages.first_serve_win_pct },
  ]

  // Surface breakdown
  const allSurfaces = [...new Set([
    ...Object.keys(statsA.surface_breakdown || {}),
    ...Object.keys(statsB.surface_breakdown || {}),
  ])]

  return (
    <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/60">
      <div className="border-b border-slate-800 p-4">
        <h3 className="text-lg font-semibold">Stats Comparison</h3>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-800 text-slate-400">
              <th className="px-4 py-3 text-left font-medium">{a.player.name}</th>
              <th className="px-4 py-3 text-center font-medium">Stat</th>
              <th className="px-4 py-3 text-right font-medium">{b.player.name}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(({ label, valA, valB, numA, numB }) => (
              <tr key={label} className="border-b border-slate-800/50">
                <td className={`px-4 py-2.5 text-left font-semibold ${numA != null && numB != null && numA > numB ? 'text-emerald-400' : ''}`}>
                  {valA}
                </td>
                <td className="px-4 py-2.5 text-center text-slate-400">{label}</td>
                <td className={`px-4 py-2.5 text-right font-semibold ${numA != null && numB != null && numB > numA ? 'text-emerald-400' : ''}`}>
                  {valB}
                </td>
              </tr>
            ))}

            {/* Surface breakdown rows */}
            {allSurfaces.length > 0 && (
              <tr className="border-b border-slate-800/50 bg-slate-800/20">
                <td colSpan={3} className="px-4 py-2 text-center text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Surface Breakdown (matches)
                </td>
              </tr>
            )}
            {allSurfaces.map((surface) => {
              const cA = statsA.surface_breakdown?.[surface] ?? 0
              const cB = statsB.surface_breakdown?.[surface] ?? 0
              return (
                <tr key={surface} className="border-b border-slate-800/50">
                  <td className="px-4 py-2 text-left">{cA}</td>
                  <td className="px-4 py-2 text-center capitalize text-slate-400">{surface}</td>
                  <td className="px-4 py-2 text-right">{cB}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

/* ───────────── AI Analysis + Prediction ───────────── */

function AnalysisSection({ report, llm, isUnavailable }) {
  return (
    <article className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-lg font-semibold">AI Match Analysis & Prediction</h3>
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
        <div className="mt-2 text-xs text-amber-200/90">
          <p>Live model output is currently unavailable.</p>
          {llm?.error && (
            <p className="mt-1 text-[11px] text-amber-100/90">Details: {llm.error}</p>
          )}
        </div>
      )}

      {!isUnavailable && (
        <div className="mt-3 text-sm leading-relaxed text-slate-200 prose prose-invert max-w-none">
          <ReactMarkdown
            components={{
              h1: ({ node, ...props }) => <h1 className="mt-5 mb-2 text-xl font-bold text-slate-100" {...props} />,
              h2: ({ node, ...props }) => <h2 className="mt-4 mb-2 text-lg font-bold text-slate-100" {...props} />,
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
      )}
    </article>
  )
}

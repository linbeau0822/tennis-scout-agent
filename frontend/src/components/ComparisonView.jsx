import ReactMarkdown from 'react-markdown'
import PlayerPhoto from './PlayerPhoto'

export default function ComparisonView({ data, onBack }) {
  if (!data) return null

  const { players, snapshots, h2h, report, llm } = data
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
        {players.map((player) => (
          <div
            key={player.id}
            className="flex flex-col items-center rounded-xl border border-slate-800 bg-slate-900/60 p-5 text-center"
          >
            <PlayerPhoto
              imageUrl={player.image_url}
              name={player.name}
              size="lg"
              accent="emerald"
            />
            <h3 className="mt-3 text-lg font-bold">{player.name}</h3>
            <p className="mt-1 text-sm text-slate-400">
              {player.ranking ? `Rank #${player.ranking} • ` : ''}{player.country || 'N/A'}
            </p>
          </div>
        ))}
      </div>

      {/* H2H */}
      <H2HSection h2h={h2h} players={players} />

      {/* Stats Comparison */}
      <StatsComparison snapshots={snapshots} />

      {/* AI Analysis */}
      <AnalysisSection report={report} llm={llm} isUnavailable={isLLMUnavailable} />
    </div>
  )
}

/* ───────────── Head-to-Head ───────────── */

function H2HSection({ h2h, players }) {
  if (!h2h || !players || players.length < 2) return null

  const [p1, p2] = players
  const rec = h2h.record || {}
  const total = rec.total_meetings ?? 0
  const p1Wins = rec.player1_wins ?? 0
  const p2Wins = rec.player2_wins ?? 0

  let headline
  if (total === 0) {
    headline = 'No prior meetings'
  } else if (p1Wins > p2Wins) {
    headline = `${p1.name} leads ${p1Wins}–${p2Wins}`
  } else if (p2Wins > p1Wins) {
    headline = `${p2.name} leads ${p2Wins}–${p1Wins}`
  } else {
    headline = `Tied ${p1Wins}–${p2Wins}`
  }

  const surfaces = Object.entries(h2h.surface_split || {})
  const meetings = h2h.meetings || []

  return (
    <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/60">
      <div className="flex items-center justify-between border-b border-slate-800 p-4">
        <h3 className="text-lg font-semibold">Head-to-Head</h3>
        <span className="text-sm text-slate-300">
          {headline}{total > 0 ? ` · ${total} meeting${total !== 1 ? 's' : ''}` : ''}
        </span>
      </div>

      {total === 0 && (
        <div className="p-4 text-sm text-slate-400">
          These two players have no recorded meetings in the database.
        </div>
      )}

      {total > 0 && surfaces.length > 0 && (
        <div className="border-b border-slate-800/60 p-4">
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
            Surface Split
          </h4>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-slate-400">
                <th className="px-3 py-1.5 text-left font-medium">{p1.name}</th>
                <th className="px-3 py-1.5 text-center font-medium">Surface</th>
                <th className="px-3 py-1.5 text-right font-medium">{p2.name}</th>
              </tr>
            </thead>
            <tbody>
              {surfaces.map(([surface, split]) => (
                <tr key={surface} className="border-t border-slate-800/60">
                  <td className={`px-3 py-1.5 text-left font-semibold ${split.player1_wins > split.player2_wins ? 'text-emerald-400' : ''}`}>
                    {split.player1_wins}
                  </td>
                  <td className="px-3 py-1.5 text-center capitalize text-slate-400">{surface}</td>
                  <td className={`px-3 py-1.5 text-right font-semibold ${split.player2_wins > split.player1_wins ? 'text-emerald-400' : ''}`}>
                    {split.player2_wins}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {meetings.length > 0 && (
        <div className="overflow-x-auto p-4">
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
            Recent Meetings
          </h4>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-slate-400">
                <th className="px-3 py-1.5 text-left font-medium">Date</th>
                <th className="px-3 py-1.5 text-left font-medium">Tournament</th>
                <th className="px-3 py-1.5 text-left font-medium">Surface</th>
                <th className="px-3 py-1.5 text-left font-medium">Winner</th>
                <th className="px-3 py-1.5 text-left font-medium">Score</th>
              </tr>
            </thead>
            <tbody>
              {meetings.map((m) => (
                <tr key={m.match_id} className="border-t border-slate-800/60">
                  <td className="px-3 py-1.5 text-slate-300">{m.date || '—'}</td>
                  <td className="px-3 py-1.5 text-slate-300">{m.tournament || '—'}</td>
                  <td className="px-3 py-1.5 text-slate-300 capitalize">{m.surface || '—'}</td>
                  <td className="px-3 py-1.5 font-semibold text-slate-100">{m.winner_name || '—'}</td>
                  <td className="px-3 py-1.5 text-slate-300">{m.score || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
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
    { label: 'Avg Aces', valA: statsA.averages.aces_per_match != null ? statsA.averages.aces_per_match : 'N/A', valB: statsB.averages.aces_per_match != null ? statsB.averages.aces_per_match : 'N/A', numA: statsA.averages.aces_per_match, numB: statsB.averages.aces_per_match },
    {
      label: '1st Serve %',
      valA: statsA.averages.first_serve_pct == null ? 'N/A' : `${statsA.averages.first_serve_pct}%`,
      valB: statsB.averages.first_serve_pct == null ? 'N/A' : `${statsB.averages.first_serve_pct}%`,
      numA: statsA.averages.first_serve_pct,
      numB: statsB.averages.first_serve_pct,
    },
    {
      label: '1st Serve Win %',
      valA: statsA.averages.first_serve_win_pct == null ? 'N/A' : `${statsA.averages.first_serve_win_pct}%`,
      valB: statsB.averages.first_serve_win_pct == null ? 'N/A' : `${statsB.averages.first_serve_win_pct}%`,
      numA: statsA.averages.first_serve_win_pct,
      numB: statsB.averages.first_serve_win_pct,
    },
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

const PREDICTION_HEADING = /^##\s+Prediction\b.*$/im

function AnalysisSection({ report, llm, isUnavailable }) {
  const match = !isUnavailable && report ? report.match(PREDICTION_HEADING) : null
  const splitIdx = match ? match.index : -1
  const mainContent = splitIdx >= 0 ? report.slice(0, splitIdx).trimEnd() : report
  const predictionContent = splitIdx >= 0 ? report.slice(splitIdx).trim() : null

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
            {mainContent}
          </ReactMarkdown>
        </div>
      )}

      {!isUnavailable && predictionContent && (
        <div
          style={{ backgroundColor: '#F7E7CE' }}
          className="prose mt-4 max-w-none rounded-xl border border-amber-200/40 p-5 text-sm leading-relaxed text-slate-900"
        >
          <ReactMarkdown
            components={{
              h2: ({ node, ...props }) => (
                <h2 className="mb-3 mt-0 text-xl font-bold text-slate-900" {...props} />
              ),
              h3: ({ node, ...props }) => (
                <h3 className="mb-2 mt-3 text-base font-semibold text-slate-900" {...props} />
              ),
              p: ({ node, ...props }) => <p className="mb-2 text-slate-800" {...props} />,
              ul: ({ node, ...props }) => (
                <ul className="mb-2 ml-4 list-disc text-slate-800" {...props} />
              ),
              li: ({ node, ...props }) => <li className="mb-1" {...props} />,
              strong: ({ node, ...props }) => (
                <strong className="font-semibold text-slate-900" {...props} />
              ),
            }}
          >
            {predictionContent}
          </ReactMarkdown>
        </div>
      )}
    </article>
  )
}

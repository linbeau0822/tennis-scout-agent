export default function StatsTable({ snapshot }) {
  const { player, stats } = snapshot

  return (
    <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/60">
      <div className="border-b border-slate-800 p-4">
        <h2 className="text-xl font-semibold">{player.name}</h2>
        <p className="text-sm text-slate-400">
          {player.ranking ? `Rank #${player.ranking} • ` : ''}{player.country || 'N/A'}
          {player.handedness ? ` • ${player.handedness}` : ''}
        </p>
      </div>

      <div className="grid gap-4 p-4 sm:grid-cols-2 lg:grid-cols-4">
        <Metric label="Matches" value={stats.matches_played} />
        <Metric label="Wins" value={stats.wins} />
        <Metric label="Losses" value={stats.losses} />
        <Metric label="Win %" value={`${stats.win_pct}%`} />
        <Metric label="Avg Aces" value={stats.averages.aces_per_match != null ? stats.averages.aces_per_match : 'N/A'} />
        <Metric
          label="1st Serve %"
          value={
            stats.averages.first_serve_pct != null
              ? `${stats.averages.first_serve_pct}%`
              : 'N/A'
          }
        />
        <Metric
          label="1st Serve Win %"
          value={
            stats.averages.first_serve_win_pct != null
              ? `${stats.averages.first_serve_win_pct}%`
              : 'N/A'
          }
        />
      </div>
    </div>
  )
}

function Metric({ label, value }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
      <div className="text-xs uppercase tracking-wide text-slate-400">{label}</div>
      <div className="mt-1 text-lg font-semibold">{value}</div>
    </div>
  )
}

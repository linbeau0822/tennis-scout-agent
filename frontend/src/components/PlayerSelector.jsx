import { useState } from 'react'

export default function PlayerSelector({ selectedPlayers, onAdd, onRemove, onCompare, isLoading }) {
  const [query, setQuery] = useState('')

  const canCompare = selectedPlayers.length === 2
  const isFull = selectedPlayers.length >= 2

  const isAlreadySelected = (name) =>
    selectedPlayers.some((p) => p.toLowerCase() === name.toLowerCase())

  const handleAdd = () => {
    const trimmed = query.trim()
    if (!trimmed || isFull || isAlreadySelected(trimmed)) return
    onAdd(trimmed)
    setQuery('')
  }

  return (
    <div className="space-y-4">
      {/* Add player by name — instant, no API call */}
      {!isFull && (
        <div>
          <label className="mb-1.5 block text-sm font-medium text-slate-400">
            Enter a player name to add ({selectedPlayers.length}/2)
          </label>
          <div className="flex flex-col gap-2 sm:flex-row">
            <input
              className="w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 outline-none ring-emerald-400 placeholder:text-slate-500 focus:ring"
              placeholder="e.g. Jannik Sinner"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleAdd()
              }}
            />
            <button
              className="rounded-lg bg-emerald-600 px-4 py-2 font-medium text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
              onClick={handleAdd}
              disabled={!query.trim() || isAlreadySelected(query.trim())}
            >
              + Add Player
            </button>
          </div>
        </div>
      )}

      {/* Selected players chips */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">
          Selected Players ({selectedPlayers.length}/2)
        </h3>

        <div className="mt-3 flex flex-wrap gap-2">
          {selectedPlayers.length === 0 && (
            <p className="text-sm text-slate-500">
              No players selected yet. Use the search above to add players.
            </p>
          )}

          {selectedPlayers.map((name) => (
            <span
              key={name}
              className="inline-flex items-center gap-1.5 rounded-full border border-emerald-400/30 bg-emerald-500/15 px-3 py-1.5 text-sm font-medium text-emerald-200"
            >
              {name}
              <button
                onClick={() => onRemove(name)}
                className="ml-0.5 rounded-full p-0.5 text-emerald-300 transition hover:bg-emerald-500/30 hover:text-white"
                aria-label={`Remove ${name}`}
              >
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-3.5 w-3.5">
                  <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
                </svg>
              </button>
            </span>
          ))}
        </div>

        {/* Compare button — prominent when ready */}
        <div className="mt-4">
          <button
            className="w-full rounded-lg bg-emerald-600 px-4 py-2.5 font-semibold text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-40 sm:w-auto"
            disabled={!canCompare || isLoading}
            onClick={onCompare}
          >
            {isLoading ? 'Comparing…' : canCompare ? '⚡ Compare Players' : 'Select 2 players to compare'}
          </button>
        </div>
      </div>
    </div>
  )
}

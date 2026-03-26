export default function PlayerInput({ playerName, onPlayerNameChange, onSearch, loading }) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row">
      <input
        className="w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 outline-none ring-indigo-400 placeholder:text-slate-500 focus:ring"
        placeholder="e.g. Carlos Alcaraz"
        value={playerName}
        onChange={(e) => onPlayerNameChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') onSearch()
        }}
      />
      <button
        className="rounded-lg bg-indigo-500 px-4 py-2 font-medium text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-50"
        onClick={onSearch}
        disabled={loading}
      >
        {loading ? 'Loading...' : 'Generate Report'}
      </button>
    </div>
  )
}

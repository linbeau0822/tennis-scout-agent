import PlayerAutocomplete from './PlayerAutocomplete'

export default function PlayerInput({ playerName, onPlayerNameChange, onSearch, loading }) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-start">
      <div className="w-full">
        <PlayerAutocomplete
          value={playerName}
          onChange={onPlayerNameChange}
          onSelect={(player) => {
            onPlayerNameChange(player.name)
            onSearch(player.name)
          }}
          onSubmit={() => {
            if (!loading) onSearch()
          }}
          placeholder="e.g. Carlos Alcaraz"
          accent="indigo"
          disabled={loading}
        />
      </div>
      <button
        className="rounded-lg bg-indigo-500 px-4 py-2 font-medium text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-50"
        onClick={() => onSearch()}
        disabled={loading}
      >
        {loading ? 'Loading...' : 'Generate Report'}
      </button>
    </div>
  )
}

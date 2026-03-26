import { useState } from 'react'
import PlayerInput from './components/PlayerInput'
import StatsTable from './components/StatsTable'
import ReportDisplay from './components/ReportDisplay'
import { fetchPlayerReport } from './utils'

export default function App() {
  const [playerName, setPlayerName] = useState('')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const onSearch = async () => {
    if (loading || !playerName.trim()) return

    setLoading(true)
    setError('')

    try {
      const response = await fetchPlayerReport(playerName)
      setData(response)
    } catch (err) {
      setData(null)
      setError(err?.response?.data?.detail || 'Failed to fetch player report.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-5xl px-4 py-8">
        <h1 className="text-3xl font-bold tracking-tight">Tennis Scouting Agent</h1>
        <p className="mt-2 text-slate-400">Search a player and generate an AI scouting report.</p>

        <div className="mt-6">
          <PlayerInput
            playerName={playerName}
            onPlayerNameChange={setPlayerName}
            onSearch={onSearch}
            loading={loading}
          />
        </div>

        {error && (
          <div className="mt-4 rounded-lg border border-red-400/50 bg-red-500/10 p-3 text-sm text-red-200">
            {error}
          </div>
        )}

        {data && (
          <section className="mt-8 space-y-6">
            <StatsTable snapshot={data} />
            <ReportDisplay report={data.report} />
          </section>
        )}
      </div>
    </main>
  )
}

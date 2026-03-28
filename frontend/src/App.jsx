import { useState } from 'react'
import PlayerInput from './components/PlayerInput'
import PlayerSelector from './components/PlayerSelector'
import StatsTable from './components/StatsTable'
import ReportDisplay from './components/ReportDisplay'
import ComparisonView from './components/ComparisonView'
import { fetchPlayerReport, comparePlayers } from './utils'

const TABS = [
  { key: 'scout', label: '🔍 Scout Report', description: 'Search a player and generate an AI scouting report.' },
  { key: 'compare', label: '⚔️ Compare Players', description: 'Select two players for a head-to-head comparison & AI match prediction.' },
]

export default function App() {
  const [activeTab, setActiveTab] = useState('scout')

  // Scout state
  const [playerName, setPlayerName] = useState('')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // Comparison state
  const [selectedPlayers, setSelectedPlayers] = useState([])
  const [comparisonData, setComparisonData] = useState(null)
  const [compareLoading, setCompareLoading] = useState(false)
  const [compareError, setCompareError] = useState('')
  const [viewMode, setViewMode] = useState('select') // 'select' | 'result'

  // ──── Scout handlers ────
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

  // ──── Compare handlers ────
  const addPlayer = (name) => {
    if (selectedPlayers.length >= 2) return
    if (selectedPlayers.some((p) => p.toLowerCase() === name.toLowerCase())) return
    setSelectedPlayers((prev) => [...prev, name])
  }

  const removePlayer = (name) => {
    setSelectedPlayers((prev) => prev.filter((p) => p !== name))
  }

  const onCompare = async () => {
    if (selectedPlayers.length !== 2 || compareLoading) return

    setCompareLoading(true)
    setCompareError('')

    try {
      const result = await comparePlayers(selectedPlayers)
      setComparisonData(result)
      setViewMode('result')
    } catch (err) {
      const detail = err?.response?.data?.detail
      const msg = typeof detail === 'object' ? detail.message : detail
      setCompareError(msg || 'Failed to compare players.')
    } finally {
      setCompareLoading(false)
    }
  }

  const goBackToSelect = () => {
    setViewMode('select')
  }

  // ──── Derive current tab info ────
  const currentTab = TABS.find((t) => t.key === activeTab)

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-5xl px-4 py-8">
        {/* ── Header ── */}
        <h1 className="text-3xl font-bold tracking-tight">Tennis Scouting Agent</h1>

        {/* ── Tab Bar ── */}
        <div className="mt-5 flex gap-1 rounded-lg border border-slate-800 bg-slate-900/60 p-1">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex-1 rounded-md px-4 py-2.5 text-sm font-semibold transition ${
                activeTab === tab.key
                  ? tab.key === 'scout'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'bg-emerald-600 text-white shadow-sm'
                  : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* ── Tab Description ── */}
        <p className="mt-3 text-sm text-slate-400">{currentTab?.description}</p>

        {/* ═══════════════════════════════════════════ */}
        {/* ── Scout Report Tab ── */}
        {/* ═══════════════════════════════════════════ */}
        {activeTab === 'scout' && (
          <div className="mt-6 space-y-6">
            <PlayerInput
              playerName={playerName}
              onPlayerNameChange={setPlayerName}
              onSearch={onSearch}
              loading={loading}
            />

            {error && (
              <div className="rounded-lg border border-red-400/50 bg-red-500/10 p-3 text-sm text-red-200">
                {error}
              </div>
            )}

            {data && (
              <section className="space-y-6">
                <StatsTable snapshot={data} />
                <ReportDisplay report={data.report} llm={data.llm} />
              </section>
            )}
          </div>
        )}

        {/* ═══════════════════════════════════════════ */}
        {/* ── Compare Players Tab ── */}
        {/* ═══════════════════════════════════════════ */}
        {activeTab === 'compare' && (
          <div className="mt-6">
            {viewMode === 'result' && comparisonData ? (
              <ComparisonView data={comparisonData} onBack={goBackToSelect} />
            ) : (
              <div className="space-y-4">
                <PlayerSelector
                  selectedPlayers={selectedPlayers}
                  onAdd={addPlayer}
                  onRemove={removePlayer}
                  onCompare={onCompare}
                  isLoading={compareLoading}
                />

                {compareError && (
                  <div className="rounded-lg border border-red-400/50 bg-red-500/10 p-3 text-sm text-red-200">
                    {compareError}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </main>
  )
}

import { useEffect, useRef, useState } from 'react'
import { searchPlayers } from '../utils'

const ACCENTS = {
  indigo: {
    ring: 'ring-indigo-400',
    highlight: 'bg-indigo-500/20 text-indigo-100',
  },
  emerald: {
    ring: 'ring-emerald-400',
    highlight: 'bg-emerald-500/20 text-emerald-100',
  },
}

const MIN_QUERY_LENGTH = 2
const DEBOUNCE_MS = 200

export default function PlayerAutocomplete({
  value,
  onChange,
  onSelect,
  onSubmit,
  placeholder,
  disabled = false,
  accent = 'indigo',
  excludeNames = [],
}) {
  const [suggestions, setSuggestions] = useState([])
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)
  const [highlight, setHighlight] = useState(-1)
  const containerRef = useRef(null)

  const accentClasses = ACCENTS[accent] ?? ACCENTS.indigo
  const excludeSet = new Set(excludeNames.map((n) => n.toLowerCase()))
  const visibleSuggestions = suggestions.filter(
    (s) => !excludeSet.has(s.name.toLowerCase()),
  )

  useEffect(() => {
    const trimmed = value.trim()
    if (trimmed.length < MIN_QUERY_LENGTH) {
      setSuggestions([])
      setHasSearched(false)
      setLoading(false)
      return undefined
    }

    const controller = new AbortController()
    const timer = setTimeout(async () => {
      setLoading(true)
      try {
        const results = await searchPlayers(trimmed, 8, { signal: controller.signal })
        setSuggestions(results)
        setHasSearched(true)
        setHighlight(-1)
      } catch (err) {
        if (err?.name !== 'CanceledError' && err?.name !== 'AbortError') {
          setSuggestions([])
          setHasSearched(true)
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      }
    }, DEBOUNCE_MS)

    return () => {
      clearTimeout(timer)
      controller.abort()
    }
  }, [value])

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setOpen(true)
      setHighlight((h) => Math.min(h + 1, visibleSuggestions.length - 1))
      return
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault()
      setHighlight((h) => Math.max(h - 1, 0))
      return
    }
    if (e.key === 'Enter') {
      if (open && highlight >= 0 && visibleSuggestions[highlight]) {
        e.preventDefault()
        handleSelect(visibleSuggestions[highlight])
        return
      }
      setOpen(false)
      onSubmit?.()
      return
    }
    if (e.key === 'Escape') {
      setOpen(false)
      return
    }
    if (e.key === 'Tab') {
      setOpen(false)
    }
  }

  const handleSelect = (player) => {
    onSelect?.(player)
    setOpen(false)
    setHighlight(-1)
  }

  const showDropdown =
    open &&
    value.trim().length >= MIN_QUERY_LENGTH &&
    (loading || visibleSuggestions.length > 0 || hasSearched)

  return (
    <div ref={containerRef} className="relative w-full">
      <input
        className={`w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 outline-none ${accentClasses.ring} placeholder:text-slate-500 focus:ring`}
        placeholder={placeholder}
        value={value}
        disabled={disabled}
        onChange={(e) => {
          onChange(e.target.value)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={handleKeyDown}
        autoComplete="off"
        role="combobox"
        aria-expanded={showDropdown}
        aria-autocomplete="list"
      />

      {showDropdown && (
        <ul
          className="absolute z-10 mt-1 max-h-72 w-full overflow-auto rounded-lg border border-slate-700 bg-slate-900 shadow-lg"
          role="listbox"
        >
          {loading && (
            <li className="px-4 py-2 text-sm text-slate-400">Searching…</li>
          )}
          {!loading &&
            visibleSuggestions.map((player, idx) => {
              const isHighlighted = idx === highlight
              return (
                <li
                  key={player.id}
                  role="option"
                  aria-selected={isHighlighted}
                  className={`flex cursor-pointer items-center justify-between px-4 py-2 text-sm transition ${
                    isHighlighted ? accentClasses.highlight : 'text-slate-200 hover:bg-slate-800'
                  }`}
                  onMouseEnter={() => setHighlight(idx)}
                  onMouseDown={(e) => {
                    e.preventDefault()
                    handleSelect(player)
                  }}
                >
                  <span className="font-medium">{player.name}</span>
                  <span className="text-xs text-slate-400">
                    {player.ranking != null ? `#${player.ranking}` : 'Unranked'}
                    {player.country ? ` · ${player.country}` : ''}
                  </span>
                </li>
              )
            })}
          {!loading && visibleSuggestions.length === 0 && hasSearched && (
            <li className="px-4 py-2 text-sm text-slate-400">No players found</li>
          )}
        </ul>
      )}
    </div>
  )
}

import { useState, useEffect } from 'react'

const SIZE_CLASSES = {
  md: 'h-14 w-14 text-base',
  lg: 'h-20 w-20 text-xl',
}

const ACCENT_RINGS = {
  indigo: 'ring-indigo-400/40',
  emerald: 'ring-emerald-400/40',
  slate: 'ring-slate-700',
}

function getInitials(name) {
  if (!name) return '?'
  const parts = name.trim().split(/\s+/)
  if (parts.length === 1) return parts[0][0].toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

export default function PlayerPhoto({ imageUrl, name, size = 'md', accent = 'slate' }) {
  const [errored, setErrored] = useState(false)
  const sizeClass = SIZE_CLASSES[size] ?? SIZE_CLASSES.md
  const ringClass = ACCENT_RINGS[accent] ?? ACCENT_RINGS.slate

  useEffect(() => {
    setErrored(false)
  }, [imageUrl])

  const showImage = imageUrl && !errored

  if (showImage) {
    return (
      <img
        src={imageUrl}
        alt={name || 'Player'}
        loading="lazy"
        onError={() => setErrored(true)}
        className={`${sizeClass} shrink-0 rounded-full object-cover ring-2 ${ringClass} bg-slate-800`}
      />
    )
  }

  return (
    <div
      className={`${sizeClass} flex shrink-0 items-center justify-center rounded-full bg-slate-800 font-semibold text-slate-300 ring-2 ${ringClass}`}
      aria-label={name || 'Player'}
    >
      {getInitials(name)}
    </div>
  )
}

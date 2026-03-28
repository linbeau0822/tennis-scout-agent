import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
})

export async function fetchPlayerReport(playerName) {
  const { data } = await api.get(`/player/${encodeURIComponent(playerName)}`)
  return data
}

export async function comparePlayers(playerNames) {
  const { data } = await api.post('/compare', { player_names: playerNames })
  return data
}

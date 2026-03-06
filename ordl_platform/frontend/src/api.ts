const API_BASE = import.meta.env.VITE_ORDL_API_BASE || 'http://127.0.0.1:8891/v1'

export async function getHealth() {
  const res = await fetch('http://127.0.0.1:8891/health')
  if (!res.ok) throw new Error('health request failed')
  return res.json()
}

export async function getInfo(token: string) {
  const res = await fetch(`${API_BASE}/info`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error('info request failed')
  return res.json()
}

export async function getProviders(token: string) {
  const res = await fetch(`${API_BASE}/providers`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error('providers request failed')
  return res.json()
}

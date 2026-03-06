import { useEffect, useMemo, useState } from 'react'
import { getHealth, getInfo, getProviders } from './api'
import './styles.css'

type ViewState = {
  health?: any
  info?: any
  providers?: any
  error?: string
}

export default function App() {
  const [token, setToken] = useState('')
  const [state, setState] = useState<ViewState>({})

  const hasToken = useMemo(() => token.trim().length > 0, [token])

  useEffect(() => {
    getHealth()
      .then((health) => setState((s) => ({ ...s, health })))
      .catch((err: Error) => setState((s) => ({ ...s, error: err.message })))
  }, [])

  async function loadSecuredViews() {
    try {
      const [info, providers] = await Promise.all([getInfo(token), getProviders(token)])
      setState((s) => ({ ...s, info, providers, error: undefined }))
    } catch (err) {
      setState((s) => ({ ...s, error: (err as Error).message }))
    }
  }

  return (
    <div className="app">
      <div className="header">
        <div>
          <h1>ORDL Platform Control</h1>
          <div className="badge ok">Clean-room Enterprise Fleet Stack</div>
        </div>
        <div>
          <input
            style={{ width: 380, padding: 8, borderRadius: 8, border: '1px solid #38527f', background: '#0f1a2f', color: '#d8e5ff' }}
            placeholder="Paste bearer token"
            value={token}
            onChange={(e) => setToken(e.target.value)}
          />
          <button
            style={{ marginLeft: 8, padding: '8px 12px', borderRadius: 8, border: 0, background: '#27d98b', color: '#052112', fontWeight: 600 }}
            disabled={!hasToken}
            onClick={loadSecuredViews}
          >
            Load Tenant View
          </button>
        </div>
      </div>

      <div className="grid">
        <div className="card">
          <h3>Health</h3>
          <pre>{JSON.stringify(state.health ?? { status: 'loading' }, null, 2)}</pre>
        </div>

        <div className="card">
          <h3>Identity / Scope</h3>
          <pre>{JSON.stringify(state.info ?? { note: 'token required' }, null, 2)}</pre>
        </div>

        <div className="card">
          <h3>Provider Catalog</h3>
          <pre>{JSON.stringify(state.providers ?? { note: 'token required' }, null, 2)}</pre>
        </div>
      </div>

      <div style={{ marginTop: 16 }} className="card">
        <h3>Governance Reminder</h3>
        <div className="kv">
          <span>Default Ingress</span>
          <span className="badge">Zero-Trust</span>
        </div>
        <div className="kv">
          <span>Clearance Model</span>
          <span className="badge">4-tier + compartments</span>
        </div>
        <div className="kv">
          <span>Extension Policy</span>
          <span className="badge warn">Signed only</span>
        </div>
        {state.error ? <p style={{ color: '#ff9fa8' }}>Error: {state.error}</p> : null}
      </div>
    </div>
  )
}

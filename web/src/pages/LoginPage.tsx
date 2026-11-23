import { useState } from 'react'
import type { FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { api } from '../api'
import type { UserInput } from '../api'
import { useAuth } from '../useAuth'
import AuthModeBadge from '../components/AuthModeBadge'
import UserForm from '../components/UserForm'

export default function LoginPage() {
  const { ready, session, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const redirectTo = (location.state as { from?: string } | null)?.from ?? '/users'

  const [mode, setMode] = useState<'login' | 'signup'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (!ready) return null // cookie mode: still asking the API whether we're logged in
  if (session) return <Navigate to={redirectTo} replace />

  async function handleLogin(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      await login(email, password)
      navigate(redirectTo, { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  // Sign up, then log straight in with the same credentials.
  async function handleSignup(values: UserInput) {
    await api.createUser(values)
    await login(values.email, values.password)
    navigate(redirectTo, { replace: true })
  }

  return (
    <main className="auth-page">
      <div className="card">
        <h1>{mode === 'login' ? 'Log in' : 'Create an account'}</h1>
        <p className="auth-mode">
          <AuthModeBadge />
        </p>

        {mode === 'login' ? (
          <form className="form" onSubmit={handleLogin}>
            <label>
              Email
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoFocus
                autoComplete="email"
              />
            </label>
            <label>
              Password
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
            </label>
            {error && <p className="error" role="alert">{error}</p>}
            <button type="submit" disabled={busy}>
              {busy ? 'Logging in…' : 'Log in'}
            </button>
          </form>
        ) : (
          <UserForm submitLabel="Sign up" onSubmit={handleSignup} />
        )}

        <p className="switch">
          {mode === 'login' ? "Don't have an account? " : 'Already have an account? '}
          <button
            type="button"
            className="link"
            onClick={() => {
              setError(null)
              setMode(mode === 'login' ? 'signup' : 'login')
            }}
          >
            {mode === 'login' ? 'Sign up' : 'Log in'}
          </button>
        </p>
      </div>
    </main>
  )
}

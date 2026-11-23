import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { api, setAuthToken, setUnauthorizedHandler } from './api'
import { AUTH_MODE } from './config'
import { sessionFromToken } from './token'
import { AuthContext, useAuth } from './useAuth'
import type { Session } from './useAuth'

/*
 * Two ways to keep the user logged in (pick with VITE_AUTH_MODE, see config.ts):
 *
 *   localStorage                         cookie
 *   ------------                         ------
 *   login returns the JWT in JSON        login sets an HttpOnly cookie; JSON has no token
 *   we save it in localStorage           browser saves it; JS can't read it
 *   we send Authorization: Bearer ...    browser sends the cookie automatically
 *   on reload: decode the saved JWT      on reload: ask GET /me who we are
 *   logout: delete it from localStorage  logout: POST /logout so the server clears it
 */

const STORAGE_KEY = 'token'

type AuthState = { ready: boolean; session: Session | null }

function readStoredToken(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}

function initialState(): AuthState {
  if (AUTH_MODE === 'cookie') return { ready: false, session: null } // resolved by /me below
  const token = readStoredToken()
  const session = token ? sessionFromToken(token) : null
  // Hand the token to the API client now, not in an effect: child effects (like the
  // users page fetching data) run before this provider's effects would.
  setAuthToken(session ? token : null)
  return { ready: true, session }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [{ ready, session }, setState] = useState<AuthState>(initialState)

  // Cookie mode: we can't read the HttpOnly cookie, so ask the API who is logged in.
  useEffect(() => {
    if (AUTH_MODE !== 'cookie') return
    let active = true
    api
      .me()
      .then((me) => {
        if (active) {
          setState({
            ready: true,
            session: { userId: me.id, email: me.email, expiresAt: me.expires_at * 1000 },
          })
        }
      })
      .catch(() => active && setState({ ready: true, session: null }))
    return () => {
      active = false
    }
  }, [])

  const logout = useCallback(() => {
    if (AUTH_MODE === 'cookie') {
      void api.logout().catch(() => {}) // only the server can clear an HttpOnly cookie
    } else {
      try {
        localStorage.removeItem(STORAGE_KEY)
      } catch {
        /* storage unavailable: session still ends in memory */
      }
      setAuthToken(null)
    }
    setState({ ready: true, session: null })
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const res = await api.login(email, password)
    let next: Session | null
    if (AUTH_MODE === 'cookie') {
      // The cookie is already set by the response; we only keep who we are.
      next = { userId: res.user_id, email: res.email, expiresAt: Date.now() + res.expires_in * 1000 }
    } else {
      next = res.access_token ? sessionFromToken(res.access_token) : null
      if (!next || !res.access_token) throw new Error('Received an invalid token')
      try {
        localStorage.setItem(STORAGE_KEY, res.access_token)
      } catch {
        /* storage unavailable: stay logged in for this tab only */
      }
      setAuthToken(res.access_token)
    }
    setState({ ready: true, session: next })
  }, [])

  // Any 401 on a protected call (expired/revoked session) logs out.
  useEffect(() => setUnauthorizedHandler(logout), [logout])

  // Log out automatically when the token expires.
  useEffect(() => {
    if (!session) return
    const timer = setTimeout(logout, session.expiresAt - Date.now())
    return () => clearTimeout(timer)
  }, [session, logout])

  const value = useMemo(() => ({ ready, session, login, logout }), [ready, session, login, logout])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

/** Renders children only when logged in; otherwise redirects to /login. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { ready, session } = useAuth()
  const location = useLocation()
  if (!ready) return <p className="container muted">Loading…</p>
  if (!session) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  return children
}

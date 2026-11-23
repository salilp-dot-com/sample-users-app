import { createContext, useContext } from 'react'

export type Session = { userId: number; email: string; expiresAt: number }

export type AuthContextValue = {
  /** false until we know whether someone is logged in (cookie mode asks the API). */
  ready: boolean
  session: Session | null
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}

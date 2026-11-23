import type { Session } from './useAuth'

type Claims = { sub: string; email: string; exp: number }

/**
 * localStorage mode: read the JWT payload to learn who is logged in and until when.
 * No signature check is needed here because the API verifies every request.
 * (Note that any script on the page could do the same, which is the XSS risk.)
 * Returns null for malformed or expired tokens.
 */
export function sessionFromToken(token: string, now: number = Date.now()): Session | null {
  try {
    const payload = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
    const claims = JSON.parse(atob(payload)) as Claims
    const expiresAt = claims.exp * 1000
    if (!Number.isFinite(expiresAt) || expiresAt <= now) return null
    return { userId: Number(claims.sub), email: claims.email, expiresAt }
  } catch {
    return null
  }
}

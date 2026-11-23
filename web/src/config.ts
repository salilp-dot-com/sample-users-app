export const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

/**
 * Where the JWT lives after login. Set VITE_AUTH_MODE in web/.env.local and restart Vite.
 *
 * localStorage - the app stores the token and sends `Authorization: Bearer <jwt>`.
 *                Simple and explicit, but any script on the page (e.g. via XSS) can read it.
 * cookie       - the API sets an HttpOnly cookie that JavaScript can never read; the browser
 *                sends it automatically. Safer against XSS, but needs CSRF protection and a
 *                /me call to learn who is logged in.
 */
export type AuthMode = 'localStorage' | 'cookie'

export const AUTH_MODE: AuthMode =
  import.meta.env.VITE_AUTH_MODE === 'cookie' ? 'cookie' : 'localStorage'

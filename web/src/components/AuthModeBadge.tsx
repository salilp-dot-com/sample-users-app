import { AUTH_MODE } from '../config'

/** Shows which token storage is active, so it's visible while demoing both modes. */
export default function AuthModeBadge() {
  const cookie = AUTH_MODE === 'cookie'
  return (
    <span
      className="mode-badge"
      title={
        cookie
          ? 'JWT in an HttpOnly cookie: JavaScript cannot read it (DevTools → Application → Cookies)'
          : 'JWT in localStorage: readable by any script on the page (DevTools → Application → Local storage)'
      }
    >
      Token: {cookie ? 'HttpOnly cookie' : 'localStorage'}
    </span>
  )
}

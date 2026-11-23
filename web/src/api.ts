// Typed client for the FastAPI backend in ../api

import { API_URL, AUTH_MODE } from './config'

export type User = {
  id: number
  first_name: string
  last_name: string
  credit_card_number: string // masked by the API, e.g. "**** **** **** 1111"
  email: string
}

export type UserInput = {
  first_name: string
  last_name: string
  credit_card_number: string
  email: string
  password: string
}

export type LoginResponse = {
  access_token: string | null // null in cookie mode: the token is only in the HttpOnly cookie
  token_type: 'bearer' | 'cookie'
  expires_in: number // seconds
  user_id: number
  email: string
}

export type Me = {
  id: number
  email: string
  expires_at: number // Unix seconds
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

// localStorage mode only: the token AuthProvider gives us to send as a Bearer header.
let authToken: string | null = null
let onUnauthorized: () => void = () => {}

export function setAuthToken(token: string | null) {
  authToken = token
}

export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler
}

// A 401 from these just means "not logged in", not "session expired".
const AUTH_PATHS = ['/login', '/login?cookie=true', '/me', '/logout']

type ValidationIssue = { loc: (string | number)[]; msg: string }

// FastAPI errors are either {"detail": "text"} or {"detail": [{loc, msg}, ...]}.
function errorMessage(body: unknown, fallback: string): string {
  const detail = (body as { detail?: unknown } | null)?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return (detail as ValidationIssue[])
      .map((d) => {
        // ["body", "credit_card_number"] -> "Credit card number"
        const field = d.loc.filter((p) => p !== 'body').join(' ').replace(/_/g, ' ')
        const label = field.charAt(0).toUpperCase() + field.slice(1)
        const msg = d.msg.replace(/^Value error, /, '')
        return label ? `${label}: ${msg}` : msg
      })
      .join('\n')
  }
  return fallback
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'

  if (AUTH_MODE === 'localStorage') {
    // We hold the token, so we attach it ourselves.
    if (authToken) headers['Authorization'] = `Bearer ${authToken}`
  } else {
    // The browser attaches the cookie. This header proves the request came from our
    // own JavaScript, not a form on another site (the API's CSRF check).
    headers['X-Requested-With'] = 'fetch'
  }

  let res: Response
  try {
    res = await fetch(`${API_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      // Cookie mode: send and accept cookies on this cross-origin (5173 -> 8000) request.
      credentials: AUTH_MODE === 'cookie' ? 'include' : 'same-origin',
    })
  } catch {
    throw new ApiError(0, `Cannot reach the API at ${API_URL}. Is it running?`)
  }

  if (res.status === 204) return undefined as T
  const data = await res.json().catch(() => null)
  if (!res.ok) {
    // An expired/invalid session on a protected call: drop it.
    if (res.status === 401 && !AUTH_PATHS.includes(path)) onUnauthorized()
    throw new ApiError(res.status, errorMessage(data, `${res.status} ${res.statusText}`))
  }
  return data as T
}

export const api = {
  login: (email: string, password: string) =>
    request<LoginResponse>(
      'POST',
      AUTH_MODE === 'cookie' ? '/login?cookie=true' : '/login',
      { email, password },
    ),
  me: () => request<Me>('GET', '/me'),
  logout: () => request<void>('POST', '/logout'),
  listUsers: () => request<User[]>('GET', '/users'),
  getUser: (id: number) => request<User>('GET', `/users/${id}`),
  createUser: (input: UserInput) => request<User>('POST', '/users', input),
  replaceUser: (id: number, input: UserInput) => request<User>('PUT', `/users/${id}`, input),
  updateUser: (id: number, changes: Partial<UserInput>) =>
    request<User>('PATCH', `/users/${id}`, changes),
  deleteUser: (id: number) => request<void>('DELETE', `/users/${id}`),
}

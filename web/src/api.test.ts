import { describe, expect, it, vi } from 'vitest'
import { api, errorMessage, setAuthToken, setUnauthorizedHandler } from './api'
import { jsonResponse, mockFetch } from './test/helpers'

describe('errorMessage', () => {
  it('passes through a plain detail string', () => {
    expect(errorMessage({ detail: 'Email is already registered' }, 'x')).toBe(
      'Email is already registered',
    )
  })

  it('turns FastAPI validation errors into readable lines', () => {
    const body = {
      detail: [
        { loc: ['body', 'credit_card_number'], msg: 'Value error, must be 12-19 digits' },
        { loc: ['body', 'password'], msg: 'String should have at least 8 characters' },
      ],
    }
    expect(errorMessage(body, 'x')).toBe(
      'Credit card number: must be 12-19 digits\nPassword: String should have at least 8 characters',
    )
  })

  it('falls back when the body has no detail', () => {
    expect(errorMessage(null, '500 Internal Server Error')).toBe('500 Internal Server Error')
  })
})

describe('request (localStorage mode)', () => {
  it('sends the bearer token and no cookies', async () => {
    const fetchMock = mockFetch([
      { method: 'GET', path: '/users', respond: () => jsonResponse(200, []) },
    ])
    setAuthToken('abc.def.ghi')
    await api.listUsers()
    const init = fetchMock.mock.calls[0][1] as RequestInit
    expect(init.headers).toMatchObject({ Authorization: 'Bearer abc.def.ghi' })
    expect(init.credentials).toBe('same-origin')
    setAuthToken(null)
  })

  it('calls the unauthorized handler on a 401 from a protected endpoint', async () => {
    mockFetch([
      {
        method: 'GET',
        path: '/users',
        respond: () => jsonResponse(401, { detail: 'Invalid or expired token' }),
      },
    ])
    const onUnauthorized = vi.fn()
    setUnauthorizedHandler(onUnauthorized)
    await expect(api.listUsers()).rejects.toMatchObject({
      status: 401,
      message: 'Invalid or expired token',
    })
    expect(onUnauthorized).toHaveBeenCalledOnce()
  })

  it('does not log out on a failed login attempt', async () => {
    mockFetch([
      {
        method: 'POST',
        path: '/login',
        respond: () => jsonResponse(401, { detail: 'Invalid email or password' }),
      },
    ])
    const onUnauthorized = vi.fn()
    setUnauthorizedHandler(onUnauthorized)
    await expect(api.login('a@example.com', 'nope')).rejects.toThrow('Invalid email or password')
    expect(onUnauthorized).not.toHaveBeenCalled()
  })

  it('explains when the API is unreachable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    await expect(api.listUsers()).rejects.toThrow(/Cannot reach the API/)
  })
})

describe('request (cookie mode)', () => {
  it('includes cookies, sends the CSRF header and logs in with ?cookie=true', async () => {
    // AUTH_MODE is read when the module loads, so load a fresh copy with the env stubbed.
    vi.stubEnv('VITE_AUTH_MODE', 'cookie')
    vi.resetModules()
    const { api: cookieApi } = await import('./api')

    const fetchMock = mockFetch([
      {
        method: 'POST',
        path: '/login?cookie=true',
        respond: () =>
          jsonResponse(200, {
            access_token: null,
            token_type: 'cookie',
            expires_in: 3600,
            user_id: 1,
            email: 'a@example.com',
          }),
      },
    ])
    await cookieApi.login('a@example.com', 'pw')
    const init = fetchMock.mock.calls[0][1] as RequestInit
    expect(init.credentials).toBe('include')
    expect(init.headers).toMatchObject({ 'X-Requested-With': 'fetch' })
    expect(init.headers).not.toHaveProperty('Authorization')
  })
})

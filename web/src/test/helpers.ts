import { vi } from 'vitest'

/** Build an unsigned JWT-shaped string with the given payload (the client never verifies). */
export function fakeJwt(payload: Record<string, unknown>): string {
  const b64url = (o: unknown) =>
    btoa(JSON.stringify(o)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
  return `${b64url({ alg: 'HS256', typ: 'JWT' })}.${b64url(payload)}.signature`
}

export function jsonResponse(status: number, body?: unknown): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

type Route = { method: string; path: string; respond: () => Response }

/** Replace global fetch with a tiny router; unmatched requests fail the test loudly. */
export function mockFetch(routes: Route[]) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input))
    const method = init?.method ?? 'GET'
    const route = routes.find((r) => r.method === method && r.path === url.pathname + url.search)
    if (!route) throw new Error(`Unexpected request: ${method} ${url.pathname}${url.search}`)
    return route.respond()
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

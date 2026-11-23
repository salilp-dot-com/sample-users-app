import { describe, expect, it } from 'vitest'
import { fakeJwt } from './test/helpers'
import { sessionFromToken } from './token'

const NOW = Date.UTC(2026, 0, 1)

describe('sessionFromToken', () => {
  it('reads user id, email and expiry from the payload', () => {
    const exp = NOW / 1000 + 3600
    const token = fakeJwt({ sub: '42', email: 'ada@example.com', exp })
    expect(sessionFromToken(token, NOW)).toEqual({
      userId: 42,
      email: 'ada@example.com',
      expiresAt: exp * 1000,
    })
  })

  it('rejects an expired token', () => {
    const token = fakeJwt({ sub: '1', email: 'a@example.com', exp: NOW / 1000 - 1 })
    expect(sessionFromToken(token, NOW)).toBeNull()
  })

  it.each(['', 'not-a-jwt', 'a.b.c', fakeJwt({ sub: '1' })])('rejects malformed %j', (token) => {
    expect(sessionFromToken(token, NOW)).toBeNull()
  })
})

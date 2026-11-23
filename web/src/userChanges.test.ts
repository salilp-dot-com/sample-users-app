import { describe, expect, it } from 'vitest'
import type { User, UserInput } from './api'
import { changedFields } from './userChanges'

const user: User = {
  id: 1,
  first_name: 'Ada',
  last_name: 'Lovelace',
  email: 'ada@example.com',
  credit_card_number: '**** **** **** 1111',
}

const unchanged: UserInput = {
  first_name: 'Ada',
  last_name: 'Lovelace',
  email: 'ada@example.com',
  credit_card_number: '',
  password: '',
}

describe('changedFields', () => {
  it('returns nothing when nothing changed', () => {
    expect(changedFields(user, unchanged)).toEqual({})
  })

  it('returns only the edited fields', () => {
    expect(changedFields(user, { ...unchanged, last_name: 'King' })).toEqual({ last_name: 'King' })
  })

  it('treats blank card and password as "keep current"', () => {
    const values = { ...unchanged, credit_card_number: '5500000000000004', password: 'new-pass-1' }
    expect(changedFields(user, values)).toEqual({
      credit_card_number: '5500000000000004',
      password: 'new-pass-1',
    })
  })
})

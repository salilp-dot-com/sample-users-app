import type { User, UserInput } from './api'

/** For PATCH: only the fields that changed. Blank card/password mean "keep current". */
export function changedFields(user: User, values: UserInput): Partial<UserInput> {
  const changes: Partial<UserInput> = {}
  if (values.first_name !== user.first_name) changes.first_name = values.first_name
  if (values.last_name !== user.last_name) changes.last_name = values.last_name
  if (values.email !== user.email) changes.email = values.email
  if (values.credit_card_number) changes.credit_card_number = values.credit_card_number
  if (values.password) changes.password = values.password
  return changes
}

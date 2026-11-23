import { useState } from 'react'
import type { FormEvent } from 'react'
import type { User, UserInput } from '../api'

type Props = {
  /** When set, the form edits this user: blank card/password mean "keep current". */
  user?: User
  submitLabel: string
  onSubmit: (values: UserInput) => Promise<void>
  onCancel?: () => void
}

const empty: UserInput = {
  first_name: '',
  last_name: '',
  email: '',
  credit_card_number: '',
  password: '',
}

export default function UserForm({ user, submitLabel, onSubmit, onCancel }: Props) {
  const editing = user !== undefined
  const [values, setValues] = useState<UserInput>(
    user
      ? { ...empty, first_name: user.first_name, last_name: user.last_name, email: user.email }
      : empty,
  )
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const set = (field: keyof UserInput) => (e: { target: { value: string } }) =>
    setValues((v) => ({ ...v, [field]: e.target.value }))

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      await onSubmit(values)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="form" onSubmit={handleSubmit}>
      <div className="row">
        <label>
          First name
          <input value={values.first_name} onChange={set('first_name')} required maxLength={100} />
        </label>
        <label>
          Last name
          <input value={values.last_name} onChange={set('last_name')} required maxLength={100} />
        </label>
      </div>
      <label>
        Email
        <input type="email" value={values.email} onChange={set('email')} required autoComplete="email" />
      </label>
      <label>
        Credit card number
        <input
          value={values.credit_card_number}
          onChange={set('credit_card_number')}
          required={!editing}
          inputMode="numeric"
          autoComplete="cc-number"
          placeholder={editing ? `Current: ${user.credit_card_number} (leave blank to keep)` : '4111 1111 1111 1111'}
        />
      </label>
      <label>
        Password
        <input
          type="password"
          value={values.password}
          onChange={set('password')}
          required={!editing}
          minLength={8}
          autoComplete="new-password"
          placeholder={editing ? 'Leave blank to keep current password' : 'At least 8 characters'}
        />
      </label>

      {error && <p className="error" role="alert">{error}</p>}

      <div className="actions">
        {onCancel && (
          <button type="button" className="secondary" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
        )}
        <button type="submit" disabled={busy}>
          {busy ? 'Saving…' : submitLabel}
        </button>
      </div>
    </form>
  )
}

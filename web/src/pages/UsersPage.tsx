import { useEffect, useState } from 'react'
import { api } from '../api'
import type { User, UserInput } from '../api'
import { useAuth } from '../useAuth'
import AuthModeBadge from '../components/AuthModeBadge'
import UserForm from '../components/UserForm'

// Which form is open: none, "new user", or editing a specific user.
type Editor = { kind: 'closed' } | { kind: 'create' } | { kind: 'edit'; user: User }

// For PATCH: send only fields that changed; blank card/password mean "keep".
function changedFields(user: User, values: UserInput): Partial<UserInput> {
  const changes: Partial<UserInput> = {}
  if (values.first_name !== user.first_name) changes.first_name = values.first_name
  if (values.last_name !== user.last_name) changes.last_name = values.last_name
  if (values.email !== user.email) changes.email = values.email
  if (values.credit_card_number) changes.credit_card_number = values.credit_card_number
  if (values.password) changes.password = values.password
  return changes
}

export default function UsersPage() {
  const { session, logout } = useAuth()
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [editor, setEditor] = useState<Editor>({ kind: 'closed' })

  useEffect(() => {
    let active = true // ignore the result if the page unmounted meanwhile
    api
      .listUsers()
      .then((list) => active && setUsers(list))
      .catch((err) => active && setError(err instanceof Error ? err.message : String(err)))
      .finally(() => active && setLoading(false))
    return () => {
      active = false
    }
  }, [])

  function flash(message: string) {
    setNotice(message)
    setTimeout(() => setNotice(null), 3000)
  }

  async function handleCreate(values: UserInput) {
    const created = await api.createUser(values)
    setUsers((list) => [...list, created])
    setEditor({ kind: 'closed' })
    flash(`Created ${created.first_name} ${created.last_name}`)
  }

  async function handleEdit(user: User, values: UserInput) {
    const changes = changedFields(user, values)
    if (Object.keys(changes).length === 0) {
      setEditor({ kind: 'closed' })
      return
    }
    const updated = await api.updateUser(user.id, changes)
    setUsers((list) => list.map((u) => (u.id === updated.id ? updated : u)))
    setEditor({ kind: 'closed' })
    flash(`Saved ${updated.first_name} ${updated.last_name}`)
  }

  async function handleDelete(user: User) {
    const isSelf = user.id === session?.userId
    const prompt = isSelf
      ? 'Delete your own account? You will be logged out.'
      : `Delete ${user.first_name} ${user.last_name} (${user.email})?`
    if (!window.confirm(prompt)) return
    try {
      await api.deleteUser(user.id)
      if (isSelf) return logout()
      setUsers((list) => list.filter((u) => u.id !== user.id))
      if (editor.kind === 'edit' && editor.user.id === user.id) setEditor({ kind: 'closed' })
      flash(`Deleted ${user.first_name} ${user.last_name}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  return (
    <>
      <header className="topbar">
        <strong>Sample Users App</strong>
        <AuthModeBadge />
        <span className="spacer" />
        <span className="muted">{session?.email}</span>
        <button className="secondary" onClick={logout}>
          Log out
        </button>
      </header>

      <main className="container">
        <div className="page-head">
          <h1>Users</h1>
          {editor.kind === 'closed' && (
            <button onClick={() => setEditor({ kind: 'create' })}>+ New user</button>
          )}
        </div>

        {notice && <p className="notice" role="status">{notice}</p>}
        {error && <p className="error" role="alert">{error}</p>}

        {editor.kind !== 'closed' && (
          <section className="card">
            <h2>
              {editor.kind === 'create'
                ? 'New user'
                : `Edit ${editor.user.first_name} ${editor.user.last_name}`}
            </h2>
            {editor.kind === 'create' ? (
              <UserForm
                submitLabel="Create user"
                onSubmit={handleCreate}
                onCancel={() => setEditor({ kind: 'closed' })}
              />
            ) : (
              <UserForm
                key={editor.user.id}
                user={editor.user}
                submitLabel="Save changes"
                onSubmit={(values) => handleEdit(editor.user, values)}
                onCancel={() => setEditor({ kind: 'closed' })}
              />
            )}
          </section>
        )}

        {loading ? (
          <p className="muted">Loading…</p>
        ) : users.length === 0 ? (
          <p className="muted">No users yet.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Card</th>
                  <th aria-label="Actions" />
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td className="muted">{u.id}</td>
                    <td>
                      {u.first_name} {u.last_name}
                      {u.id === session?.userId && <span className="badge">you</span>}
                    </td>
                    <td>{u.email}</td>
                    <td className="mono">{u.credit_card_number}</td>
                    <td className="row-actions">
                      <button className="secondary" onClick={() => setEditor({ kind: 'edit', user: u })}>
                        Edit
                      </button>
                      <button className="danger" onClick={() => handleDelete(u)}>
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </>
  )
}

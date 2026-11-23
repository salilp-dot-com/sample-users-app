import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { AuthProvider } from '../auth'
import { fakeJwt, jsonResponse, mockFetch } from '../test/helpers'
import LoginPage from './LoginPage'

function renderLogin() {
  render(
    <MemoryRouter initialEntries={['/login']}>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/users" element={<h1>Users page</h1>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  )
}

function submitLogin(email: string, password: string) {
  fireEvent.change(screen.getByLabelText('Email'), { target: { value: email } })
  fireEvent.change(screen.getByLabelText('Password'), { target: { value: password } })
  fireEvent.click(screen.getByRole('button', { name: 'Log in' }))
}

describe('LoginPage (localStorage mode)', () => {
  it('shows the API error for bad credentials', async () => {
    mockFetch([
      {
        method: 'POST',
        path: '/login',
        respond: () => jsonResponse(401, { detail: 'Invalid email or password' }),
      },
    ])
    renderLogin()
    submitLogin('ada@example.com', 'wrong')
    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid email or password')
    expect(localStorage.getItem('token')).toBeNull()
  })

  it('stores the token and goes to the users page on success', async () => {
    const token = fakeJwt({ sub: '1', email: 'ada@example.com', exp: Date.now() / 1000 + 3600 })
    mockFetch([
      {
        method: 'POST',
        path: '/login',
        respond: () =>
          jsonResponse(200, {
            access_token: token,
            token_type: 'bearer',
            expires_in: 3600,
            user_id: 1,
            email: 'ada@example.com',
          }),
      },
    ])
    renderLogin()
    submitLogin('ada@example.com', 'correct-pass')
    expect(await screen.findByRole('heading', { name: 'Users page' })).toBeInTheDocument()
    expect(localStorage.getItem('token')).toBe(token)
  })
})

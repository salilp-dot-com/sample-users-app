import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { User } from '../api'
import UserForm from './UserForm'

const user: User = {
  id: 7,
  first_name: 'Ada',
  last_name: 'Lovelace',
  email: 'ada@example.com',
  credit_card_number: '**** **** **** 1111',
}

function fill(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } })
}

describe('UserForm', () => {
  it('requires card and password when creating', () => {
    render(<UserForm submitLabel="Create user" onSubmit={vi.fn()} />)
    expect(screen.getByLabelText('Credit card number')).toBeRequired()
    expect(screen.getByLabelText('Password')).toBeRequired()
  })

  it('prefills an existing user and makes card/password optional when editing', () => {
    render(<UserForm user={user} submitLabel="Save changes" onSubmit={vi.fn()} />)
    expect(screen.getByLabelText('First name')).toHaveValue('Ada')
    expect(screen.getByLabelText('Email')).toHaveValue('ada@example.com')
    expect(screen.getByLabelText('Credit card number')).not.toBeRequired()
    expect(screen.getByLabelText('Credit card number')).toHaveAttribute(
      'placeholder',
      expect.stringContaining('1111'),
    )
    expect(screen.getByLabelText('Password')).not.toBeRequired()
  })

  it('submits the entered values', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined)
    render(<UserForm submitLabel="Create user" onSubmit={onSubmit} />)
    fill('First name', 'Grace')
    fill('Last name', 'Hopper')
    fill('Email', 'grace@example.com')
    fill('Credit card number', '4111 1111 1111 1111')
    fill('Password', 'secret-pass')
    fireEvent.click(screen.getByRole('button', { name: 'Create user' }))
    await vi.waitFor(() => expect(onSubmit).toHaveBeenCalledOnce())
    expect(onSubmit).toHaveBeenCalledWith({
      first_name: 'Grace',
      last_name: 'Hopper',
      email: 'grace@example.com',
      credit_card_number: '4111 1111 1111 1111',
      password: 'secret-pass',
    })
  })

  it('shows the error when saving fails', async () => {
    const onSubmit = vi.fn().mockRejectedValue(new Error('Email is already registered'))
    render(<UserForm user={user} submitLabel="Save changes" onSubmit={onSubmit} />)
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Email is already registered')
  })
})

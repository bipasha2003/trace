/**
 * TRACE — Login Page
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import './LoginPage.css'

export default function LoginPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    // TODO: integrate with POST /api/v1/auth/login
    console.log('Login:', { email, password })
    navigate('/dashboard')
  }

  return (
    <div className="login-page">
      <div className="login-card glass-card animate-fade-in">
        <div className="login-card__brand">
          <div className="login-card__logo">T</div>
          <h1 className="login-card__title gradient-text">TRACE</h1>
          <p className="login-card__subtitle">
            Task &amp; Resource Attendance and Comprehensive Evaluation
          </p>
        </div>

        <form className="login-form" onSubmit={handleSubmit} id="login-form">
          <div className="login-form__group">
            <label className="login-form__label" htmlFor="login-email">
              Email Address
            </label>
            <input
              className="input"
              id="login-email"
              type="email"
              placeholder="admin@trace.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="login-form__group">
            <label className="login-form__label" htmlFor="login-password">
              Password
            </label>
            <input
              className="input"
              id="login-password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <button type="submit" className="btn btn--primary login-form__submit" id="login-submit">
            Sign In
          </button>
        </form>
      </div>
    </div>
  )
}

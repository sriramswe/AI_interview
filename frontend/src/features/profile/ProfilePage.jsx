import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useInterviewApp } from '../../context/useInterviewApp'
import { getApiError } from '../../services/apiClient'
import { changePassword } from '../../services/authService'
import { DASHBOARD_PATH } from '../../routing/routes'

export default function ProfilePage() {
  const {
    busy,
    handleHome,
    handleLogout,
    handleProfileUpdate,
    paymentStatus,
    profile,
    stats,
    subscription,
    token,
  } = useInterviewApp()
  const [username, setUsername] = useState(profile?.username || '')
  const [email, setEmail] = useState(profile?.email || '')
  const [gender, setGender] = useState(profile?.gender || '')
  const [profileErrors, setProfileErrors] = useState({})
  const [profileError, setProfileError] = useState('')
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordBusy, setPasswordBusy] = useState(false)
  const [passwordMessage, setPasswordMessage] = useState('')
  const [passwordError, setPasswordError] = useState('')

  const saveProfile = async (event) => {
    event.preventDefault()
    setProfileErrors({})
    setProfileError('')
    const trimmedUsername = username.trim()
    const trimmedEmail = email.trim()
    const errors = {}
    if (!trimmedUsername) errors.username = 'Enter your display name.'
    if (trimmedUsername.length > 80) errors.username = 'Display name must be 80 characters or fewer.'
    if (!trimmedEmail) {
      errors.email = 'Enter your email address.'
    } else if (
      trimmedEmail.length > 120
      || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)
    ) {
      errors.email = 'Enter a valid email address (maximum 120 characters).'
    }
    if (Object.keys(errors).length > 0) {
      setProfileErrors(errors)
      return
    }

    const saved = await handleProfileUpdate({
      username: trimmedUsername,
      email: trimmedEmail,
      gender: gender || null,
    })
    if (!saved) setProfileError('Profile changes could not be saved. Review the error above and try again.')
  }

  const savePassword = async (event) => {
    event.preventDefault()
    setPasswordMessage('')
    setPasswordError('')
    const errors = {}
    if (!currentPassword) errors.currentPassword = 'Enter your current password.'
    if (newPassword.length < 6 || newPassword.length > 128) {
      errors.newPassword = 'New password must be between 6 and 128 characters.'
    }
    if (newPassword === currentPassword) {
      errors.newPassword = 'Choose a new password that differs from your current password.'
    }
    if (newPassword !== confirmPassword) {
      errors.confirmPassword = 'New password and confirmation do not match.'
    }
    if (Object.keys(errors).length > 0) {
      setPasswordError(Object.values(errors)[0])
      return
    }

    setPasswordBusy(true)
    try {
      const result = await changePassword({ token, currentPassword, newPassword })
      setPasswordMessage(result.message)
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (error) {
      setPasswordError(getApiError(error, 'Could not change your password.'))
    } finally {
      setPasswordBusy(false)
    }
  }

  return (
    <main className="page-shell">
      <header className="topbar">
        <Link className="brand" onClick={handleHome} to={DASHBOARD_PATH}>
          <span className="brand-mark">IA</span> InterviewAI
        </Link>
        <nav aria-label="Profile navigation" className="account">
          <Link className="text-button" onClick={handleHome} to={DASHBOARD_PATH}>Home</Link>
          <button className="text-button" onClick={handleLogout} type="button">Sign out</button>
        </nav>
      </header>
      <section className="hero-card profile-hero">
        <div>
          <p className="eyebrow">Candidate account</p>
          <h1>Your profile</h1>
          <p className="muted">Manage the account details used across your InterviewAI sessions.</p>
        </div>
        <div aria-hidden="true" className="hero-orb">{profile?.username?.slice(0, 1).toUpperCase() || 'IA'}</div>
      </section>
      <div className="profile-grid">
        <section className="panel">
          <p className="eyebrow">Personal information</p>
          <h2>Account details</h2>
          <form className="stack-form" noValidate onSubmit={saveProfile}>
            <label>
              Display name
              <input
                aria-describedby={profileErrors.username ? 'profile-username-error' : undefined}
                aria-invalid={Boolean(profileErrors.username)}
                autoComplete="name"
                maxLength={80}
                onChange={(event) => {
                  setUsername(event.target.value)
                  setProfileErrors((current) => ({ ...current, username: '' }))
                  setProfileError('')
                }}
                value={username}
              />
              {profileErrors.username && <small className="field-error" id="profile-username-error">{profileErrors.username}</small>}
            </label>
            <label>
              Email address
              <input
                aria-describedby={profileErrors.email ? 'profile-email-error' : undefined}
                aria-invalid={Boolean(profileErrors.email)}
                autoComplete="email"
                maxLength={120}
                onChange={(event) => {
                  setEmail(event.target.value)
                  setProfileErrors((current) => ({ ...current, email: '' }))
                  setProfileError('')
                }}
                type="email"
                value={email}
              />
              {profileErrors.email && <small className="field-error" id="profile-email-error">{profileErrors.email}</small>}
            </label>
            <label>
              Gender <span className="muted">(optional)</span>
              <select
                onChange={(event) => setGender(event.target.value)}
                value={gender}
              >
                <option value="">Prefer not to say</option>
                <option value="female">Female</option>
                <option value="male">Male</option>
                <option value="non_binary">Non-binary</option>
                <option value="prefer_not_to_say">Prefer not to say</option>
              </select>
            </label>
            {paymentStatus && <p className="notice" role="status">{paymentStatus}</p>}
            {profileError && <p className="notice error" role="alert">{profileError}</p>}
            <button className="button primary" disabled={busy} type="submit">
              {busy ? 'Saving…' : 'Save changes'}
            </button>
          </form>
        </section>
        <section className="panel">
          <p className="eyebrow">Account security</p>
          <h2>Change password</h2>
          <form className="stack-form" noValidate onSubmit={savePassword}>
            <label>
              Current password
              <input
                autoComplete="current-password"
                maxLength={128}
                onChange={(event) => setCurrentPassword(event.target.value)}
                type="password"
                value={currentPassword}
              />
            </label>
            <label>
              New password
              <input
                autoComplete="new-password"
                maxLength={128}
                onChange={(event) => setNewPassword(event.target.value)}
                type="password"
                value={newPassword}
              />
            </label>
            <label>
              Confirm new password
              <input
                autoComplete="new-password"
                maxLength={128}
                onChange={(event) => setConfirmPassword(event.target.value)}
                type="password"
                value={confirmPassword}
              />
            </label>
            {passwordError && <p className="notice error" role="alert">{passwordError}</p>}
            {passwordMessage && <p className="notice" role="status">{passwordMessage}</p>}
            <button className="button primary" disabled={passwordBusy} type="submit">
              {passwordBusy ? 'Updating…' : 'Update password'}
            </button>
          </form>
        </section>
        <aside className="side-stack">
          <section className="panel">
            <p className="eyebrow">Practice snapshot</p>
            <h2>Your progress</h2>
            <div className="profile-metrics">
              <div><span>Interviews</span><strong>{stats.total_interviews || 0}</strong></div>
              <div><span>Average score</span><strong>{Number(stats.avg_score || 0).toFixed(1)}</strong></div>
            </div>
          </section>
          <section className="panel">
            <p className="eyebrow">Plan</p>
            <p className="muted">Account role: {profile?.role || 'user'}</p>
            <h2>
              {subscription?.plan === 'legacy_resume'
                ? 'Legacy resume membership'
                : `${subscription?.plan || 'Free'} membership`}
            </h2>
            <p className="muted">Your current subscription and available interview features.</p>
            <Link className="button secondary full-width profile-home-link" onClick={handleHome} to={DASHBOARD_PATH}>
              Manage plan on home
            </Link>
          </section>
        </aside>
      </div>
      <footer className="footer-note">Your account information is private to your authenticated session.</footer>
    </main>
  )
}

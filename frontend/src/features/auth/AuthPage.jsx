import { useEffect, useState } from 'react'
import { Eye, EyeOff } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useInterviewApp } from '../../context/useInterviewApp'
import { GOOGLE_CLIENT_ID } from '../../services/apiClient'
import { DASHBOARD_PATH } from '../../routing/routes'

const GOOGLE_STATE_KEY = '__interviewAiGoogleState'

function getGoogleState() {
  window[GOOGLE_STATE_KEY] ??= {
    credentialHandler: null,
    initializedClientId: null,
    scriptPromise: null,
  }
  return window[GOOGLE_STATE_KEY]
}

function loadGoogleIdentity(state) {
  const googleIdentity = window.google?.accounts?.id
  if (googleIdentity) return Promise.resolve(googleIdentity)
  if (state.scriptPromise) return state.scriptPromise

  state.scriptPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = 'https://accounts.google.com/gsi/client'
    script.async = true
    script.onload = () => {
      const identity = window.google?.accounts?.id
      if (identity) resolve(identity)
      else reject(new Error('Google sign-in could not be initialized.'))
    }
    script.onerror = () => {
      state.scriptPromise = null
      reject(new Error('Could not load Google sign-in.'))
    }
    document.head.append(script)
  })

  return state.scriptPromise
}

export default function AuthPage() {
  const [showPassword, setShowPassword] = useState(false)
  const {
    authError,
    authForm,
    authMode,
    busy,
    changeAuthMode,
    handleAuthChange,
    handleAuthSubmit,
    handleGoogleCredential,
    profile,
    token,
  } = useInterviewApp()
  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) return undefined
    let active = true
    const googleState = getGoogleState()
    googleState.credentialHandler = handleGoogleCredential

    loadGoogleIdentity(googleState).then((googleIdentity) => {
      if (!active) return
      if (googleState.initializedClientId !== GOOGLE_CLIENT_ID) {
        googleIdentity.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: ({ credential }) => {
            const onCredential = googleState.credentialHandler
            if (!credential) {
              onCredential?.(null, 'Google did not return a sign-in credential.')
              return
            }
            onCredential?.(credential)
          },
        })
        googleState.initializedClientId = GOOGLE_CLIENT_ID
      }

      const buttonContainer = document.getElementById('google-sign-in')
      if (buttonContainer) {
        buttonContainer.replaceChildren()
        googleIdentity.renderButton(buttonContainer, {
          theme: 'outline',
          size: 'large',
          text: 'continue_with',
          width: Math.max(200, Math.min(320, buttonContainer.clientWidth)),
        })
      }
    }).catch((error) => {
      if (active) handleGoogleCredential(null, error.message)
    })

    return () => {
      active = false
      if (googleState.credentialHandler === handleGoogleCredential) {
        googleState.credentialHandler = null
      }
    }
  }, [handleGoogleCredential])

  const homeDestination = token && profile ? DASHBOARD_PATH : '/'

  return (
    <main className="page-shell auth-page">
      <header className="auth-header">
        <Link aria-label="InterviewAI home" className="landing-brand" to={homeDestination}>
          <span className="brand-mark">IA</span>
          <span>InterviewAI</span>
        </Link>
        <nav aria-label="Account navigation" className="auth-header-nav">
          <Link className="auth-header-link" to="/#how-it-works">How it works</Link>
          <Link className="auth-header-home" to={homeDestination}>
            {token && profile ? 'Dashboard' : 'Back to home'}
          </Link>
        </nav>
      </header>
      <div className="auth-shell">
        <section className="auth-card">
          <div className="brand-mark">IA</div>
          <p className="eyebrow">InterviewAI · Practice studio</p>
          <h1>Prepare with purpose.</h1>
          <p className="muted">Practice role-specific interviews and review clear, evidence-based feedback.</p>
          <form className="stack-form" onSubmit={handleAuthSubmit}>
            {authMode === 'register' && (
              <label>
                Name
                <input
                  required
                  value={authForm.username}
                  onChange={(event) => handleAuthChange('username', event.target.value)}
                />
              </label>
            )}
            {authMode === 'register' && (
              <label>
                Gender <span className="muted">(optional)</span>
                <select
                  value={authForm.gender}
                  onChange={(event) => handleAuthChange('gender', event.target.value)}
                >
                  <option value="">Select an option</option>
                  <option value="female">Female</option>
                  <option value="male">Male</option>
                  <option value="non_binary">Non-binary</option>
                  <option value="prefer_not_to_say">Prefer not to say</option>
                </select>
              </label>
            )}
            <label>
              Email
              <input
                required
                type="email"
                autoComplete="email"
                value={authForm.email}
                onChange={(event) => handleAuthChange('email', event.target.value)}
              />
            </label>
            <label>
              Password
              <span className="password-input-wrap">
                <input
                  required
                  minLength={authMode === 'register' ? 6 : 1}
                  type={showPassword ? 'text' : 'password'}
                  autoComplete={authMode === 'login' ? 'current-password' : 'new-password'}
                  value={authForm.password}
                  onChange={(event) => handleAuthChange('password', event.target.value)}
                />
                <button
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  aria-pressed={showPassword}
                  className="password-visibility-button"
                  onClick={() => setShowPassword((visible) => !visible)}
                  type="button"
                >
                  {showPassword ? <EyeOff aria-hidden="true" size={18} /> : <Eye aria-hidden="true" size={18} />}
                </button>
              </span>
            </label>
            {authError && <p className="notice error" role="alert">{authError}</p>}
            <button className="button primary full-width" disabled={busy} type="submit">
              {busy ? 'Please wait…' : authMode === 'login' ? 'Sign in' : 'Create account'}
            </button>
          </form>
          {GOOGLE_CLIENT_ID && <div className="google-sign-in" id="google-sign-in" />}
          <button className="text-button" onClick={changeAuthMode} type="button">
            {authMode === 'login' ? 'New here? Create an account' : 'Already registered? Sign in'}
          </button>
        </section>
      </div>
    </main>
  )
}

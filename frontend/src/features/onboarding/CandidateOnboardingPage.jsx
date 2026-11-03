import { ArrowRight, GraduationCap, BriefcaseBusiness, Sparkles } from 'lucide-react'
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { useState } from 'react'
import { useInterviewApp } from '../../context/useInterviewApp'
import { DASHBOARD_PATH, LOGIN_PATH, REGISTER_PATH } from '../../routing/routes'
import TargetRoleField from '../interview/TargetRoleField'

const INITIAL_PROFILE = {
  employment_status: 'college_student',
  education_level: '',
  institution: '',
  field_of_study: '',
  current_role: '',
  years_of_experience: '',
}

export default function CandidateOnboardingPage() {
  const { profile: account, token } = useInterviewApp()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const requestedPlan = searchParams.get('plan')
  const [candidate, setCandidate] = useState(INITIAL_PROFILE)
  const [role, setRole] = useState('')
  const [subRole, setSubRole] = useState('')
  const [accessPlan, setAccessPlan] = useState(
    () => ['pro', 'elite'].includes(requestedPlan) ? requestedPlan : 'free',
  )
  const [error, setError] = useState('')

  if (token && account) return <Navigate replace to={DASHBOARD_PATH} />

  const update = (field, value) => setCandidate((current) => ({ ...current, [field]: value }))
  const continueToAccount = (event) => {
    event.preventDefault()
    if (!role.trim()) {
      setError('Enter the role you want to practice for.')
      return
    }
    const draft = {
      candidateProfile: {
        ...candidate,
        years_of_experience: candidate.years_of_experience === ''
          ? null
          : Number(candidate.years_of_experience),
      },
      role: role.trim(),
      subRole: subRole.trim() || role.trim(),
      accessPlan,
    }
    localStorage.setItem('interview_setup_draft', JSON.stringify(draft))
    navigate(REGISTER_PATH)
  }

  return (
    <main className="page-shell onboarding-page">
      <header className="auth-header">
        <Link aria-label="InterviewAI home" className="landing-brand" to="/">
          <span className="brand-mark">IA</span><span>InterviewAI</span>
        </Link>
        <nav aria-label="Account navigation" className="auth-header-nav">
          <span>Already have an account?</span>
          <Link className="auth-header-home" to={LOGIN_PATH}>Sign in</Link>
        </nav>
      </header>
      <section aria-labelledby="onboarding-title" className="panel onboarding-card">
        <p className="eyebrow"><Sparkles aria-hidden="true" size={15} /> Your practice setup · Step 1 of 2</p>
        <h1 id="onboarding-title">Tell us where you’re starting from.</h1>
        <p className="muted">
          We’ll use your education and experience stage to keep questions relevant. This is for interview practice, not job applications.
        </p>
        <form className="stack-form onboarding-form" onSubmit={continueToAccount}>
          <label>
            Current stage
            <select
              onChange={(event) => update('employment_status', event.target.value)}
              value={candidate.employment_status}
            >
              <option value="school_student">School student</option>
              <option value="college_student">College / university student</option>
              <option value="recent_graduate">Recent graduate</option>
              <option value="employed">Currently working</option>
              <option value="unemployed">Currently not working</option>
              <option value="career_changer">Changing careers</option>
              <option value="other">Other</option>
            </select>
          </label>
          <div className="onboarding-field-grid">
            <label>
              Education level <span className="resume-optional-label">· optional</span>
              <select onChange={(event) => update('education_level', event.target.value)} value={candidate.education_level}>
                <option value="">Choose level</option>
                <option>High school</option>
                <option>Diploma</option>
                <option>Bachelor’s degree</option>
                <option>Master’s degree</option>
                <option>Doctorate</option>
                <option>Other</option>
              </select>
            </label>
            <label>
              School / college <span className="resume-optional-label">· optional</span>
              <input maxLength={160} onChange={(event) => update('institution', event.target.value)} value={candidate.institution} />
            </label>
            <label>
              Field of study <span className="resume-optional-label">· optional</span>
              <input maxLength={120} onChange={(event) => update('field_of_study', event.target.value)} value={candidate.field_of_study} />
            </label>
            <label>
              Current / most recent role <span className="resume-optional-label">· optional</span>
              <input maxLength={120} onChange={(event) => update('current_role', event.target.value)} value={candidate.current_role} />
            </label>
            <label>
              Years of experience <span className="resume-optional-label">· optional</span>
              <input
                max={60}
                min={0}
                onChange={(event) => update('years_of_experience', event.target.value)}
                step="0.5"
                type="number"
                value={candidate.years_of_experience}
              />
            </label>
          </div>
          <div className="onboarding-section-heading">
            <GraduationCap aria-hidden="true" size={19} />
            <h2>What do you want to practice?</h2>
          </div>
          <TargetRoleField onChange={setRole} required value={role} />
          <label>
            Specialization <span className="resume-optional-label">· optional</span>
            <input maxLength={120} onChange={(event) => setSubRole(event.target.value)} placeholder="For example: Backend, data, product design" value={subRole} />
          </label>
          <fieldset className="onboarding-plan-picker">
            <legend>Choose how to start</legend>
            <label className={accessPlan === 'free' ? 'selected' : ''}>
              <input checked={accessPlan === 'free'} name="access-plan" onChange={() => setAccessPlan('free')} type="radio" />
              <span><strong>Free practice</strong><small>3 interviews and 1 resume analysis per month with basic feedback.</small></span>
            </label>
            <label className={accessPlan === 'pro' ? 'selected' : ''}>
              <input checked={accessPlan === 'pro'} name="access-plan" onChange={() => setAccessPlan('pro')} type="radio" />
              <span><strong>Pro · ₹299 / month</strong><small>20 interviews, detailed feedback, 5 resume analyses, and 30 company-specific questions monthly.</small></span>
            </label>
            <label className={accessPlan === 'elite' ? 'selected' : ''}>
              <input checked={accessPlan === 'elite'} name="access-plan" onChange={() => setAccessPlan('elite')} type="radio" />
              <span><strong>Elite · ₹599 / month</strong><small>Unlimited interviews, resume analyses, and company-specific questions, plus a learning roadmap.</small></span>
            </label>
          </fieldset>
          {error && <p className="notice error" role="alert">{error}</p>}
          <div className="onboarding-footer">
            <p className="fine-print"><BriefcaseBusiness aria-hidden="true" size={14} /> Your details personalize mock interviews only.</p>
            <button className="button primary" type="submit">Continue to sign up <ArrowRight aria-hidden="true" size={16} /></button>
          </div>
        </form>
      </section>
    </main>
  )
}
